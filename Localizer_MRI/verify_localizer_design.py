"""Independent check of localizer designs (re-derives every rule from the CSV alone).

Usage:  python3 verify_localizer_design.py designs/sub-001_localizer.csv [more.csv ...]
        python3 verify_localizer_design.py designs/*.csv
Prints one line per file and a summary; exits 1 if any rule fails.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ITEMS = json.loads((HERE / "stimuli" / "localizer_manifest_video.json").read_text())["items"]
CLASSES = sorted(ITEMS)
N_BLOCKS, PAIR_REPS, CAP_S = 6, 5, 3600.0
T_STIM, PROBE_TOTAL, LEAD, BREAK = 1.0, 2.0, 5.0, 30.0


def check(path):
    rows = list(csv.DictReader(open(path)))
    errs = []
    need = lambda ok, msg: ok or errs.append(msg)
    blocks = [[r for r in rows if int(r["block"]) == b] for b in range(1, N_BLOCKS + 1)]
    need(sum(map(len, blocks)) == len(rows), "rows outside blocks 1..6")
    need([int(r["trial"]) for r in rows] == list(range(1, len(rows) + 1)), "trial not 1..N")
    pairs, shown, preceded = Counter(), Counter(), Counter()
    for b, blk in enumerate(blocks, 1):
        seq = [r["stimulus"] for r in blk]
        need([int(r["trial_in_block"]) for r in blk] == list(range(1, len(blk) + 1)),
             f"block {b}: trial_in_block not 1..n")
        need(blk[0]["prev_stimulus"] == "", f"block {b}: first trial has a prev_stimulus")
        for r, prev in zip(blk[1:], seq[:-1]):
            need(r["prev_stimulus"] == prev, f"block {b} trial {r['trial']}: prev_stimulus wrong")
        pairs.update(zip(seq[:-1], seq[1:]))
        preceded.update(seq[1:])
        shown.update(seq)
        cnt = Counter(seq)
        need(set(cnt) == set(CLASSES) and min(cnt.values()) >= 8 and max(cnt.values()) <= 11,
             f"block {b}: class counts {sorted(cnt.values())}")
        need(max(Counter(zip(seq[:-1], seq[1:])).values()) <= 2, f"block {b}: a pair 3+ times")
        for r in blk:
            need(r["stimulus_file"] == ITEMS[r["stimulus"]]["video"], f"trial {r['trial']}: file")
            need(2.0 <= float(r["stimulus_ITI"]) <= 7.0, f"trial {r['trial']}: ITI out of range")
    need(all(pairs[(a, b)] == PAIR_REPS for a in CLASSES for b in CLASSES if a != b)
         and not any(a == b for a, b in pairs), "ordered pairs not exactly 5 each / self repeat")
    need(set(preceded.values()) == {PAIR_REPS * (len(CLASSES) - 1)}, "preceded counts unequal")
    need(len({blk[0]["stimulus"] for blk in blocks}) == N_BLOCKS, "block openers not distinct")
    need(max(shown.values()) - min(shown.values()) <= 1, f"shown counts {sorted(set(shown.values()))}")

    probes = [r for r in rows if r["probe"] == "1"]
    by_trial = {int(r["trial"]): r for r in rows}
    need(set(Counter(r["stimulus"] for r in probes).values()) == {5}, "probes per class not 5")
    kinds = Counter(r["probe_kind"] for r in probes)
    need(kinds["neither"] == round(len(probes) / 3), f"probe kinds {dict(kinds)}")
    sides = Counter(r["probe_correct"] for r in probes if r["probe_kind"] == "match")
    need(abs(sides["left"] - sides["right"]) <= 2, f"match sides {dict(sides)}")
    versions = Counter((r["probe_kind"], r[f"probe_{s}_version"]) for r in probes for s in ("left", "right"))
    for k in ("match", "neither"):
        need(abs(versions[(k, "task")] - versions[(k, "alt")]) <= 1, f"{k} versions {dict(versions)}")
    alt_use = Counter()
    for blk in blocks:
        last = int(blk[-1]["trial"])
        for i, r in enumerate(blk):
            if r["probe"] != "1":
                continue
            t = int(r["trial"])
            need(0 < i < len(blk) - 1, f"trial {t}: probe on a block's first or last trial")
            nxt = by_trial[t + 1]["stimulus"] if t < last else None
            L, R = r["probe_left_class"], r["probe_right_class"]
            need(L != R, f"trial {t}: same class twice on a probe")
            if r["probe_kind"] == "match":
                need(r["stimulus"] in (L, R) and r["probe_correct"] == ("left" if L == r["stimulus"] else "right"),
                     f"trial {t}: match probe answer")
                foil = R if L == r["stimulus"] else L
                need(foil != nxt, f"trial {t}: foil is the next stimulus")
            else:
                need(r["probe_correct"] == "neither" and r["stimulus"] not in (L, R) and nxt not in (L, R),
                     f"trial {t}: neither probe content")
            for s, c in (("left", L), ("right", R)):
                f, v = r[f"probe_{s}_file"], r[f"probe_{s}_version"]
                ok = f == ITEMS[c]["task"] if v == "task" else f in ITEMS[c]["alternatives"]
                need(ok and (HERE / "stimuli" / f).exists(), f"trial {t}: {s} picture file")
                if v == "alt":
                    alt_use[(c, f)] += 1
            need(float(r["probe_max_rt"]) == 1.5 and float(r["probe_total"]) == 2.0, f"trial {t}: probe timing")
        gaps = [int(r["trial_in_block"]) for r in blk if r["probe"] == "1"]
        need(all(b - a >= 4 for a, b in zip(gaps, gaps[1:])), "probes closer than 4 trials")
    for c in CLASSES:
        uses = [alt_use[(c, f)] for f in ITEMS[c]["alternatives"]]
        need(max(uses) - min(uses) <= 1, f"{c}: replacement views not rotated {uses}")

    total = sum(float(r["stimulus_ITI"]) + T_STIM for r in rows)
    total += sum(float(r["probe_ITI"]) + PROBE_TOTAL for r in probes)
    total += N_BLOCKS * 2 * LEAD + (N_BLOCKS - 1) * BREAK
    need(total <= CAP_S, f"planned {total / 60:.1f} min > 60")
    return errs, len(rows), len(probes), total


def main():
    bad = 0
    for p in sys.argv[1:]:
        errs, n, k, total = check(p)
        status = "OK" if not errs else f"FAIL ({len(errs)})"
        print(f"{Path(p).name}: {status}  {n} trials, {k} probes, {total / 60:.1f} min")
        for e in errs[:10]:
            print("   ", e)
        bad += bool(errs)
    print(f"{len(sys.argv) - 1 - bad} of {len(sys.argv) - 1} designs pass")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
