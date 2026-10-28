"""
Familiarization block and mastery gate, both derived from the schedule's FIRST ROW ground truth.

Familiarization: the three real journeys, each walked in full with its reward image and current
amount, over FAMILIARIZATION_PASSES passes. The worth-100 journey is FIXED at the schedule's actual
starting winner in every pass, so the participant learns ONE stable 100 journey and the block ends
in exactly the state trial 1 begins in. The graph is the identity map at session start, so each
journey is simply its own column -- nothing false is taught.

Gate: same-sequence and preference questions about that same starting state, all-correct to pass.
Everything is deterministic from (schedule_number), so it is reproducible and identical across
the two arms (mirrored by ../jspsych/familiarization.js).
"""

import config as cfg
from iti import Mulberry32, hash32

COLUMNS = ("A", "B", "C")


def _seeded_shuffle(items, seed):
    """Fisher-Yates with Mulberry32, identical in both arms."""
    rng = Mulberry32(seed)
    out = list(items)
    for i in range(len(out) - 1, 0, -1):
        j = int(rng.random() * (i + 1))
        out[i], out[j] = out[j], out[i]
    return out


def _identity_route(first_row, column):
    cells = [f"{column}{step}" for step in range(1, cfg.N_STEPS + 1)]
    return cells, [first_row[c] for c in cells]


def pass_winners(first_row):
    """
    The worth-100 journey for each pass. It does NOT move: every pass uses the schedule's actual
    starting winner, so familiarization teaches one stable 100 journey and leaves the participant
    in exactly the worth state trial 1 begins in. The winner moving is what the main task's value
    changes are for; teaching it here would only blur the first change.
    """
    return [first_row["winner_column"]] * cfg.FAMILIARIZATION_PASSES


def build_structure_overview(first_row):
    """
    The last intro screen: the whole STARTING state on one screen. One row per journey, in
    column order, each from start to finish with the treasure it ends at and the points it is
    worth, all read from the schedule's first row (the identity graph and the starting worth).
    Shown once, before the main task, with the message that from here on it keeps changing.
    """
    rows = []
    for column in COLUMNS:
        path = first_row[f"route_{column}_path"].split("|")
        videos = first_row[f"route_{column}_videos"].split("|")
        terminal_column = path[-1][0]
        rows.append({"label": None, "stimuli": videos,
                     "reward": first_row[f"reward_image_{terminal_column}"],
                     "amount": int(first_row[f"worth_{column}"])})
    return {"caption": "structure_overview", "rows": rows}


def build_state_overview(row, caption="break_overview"):
    """
    The overview in every break between blocks (2026-10-01): the CURRENT state, as it stands
    after the block's last trial, read from that trial's row exactly like the starting overview
    reads the first row. Mirrors buildStateOverview in ../jspsych/familiarization.js.
    """
    return {**build_structure_overview(row), "caption": caption}


def validate_state_overview(overview, row):
    """The break overview must show the row's own journeys, treasures and points."""
    problems = []
    if len(overview["rows"]) != len(COLUMNS):
        problems.append(f"overview has {len(overview['rows'])} rows")
    for column, r in zip(COLUMNS, overview["rows"]):
        if "|".join(r["stimuli"]) != row[f"route_{column}_videos"]:
            problems.append(f"overview row {column} is not the current journey "
                            f"{row[f'route_{column}_videos']}")
        terminal = row[f"route_{column}_path"].split("|")[-1][0]
        if r["reward"] != row[f"reward_image_{terminal}"]:
            problems.append(f"overview row {column} shows the wrong treasure {r['reward']}")
        if r["amount"] != (100 if column == row["winner_column"] else 50):
            problems.append(f"overview row {column} shows {r['amount']} points")
    return problems


def validate_structure_overview(overview, first_row):
    problems = []
    rows = overview["rows"]
    if len(rows) != len(COLUMNS):
        problems.append(f"overview has {len(rows)} rows, expected {len(COLUMNS)}")
    for column, row in zip(COLUMNS, rows):
        cells, videos = _identity_route(first_row, column)
        if row["stimuli"] != videos:
            problems.append(f"overview row {column} is not the starting journey {videos}")
        if row["reward"] != first_row[f"reward_image_{column}"]:
            problems.append(f"overview row {column} shows the wrong treasure {row['reward']}")
        want = 100 if column == first_row["winner_column"] else 50
        if row["amount"] != want:
            problems.append(f"overview row {column} shows {row['amount']} points, expected {want}")
    return problems


def build_familiarization_trials(schedule_number, first_row):
    """Full walks only: no rest, no probe, no changes. Trial numbers are block-local."""
    winners = pass_winners(first_row)
    trials = []
    number = 0
    previous_route = None
    for pass_index, winner in enumerate(winners, start=1):
        order = _seeded_shuffle(COLUMNS, hash32(schedule_number, 9, pass_index))
        if order[0] == previous_route:
            order[0], order[1] = order[1], order[0]
        for column in order:
            number += 1
            cells, videos = _identity_route(first_row, column)
            amount = 100 if column == winner else 50
            trials.append({
                "raw": {"trial": number, "kind": "T", "event": "familiarization",
                        "walk_cells": "|".join(cells), "walk_videos": "|".join(videos),
                        "shown_videos": "|".join(videos), "break_20s": "0", "probe": "0",
                        "winner_column": winner, "terminal_amount": str(amount),
                        "terminal_image": first_row[f"reward_image_{column}"]},
                "trial": number,
                "kind": "T",
                "event_type": "familiarization",
                "break_20s": False,
                "probe": False,
                "shown_videos": videos,
                "hidden_videos": [],
                "terminal_amount": amount,
                "terminal_image": first_row[f"reward_image_{column}"],
                "probe_type": "", "probe_subtype": "", "probe_question": "",
                "probe_options": [], "probe_correct_video": "", "probe_correct_index": None,
                "probe_cue": None, "probe_direction": "",
            })
            previous_route = column
    return trials


def validate_familiarization(trials, first_row):
    problems = []
    expected = cfg.FAMILIARIZATION_PASSES * 3
    if len(trials) != expected:
        problems.append(f"{len(trials)} trials, expected {expected}")
    for a, b in zip(trials, trials[1:]):
        if a["shown_videos"] == b["shown_videos"]:
            problems.append(f"trials {a['trial']} and {b['trial']} repeat the same journey")
    # the 100 journey is fixed at the schedule's starting winner, in EVERY pass
    winner = first_row["winner_column"]
    for t in trials:
        column = t["raw"]["walk_cells"][0][0]
        expect = 100 if column == winner else 50
        if t["terminal_amount"] != expect:
            problems.append(
                f"trial {t['trial']}: amount {t['terminal_amount']}, expected "
                f"{expect} (schedule starting winner {winner})")
    # every journey must be walked, with its own reward image, at least once
    seen = {t["raw"]["walk_cells"][0][0] for t in trials}
    if seen != set(COLUMNS):
        problems.append(f"familiarization walks {sorted(seen)}, not all three journeys")
    for t in trials:
        column = t["raw"]["walk_cells"][0][0]
        if t["terminal_image"] != first_row[f"reward_image_{column}"]:
            problems.append(f"trial {t['trial']}: reward image {t['terminal_image']} is not "
                            f"journey {column}'s")
    return problems


def _gate_probe(number, probe_type, direction, question, cue, options, correct):
    return {
        "trial": number,
        "kind": "gate",
        "event_type": "gate",
        "probe": True,
        "probe_type": probe_type,
        "probe_subtype": "",
        "probe_question": question,
        "probe_direction": direction,
        "probe_options": options,
        "probe_correct_video": correct,
        "probe_correct_index": options.index(correct) + 1,
        "probe_cue": cue,
        "auto_correct_in_dry_run": True,
        "raw": {"trial": number, "kind": "gate", "event": "gate",
                "probe": "1", "break_20s": "0",
                "probe_type": probe_type, "probe_options": "|".join(options),
                "probe_correct_video": correct, "probe_question": question,
                "probe_direction": direction, "probe_cue_video": cue or ""},
    }


def build_gate_probes(schedule_number, first_row):
    """
    GATE_N_STRUCTURE same-sequence questions (one per journey, seeded step, one option per route) and
    GATE_N_VALUE preference questions (the three same-step clips, correct = the winner journey's).
    All answers derive from the identity graph and the starting worths of trial 1.
    """
    probes = []
    number = 0

    route_order = _seeded_shuffle(COLUMNS, hash32(schedule_number, 13, 1))
    for i, column in enumerate(route_order[:cfg.GATE_N_STRUCTURE]):
        step = 1 + hash32(schedule_number, 17, i) % (cfg.N_STEPS - 1)   # cue step, answer step+1
        cue = first_row[f"{column}{step}"]
        correct = first_row[f"{column}{step + 1}"]
        foils = [first_row[f"{other}{step + 1}"] for other in COLUMNS if other != column]
        options = _seeded_shuffle([correct] + foils, hash32(schedule_number, 19, i))
        number += 1
        probes.append(_gate_probe(number, "structure_observed", "same_sequence",
                                  "gate same-sequence question", cue, options, correct))

    winner = first_row["winner_column"]
    for i in range(cfg.GATE_N_VALUE):
        step = 1 + hash32(schedule_number, 23, i) % cfg.N_STEPS         # any step
        options = _seeded_shuffle([first_row[f"{c}{step}"] for c in COLUMNS],
                                  hash32(schedule_number, 29, i))
        correct = first_row[f"{winner}{step}"]
        number += 1
        probes.append(_gate_probe(number, "value_observed", "preference",
                                  "gate preference question", None, options, correct))

    return probes


def validate_gate(probes, first_row):
    problems = []
    cell_of = {first_row[f"{c}{s}"]: (c, s) for c in COLUMNS for s in range(1, cfg.N_STEPS + 1)}
    winner = first_row["winner_column"]
    for p in probes:
        opts = p["probe_options"]
        if len(opts) != 3 or len(set(opts)) != 3:
            problems.append(f"gate {p['trial']}: bad options {opts}")
            continue
        if opts[p["probe_correct_index"] - 1] != p["probe_correct_video"]:
            problems.append(f"gate {p['trial']}: correct index mismatch")
        if p["probe_type"] == "structure_observed":
            cue_col, cue_step = cell_of[p["probe_cue"]]
            matches = [o for o in opts if cell_of[o] == (cue_col, cue_step + 1)]
            if matches != [p["probe_correct_video"]]:
                problems.append(f"gate {p['trial']}: same-sequence answer inconsistent")
            if p["probe_cue"] in opts:
                problems.append(f"gate {p['trial']}: cue among its own options")
        else:
            winners = [o for o in opts if cell_of[o][0] == winner]
            if winners != [p["probe_correct_video"]]:
                problems.append(f"gate {p['trial']}: preference answer inconsistent")
    return problems
