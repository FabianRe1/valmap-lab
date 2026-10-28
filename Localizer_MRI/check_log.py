"""Check a localizer output file against its design.

Usage:  python3 check_log.py data/<file>.tsv [--timing] [--partial]
Confirms the log reconstructs the design exactly (every trial's picture in order, every probe
with its two pictures and answer key, nothing extra), onsets increase within each block, every
trial follows the event sequence fixation, stimulus[, probe_fixation, probe, feedback|timeout],
and (with --timing, for real runs only) that measured durations match the planned ones within two
frames.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import config as cfg  # noqa: E402

TOL = 2 / 60 + 0.002


def main():
    path = Path(sys.argv[1])
    timing = "--timing" in sys.argv
    log = list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"))
    meta = {r["note"].split("=", 1)[0]: r["note"].split("=", 1)[1] for r in log if r["event"] == "meta"}
    design = list(csv.DictReader(open(cfg.DESIGN_DIR / meta["design_file"])))
    start = int(meta["start_block"])
    design = [d for d in design if int(d["block"]) >= start]
    errs = []
    need = lambda ok, msg: ok or errs.append(msg)

    by_trial = defaultdict(list)
    for r in log:
        if r["trial"]:
            by_trial[int(r["trial"])].append(r)
    complete = meta.get("session_end") == "complete"
    # an unfinished log (a crash, or quit) fails unless --partial asks to check what is there
    need(complete or "--partial" in sys.argv, f"session_end={meta.get('session_end')}: not complete")
    if complete:
        need(sorted(by_trial) == [int(d["trial"]) for d in design], "logged trials differ from the design")
    for d in design:
        t = int(d["trial"])
        if t not in by_trial:
            continue
        ev = [r["event"] for r in by_trial[t]]
        rows = {r["event"]: r for r in by_trial[t]}
        expected = ["fixation", "stimulus"]
        if d["probe"] == "1":
            expected += ["probe_fixation", "probe", "timeout" if rows.get("probe", {}).get("response") == "timed_out" else "feedback"]
        need(ev == expected, f"trial {t}: events {ev}")
        need(rows["stimulus"]["stimulus"] == d["stimulus"] and rows["stimulus"]["image"] == d["stimulus_file"],
             f"trial {t}: wrong picture")
        for k in ("probe_left_file", "probe_right_file", "probe_correct", "stimulus_ITI", "probe_ITI"):
            need(rows["stimulus"][k] == d[k], f"trial {t}: {k} not copied from the design")
        if d["probe"] == "1" and "probe" in rows:
            p = rows["probe"]
            if p["response"] != "timed_out":
                need(p["correct"] == str(int(p["response"] == d["probe_correct"])), f"trial {t}: scoring")
                need(0 < float(p["rt"]) <= cfg.PROBE_MAX_RT + TOL, f"trial {t}: rt {p['rt']}")
        if timing:
            need(abs(float(rows["fixation"]["duration"]) - float(d["stimulus_ITI"])) < TOL, f"trial {t}: ITI duration")
            need(abs(float(rows["stimulus"]["duration"]) - cfg.T_STIM) < TOL, f"trial {t}: video duration")
            need(rows["stimulus"]["note"] == "video_frames=24", f"trial {t}: {rows['stimulus']['note']}")
            if d["probe"] == "1" and "feedback" in rows:
                end = float(rows["feedback"]["onset"]) + float(rows["feedback"]["duration"])
                need(abs(end - float(rows["probe"]["onset"]) - cfg.PROBE_TOTAL) < TOL, f"trial {t}: probe total")

    blocks = defaultdict(list)
    for r in log:
        if r["block"] and r["onset"] != "":
            blocks[r["block"]].append(float(r["onset"]))
    for b, onsets in blocks.items():
        need(all(x < y for x, y in zip(onsets, onsets[1:])), f"block {b}: onsets not increasing")
        need(onsets[0] == 0.0, f"block {b}: does not start at the trigger")
    print(f"{path.name}: {'OK' if not errs else 'FAIL'}  {len(by_trial)} trials logged, "
          f"session_end={meta.get('session_end')}, bonus={meta.get('bonus_percent')}")
    for e in errs[:15]:
        print("   ", e)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
