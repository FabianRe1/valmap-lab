#!/usr/bin/env python3
"""
Schedule and asset validation (experiment_spec.md section 9).

Updated 2026-09-23 for the sequential partial format: every trial plays its shown clips and ends on
an outcome, and how much it shows is fixed by its kind (full walk: EST, T; ONE clip of the 100 route
plus 100: V, CV, TV; ONE transition of a 50 route plus 50: S, CS, TS). The controls replace one
cluster walk each, so the post-change cluster check now asks for full walks.

Updated 2026-09-07 for the regenerated schedules: the reward image is tied to the TERMINAL grid column
(not the walked route), the probe cue and prompt form come from the explicit probe_cue_video and
probe_direction columns, tracking/establish rows carry no rest or probe (except the rested,
probed follow-up right after a change, since 2026-09-23), and every change is followed by at least three
stable trials that walk all three current routes before the next change. A `block` column, when present, must be contiguous
and may only change immediately before a change trial of either kind.

Validates one or more pre-generated schedule CSVs against the invariants the presentation code
relies on, and (optionally) checks that every referenced asset resolves through the manifest.
Never modifies anything. Exit code 0 = all files pass.

Usage:
  python validate_schedule.py schedules_grid/sub-001_schedule.csv
  python validate_schedule.py --all                       # every CSV in schedules_grid/
  python validate_schedule.py --all --manifest stimuli/manifest.json
"""

import argparse
import csv
import os
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
# the step count is read from each file's header; both the 3-step and 4-step designs pass
def cells_for(nrow):
    return [f"{col}{step}" for col in "ABC" for step in range(1, nrow + 1)]


CELLS = cells_for(4)
CHANGE_KINDS = {"V", "S"}
STABLE_KINDS = {"EST", "CV", "CS", "T", "TV", "TS"}
ALL_KINDS = CHANGE_KINDS | STABLE_KINDS
# what each kind shows: the whole route, one clip (and then 100), or one transition (and then 50)
FULL_KINDS = {"EST", "T"}
SINGLE_KINDS = {"V", "CV", "TV"}
PAIR_KINDS = {"S", "CS", "TS"}
PROBE_DIRECTIONS = {"preference", "same_sequence"}


def split(field):
    return field.split("|") if field else []


def is_subsequence(sub, seq):
    it = iter(seq)
    return all(x in it for x in sub)


class RowChecker:
    def __init__(self, filename, nrow=4):
        self.filename = filename
        self.nrow = nrow
        self.cells = cells_for(nrow)
        self.errors = []

    def check(self, cond, trial, message):
        if not cond:
            self.errors.append(f"{self.filename} trial {trial}: {message}")

    def validate_row(self, r):
        t = r["trial"]
        kind = r["kind"]
        self.check(kind in ALL_KINDS, t, f"unknown kind '{kind}'")

        walk_cells = split(r["walk_cells"])
        walk_videos = split(r["walk_videos"])
        shown_cells = split(r["shown_cells"])
        shown_videos = split(r["shown_videos"])
        hidden_cells = split(r["hidden_cells"])
        hidden_videos = split(r["hidden_videos"])

        self.check(len(walk_cells) == self.nrow, t,
                   f"walk_cells has {len(walk_cells)} entries, expected {self.nrow}")
        self.check(len(walk_cells) == len(walk_videos), t, "walk_cells / walk_videos length mismatch")
        self.check(len(shown_cells) == len(shown_videos), t, "shown_cells / shown_videos length mismatch")

        cell_map = {cell: r[cell] for cell in self.cells}
        # one category per step (2026-09-29): the ids are <category>_<n>, and the three cells of
        # a step hold three different exemplars of the same category
        for step in range(1, self.nrow + 1):
            ids = [cell_map[f"{c}{step}"] for c in "ABC"]
            cats = {i.rsplit("_", 1)[0] for i in ids}
            self.check(len(cats) == 1 and len(set(ids)) == 3, t,
                       f"step {step} does not hold three exemplars of one category: {ids}")
        for cells, videos, name in [(walk_cells, walk_videos, "walk"),
                                    (shown_cells, shown_videos, "shown"),
                                    (hidden_cells, hidden_videos, "hidden")]:
            for c, v in zip(cells, videos):
                self.check(cell_map.get(c) == v, t, f"{name}: cell {c} maps to {cell_map.get(c)}, row says {v}")

        # shown is an in-order subset of walk; hidden is walk minus shown, order preserved
        self.check(is_subsequence(shown_cells, walk_cells), t, "shown_cells is not an in-order subset of walk_cells")
        expect_hidden = [c for c in walk_cells if c not in shown_cells]
        self.check(hidden_cells == expect_hidden, t,
                   f"hidden_cells {hidden_cells} != walk minus shown {expect_hidden}")

        # every trial is a sequential walk; the kind fixes how much of the route is shown and
        # whether it ends on an outcome. Since 2026-10-05 the single format (V, CV, TV) shows NO
        # cell and only the outcome, V and CV "100", TV the walked route's own worth; the pair
        # format (S, CS, TS) shows its two cells and NO outcome. Full walks end on an outcome.
        amount = r["terminal_amount"]
        if kind in PAIR_KINDS:
            self.check(amount == "" and r["terminal_image"] == "", t,
                       f"{kind} row has an outcome ({amount} {r['terminal_image']}), expected none")
        else:
            self.check(amount != "" and r["terminal_image"] != "", t, f"{kind} row has no outcome")
        if kind in FULL_KINDS:
            self.check(shown_cells == walk_cells, t, f"{kind} row hides cells: {hidden_cells}")
        elif kind in SINGLE_KINDS:
            self.check(len(shown_cells) == 0, t,
                       f"{kind} shows {len(shown_cells)} cells, expected none")
            if kind in ("V", "CV"):
                self.check(amount == "100", t, f"{kind} terminal_amount is '{amount}', expected 100")
        elif kind in PAIR_KINDS:
            self.check(len(shown_cells) == 2, t, f"{kind} shows {len(shown_cells)} cells, expected 2")
            idx = [walk_cells.index(c) for c in shown_cells if c in walk_cells]
            self.check(len(idx) == 2 and idx[1] == idx[0] + 1, t,
                       f"{kind} shown cells {shown_cells} are not consecutive walk steps")

        # graph snapshot: routes partition the 12 cells, starts fixed, walk taken from snapshot
        paths = {route: split(r[f"route_{route}_path"]) for route in "ABC"}
        union = [c for p in paths.values() for c in p]
        self.check(sorted(union) == sorted(self.cells), t,
                   f"route paths do not partition the {len(self.cells)} cells")
        for route in "ABC":
            self.check(paths[route] and paths[route][0] == f"{route}1", t,
                       f"route {route} starts at {paths[route][:1]}, expected {route}1")
            # route_X_videos is the same route said in clips: it must be exactly the clips sitting
            # in route_X_path, in step order, read off this row's own cell columns
            expect = [r[c] for c in paths[route]]
            self.check(split(r[f"route_{route}_videos"]) == expect, t,
                       f"route_{route}_videos {r[f'route_{route}_videos']} does not match "
                       f"route_{route}_path {r[f'route_{route}_path']}")

        if walk_cells:
            walked_route = walk_cells[0][0]
            self.check(walk_cells == paths.get(walked_route), t,
                       f"walk_cells != route_{walked_route}_path snapshot")

        worths = {route: r[f"worth_{route}"] for route in "ABC"}
        self.check(sorted(worths.values()) == ["100", "50", "50"], t, f"worths are {worths}, expected one 100 and two 50s")
        winner = r["winner_column"]
        self.check(worths.get(winner) == "100", t, f"winner_column {winner} has worth {worths.get(winner)}")

        if kind == "S":
            for role in ("observed_route", "counterfactual_route"):
                route = r[role]
                self.check(worths.get(route) == "50", t,
                           f"structure change {role} {route} has worth {worths.get(route)}, must be 50")

        # outcome consistency: the IMAGE belongs to the grid column the route currently ends in
        # (A4 = money, B4 = gold, C4 = diamonds); the AMOUNT is the walked route's worth.
        if amount != "" and walk_cells:
            walked_route = walk_cells[0][0]
            terminal_col = walk_cells[-1][0]
            expect_img = r[f"reward_image_{terminal_col}"]
            self.check(r["terminal_image"] == expect_img, t,
                       f"terminal_image '{r['terminal_image']}' != reward_image_{terminal_col} '{expect_img}' "
                       f"(image is tied to the terminal column, not the route)")
            self.check(amount == worths.get(walked_route), t,
                       f"terminal_amount {amount} != worth of walked route {walked_route} ({worths.get(walked_route)})")

        # rest and probe flags
        if r["break_20s"] == "1":
            self.check(kind in {"V", "S", "CV", "CS", "TV", "TS"} or r.get("probe_slot") == "followup", t,
                       f"break_20s on kind {kind}, expected a short trial or a change follow-up")
        if r["probe"] == "1":
            options = split(r["probe_options"])
            self.check(len(options) == 3, t, f"{len(options)} probe options, expected 3")
            self.check(len(set(options)) == len(options), t, f"duplicate probe options {options}")
            # every probe's options share one picture category (2026-09-29), so the category
            # never tells the answer apart; for structure probes this was always true
            self.check(len({o.rsplit("_", 1)[0] for o in options}) == 1, t,
                       f"probe options {options} mix picture categories")
            try:
                idx = int(r["probe_correct_index"])
            except ValueError:
                idx = -1
            self.check(1 <= idx <= len(options), t, f"probe_correct_index '{r['probe_correct_index']}' out of range")
            if 1 <= idx <= len(options):
                self.check(options[idx - 1] == r["probe_correct_video"], t,
                           f"option {idx} is {options[idx - 1]}, probe_correct_video says {r['probe_correct_video']}")
            # explicit cue and prompt form (the presentation code must use these, never parse probe_question)
            direction = r.get("probe_direction", "")
            cue = r.get("probe_cue_video", "")
            self.check(direction in PROBE_DIRECTIONS, t, f"probe_direction '{direction}' not one of {sorted(PROBE_DIRECTIONS)}")
            if r["probe_domain"] == "value":
                self.check(direction == "preference", t, f"value probe has direction '{direction}'")
                self.check(cue == "", t, f"value probe has a cue '{cue}', expected none")
            else:
                self.check(direction in PROBE_DIRECTIONS - {"preference"}, t, f"structure probe has direction '{direction}'")
                self.check(cue != "", t, "structure probe has no probe_cue_video")
                self.check(cue != r["probe_correct_video"], t, f"probe_cue_video equals the correct answer {cue}")
                self.check(cue not in options, t, f"probe_cue_video {cue} appears among the options")
                # clip ids are the picture file stems, e.g. animals_1 (see stimuli/manifest.json)
                m = re.search(r"[a-z]+_\d+", r["probe_question"])
                self.check(m is not None and m.group(0) == cue, t,
                           f"probe_cue_video {cue} != clip named in probe_question ({m.group(0) if m else None})")
                # every structure probe is now the same unified question: "which of these belongs
                # to the same sequence as the cue?". The subtype records which leg was queried.
                self.check(direction == "same_sequence", t,
                           f"structure probe has direction '{direction}', expected same_sequence")
                if r["kind"] == "S":
                    self.check(r["probe_subtype"] in {"observed_leg", "counterfactual_leg"}, t,
                               f"structure-change probe subtype '{r['probe_subtype']}'")
                    shown_v = set(r["shown_videos"].split("|"))
                    self.check(r["probe_correct_video"] not in shown_v, t,
                               "the probe answer is a clip shown on this trial")
                    # a just-shown clip may be among the options only on a counterfactual-leg
                    # probe (decided 2026-09-09); the observed leg's options never contain one
                    if r["probe_subtype"] == "observed_leg":
                        self.check(not (set(options) & shown_v), t,
                                   "an observed-leg probe option is a clip shown on this trial")


def validate_file(path, manifest):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return [f"{path.name}: empty schedule"]
    # the step count comes from the file, so both the 3-step and 4-step designs validate
    nrow = max(int(k[1]) for k in rows[0] if len(k) == 2 and k[0] in "ABC" and k[1].isdigit())
    checker = RowChecker(path.name, nrow)

    consecutive_changes = 0
    for r in rows:
        checker.validate_row(r)
        if r["kind"] in CHANGE_KINDS:
            consecutive_changes += 1
            checker.check(consecutive_changes <= 2, r["trial"],
                          f"{consecutive_changes} change trials in a row")
        else:
            consecutive_changes = 0

    checker.check(rows[0]["kind"] == "EST", rows[0]["trial"], "first trial is not the establish trial")
    # the TV worth split (2026-10-05): half the partial tracking trials in the single format show
    # the 100 route's treasure with 100, half a 50 route's with 50 (both 50 routes used)
    tv = [r for r in rows if r["kind"] == "TV"]
    tv_lo = [r for r in tv if r["terminal_amount"] == "50"]
    checker.check(abs(2 * len(tv_lo) - len(tv)) <= 1, tv[0]["trial"] if tv else "-",
                  f"TV worth split {len(tv) - len(tv_lo)} x 100 / {len(tv_lo)} x 50, expected half each")
    checker.check(len({split(r["walk_cells"])[0][0] for r in tv_lo}) >= 2 or len(tv_lo) < 2,
                  tv_lo[0]["trial"] if tv_lo else "-", "the TV '50' screens use only one route")
    for half in (tv[: len(tv) // 2], tv[len(tv) // 2:]):
        n_lo = sum(r["terminal_amount"] == "50" for r in half)
        checker.check(abs(2 * n_lo - len(half)) <= 1, half[0]["trial"] if half else "-",
                      f"TV worth split within a half of the session: {n_lo} x 50 of {len(half)}")
    for r in rows:
        # every short trial is rested since 2026-10-09; of the full walks only the change follow-ups
        if r["kind"] == "EST" or (r["kind"] == "T" and r.get("probe_slot") != "followup"):
            checker.check(r["break_20s"] == "0", r["trial"],
                          f"{r['kind']} row has a rest (only short trials and change follow-ups may)")
        if r["kind"] in {"TV", "TS"}:
            checker.check(r["break_20s"] == "1", r["trial"], f"{r['kind']} row has no rest")
            checker.check(r["probe"] == "0", r["trial"], f"{r['kind']} row has a probe")
        if r["kind"] in {"V", "S", "CV", "CS"}:
            checker.check(r["break_20s"] == "1" and r["probe"] == "1", r["trial"],
                          f"{r['kind']} row is not rested and probed")
        if r["kind"] == "EST":
            checker.check(r["probe"] == "0", r["trial"], "establish row has a probe")
        if r["probe"] == "1":
            shown_v = set(split(r["shown_videos"]))
            if r["probe_slot"] == "control" and r["probe_domain"] == "value":
                # the value control shows no clip since 2026-10-05: its answer is on the current
                # 100 route (an established fact)
                checker.check(r["probe_correct_video"] in split(r[f"route_{r['winner_column']}_videos"]),
                              r["trial"], "a value control's answer is not on the 100 route")
            elif r["kind"] in CHANGE_KINDS:
                checker.check(r["probe_correct_video"] not in shown_v, r["trial"],
                              "a change probe's answer was shown on the change trial")
        # a tracking trial may carry a probe ONLY as the follow-up to a change, and never a rest
        if r["kind"] == "T" and r["probe"] == "1":
            checker.check(r["probe_slot"] == "followup", r["trial"],
                          f"tracking row is probed but probe_slot is '{r['probe_slot']}'")
    # --- structure controls ask about ESTABLISHED pairings (2026-09-23) --------------------------
    # A pairing is two clips of one current journey that the participant has seen belong together:
    # every pairing of the starting journeys (familiarization walked them), and any two clips shown
    # in one trial since. A swap un-establishes the pairings it creates until they are shown
    # together. The control's cue and answer must be such a pairing; the distances are balanced.
    cellvid = {c: rows[0][c] for c in checker.cells}
    est = set()
    for c in "ABC":
        path = [f"{c}{k}" for k in range(1, checker.nrow + 1)]
        est |= {frozenset((cellvid[a], cellvid[b])) for a in path for b in path if a != b}
    ctrl_dist = {}
    for r in rows:
        if r["kind"] == "S":
            k = int(r["swap_step"].split("->")[0])
            for route in (r["observed_route"], r["counterfactual_route"]):
                path = [cellvid[c] for c in split(r[f"route_{route}_path"])]
                est -= {frozenset((h, t)) for h in path[:k] for t in path[k:]}
        shown_v = split(r["shown_videos"])
        est |= {frozenset((a, b)) for a in shown_v for b in shown_v if a != b}
        if r["kind"] == "CS" and r["probe"] == "1":
            cue, ans = r["probe_cue_video"], r["probe_correct_video"]
            checker.check(r["probe_observability"] == "established", r["trial"],
                          f"structure control observability '{r['probe_observability']}'")
            checker.check(frozenset((cue, ans)) in est, r["trial"],
                          f"structure control asks about {cue} with {ans}, not an established pairing")
            vstep = {v: int(c[1]) for c, v in cellvid.items()}
            d = abs(vstep[cue] - vstep[ans])
            ctrl_dist[d] = ctrl_dist.get(d, 0) + 1
    if ctrl_dist:
        want = range(1, checker.nrow)
        counts = [ctrl_dist.get(d, 0) for d in want]
        checker.check(max(counts) - min(counts) <= 1, rows[0]["trial"],
                      f"structure-control distances {dict(zip(want, counts))} are not balanced")

    # --- the follow-up probe: the trial right after every change ------------------------------
    for i, r in enumerate(rows):
        if r["kind"] not in CHANGE_KINDS or i + 1 >= len(rows):
            continue
        nxt = rows[i + 1]
        checker.check(nxt["probe_slot"] == "followup", r["trial"],
                      "the trial after a change is not the follow-up probe trial")
        checker.check(nxt["break_20s"] == "1" and nxt["probe"] == "1", r["trial"],
                      "the follow-up trial is not rested and probed")
        checker.check(nxt["walk_cells"] == r[f"route_{r['untouched_column']}_path"], r["trial"],
                      "the follow-up trial does not walk the untouched route")
        shown_prev = set(r["shown_videos"].split("|"))
        checker.check(nxt["probe_correct_video"] not in shown_prev, r["trial"],
                      "the follow-up answer was shown during the change")
        if r["kind"] == "V":
            # a different unseen clip from the change probe's (2026-09-23)
            checker.check(nxt["probe_correct_video"] != r["probe_correct_video"], r["trial"],
                          "the value follow-up repeats the change probe's answer")
        if r["kind"] == "S":
            checker.check(nxt["probe_subtype"] != r["probe_subtype"], r["trial"],
                          "the follow-up probes the same leg as the change trial")
            checker.check({r["probe_subtype"], nxt["probe_subtype"]}
                          == {"observed_leg", "counterfactual_leg"}, r["trial"],
                          "the change and its follow-up do not cover both legs")
            checker.check(nxt["probe_cue_video"] != r["probe_cue_video"], r["trial"],
                          "the follow-up cue repeats the change trial's cue")
            if nxt["probe_subtype"] == "observed_leg":
                checker.check(not (set(nxt["probe_options"].split("|")) & shown_prev), r["trial"],
                              "an observed-leg follow-up option was shown during the change")

    # --- every change is followed by a stable cluster covering all three routes ---------------
    COLS_ = ["A", "B", "C"]
    change_idx = [i for i, r in enumerate(rows) if r["kind"] in CHANGE_KINDS]
    for n, i in enumerate(change_idx):
        end = change_idx[n + 1] if n + 1 < len(change_idx) else len(rows)
        gap = rows[i + 1:end]
        checker.check(len(gap) >= 3, rows[i]["trial"],
                      f"only {len(gap)} stable trials before the next change (need at least 3)")
        # Coverage counts FULL walks; a control replaces the walk of exactly one route (the new
        # 100 route after a value change, the observed leg after a structure change). The routes
        # a control may not replace must be walked in full, so the counterfactual leg always is.
        full, ctrl = set(), set()
        for x in gap:
            for c in COLS_:
                if x[f"route_{c}_path"] == x["walk_cells"]:
                    if not x["hidden_cells"]:
                        full.add(c)
                    elif x["kind"] in {"CV", "CS"}:
                        ctrl.add(c)
        checker.check(full | ctrl == set(COLS_), rows[i]["trial"],
                      f"the stable trials after this change cover {sorted(full | ctrl)}, "
                      "not all three routes")
        r0 = rows[i]
        must = ({r0["loser_column"], r0["untouched_column"]} if r0["kind"] == "V"
                else {r0["winner_column"], r0["counterfactual_route"]})
        checker.check(must <= full, rows[i]["trial"],
                      f"routes {sorted(must - full)} are not walked in full after this change")
        for x in gap:
            # since 2026-11-04 the controls are spread through the session (no longer one per
            # cluster); a structure control still never shows the transition its swap just showed
            if x["kind"] == "CS" and r0["kind"] == "S":
                checker.check(x["shown_cells"] != r0["shown_cells"], x["trial"],
                              "a structure control repeats the transition its swap just showed")
        checker.check(all(x["kind"] not in CHANGE_KINDS for x in gap), rows[i]["trial"],
                      "a change trial appears inside a stable cluster")

    # --- MRI blocks: contiguous, 1..N, boundaries only immediately before a value change ---
    if "block" in rows[0]:
        try:
            blocks = [int(r["block"]) for r in rows]
        except ValueError:
            blocks = None
            checker.errors.append(f"{path.name}: block column is not integer")
        if blocks:
            n_blocks = max(blocks)
            checker.check(sorted(set(blocks)) == list(range(1, n_blocks + 1)), rows[0]["trial"],
                          f"blocks are not 1..{n_blocks} without gaps")
            checker.check(blocks == sorted(blocks), rows[0]["trial"],
                          "block numbers are not non-decreasing down the file")
            checker.check(blocks[0] == 1 and rows[0]["kind"] == "EST", rows[0]["trial"],
                          "the establish trial is not the first trial of block 1")
            for i in range(1, len(rows)):
                if blocks[i] != blocks[i - 1]:
                    checker.check(rows[i]["kind"] in CHANGE_KINDS, rows[i]["trial"],
                                  "a block boundary falls somewhere other than immediately "
                                  "before a change trial")
            for n, i in enumerate(change_idx):
                end = change_idx[n + 1] if n + 1 < len(change_idx) else len(rows)
                same = all(blocks[j] == blocks[i] for j in range(i, end))
                checker.check(same, rows[i]["trial"],
                              "a change is separated from its stable cluster by a block boundary")

    if manifest is not None:
        clip_ids = {r[cell] for r in rows for cell in checker.cells}
        for vid in sorted(clip_ids):
            entry = manifest["clips"].get(vid)
            if entry is None:
                checker.errors.append(f"{path.name}: clip id '{vid}' missing from manifest")
                continue
            for key in ("image",):
                if key not in entry or not (ROOT / entry[key]).exists():
                    checker.errors.append(f"{path.name}: {vid} {key} file missing: {entry[key]}")
        reward_names = {r[f"reward_image_{route}"] for r in rows for route in "ABC"}
        for name in sorted(reward_names):
            img = manifest["rewards"].get(name)
            if img is None:
                checker.errors.append(f"{path.name}: reward image '{name}' missing from manifest")
            elif not (ROOT / img).exists():
                checker.errors.append(f"{path.name}: reward file missing: {img}")

    return checker.errors


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csvs", nargs="*", type=Path, help="schedule CSVs to validate")
    parser.add_argument("--all", action="store_true", help="validate every CSV in schedules_grid/")
    parser.add_argument("--manifest", type=Path, default=ROOT / "stimuli" / "manifest.json",
                        help="manifest for asset checks (pass --no-assets to skip)")
    parser.add_argument("--no-assets", action="store_true", help="skip manifest/asset checks")
    args = parser.parse_args()

    files = list(args.csvs)
    if args.all:
        # GRID_DIR selects the variant, matching verify_design.py and verify_invariants.py
        files += sorted((ROOT / (os.environ.get("GRID_DIR") or "schedules_grid"))
                        .glob("sub-*_schedule.csv"))
    if not files:
        parser.error("no schedule CSVs given (pass paths or --all)")

    manifest = None
    if not args.no_assets:
        manifest = json.loads(args.manifest.read_text())

    failed = 0
    for path in files:
        errors = validate_file(path, manifest)
        if errors:
            failed += 1
            print(f"FAIL {path.name}: {len(errors)} problem(s)")
            for e in errors[:20]:
                print(f"  - {e}")
            if len(errors) > 20:
                print(f"  ... and {len(errors) - 20} more")
        else:
            print(f"OK   {path.name}")

    print(f"\n{len(files) - failed}/{len(files)} schedules valid")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
