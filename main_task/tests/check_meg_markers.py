#!/usr/bin/env python3
"""
check_meg_markers.py: the MEG marker stream of a dry run against its log (2026-10-14).

A dry run with the dummy backend prints every code it sends ("[marker] <code>"). This rebuilds,
from the session's one output file alone, the code each logged screen should have sent and
compares the two streams in order:

  main block start / end   100 + block / 110 + block
  fixation_start           the trial type (TRIAL_START_CODES; practice 29, familiarization 19)
  clip1..clip4             the picture's class (1..12, as in the localizer; a practice shape 13)
  fixation_gap             20
  outcome                  the treasure's class (money 10, gold 11, diamonds 12)
  rest_readout             30
  probe                    the question type (PROBE_CODES); a gate question 41 or 43
  response                 50 / 51 / 52 for the left / middle / right option
  no_response              62 (timed questions only)
  feedback                 60 correct, 61 wrong

It also checks that every code lies in 1..127. Codes are taken from the main task's config, so a
change there is followed here.

Usage:
  python run_task.py --dry-run ... --marker-backend dummy > run.txt   (PsychoPy's python)
  python3 tests/check_meg_markers.py <session.tsv> run.txt
"""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "psychopy"))
import config as cfg          # noqa: E402  (also puts meg_lab on the path)
import triggers               # noqa: E402

MAIN_TYPES = {"establish", "value_change", "structure_change", "value_control",
              "structure_control", "tracking", "partial_tracking_value",
              "partial_tracking_structure"}


def expected(rows):
    out = []
    for r in rows:
        ev, tt = r["event"], r["trial_type"]
        main_block = tt in ("n/a", "") and r["block"] in [str(b) for b in range(1, 10)]
        if ev == "block_start" and main_block:
            out.append((cfg.MARKER_CODES["block_start"] + int(r["block"]), ev))
        elif ev == "block_end" and main_block:
            out.append((cfg.MARKER_CODES["block_end"] + int(r["block"]), ev))
        elif ev == "fixation_start":
            key = tt if tt in ("practice", "familiarization") else r["kind"]
            out.append((triggers.trial_marker_code(key), f"{ev} {key}"))
        elif re.fullmatch(r"clip\d", ev):
            out.append((triggers.picture_code(r["stimulus"]), f"{ev} {r['stimulus']}"))
        elif ev == "fixation_gap":
            out.append((cfg.MARKER_CODES["fixation"], ev))
        elif ev == "outcome":
            out.append((triggers.outcome_code(r["stimulus"].split("+")[0]), f"{ev} {r['stimulus']}"))
        elif ev == "rest_readout":
            out.append((cfg.MARKER_CODES["rest"], ev))
        elif ev == "probe" and tt == "gate":
            # the gate asks about the starting journeys: an established value or structure
            # question; its log rows do not carry the type, so either code is right
            out.append(({cfg.PROBE_CODES["value_established"], cfg.PROBE_CODES["structure_established"]},
                        "probe gate"))
        elif ev == "probe":
            out.append((triggers.probe_code(r["probe_type"]), f"{ev} {r['probe_type']}"))
        elif ev == "response":
            options = r["stimulus"].split("|")
            out.append((triggers.response_code(options.index(r["response"])), ev))
        elif ev == "no_response" and tt in MAIN_TYPES:
            out.append((cfg.MARKER_CODES["timeout"], ev))
        elif ev == "feedback":
            ok = r["correct"] == "1"
            out.append((cfg.MARKER_CODES["feedback_correct" if ok else "feedback_incorrect"], ev))
    return out


def main():
    log, console = sys.argv[1], sys.argv[2]
    with open(log, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    sent = [int(m) for m in re.findall(r"^\[marker\] (\d+)$", Path(console).read_text(), re.M)]
    want = expected(rows)
    fails = []
    bad = triggers.check_codes(sent)
    if bad:
        fails.append(f"codes outside 1..{cfg.MARKER_MAX_CODE}: {sorted(set(bad))}")
    if len(sent) != len(want):
        fails.append(f"{len(sent)} codes sent, {len(want)} expected from the log")
    for i, (got, (code, what)) in enumerate(zip(sent, want)):
        if (got not in code) if isinstance(code, set) else (got != code):
            fails.append(f"code {i + 1}: sent {got}, expected {code} ({what})")
            break
    if fails:
        print("FAILED --", "; ".join(fails))
        sys.exit(1)
    print(f"PASSED -- {len(sent)} marker codes, each the code its logged screen calls for "
          f"(every one in 1..{cfg.MARKER_MAX_CODE}).")


if __name__ == "__main__":
    main()
