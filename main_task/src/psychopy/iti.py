"""
Jitter generation and the deterministic hashes shared with the jsPsych arm.

Everything here has a byte-for-byte equivalent in ../jspsych/iti.js. If you change one, change the
other and re-run tests/check_parity.py, which asserts both arms draw identical gap sequences.

Why a hand-rolled PRNG: the two arms must produce the same jitter for the same participant, and no
RNG is bit-identical between NumPy and JavaScript. mulberry32 is small enough to port exactly, and
inverse-CDF exponential sampling is mathematically identical to np.random.exponential.

Unlike the previous experiment (four gaps on every trial), trials here have a variable number of
gaps: one per shown event (each clip, and the outcome). Gaps are drawn and balanced
per RUN, then split per trial by each trial's event count. In the fMRI timing profile each trial
additionally carries exactly one long (~3 s) ISI at a randomly chosen slot.
"""

import math

MASK32 = 0xFFFFFFFF
MAX_ITI_ATTEMPTS = 200_000


def _imul(a, b):
    """32-bit multiply, matching JavaScript's Math.imul on the low 32 bits."""
    return (a * b) & MASK32


class Mulberry32:
    """Exact port of the mulberry32 PRNG. Returns floats in [0, 1)."""

    def __init__(self, seed):
        self.a = seed & MASK32

    def random(self):
        self.a = (self.a + 0x6D2B79F5) & MASK32
        a = self.a
        t = _imul(a ^ (a >> 15), 1 | a)
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & MASK32) ^ t
        t &= MASK32
        return ((t ^ (t >> 14)) & MASK32) / 4294967296.0


def hash32(*numbers):
    """FNV-1a over the four bytes of each argument. Identical in Python and JavaScript."""
    h = 2166136261
    for n in numbers:
        n &= MASK32
        for shift in (0, 8, 16, 24):
            h ^= (n >> shift) & 0xFF
            h = _imul(h, 16777619)
    return h & MASK32


def make_iti(meaniti=3, rangeiti=(2, 7), N=60, maxdiviation=0.01, rng=None, strict=False):
    """
    Faithful port of the lab's makeITI: exponential draws offset by the range minimum, clamped to
    the range, redrawn until the sum matches N * meaniti within tolerance.

    strict=False reproduces the original unsigned acceptance test `(N*mean - sum) < tol`, which
    only rejects sums that are too small. strict=True uses abs().
    """
    lo, hi = rangeiti[0], rangeiti[1]
    scale = meaniti - lo
    target = N * meaniti

    if rng is None:
        rng = Mulberry32(0)

    for _ in range(MAX_ITI_ATTEMPTS):
        itis = [-scale * math.log(1.0 - rng.random()) + lo for _ in range(N)]
        itis = [hi if x > hi else (lo if x < lo else x) for x in itis]
        deviation = target - sum(itis)
        worked = abs(deviation) < maxdiviation if strict else deviation < maxdiviation
        if worked:
            return itis

    raise RuntimeError(
        f"make_iti failed to converge in {MAX_ITI_ATTEMPTS} attempts "
        f"(N={N}, mean={meaniti}, range={rangeiti}, strict={strict})."
    )


def make_iti_numpy(meaniti=3, rangeiti=(2, 7), N=60, maxdiviation=0.01, seed=None, strict=False):
    """The original numpy function, for ITI_USE_NUMPY (gives up cross-arm parity, nothing else)."""
    import numpy as np

    rs = np.random.RandomState(seed) if seed is not None else np.random
    lo, hi = rangeiti[0], rangeiti[1]

    for _ in range(MAX_ITI_ATTEMPTS):
        itit = rs.exponential(meaniti - lo, N) + lo
        itit[itit > hi] = hi
        itit[itit < lo] = lo
        deviation = N * meaniti - itit.sum()
        worked = abs(deviation) < maxdiviation if strict else deviation < maxdiviation
        if worked:
            return list(itit)

    raise RuntimeError("make_iti_numpy failed to converge")


def order_trial_gaps(gaps, slot):
    """
    Move the longest gap into `slot`, leaving the rest in their drawn order. Permutation only, so
    the trial's total duration is unchanged. Ties resolve to the first occurrence (same rule as
    JavaScript indexOf, so both arms order identically).
    """
    longest = max(gaps)
    i = gaps.index(longest)
    rest = list(gaps[:i]) + list(gaps[i + 1:])
    return rest[:slot] + [longest] + rest[slot:]


def split_gaps(flat, counts, permute_flags, cfg):
    """
    Chop a flat draw into per-trial lists sized by `counts`. Where permute_flags[i] is true (full
    walks) the longest gap moves to the pre-outcome slot (second to last).
    """
    out = []
    pos = 0
    for n, permute in zip(counts, permute_flags):
        gaps = flat[pos:pos + n]
        pos += n
        if permute and cfg.LONGEST_GAP_BEFORE_OUTCOME and n >= 2:
            gaps = order_trial_gaps(gaps, n - 2)
        out.append(gaps)
    return out


def long_isi_slots(schedule_number, block_index, counts):
    """
    Which ISI slot of each trial carries the long (~3 s) interval, in the fMRI profile. Chosen
    deterministically from the same portable hash both arms use, so the draw is reproducible and
    identical across arms. A change trial has a single ISI, so its slot is 0 by construction.
    """
    return [hash32(schedule_number, block_index, 10 + i) % n if n else 0
            for i, n in enumerate(counts)]


def start_gaps_for_block(schedule_number, block_index, n_trials, cfg):
    """
    The fixation that OPENS every trial (decided 2026-09-11): mean TRIAL_START_MEAN (3 s) within
    TRIAL_START_RANGE, drawn with the same make_iti machinery as the ISIs and balanced across the
    block, seeded so both arms draw the same values (stream 3; the ISIs use 1 and 2).
    """
    if n_trials == 0:
        return []
    s = hash32(schedule_number, block_index, 3)
    if cfg.ITI_USE_NUMPY:
        return make_iti_numpy(cfg.TRIAL_START_MEAN, cfg.TRIAL_START_RANGE, n_trials,
                              cfg.GAP_MAX_DEVIATION, seed=s % (2 ** 31),
                              strict=cfg.ITI_STRICT_BALANCE)
    return make_iti(cfg.TRIAL_START_MEAN, cfg.TRIAL_START_RANGE, n_trials, cfg.GAP_MAX_DEVIATION,
                    rng=Mulberry32(s), strict=cfg.ITI_STRICT_BALANCE)


def gaps_for_block(schedule_number, block_index, counts, permute_flags, cfg):
    """
    Draw every gap for one block (a main run, or a practice/familiarization block).

    Without a long ISI (online and MEG) all sum(counts) intervals are drawn and balanced together,
    then split per trial. With one (fMRI) each trial gets exactly ONE long interval at a randomly
    chosen slot and the remaining slots are ordinary intervals; the ordinary intervals are balanced
    together across the block and the long ones are balanced among themselves.

    block_index seeds the draw: main runs use 1..N_RUNS, practice uses 801, familiarization
    attempts 901, 902, ... so every block is reproducible and distinct.
    """
    return add_clip_gap_extra(_draw_block_gaps(schedule_number, block_index, counts,
                                               permute_flags, cfg),
                              getattr(cfg, "CLIP_GAP_EXTRA", 0.0), permute_flags)


def add_clip_gap_extra(per_trial, extra, ends_on_outcome=None):
    """
    Lengthen every gap that follows a clip by `extra` seconds, leaving the gap after the outcome
    as drawn. A trial's last gap follows its outcome only if it has one: since 2026-10-05 the
    pair format ends on its second clip, so all its gaps are lengthened (`ends_on_outcome`, one
    flag per trial; without it every trial is taken to end on an outcome). A constant shift on top
    of the seeded draw, so the draw itself and its balancing are unchanged. Mirrors
    addClipGapExtra in ../jspsych/iti.js.
    """
    if not extra:
        return per_trial
    flags = ends_on_outcome if ends_on_outcome is not None else [True] * len(per_trial)
    return [([g + extra for g in gaps[:-1]] + gaps[-1:]) if out else [g + extra for g in gaps]
            for gaps, out in zip(per_trial, flags)]


def _draw_block_gaps(schedule_number, block_index, counts, permute_flags, cfg):
    seed = hash32(schedule_number, block_index, 1)

    def draw(mean, rng_range, n, s):
        if n == 0:
            return []
        if cfg.ITI_USE_NUMPY:
            return make_iti_numpy(mean, rng_range, n, cfg.GAP_MAX_DEVIATION,
                                  seed=s % (2 ** 31), strict=cfg.ITI_STRICT_BALANCE)
        return make_iti(mean, rng_range, n, cfg.GAP_MAX_DEVIATION,
                        rng=Mulberry32(s), strict=cfg.ITI_STRICT_BALANCE)

    long_isi = getattr(cfg, "LONG_ISI", None)
    if not long_isi:
        flat = draw(cfg.GAP_MEAN, cfg.GAP_RANGE, sum(counts), seed)
        return split_gaps(flat, counts, permute_flags, cfg)

    n_trials = len(counts)
    short = draw(cfg.GAP_MEAN, cfg.GAP_RANGE, sum(counts) - n_trials, seed)
    longs = draw(long_isi, cfg.LONG_ISI_RANGE, n_trials,
                 hash32(schedule_number, block_index, 2))
    slots = long_isi_slots(schedule_number, block_index, counts)

    out = []
    pos = 0
    for i, n in enumerate(counts):
        rest = short[pos:pos + n - 1]
        pos += n - 1
        slot = slots[i]
        out.append(list(rest[:slot]) + [longs[i]] + list(rest[slot:]))
    return out
