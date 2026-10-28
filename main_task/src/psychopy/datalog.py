"""
Crash-safe output: ONE file per subject (decided 2026-09-10).

`sub-<code>_task-gridvalstruct_<stamp>[_dryrun].tsv` holds everything: a few `meta` rows at the
top (the session facts that never change), then one row per screen change for the whole session
in time order, with the answer on the `response` rows, and `session_end` rows at the bottom. It
is opened once and flushed after every write, so a session that dies mid-run still leaves
everything up to the last completed screen change on disk. Nothing is ever overwritten: filenames
carry a session timestamp.

Column names and order match ../jspsych/experiment.js exactly, so the offline and online arms pool
directly; tests/check_columns.py asserts it. OUTPUT_FILES.md explains every column and row kind.
"""

import csv
import json
from datetime import datetime

import config as cfg

# The schedule columns carried onto every event row: a LEAN set. Everything else in a schedule row
# is either constant per participant (the layout A1..C4 and the reward images, written once as
# `meta` rows) or derivable from these on the row; OUTPUT_FILES.md gives the derivation of every
# dropped column. The schedule CSV named in the meta rows stays the source of truth and joins back
# by `trial`.
KEPT_SCHEDULE_COLUMNS = [
    "kind", "probe_slot",
    "winner_column", "untouched_column", "swap_step", "counterfactual_route",
    "shown_videos", "hidden_videos",
    "route_A_videos", "route_B_videos", "route_C_videos", "reactivation_targets",
    "probe_type", "probe_subtype", "probe_options", "probe_correct_video", "probe_cue_video",
]
# constant per participant: written once as meta rows, never on an event row
META_SCHEDULE_COLUMNS = list(cfg.CELLS) + ["reward_image_A", "reward_image_B", "reward_image_C"]

# One row per SCREEN CHANGE (plus the meta and session_end rows). `onset` is relative to the block
# clock (the scanner trigger in fMRI mode); block_start sits at 0.0000 by definition and carries
# the wall-clock time in `stimulus`. `trial_type` is the spec's modelable event type (establish /
# value_change / structure_change / value_control / structure_control / tracking), the intro phase
# (practice / familiarization / gate / overview) or `session` on the meta rows.
EVENT_BASE_COLUMNS = ["subj_id", "block", "trial", "onset", "duration", "event", "trial_type",
                      "stimulus", "response", "rt", "correct"]
EVENTS_COLUMNS = EVENT_BASE_COLUMNS + KEPT_SCHEDULE_COLUMNS
COLUMNS = EVENTS_COLUMNS


def rebuild_columns():
    """Recompute the per-participant column list after config.apply_steps() chose a variant."""
    g = globals()
    g["META_SCHEDULE_COLUMNS"] = list(cfg.CELLS) + [f"reward_image_{c}" for c in "ABC"]
    return g["EVENTS_COLUMNS"]


EVENT_NAMES = (
    "meta",                     # session facts, one key=value per row, at the top of the file
    "block_start",              # onset 0 of a block; stimulus = wall-clock time
    "clip1", "clip2", "clip3", "clip4",
    "outcome",                  # reward image + amount on full-walk trials
    "fixation_start",           # the fixation that opens every trial; stimulus = the scheduled draw
    "fixation_gap",             # every jittered gap inside a trial; stimulus = the scheduled draw
    "block_lead_in",            # fixation between the block trigger and the block's first trial
    "rest_readout",             # the replay readout window (additive, after the last gap)
    "probe",
    "response",                 # instantaneous: the moment an option key was pressed
    "no_response",              # instantaneous: probe window elapsed with no press
    "feedback",                 # after a probe response (main task only while piloting)
    "practice_note",            # practice: the self-paced screen explaining a change
    "lab_refresher",            # a lab session's refresher screen (2026-10-26); response = key
    "button_check",             # a lab session's button check screen; response = the button pressed
    "practice_map",             # practice: both rewired journeys drawn on one screen
    "structure_overview",       # intro end: the whole starting state on one screen
    "break_overview",           # every break between blocks: the current state (2026-10-01)
    "block_end",                # stimulus = dropped_frames=N for the block
    "session_end",              # gate outcome and finish time, at the bottom of the file
)

NA = "n/a"


def wallclock():
    """ISO wall-clock time with milliseconds, carried in the stimulus field of every block_start
       event so blocks can be placed in absolute time and the unlogged breaks between them measured."""
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def flatten(value):
    """A meta value as one cell: dicts and lists become `a=b|c=d` / `a|b`, scalars as is."""
    if isinstance(value, dict):
        return "|".join(f"{k}={flatten(v)}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return "|".join(str(flatten(v)) for v in value)
    if value is None:
        return NA
    return str(value)


class DataLogger:
    def __init__(self, participant, schedule_number, modality, language, dry_run=False):
        cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.participant = participant
        self.schedule_number = schedule_number
        self.modality = modality
        self.language = language
        self.stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        suffix = "_dryrun" if dry_run else ""
        self.path = cfg.DATA_DIR / f"sub-{participant}_task-{cfg.TASK_NAME}_{self.stamp}{suffix}.tsv"
        self._fh = open(self.path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._fh, fieldnames=EVENTS_COLUMNS, delimiter="\t",
                                      restval=NA, extrasaction="ignore")
        self._writer.writeheader()
        self._fh.flush()
        self._block = 0

    # -- blocks ---------------------------------------------------------------------------

    def open_block(self, label, block=0):
        """Start a block. `label` is only echoed to the console; `block` is what the block column
           carries on rows without a schedule row (the run number in the main task, the attempt in
           familiarization and the gate, 0 elsewhere). Returns the one output path."""
        self._block = block
        self._label = label
        return self.path

    def close_run(self):
        self._fh.flush()

    # -- rows -----------------------------------------------------------------------------

    def _write(self, row):
        self._writer.writerow(row)
        self._fh.flush()

    def write_event(self, onset, duration, event, trial=NA, trial_type=NA,
                    stimulus=NA, response=NA, rt=NA, correct=NA, design=None):
        """
        Append one screen-change row; `onset` must already be relative to the block clock.
        `design` is the trial's schedule row; the kept columns are copied onto the row.
        """
        if event not in EVENT_NAMES:
            raise ValueError(f"Unknown event name '{event}'. Add it to datalog.EVENT_NAMES.")
        design = design or {}
        row = {
            "subj_id": self.participant,
            "block": design.get("block") or self._block,
            "trial": trial,
            "onset": f"{onset:.4f}",
            "duration": f"{duration:.4f}",
            "event": event,
            "trial_type": trial_type,
            "stimulus": stimulus,
            "response": response,
            "rt": rt if rt == NA else f"{rt:.4f}",
            "correct": correct,
        }
        for column in KEPT_SCHEDULE_COLUMNS:
            value = design.get(column, "")
            row[column] = value if value not in ("", None) else NA
        self._write(row)

    def write_meta(self, meta):
        """The session facts as `meta` rows, one `key=value` per row, at the top of the file."""
        for key, value in meta.items():
            self._write({"subj_id": self.participant, "block": 0, "event": "meta",
                         "trial_type": "session", "stimulus": f"{key}={flatten(value)}"})

    def write_session_end(self, info):
        """Whatever is only known at the end (gate outcome, finish time), as `session_end` rows."""
        for key, value in info.items():
            self._write({"subj_id": self.participant, "block": 0, "event": "session_end",
                         "trial_type": "session", "stimulus": f"{key}={flatten(value)}"})

    def close(self):
        if not self._fh.closed:
            self._fh.close()


def next_free_schedule_number(max_number=100):
    """Lowest schedule number with no non-dry-run data yet, read from the meta rows of the
       existing session files."""
    used = set()
    for path in cfg.DATA_DIR.glob(f"sub-*_task-{cfg.TASK_NAME}_*.tsv"):
        if path.name.endswith("_dryrun.tsv"):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                for row in reader:
                    if row.get("event") != "meta":
                        break
                    if row.get("stimulus", "").startswith("schedule="):
                        used.add(int(row["stimulus"].split("=", 1)[1]))
                        break
        except (OSError, ValueError, KeyError):
            continue
    for n in range(1, max_number + 1):
        if n not in used:
            return n
    return 1
