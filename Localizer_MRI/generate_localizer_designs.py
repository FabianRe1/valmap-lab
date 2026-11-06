"""Per-participant designs for the alien MRI localizer (2026-10-13).

One session, 6 scanner blocks. The 12 classes are the main task's pictures (aliens_1-3,
spaceships_1-3, planets_1-3) and treasures (money, gold, diamonds), each shown as its VIDEO
(stimuli/videos/, 1.0 s in full, since 2026-10-23; before that the still picture for 0.75 s, kept in
designs_pictures/), centrally, after a fixation ITI. Probes show still images on grey
(stimuli/probe/ and stimuli/alternatives_grey/, manifest localizer_manifest_video.json).

Order (first order counterbalancing, decided 2026-10-13):
- one random Eulerian circuit over the multigraph holding every ordered pair of DIFFERENT classes
  N_CIRCUITS times (no self repeats): 12 * 11 * 5 = 660 transitions;
- cut into N_BLOCKS consecutive pieces of 110 transitions, so a block holds 111 trials and no
  transition is lost: every ordered pair occurs exactly N_CIRCUITS times inside blocks, so every
  class is preceded N_CIRCUITS times by each other class;
- a block's first trial has no preceding picture (the rest in between); the 6 block openers are 6
  DIFFERENT classes, so 6 classes are shown 56 times and 6 shown 55 times;
- within each block every class appears 8 to 11 times (9 or 10 as far as the search gets) and
  no ordered pair more than twice; reached by Kotzig swaps of the circuit (balanced_blocks), which
  never change the transitions, so the exact pair counts above always hold.

ITIs: makeITI exactly as in the old RepChanges localizer (truncated exponential, mean 3, range
[2, 7] s, drawn in batches of 10; its acceptance test only bounds the mean from BELOW, so the real
mean is about 3.26 s, kept on purpose). Stimulus and probe ITIs come from one pool per block, as in
the old design.

Probes (attention only): after PROBES_PER_CLASS trials of every class (about 9% of trials), never
on a block's first or last trial and at least MIN_PROBE_GAP trials apart. Two pictures, left and
right. MATCH probes (2/3) show the class just seen and a foil; NEITHER probes (1/3) show two foils.
Each shown picture is independently the task version or a replacement (half each, balanced per
probe kind), and replacements rotate through every view of a class (stimuli/alternatives/). Foils
are never the class just seen or the next trial's class and are balanced over classes. Response
window PROBE_MAX_RT (1.5 s), the probe screen plus feedback lasting PROBE_TOTAL (2 s) from probe
onset, as the old study actually ran.

Each design is checked against the time budget (scanning plus breaks at most SESSION_CAP_S) and
redrawn if it is over.

Since 2026-11-06 every class has ONE replacement view (aliens and spaceships alt3, planets_1 alt2,
the others their only one): the manifests list just that file, and the existing designs were
remapped to it by file name only (order, timing and probes unchanged; backup
../localizer_backup_before_one_alternative_2026-11-06.tgz).

Usage:  python3 generate_localizer_designs.py [--n 60] [--seed 20261013]
Writes designs/sub-XXX_localizer.csv (never overwrites; pass --force to replace).
"""
import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
# the video version (2026-10-23): videos as stimuli, still images on grey for the probes
MANIFEST = HERE / "stimuli" / "localizer_manifest_video.json"
OUT_DIR = HERE / "designs"

N_BLOCKS = 6
N_CIRCUITS = 5
T_STIM = 1.0                 # each video plays in full (1.0 s, decided 2026-10-23)
PROBES_PER_CLASS = 5
NEITHER_SHARE = 1 / 3
MIN_PROBE_GAP = 4
PROBE_MAX_RT = 1.5
PROBE_TOTAL = 2.0
T_BLOCK_LEAD_IN = 5.0
T_BLOCK_LEAD_OUT = 5.0
T_BREAK_PLAN = 30.0          # planned pause between blocks, for the budget only
SESSION_CAP_S = 3600.0
BLOCK_COUNT_HARD = (8, 11)
BLOCK_COUNT_SOFT = (9, 10)
ANNEAL_ITERS = 120000

COLUMNS = ["subject", "block", "trial", "trial_in_block", "stimulus", "stimulus_file",
           "prev_stimulus", "stimulus_ITI", "probe", "probe_ITI", "probe_kind", "probe_correct",
           "probe_left_class", "probe_left_version", "probe_left_file",
           "probe_right_class", "probe_right_version", "probe_right_file",
           "probe_max_rt", "probe_total"]


def makeITI(meaniti=3, rangeiti=(2, 7), N=60, maxdiviation=0.01, rng=np.random):
    """The old RepChanges makeITI, unchanged in behavior (one-sided acceptance test)."""
    worked = False
    while not worked:
        ITIt = rng.exponential(meaniti - rangeiti[0], N) + rangeiti[0]
        ITIt[ITIt > rangeiti[1]] = rangeiti[1]
        ITIt[ITIt < rangeiti[0]] = rangeiti[0]
        worked = (N * meaniti - sum(ITIt)) < maxdiviation
    return ITIt


def iti_pool(n, rng):
    """n ITIs drawn in batches of 10 (the remainder as one smaller batch), as the old design."""
    out = []
    while len(out) < n:
        out.extend(makeITI(N=min(10, n - len(out)), rng=rng))
    return list(out)


def euler_circuit(classes, rng):
    """Random Eulerian circuit (Hierholzer) over every ordered pair of different classes,
    N_CIRCUITS times each; returns the node sequence (first == last)."""
    out = {c: [d for d in classes if d != c] * N_CIRCUITS for c in classes}
    for c in classes:
        rng.shuffle(out[c])
    stack, path = [rng.choice(classes)], []
    while stack:
        v = stack[-1]
        if out[v]:
            stack.append(out[v].pop())
        else:
            path.append(stack.pop())
    return path[::-1]


def block_costs(seq, classes):
    """(hard, soft) violations of the per-block rules for a circuit cut at every PER_BLOCK
    transitions. Hard: the block openers differ, every class 8..11 times per block
    (BLOCK_COUNT_HARD), no ordered pair more than twice per block. Soft: counts outside 9..10
    (BLOCK_COUNT_SOFT) and, lightly, any pair repeated within a block."""
    per = (len(seq) - 1) // N_BLOCKS
    hard = N_BLOCKS - len({seq[b * per] for b in range(N_BLOCKS)})
    soft = 0.0
    for b in range(N_BLOCKS):
        blk = seq[b * per: b * per + per + 1]
        cnt = Counter(blk)
        for c in classes:
            n = cnt.get(c, 0)
            hard += max(0, BLOCK_COUNT_HARD[0] - n) + max(0, n - BLOCK_COUNT_HARD[1])
            soft += max(0, BLOCK_COUNT_SOFT[0] - n) + max(0, n - BLOCK_COUNT_SOFT[1])
        pairs = Counter(zip(blk[:-1], blk[1:]))
        hard += sum(max(0, v - 2) for v in pairs.values())
        soft += 0.2 * sum(max(0, v - 1) for v in pairs.values())
    return hard, soft


def kotzig(seq, classes, rng):
    """Swap the two closed walks between three visits i < j < k of one class: still an Eulerian
    circuit over exactly the same transitions, with its content moved between blocks."""
    a = rng.choice(classes)
    i, j, k = sorted(rng.sample([n for n, x in enumerate(seq) if x == a], 3))
    return seq[:i] + seq[j:k] + seq[i:j] + seq[k:]


def balanced_blocks(classes, rng):
    """A circuit annealed by Kotzig swaps until the hard block rules hold (soft ones as close as
    ANNEAL_ITERS allows), cut into N_BLOCKS blocks of equal transitions."""
    while True:
        seq = euler_circuit(classes, rng)
        h, s = block_costs(seq, classes)
        cost, temp = 10 * h + s, 2.0
        for _ in range(ANNEAL_ITERS):
            new = kotzig(seq, classes, rng)
            nh, ns = block_costs(new, classes)
            ncost = 10 * nh + ns
            if ncost <= cost or rng.random() < np.exp((cost - ncost) / temp):
                seq, cost, h, s = new, ncost, nh, ns
            temp = max(0.05, temp * 0.99995)
        if h == 0:
            per = (len(seq) - 1) // N_BLOCKS
            return [seq[b * per: b * per + per + 1] for b in range(N_BLOCKS)]


def place_probes(blocks, classes, rng):
    """Set of (block index, position) carrying a probe: PROBES_PER_CLASS per class, spread evenly
    over blocks, never on a block's first or last trial, at least MIN_PROBE_GAP apart."""
    total = PROBES_PER_CLASS * len(classes)
    per_block = [total // N_BLOCKS + (1 if b < total % N_BLOCKS else 0) for b in range(N_BLOCKS)]
    for _ in range(5000):
        need = Counter({c: PROBES_PER_CLASS for c in classes})
        chosen = set()
        for b, seq in enumerate(blocks):
            slots = list(range(1, len(seq) - 1))
            rng.shuffle(slots)
            picked = []
            for p in slots:
                if len(picked) == per_block[b]:
                    break
                if need[seq[p]] <= 0 or any(abs(p - q) < MIN_PROBE_GAP for q in picked):
                    continue
                picked.append(p)
                need[seq[p]] -= 1
            chosen |= {(b, p) for p in picked}
        if sum(need.values()) == 0:
            return chosen
    raise RuntimeError("could not place the probes")


def build_probes(blocks, probe_slots, manifest, rng):
    """Probe content for every slot, balanced: kinds, versions, foils, the correct side and the
    rotation through replacement views."""
    items = manifest["items"]
    classes = list(items)
    slots = sorted(probe_slots)
    n = len(slots)
    n_neither = round(n * NEITHER_SHARE)
    kinds = ["neither"] * n_neither + ["match"] * (n - n_neither)
    rng.shuffle(kinds)
    n_match = n - n_neither

    def halves(m):
        """m labels, task and alt (or left and right) as equal as possible, shuffled."""
        out = ["task", "alt"] * (m // 2) + ([rng.choice(["task", "alt"])] if m % 2 else [])
        rng.shuffle(out)
        return out

    match_sides = ["left" if v == "task" else "right" for v in halves(n_match)]
    # versions per shown picture: on match probes the target and the foil balanced separately
    target_versions, foil_versions = halves(n_match), halves(n_match)
    neither_versions = halves(2 * n_neither)
    alt_next = {c: rng.randrange(len(items[c]["alternatives"])) for c in classes}
    foil_use = Counter({c: 0 for c in classes})

    def picture(c, version):
        if version == "task":
            return items[c]["task"]
        alts = items[c]["alternatives"]
        f = alts[alt_next[c] % len(alts)]
        alt_next[c] += 1
        return f

    def pick_foil(excluded):
        options = [c for c in classes if c not in excluded]
        low = min(foil_use[c] for c in options)
        c = rng.choice([c for c in options if foil_use[c] == low])
        foil_use[c] += 1
        return c

    out = {}
    for (b, p), kind in zip(slots, kinds):
        seq = blocks[b]
        seen = seq[p]
        nxt = seq[p + 1] if p + 1 < len(seq) else None
        excluded = {seen, nxt}
        if kind == "match":
            foil = pick_foil(excluded)
            side = match_sides.pop()
            tv, fv = target_versions.pop(), foil_versions.pop()
            left, right = (seen, foil) if side == "left" else (foil, seen)
            lv, rv = (tv, fv) if side == "left" else (fv, tv)
            correct = side
        else:
            f1 = pick_foil(excluded)
            f2 = pick_foil(excluded | {f1})
            left, right = f1, f2
            lv, rv = neither_versions.pop(), neither_versions.pop()
            correct = "neither"
        out[(b, p)] = dict(probe_kind=kind, probe_correct=correct,
                           probe_left_class=left, probe_left_version=lv,
                           probe_left_file=picture(left, lv),
                           probe_right_class=right, probe_right_version=rv,
                           probe_right_file=picture(right, rv))
    return out


def session_seconds(rows):
    by_block = defaultdict(float)
    for r in rows:
        t = r["stimulus_ITI"] + T_STIM
        if r["probe"]:
            t += r["probe_ITI"] + PROBE_TOTAL
        by_block[r["block"]] += t
    blocks = sum(v + T_BLOCK_LEAD_IN + T_BLOCK_LEAD_OUT for v in by_block.values())
    return blocks + T_BREAK_PLAN * (N_BLOCKS - 1)


def design_for(subject, manifest, seed):
    rng = random.Random(seed)
    nrng = np.random.RandomState(seed % (2 ** 32))
    classes = list(manifest["items"])
    while True:
        blocks = balanced_blocks(classes, rng)
        slots = place_probes(blocks, classes, rng)
        probes = build_probes(blocks, slots, manifest, rng)
        rows, trial = [], 0
        for b, seq in enumerate(blocks):
            n_probe = sum(1 for (bb, _) in slots if bb == b)
            pool = iti_pool(len(seq) + n_probe, nrng)
            stim_iti, probe_iti = pool[: len(seq)], pool[len(seq):]
            for p, c in enumerate(seq):
                trial += 1
                row = {k: "" for k in COLUMNS}
                row.update(subject=subject, block=b + 1, trial=trial, trial_in_block=p + 1,
                           stimulus=c, stimulus_file=manifest["items"][c]["video"],
                           prev_stimulus=seq[p - 1] if p else "",
                           stimulus_ITI=round(float(stim_iti[p]), 6), probe=0)
                if (b, p) in slots:
                    row.update(probe=1, probe_ITI=round(float(probe_iti.pop()), 6),
                               probe_max_rt=PROBE_MAX_RT, probe_total=PROBE_TOTAL, **probes[(b, p)])
                rows.append(row)
        if session_seconds(rows) <= SESSION_CAP_S:
            return rows


def write_csv(path, rows):
    import csv
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=20261013)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    OUT_DIR.mkdir(exist_ok=True)
    for s in range(1, a.n + 1):
        subject = f"sub-{s:03d}"
        path = OUT_DIR / f"{subject}_localizer.csv"
        if path.exists() and not a.force:
            print(f"{path.name} exists, kept")
            continue
        rows = design_for(subject, manifest, a.seed * 1000 + s)
        write_csv(path, rows)
        print(f"{path.name}: {len(rows)} trials, {sum(r['probe'] for r in rows)} probes, "
              f"{session_seconds(rows) / 60:.1f} min planned")


if __name__ == "__main__":
    main()
