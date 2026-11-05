"""
Schedule loading, validation, epoch-based run splitting, and jitter attachment.

The CSV is the single source of truth and is never modified. Heavy validation is delegated to the
repository's validate_schedule.py (the same checks the CI-style test suite runs), so the app and
the standalone validator can never drift apart.
"""

import csv
import importlib.util
import sys
from pathlib import Path

import config as cfg
from iti import gaps_for_block, start_gaps_for_block


class ScheduleError(Exception):
    """Schedule missing or inconsistent. Always fatal before the session starts."""


def _load_validator():
    path = cfg.REPO_ROOT / "validate_schedule.py"
    spec = importlib.util.spec_from_file_location("validate_schedule", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("validate_schedule", module)
    spec.loader.exec_module(module)
    return module


def schedule_path(schedule_number):
    return cfg.SCHEDULE_DIR / cfg.SCHEDULE_PATTERN.format(schedule_number)


def _split(field):
    return field.split("|") if field else []


def parse_row(raw):
    """One schedule row -> the trial dict the engine consumes. `raw` is carried through to logs."""
    kind = raw["kind"]
    probe_type = raw["probe_type"]
    probe_direction = raw["probe_direction"]

    trial = {
        "raw": raw,
        "trial": int(raw["trial"]),
        "block": int(raw["block"]),
        "kind": kind,
        "event_type": cfg.KIND_EVENT_TYPE[kind],
        "break_20s": raw["break_20s"] == "1",
        "probe": raw["probe"] == "1",
        "walk_cells": _split(raw["walk_cells"]),
        "walk_videos": _split(raw["walk_videos"]),
        "shown_cells": _split(raw["shown_cells"]),
        "shown_videos": _split(raw["shown_videos"]),
        "hidden_videos": _split(raw["hidden_videos"]),
        "terminal_amount": int(raw["terminal_amount"]) if raw["terminal_amount"] else None,
        "terminal_image": raw["terminal_image"] or None,
        "probe_type": probe_type,
        "probe_subtype": raw["probe_subtype"],
        # logged verbatim, NEVER displayed and never parsed (spec section 2)
        "probe_question": raw["probe_question"],
        "probe_direction": probe_direction,
        "probe_options": _split(raw["probe_options"]),
        "probe_correct_video": raw["probe_correct_video"],
        "probe_correct_index": int(raw["probe_correct_index"]) if raw["probe_correct_index"] else None,
        # the cue still shown on structure probes, straight from its own column; blank on value
        # probes, which show options only.
        "probe_cue": raw["probe_cue_video"] or None,
    }

    if trial["probe"]:
        if probe_direction not in cfg.PROBE_DIRECTIONS:
            raise ScheduleError(
                f"trial {trial['trial']}: probe_direction '{probe_direction}' is not one of "
                f"{list(cfg.PROBE_DIRECTIONS)}")
        if probe_direction == "preference":
            if trial["probe_cue"] is not None:
                raise ScheduleError(
                    f"trial {trial['trial']}: value probe must have a blank probe_cue_video")
        elif trial["probe_cue"] is None:
            raise ScheduleError(
                f"trial {trial['trial']}: {probe_direction} probe has no probe_cue_video")

    return trial


def n_events(trial):
    """Shown events per trial = ISIs per trial: its clips plus the outcome if it has one. Every
       kind is the same sequential walk; since 2026-10-05 a value change gives 1 (the outcome
       alone), a structure change 2 (its two clips, no outcome), and a full walk route length + 1."""
    return len(trial["shown_videos"]) + (1 if trial["terminal_amount"] is not None else 0)


def ends_on_outcome(trial):
    """True for every trial that ends on an outcome screen: all but the pair format since
       2026-10-05. Gates
       the optional pre-outcome placement of the longest gap (LONGEST_GAP_BEFORE_OUTCOME)."""
    return trial["terminal_amount"] is not None


def group_into_runs(trials):
    """
    Group trials into runs by the schedule's own `block` column (the schedule states the split; the
    presentation code never recomputes it). Blocks are contiguous and non-decreasing, which
    validate_schedule.py has already asserted by the time this runs. Returns [(block, trials), ...].
    """
    runs = []
    for trial in trials:
        block = trial["block"]
        if not runs or runs[-1][0] != block:
            runs.append((block, []))
        runs[-1][1].append(trial)
    return runs


def load_schedule(schedule_number, validate=True):
    """
    Load, validate, split into runs and attach jitter. Returns a list of
    {'run': int, 'trials': [trial, ...]} with trial['gaps'] filled in.
    """
    path = schedule_path(schedule_number)
    if not path.exists():
        raise ScheduleError(f"Schedule not found: {path}")

    if validate:
        validator = _load_validator()
        errors = validator.validate_file(Path(path), manifest=None)
        if errors:
            raise ScheduleError(f"{path.name} failed validation:\n"
                                + "\n".join(f"  - {e}" for e in errors[:20]))

    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    trials = [parse_row(r) for r in rows]

    # N varies per participant and is read from the file; only implausible counts abort.
    lo, hi = cfg.EXPECTED_N_TRIALS_RANGE
    if not lo <= len(trials) <= hi:
        raise ScheduleError(f"{path.name}: {len(trials)} trials, outside the plausible "
                            f"range {lo}-{hi}")
    # Counts are taken from the file, not asserted against a remembered number; only a file with
    # no rests or no probes at all is treated as broken.
    n_breaks = sum(t["break_20s"] for t in trials)
    n_probes = sum(t["probe"] for t in trials)
    if not 0 < n_breaks <= len(trials):
        raise ScheduleError(f"{path.name}: {n_breaks} rests in {len(trials)} trials")
    if not 0 < n_probes <= len(trials):
        raise ScheduleError(f"{path.name}: {n_probes} probes in {len(trials)} trials")

    run_lists = group_into_runs(trials)
    if len(run_lists) != cfg.N_RUNS:
        raise ScheduleError(f"{path.name}: {len(run_lists)} blocks, expected {cfg.N_RUNS}")

    runs = []
    stored = all(c in rows[0] for c in ITI_COLUMNS)
    if not stored and cfg.SESSION_SET:
        raise ScheduleError(f"{path.name}: no precomputed ITIs ({', '.join(ITI_COLUMNS)}); "
                            "run make_itis.py. Jitter is never drawn at run time for a session set.")
    for block, run_trials in run_lists:      # the run number IS the schedule's block number
        if stored:                           # read, never drawn (make_itis.py, 2026-11-05)
            for trial in run_trials:
                trial["start_gap"], trial["gaps"] = stored_itis(trial["raw"], n_events(trial),
                                                                f"{path.name} trial {trial['trial']}")
        else:                                # the Prolific set only (collected before 2026-11-05)
            counts = [n_events(t) for t in run_trials]
            flags = [ends_on_outcome(t) for t in run_trials]
            gaps = gaps_for_block(schedule_number, block, counts, flags, cfg)
            starts = start_gaps_for_block(schedule_number, block, len(run_trials), cfg)
            for trial, trial_gaps, start in zip(run_trials, gaps, starts):
                trial["gaps"] = trial_gaps
                trial["start_gap"] = start
        runs.append({"run": block, "trials": run_trials})
    return runs


# Precomputed jitter (2026-11-05, user): make_itis.py draws every fixation with the lab's makeITI,
# per trial, and stores it in the session schedules; the task only reads it. iti_start opens the
# trial, iti_k follows its k-th shown event (clip or outcome).
# Gaps lie only BETWEEN a trial's events (2026-11-05): n events, n - 1 gaps (iti_1..iti_3).
ITI_COLUMNS = ["iti_start", "iti_1", "iti_2", "iti_3"]


def stored_itis(raw, n, where):
    """(start, [gap after event 1..n-1]) from a schedule row; an error if any is missing."""
    m = max(n - 1, 0)
    try:
        start = float(raw["iti_start"])
        gaps = [float(raw[f"iti_{k}"]) for k in range(1, m + 1)]
    except (KeyError, ValueError) as exc:
        raise ScheduleError(f"{where}: precomputed ITIs missing or unreadable ({exc})")
    if any(raw.get(f"iti_{k}", "") not in ("", None) for k in range(m + 1, len(ITI_COLUMNS))):
        raise ScheduleError(f"{where}: more ITIs than the {m} gaps between its {n} events")
    return start, gaps


def load_intro_itis():
    """<schedule dir>/intro_itis.json (make_itis.py) or None for the Prolific set."""
    import json
    path = Path(cfg.SCHEDULE_DIR) / "intro_itis.json"
    if not path.exists():
        if cfg.SESSION_SET:
            raise ScheduleError(f"{path} is missing: run make_itis.py")
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["schedules"]


def trial_duration(trial, is_practice=False):
    """Planned duration at full probe cap, for the timing report."""
    stim = (len(trial["shown_videos"]) * cfg.T_VIDEO
            + (cfg.T_OUTCOME if trial["terminal_amount"] is not None else 0.0))
    dur = stim + sum(trial["gaps"]) + trial.get("start_gap", 0.0)
    if trial["break_20s"]:
        dur += cfg.T_REST_PRACTICE if is_practice else cfg.T_REST
    if trial["probe"]:
        dur += cfg.T_PROBE
        # the feedback screen after a response, when it is switched on for this block
        if cfg.PRACTICE_FEEDBACK if is_practice else cfg.MAIN_TASK_FEEDBACK:
            dur += cfg.T_FEEDBACK
    return dur


def run_duration(trials, dry_run=False, is_practice=False, lead_in=False):
    """Planned block duration. `lead_in` charges the fixation held between the block trigger and
       the first trial; the intro blocks have no trigger and so no lead-in."""
    total = sum(trial_duration(t, is_practice) for t in trials)
    if lead_in:                                  # a main block: lead-in and lead-out
        total += cfg.T_BLOCK_LEAD_IN + getattr(cfg, "T_BLOCK_LEAD_OUT", 0.0)
    return total * (cfg.DRY_RUN_SCALE if dry_run else 1.0)
