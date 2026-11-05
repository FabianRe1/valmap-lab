#!/usr/bin/env python3
"""
Post-hoc check of a PsychoPy dry-run session file against the schedule it claims to have
presented. The one output file per subject is read; nothing running is consulted.

    python3 tests/verify_dryrun_log.py <session file or stem> <schedule number>
    # e.g. tests/verify_dryrun_log.py src/psychopy/data/sub-X_task-gridvalstruct_20260910-101010_dryrun.tsv 1

Asserts:
  * the kept schedule columns on every main-task row equal the schedule CSV, trial by trial
  * each trial rendered what its row specifies: every kind the same sequential walk, exactly its
    shown clips in step order then one outcome (a value change one clip and 100, a structure change
    the two clips of its transition and 50); no composite screen ever; hidden clips never on screen
  * a rest occurs exactly on the short trials (V/S/CV/CS/TV/TS) and the change follow-ups, carries no stimulus, precedes the probe, and every rest has
    the length the session's timing profile calls for
  * the ISI structure matches the profile: in fMRI exactly one long ISI per trial at a slot that
    varies, outside fMRI none; every fixation_gap row carries its scheduled draw
  * a probe occurs exactly where the schedule sets probe_slot, over the schedule's own options, and
    correctness agrees with the schedule's answer
  * every trial was presented in the block its own `block` column names; onsets are non-decreasing
    within each block; the file opens with meta rows and closes with session_end rows
"""
import collections
import csv
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from events_view import (NA, KEPT, load, val, split, meta_from_events,  # noqa: E402
                         blocks_from_events, trials_from_events)

arg = sys.argv[1]
sched_n = int(sys.argv[2])
path = Path(arg)
if not path.exists():
    path = ROOT / "src" / "psychopy" / "data" / (arg if arg.endswith(".tsv") else f"{arg}.tsv")
fails = []
_SDIR = os.environ.get("GRID_DIR", "schedules_grid")
sched = list(csv.DictReader(open(ROOT / _SDIR / f"sub-{sched_n:03d}_schedule.csv")))
nrow = max(int(k[1]) for k in sched[0] if len(k) == 2 and k[0] in "ABC" and k[1].isdigit())
events = load(path)
meta = meta_from_events(events)
# the planned lead-out, from the timings meta row ("...|T_BLOCK_LEAD_OUT=7.0|..."), if the session has one
import re as _re
_m = _re.search(r"T_BLOCK_LEAD_OUT=([0-9.]+)", str(meta.get("timings", "")))
meta_timings = {"T_BLOCK_LEAD_OUT": float(_m.group(1))} if _m else {}
trials = trials_from_events(events)
main = sorted([t for t in trials if t["phase"] == "main"], key=lambda t: int(t["trial"]))
by_trial = {t["trial"]: t for t in main}

# 0. file shape
if not events or events[0]["event"] != "meta":
    fails.append("file does not open with meta rows")
if not any(e["event"] == "session_end" for e in events):
    fails.append("file does not close with session_end rows")
if str(meta.get("schedule")) != str(sched_n):
    fails.append(f"meta says schedule {meta.get('schedule')}, expected {sched_n}")

# 1. kept schedule columns reproduced unchanged, and the block matches
if len(main) != len(sched):
    fails.append(f"main trials {len(main)} != schedule rows {len(sched)}")
mismatch = 0; first = ""
for src in sched:
    got = by_trial.get(src["trial"])
    if got is None:
        fails.append(f"trial {src['trial']}: no rows"); continue
    for c in KEPT:
        want = src[c]
        have = "" if got[c] == NA else got[c]
        if have != want:
            mismatch += 1
            first = first or f"trial {src['trial']} col {c}: log '{got[c]}' vs schedule '{want}'"
    if got["block"] != src["block"]:
        fails.append(f"trial {src['trial']}: presented in block {got['block']}, schedule says {src['block']}")
if mismatch:
    fails.append(f"{mismatch} kept schedule values differ in the log ({first})")

# 2. rendering rules per trial
rest_secs = set()
for src in sched:
    t = by_trial.get(src["trial"])
    if t is None:
        continue
    tn, kind, rows = src["trial"], src["kind"], t["events"]
    clips = [r for r in rows if r["event"].startswith("clip")]
    shown, hidden = split(src["shown_videos"]), split(src["hidden_videos"])
    outcome = [r for r in rows if r["event"] == "outcome"]
    comp = [r for r in rows if r["event"].endswith("_composite")]
    rest = [r for r in rows if r["event"] == "rest_readout"]
    probe = [r for r in rows if r["event"] == "probe"]
    want_out = f"{src['terminal_image']}+{src['terminal_amount']}"
    has_out = src["terminal_amount"] != ""
    # one rule for every kind (2026-09-23): the shown clips in order, then one outcome if the row
    # has one (since 2026-10-05 the pair format has none)
    if comp: fails.append(f"trial {tn} ({kind}): a composite screen was drawn")
    if [r["stimulus"] for r in clips] != shown: fails.append(f"trial {tn} ({kind}): clips {[r['stimulus'] for r in clips]} != {shown}")
    if has_out and (len(outcome) != 1 or outcome[0]["stimulus"] != want_out): fails.append(f"trial {tn} ({kind}): outcome {[r['stimulus'] for r in outcome]} != {want_out}")
    if not has_out and outcome: fails.append(f"trial {tn} ({kind}): an outcome was drawn, the row has none")
    if kind in ("S", "CS", "TS") and has_out: fails.append(f"trial {tn} ({kind}): the schedule gives a pair trial an outcome")
    want_n = {"V": 0, "CV": 0, "TV": 0, "S": 2, "CS": 2, "TS": 2}.get(kind)
    if want_n is not None and len(clips) != want_n: fails.append(f"trial {tn} ({kind}): {len(clips)} clips, expected {want_n}")
    drawn = " ".join(r["stimulus"] for r in rows if r["event"] not in ("probe", "response", "no_response"))
    for h in hidden:
        if h in drawn.replace("->", " ").replace("+", " ").split(): fails.append(f"trial {tn}: HIDDEN clip {h} appeared on screen")
    # the schedule row says whether a rest follows (TV and TS are rested since 2026-10-09; sessions
    # run on earlier schedules have none there)
    want_rest = src.get("break_20s") == "1"
    if want_rest != bool(rest): fails.append(f"trial {tn}: rest presence {bool(rest)} does not fit the schedule row (kind {kind})")
    for r in rest:
        if val(r["stimulus"]) is not None: fails.append(f"trial {tn}: rest carries stimulus {r['stimulus']}")
        rest_secs.add(round(float(r["duration"]), 3))
    if (src["probe"] == "1") != bool(probe): fails.append(f"trial {tn}: probe presence {bool(probe)} != schedule probe {src['probe']}")
    if src.get("probe_slot") == "followup" and not rest: fails.append(f"trial {tn}: follow-up trial has no rest")
    if probe and probe[0]["stimulus"] != src["probe_options"]: fails.append(f"trial {tn}: options {probe[0]['stimulus']} != {src['probe_options']}")
    if rest and probe and float(probe[0]["onset"]) < float(rest[0]["onset"]): fails.append(f"trial {tn}: probe precedes the rest")
    if src["probe"] == "1" and t["responded"]:
        want = "1" if t["chosen_video"] == src["probe_correct_video"] else "0"
        if str(t["correct"]) != want: fails.append(f"trial {tn}: correct={t['correct']} but chosen {t['chosen_video']} vs key {src['probe_correct_video']}")
    for r in rows:
        if r["event"] == "fixation_gap" and not str(r["stimulus"]).startswith("scheduled="):
            fails.append(f"trial {tn}: fixation_gap without its scheduled draw")

# 3. ISI structure per timing profile
profile = meta.get("timing_profile")
scale = 0.02 if "dryrun" in path.name else 1.0
# counted on the SCHEDULED values (stimulus "scheduled=x"), so a slow frame on a test laptop is not
# taken for a long ISI (2026-11-05); the measured durations are checked against them elsewhere
long_threshold = 2.0
long_slots = collections.Counter(); n_long = collections.Counter()
for t in main:
    gaps = [float(str(r["stimulus"]).split("=", 1)[1]) for r in t["events"] if r["event"] == "fixation_gap"]
    longs = [i for i, g in enumerate(gaps) if g > long_threshold]
    n_long[len(longs)] += 1
    for i in longs: long_slots[i] += 1
if profile in ("mri", "meg"):          # the MEG has the MRI's intervals since 2026-11-05
    # exactly one long ISI per trial that HAS gaps; since 2026-11-05 the session sets have gaps only
    # between events, so a one-event trial (a value change or control) has none
    n_long = collections.Counter()
    for t in main:
        gaps = [float(str(r["stimulus"]).split("=", 1)[1]) for r in t["events"] if r["event"] == "fixation_gap"]
        if gaps: n_long[sum(g > long_threshold for g in gaps)] += 1
    wrong = {n: c for n, c in n_long.items() if n != 1}
    if wrong: fails.append(f"{profile}: trials whose long-ISI count is not exactly 1: {wrong}")
    if len(long_slots) < 2: fails.append(f"{profile}: the long ISI always lands in slot {list(long_slots)}")
elif profile:
    if any(n for n in n_long if n): fails.append(f"{profile}: long ISIs outside fMRI: {dict(n_long)}")
print(f"timing profile: {profile} | long ISIs per trial: {dict(n_long)}" + (f" | slots: {dict(sorted(long_slots.items()))}" if long_slots else ""))

# 4. monotonic onsets within each block
for b in blocks_from_events(events):
    on = [float(e["onset"]) for e in b["events"] if val(e["onset"]) is not None]
    if on != sorted(on): fails.append(f"block {b['block']}: onsets not monotonic")
    # the trigger is the block's clock zero (2026-11-04): the lead-in starts within 0.1 s of it
    # the lead-out (2026-11-05), where the session has one: the block's last screen before block_end
    outs = [e for e in b["events"] if e["event"] == "block_lead_out"]
    names = [e["event"] for e in b["events"]]
    if meta_timings.get("T_BLOCK_LEAD_OUT") and "block_lead_in" in names:   # main blocks only
        if len(outs) != 1 or names.index("block_lead_out") != names.index("block_end") - 1:
            fails.append(f"block {b['block']}: no lead-out right before block_end")
        elif abs(float(outs[0]["duration"]) - meta_timings["T_BLOCK_LEAD_OUT"] * scale) > 0.05 * max(1, scale * 50):
            fails.append(f"block {b['block']}: lead-out {outs[0]['duration']} s, want {meta_timings['T_BLOCK_LEAD_OUT'] * scale:.3f}")
    lead = [float(e["onset"]) for e in b["events"] if e["event"] == "block_lead_in"]
    if lead and not 0.0 <= lead[0] < 0.1:
        fails.append(f"block {b['block']}: lead-in {lead[0]:.3f} s after the trigger, not within 0.1 s")

if rest_secs:
    lo_r, hi_r = min(rest_secs), max(rest_secs)
    if hi_r - lo_r > 0.03: fails.append(f"rest durations vary by more than a frame: {lo_r} to {hi_r}")
    mean_r = sum(rest_secs) / len(rest_secs)
    nominal = {round(5.0 * scale, 3): "online_meg or meg (5 s)", round(20.0 * scale, 3): "mri (20 s)"}
    match = [v for k, v in nominal.items() if abs(mean_r - k) < 0.02 * max(1, scale * 50)]
    if not match: fails.append(f"rest length {mean_r:.3f} s matches no timing profile")
    print(f"rest length in the log: {mean_r:.3f} s -> {match[0] if match else 'UNKNOWN'}")
print(f"schedule sub-{sched_n:03d}: {len(sched)} rows | log: {len(main)} main trials, "
      f"{sum(len(t['events']) for t in main)} main event rows | blocks {sorted({t['block'] for t in main}, key=int)}")
if fails:
    print(f"\nFAILED -- {len(fails)} problem(s):")
    for f in fails[:25]: print("  -", f)
    sys.exit(1)
print("\nPASSED -- the one file reconstructs the schedule; rendering, rests, probes and onsets all correct.")
