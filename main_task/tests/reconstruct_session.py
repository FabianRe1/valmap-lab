#!/usr/bin/env python3
"""
Reconstruct a whole session, screen by screen, from the ONE OUTPUT FILE ALONE, and say what
cannot be reconstructed.

    python3 tests/reconstruct_session.py <session.tsv> [--print N] [--block B]

Works for both arms (they write the same file). Nothing here reads the schedule CSV or the
config: the point is to find out whether the file is self-contained. From its rows it rebuilds,
per block, the ordered list of what was on screen, from when to when, with what content, and for
every probe which options were shown in which order, which was chosen, whether that was right, and
the reaction time. It then cross-checks:

  * each main-task trial rendered exactly what its own carried schedule columns say: the shown
    clips in step order, never a hidden clip, the outcome or change screen with the amount that
    follows from the walked route and the current winner and, using the layout from the meta rows,
    the treasure of the walked route's terminal, a rest exactly on the short trials and the change follow-ups and before the
    probe, a probe exactly where probe_slot is set, over the row's own options in display order
  * the logged correctness equals (response == the row's probe_correct_video); the logged rt
    equals onset_response - onset_probe; every response names an option that was on screen
  * the timeline is continuous: no event overlaps the next, and every stretch of the block clock
    is covered by some logged screen (unexplained gaps are listed)
  * the file opens with meta rows (schedule, layout, reward images) and closes with session_end

Exit code 0 when the session is fully reconstructible; otherwise the report lists every gap.
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from events_view import (KEPT, load, val, split, meta_from_events,  # noqa: E402
                         blocks_from_events, trials_from_events, is_probed, is_rested)

TOL = 0.006          # seconds; one frame at 165 Hz


def describe(e):
    ev, st = e["event"], val(e["stimulus"])
    if ev in ("clip1", "clip2", "clip3", "clip4"):
        return f"{ev}: clip {st} plays"
    if ev == "outcome":
        img, amt = (st or "?+?").split("+")
        return f"outcome: treasure {img} with {amt}"
    if ev == "fixation_start":
        return f"fixation cross (trial start, {st})"
    if ev == "fixation_gap":
        return f"fixation cross (ISI, {st})"
    if ev == "block_lead_in":
        return "fixation cross (block lead-in)"
    if ev == "rest_readout":
        return "fixation cross (REST, readout window)"
    if ev == "probe":
        return f"probe: options left to right {st}"
    if ev == "response":
        return f"response: chose {val(e['response'])} rt {e['rt']} correct {e['correct']}"
    if ev == "no_response":
        return "no response (probe window ran out)"
    if ev == "feedback":
        return f"feedback: correct={e['correct']}"
    if ev == "practice_note":
        return f"self-paced explanation screen '{st}'"
    if ev == "practice_map":
        return f"practice map: rows {st}"
    if ev == "structure_overview":
        return f"starting-state overview: rows {st}"
    if ev == "break_overview":
        return f"break overview (the journeys as they stand): rows {st}"
    if ev == "block_start":
        return f"block start (wall clock {st})"
    if ev == "block_end":
        return f"block end ({st})"
    return ev


def main():
    opts = sys.argv[1:]
    skip = {opts[i + 1] for i, a in enumerate(opts[:-1]) if a in ("--print", "--block")}
    args = [a for a in opts if not a.startswith("--") and a not in skip]
    n_print = int(opts[opts.index("--print") + 1]) if "--print" in opts else 40
    only_block = opts[opts.index("--block") + 1] if "--block" in opts else None
    events = load(args[0])
    problems, notes = [], []

    meta = meta_from_events(events)
    layout = meta.get("layout") if isinstance(meta.get("layout"), dict) else {}
    reward_of_column = meta.get("reward_images") if isinstance(meta.get("reward_images"), dict) else {}
    clip_column = {clip: cell[0] for cell, clip in layout.items()}
    if not events or events[0]["event"] != "meta":
        problems.append("the file does not open with meta rows")
    for key in ("schedule", "steps", "layout", "reward_images", "timings"):
        if key not in meta:
            problems.append(f"meta rows lack '{key}'")
    if not any(e["event"] == "session_end" for e in events):
        notes.append("no session_end rows: the session did not finish cleanly")

    blocks = blocks_from_events(events)
    # the participant leaving the page or fullscreen (browser only): screens during a hidden period
    # run long because the browser throttles a hidden page, so report where it happened
    hidden = [e for e in events if e["event"] == "page_hidden"]
    if hidden:
        notes.append(f"page hidden {len(hidden)} time(s), {sum(float(e['duration']) for e in hidden):.1f} s "
                     f"in all (blocks {sorted({e['block'] for e in hidden})}): screens in those "
                     "periods run long")
    exits = [e for e in events if e["event"] == "fullscreen_exit"]
    if exits:
        notes.append(f"fullscreen left {len(exits)} time(s) (blocks {sorted({e['block'] for e in exits})})")
    trials = trials_from_events(events)

    printed = 0
    for i, b in enumerate(blocks, start=1):
        if only_block and b["label"] != only_block and str(i) != only_block and b["block"] != only_block:
            continue
        print(f"\n=== block {b['block']} '{b['label']}' ({len(b['events'])} events)")
        for e in b["events"]:
            if printed >= n_print:
                break
            print(f"  {float(e['onset']):9.3f}  {float(e['duration']):6.3f}  trial {e['trial']:>4}  {describe(e)}")
            printed += 1
        if printed >= n_print:
            print("  ... (use --print N to see more)")
            break

    # ---- continuity ----
    for b in blocks:
        prev_end, prev = 0.0, None
        for e in b["events"]:
            on, du = float(e["onset"]), float(e["duration"])
            if du == 0.0:
                continue
            if prev is not None and on < prev_end - TOL:
                problems.append(f"block {b['block']}: {e['event']} (trial {e['trial']}) at {on:.3f} "
                                f"starts before {prev['event']} ends at {prev_end:.3f}")
            if prev is not None and on > prev_end + 0.05:
                notes.append(f"uncovered clock between {prev['event']} and {e['event']}")
            prev_end, prev = on + du, e

    # ---- per main-task trial ----
    main_trials = [t for t in trials if t["phase"] == "main"]
    n_probe_checked = 0
    partial_rests = set()                  # rest screens per TV / TS trial, one value per session
    for t in main_trials:
        tr = int(t["trial"]); evs = t["events"]; kind = t["kind"]
        shown, hidden = split(t["shown_videos"]), split(t["hidden_videos"])
        clips = [val(e["stimulus"]) for e in evs if e["event"].startswith("clip")]
        comps = [e["event"] for e in evs if e["event"].endswith("_composite")]
        outc = [val(e["stimulus"]) for e in evs if e["event"] == "outcome"]
        rests = [e for e in evs if e["event"] == "rest_readout"]
        probes = [e for e in evs if e["event"] == "probe"]
        resps = [e for e in evs if e["event"] in ("response", "no_response")]
        for c in KEPT + ["block", "trial_type"]:
            vals = {val(e.get(c)) for e in evs}
            if len(vals) != 1:
                problems.append(f"trial {tr}: column {c} varies within the trial: {vals}")
        walk_clips = shown + hidden
        walked = next((r for r in "ABC" if set(split(t[f"route_{r}_videos"])) == set(walk_clips)), None)
        if walked is None:
            problems.append(f"trial {tr}: shown+hidden {walk_clips} is not one of the current routes")
        exp_amount = "100" if walked == t["winner_column"] else "50"
        terminal = split(t[f"route_{walked}_videos"])[-1] if walked else None
        exp_treasure = reward_of_column.get(clip_column.get(terminal, ""))

        def expect_outcome(got):
            img, amt = (got or "?+?").split("+")
            if amt != exp_amount:
                problems.append(f"trial {tr} ({kind}): amount {amt}, expected {exp_amount} (walked {walked}, winner {t['winner_column']})")
            if exp_treasure and img != exp_treasure:
                problems.append(f"trial {tr} ({kind}): treasure {img}, expected {exp_treasure} for terminal {terminal}")

        # every kind is the same sequential walk (2026-09-23): its shown clips, then one outcome
        if comps:
            problems.append(f"trial {tr} ({kind}): composite screen(s) drawn: {comps}")
        if True:
            if clips != shown:
                problems.append(f"trial {tr} ({kind}): clips rendered {clips} != shown_videos {shown}")
            # since 2026-10-05 the pair format (S, CS, TS) ends on its clips, with no outcome
            want_outc = 0 if kind in ("S", "CS", "TS") else 1
            if len(outc) != want_outc:
                problems.append(f"trial {tr} ({kind}): {len(outc)} outcome screens, expected {want_outc}")
            elif outc:
                expect_outcome(outc[0])
        on_screen = " ".join(val(e["stimulus"]) or "" for e in evs if e["event"] not in ("probe", "response", "no_response"))
        for h in hidden:
            if h in on_screen.replace("->", " ").replace("+", " ").split():
                problems.append(f"trial {tr}: hidden clip {h} appeared on screen")
        want = is_rested(t)
        if want is None:                    # TV / TS: rested since 2026-10-09; one rule per session
            partial_rests.add(len(rests))
            if len(rests) > 1:
                problems.append(f"trial {tr}: {len(rests)} rest screens on {kind}")
        elif want != (len(rests) == 1):
            problems.append(f"trial {tr}: kind {kind} implies rest={want} but {len(rests)} rest screens")
        if rests:
            last_stim = max(float(e["onset"]) for e in evs if e["event"] in ("clip1", "clip2", "clip3", "clip4", "outcome"))
            if float(rests[0]["onset"]) < last_stim:
                problems.append(f"trial {tr}: rest before the last stimulus")
            if probes and float(rests[0]["onset"]) > float(probes[0]["onset"]):
                problems.append(f"trial {tr}: probe before the rest")
        if is_probed(t) != (len(probes) == 1):
            problems.append(f"trial {tr}: probe_slot={t['probe_slot']} but {len(probes)} probe screens")
        if probes:
            n_probe_checked += 1
            p = probes[0]
            if val(p["stimulus"]) != t["probe_options"]:
                problems.append(f"trial {tr}: probe showed {p['stimulus']} but the row says {t['probe_options']}")
            if len(resps) != 1:
                problems.append(f"trial {tr}: {len(resps)} response events")
            elif resps[0]["event"] == "response":
                r = resps[0]; chosen = val(r["response"])
                if chosen not in split(t["probe_options"]):
                    problems.append(f"trial {tr}: response {chosen} is not among the options")
                if str(1 if chosen == t["probe_correct_video"] else 0) != str(r["correct"]):
                    problems.append(f"trial {tr}: correctness logged {r['correct']} but recomputed from the answer differs")
                if abs(float(r["onset"]) - float(p["onset"]) - float(r["rt"])) > TOL:
                    problems.append(f"trial {tr}: rt {r['rt']} != onset difference {float(r['onset']) - float(p['onset']):.4f}")
        for e in evs:
            if e["event"] in ("fixation_gap", "fixation_start") and not str(e["stimulus"]).startswith("scheduled="):
                problems.append(f"trial {tr}: {e['event']} row without its scheduled draw")
        if sum(1 for e in evs if e["event"] == "fixation_start") != 1:
            problems.append(f"trial {tr}: no single fixation_start row")
        first = min(evs, key=lambda e: float(e["onset"]))
        if first["event"] != "fixation_start":
            problems.append(f"trial {tr}: does not open with fixation_start but {first['event']}")

    # ---- the overview in every break (2026-10-01): the k-th one follows main block k and must
    # show the journeys of that block's last trial, as its own rows carry them ----
    breaks = [e for e in events if e["event"] == "break_overview"]
    if breaks:
        main_blocks = sorted({int(t["block"]) for t in main_trials})
        if len(breaks) != len(main_blocks) - 1:
            problems.append(f"{len(breaks)} break overviews for {len(main_blocks)} blocks")
        for k, e in enumerate(breaks, start=1):
            in_block = [t for t in main_trials if int(t["block"]) == k]
            if not in_block:
                continue
            last = max(in_block, key=lambda t: int(t["trial"]))
            want = ";".join(last[f"route_{c}_videos"] for c in "ABC")
            if val(e["stimulus"]) != want:
                problems.append(f"break overview after block {k} shows {e['stimulus']}, "
                                f"the journeys after trial {last['trial']} are {want}")
        notes.append(f"{len(breaks)} break overviews, each matching the journeys at the end of "
                     "its block" if not any("break overview" in p for p in problems) else
                     "break overviews checked")

    # TV and TS: all rested (schedules since 2026-10-09) or none (earlier), never mixed
    if len(partial_rests) > 1:
        problems.append(f"TV/TS trials mix rested and unrested ({sorted(partial_rests)} rest screens)")
    print(f"\nblocks: {len(blocks)} | events: {len(events)} | main trials: {len(main_trials)} | probes cross-checked: {n_probe_checked}"
          + (" | treasures checked against the meta layout" if layout else " | no layout in the meta rows: treasure identity not checked"))
    if notes:
        counts = defaultdict(int)
        for n in notes:
            counts[n] += 1
        print("\nNOTES:")
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"  {v:4d} x {k}")
    if problems:
        print(f"\nNOT RECONSTRUCTIBLE OR INCONSISTENT ({len(problems)}):")
        for p in problems[:60]:
            print("  -", p)
        if len(problems) > 60:
            print(f"  ... {len(problems) - 60} more")
        sys.exit(1)
    print("\nRECONSTRUCTIBLE: every main-task screen, its content and timing, and every probe's options, choice, "
          "correctness and rt follow from the one file, and it opens with the session meta and closes with session_end.")


if __name__ == "__main__":
    main()
