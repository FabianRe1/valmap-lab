"""Alien MRI localizer, PsychoPy (2026-10-13).

Presents a pre-generated design (designs/sub-XXX_localizer.csv, built by
generate_localizer_designs.py) in the scanner: instructions, a button check, then 6 blocks, each
started by the operator (space) and the scanner's first trigger 't' (the block's t0). Per trial a
fixation for `stimulus_ITI`, the video for T_STIM (its pre-decoded frames, refresh-locked, on the
grey background, since 2026-10-23); on probe trials a fixation for `probe_ITI`, two
pictures (left / right / neither), feedback until PROBE_TOTAL after probe onset, or a timeout
message. Everything the trial shows comes from the design row; nothing is recomputed.

Output: ONE tab-separated file per run in data/ (never overwritten, flushed after every row), one
row per screen change with the MEASURED onset (flip time, seconds from the block's t0) and duration.

Run (PsychoPy's own Python, as the main task):
  export PYTHONHOME=/Applications/PsychoPy.app/Contents/Resources
  PY=/Applications/PsychoPy.app/Contents/MacOS/python
  $PY run_localizer.py --design 1 --participant FaRe1995
  $PY run_localizer.py --design 1 --participant FaRe1995 --start-block 4   # after a crash
  python3 run_localizer.py --design 1 --plan-only        # check + timing plan, no window
  $PY run_localizer.py --design 1 --dry-run --keyboard-backend event   # fast-forward, simulated answers
  $PY run_localizer.py --design 900 --dry-run --real-time --keyboard-backend event   # timing test
"""
import argparse
import csv
import datetime
import json
import math
import random
import re
import sys
from pathlib import Path

import config as cfg
import strings_de as txt

DESIGN_FLOATS = ("stimulus_ITI", "probe_ITI", "probe_max_rt", "probe_total")
DESIGN_INTS = ("block", "trial", "trial_in_block", "probe")
KEPT_DESIGN_COLUMNS = ("prev_stimulus", "stimulus_ITI", "probe", "probe_ITI", "probe_kind",
                       "probe_correct", "probe_left_class", "probe_left_version", "probe_left_file",
                       "probe_right_class", "probe_right_version", "probe_right_file")
LOG_COLUMNS = (("subj_id", "design", "block", "trial", "trial_in_block", "event", "onset",
                "duration", "time_abs", "stimulus", "image", "response", "rt", "correct")
               + KEPT_DESIGN_COLUMNS + ("note",))



def ptb_key_time(k, now):
    """A ptb key press's time on core.getTime's timebase (2026-11-04). PsychoPy's KeyPress.tDown
    counts from the moment the Keyboard was created, while flips and core.getTime count from
    PsychoPy's start: using tDown directly put every key time (the trigger, so every onset of the
    block, and every reaction time) about 4 s early, found in a real (not dry) localizer run.
    The press's age on ptb's own clock, taken from now, is independent of both zero points. A
    time that is in the future or more than 2 s old falls back to now, with one warning."""
    from psychopy.hardware import keyboard as _kb
    import psychtoolbox as _ptb
    t_now = now()
    age = _ptb.GetSecs() - (k.tDown + getattr(_kb.Keyboard, "_ptbOffset", 0.0))
    if -0.01 <= age <= 2.0:
        return t_now - age
    if not getattr(ptb_key_time, "warned", False):
        print(f"WARNING: key time {age:.3f} s old, implausible; using the polling time instead")
        ptb_key_time.warned = True
    return t_now

def ptb_new_presses(kb, keys, seen):
    """Presses of `keys` not returned before, held or already released (2026-11-10). PsychoPy
    2026's getKeys(waitRelease=False) skips a press once its key is up, so a short press (the
    scanner's button box: down and up within a few ms) released before the next poll was lost;
    a release also re-adds the press it ends. Both lists are read; `seen` (a deque of KeyPress
    objects) keeps each press to one report. PsychoPy 2023 returned released presses as well."""
    out = []
    for k in kb.getKeys(keys, waitRelease=False) + kb.getKeys(keys, waitRelease=True):
        if not any(k is s for s in seen):
            seen.append(k)
            out.append(k)
    return out


def ptb_mark_held(kb, seen):
    """After clearEvents: a key still held belongs to the screen before, so its release must not
    count as a new press on the next one."""
    for k in list(getattr(getattr(kb, "device", None), "_keysStillDown", []) or []):
        seen.append(k)


class QuitExperiment(Exception):
    pass


# ---------------------------------------------------------------------------
# Design
# ---------------------------------------------------------------------------

def design_path(number):
    return cfg.DESIGN_DIR / f"sub-{int(number):03d}_localizer.csv"


def load_design(path):
    rows = list(csv.DictReader(open(path)))
    for r in rows:
        for k in DESIGN_INTS:
            r[k] = int(r[k])
        for k in DESIGN_FLOATS:
            r[k] = float(r[k]) if r[k] != "" else None
    return rows


def check_design(rows):
    """Presentation-side checks: the probe timing matches config and every picture exists."""
    errors = []
    for r in rows:
        for f in [r["stimulus_file"]] + ([r["probe_left_file"], r["probe_right_file"]] if r["probe"] else []):
            if not (cfg.STIM_DIR / f).exists():
                errors.append(f"trial {r['trial']}: missing {f}")
        if r["probe"] and (r["probe_max_rt"] != cfg.PROBE_MAX_RT or r["probe_total"] != cfg.PROBE_TOTAL):
            errors.append(f"trial {r['trial']}: probe timing differs from config")
    for k in cfg.FEEDBACK_IMAGES.values():
        if not k.exists():
            errors.append(f"missing {k}")
    return errors


def blocks_of(rows):
    out = {}
    for r in rows:
        out.setdefault(r["block"], []).append(r)
    return [out[b] for b in sorted(out)]


def plan_report(rows):
    lines, total = [], 0.0
    for blk in blocks_of(rows):
        t = cfg.T_BLOCK_LEAD_IN + cfg.T_BLOCK_LEAD_OUT
        t += sum(r["stimulus_ITI"] + cfg.T_STIM for r in blk)
        t += sum(r["probe_ITI"] + cfg.PROBE_TOTAL for r in blk if r["probe"])
        total += t
        lines.append(f"  block {blk[0]['block']}: {len(blk)} trials, "
                     f"{sum(r['probe'] for r in blk)} probes, {t / 60:.2f} min from trigger to block end")
    lines.append(f"  scanning total {total / 60:.1f} min (plus pauses, timeouts and trigger waits)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class Logger:
    """One TSV per run; a row per screen change, flushed at once."""

    def __init__(self, path, subj_id, design):
        self.f = open(path, "x", newline="", encoding="utf-8")    # "x": never overwrite
        self.w = csv.DictWriter(self.f, fieldnames=LOG_COLUMNS, delimiter="\t", extrasaction="ignore")
        self.w.writeheader()
        self.base = {"subj_id": subj_id, "design": design}
        self.path = path

    def write(self, **row):
        out = dict(self.base)
        out.update({k: ("" if v is None else v) for k, v in row.items()})
        for k in ("onset", "duration", "time_abs", "rt"):
            if isinstance(out.get(k), float):
                out[k] = f"{out[k]:.6f}"
        self.w.writerow(out)
        self.f.flush()

    def meta(self, key, value):
        self.write(event="meta", note=f"{key}={value}")

    def trial_row(self, r, event, onset, duration, t_abs, **extra):
        row = {k: r[k] for k in KEPT_DESIGN_COLUMNS}
        row.update(block=r["block"], trial=r["trial"], trial_in_block=r["trial_in_block"],
                   event=event, onset=onset, duration=duration, time_abs=t_abs,
                   stimulus=r["stimulus"])
        row.update(extra)
        self.write(**row)

    def close(self):
        self.f.close()


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

class Presenter:
    def __init__(self, rows, dry_run, real_time=False):
        from psychopy import core, visual
        from psychopy.hardware import keyboard
        from PIL import Image

        self.dry_run = dry_run
        self.scale = cfg.DRY_RUN_SCALE if dry_run and not real_time else 1.0
        self.win = visual.Window(size=cfg.WINDOW_SIZE, fullscr=cfg.FULLSCREEN and not dry_run,
                                 screen=cfg.SCREEN, color=cfg.BACKGROUND_COLOR, units=cfg.UNITS,
                                 allowGUI=False, checkTiming=True)
        self.win.mouseVisible = False
        self.now = core.getTime          # one timebase: flips; ptb key times via ptb_key_time
        self.kb = keyboard.Keyboard(backend=cfg.KEYBOARD_BACKEND)
        self._kb_seen = __import__("collections").deque(maxlen=256)   # see ptb_new_presses
        self.frame_dur = self.win.monitorFramePeriod or (1 / 60.0)
        measured = self.win.getActualFrameRate(nIdentical=10, nMaxFrames=120, nWarmUpFrames=10)
        if measured:
            self.frame_dur = 1.0 / measured
        self.in_run = False
        self.rng = random.Random(1)

        self.fixation = visual.TextStim(self.win, text=cfg.FIXATION_TEXT, height=cfg.FIXATION_HEIGHT,
                                        color=cfg.FIXATION_COLOR)
        self.text = visual.TextStim(self.win, text="", height=cfg.TEXT_HEIGHT, color=cfg.TEXT_COLOR,
                                    wrapWidth=cfg.TEXT_WRAP, alignText="center")
        self.footer = visual.TextStim(self.win, text="", height=cfg.FOOTER_HEIGHT,
                                      color=cfg.TEXT_COLOR, pos=(0, cfg.FOOTER_Y))
        # every video as its pre-decoded frames, one ImageStim each (2026-10-23): shown as a
        # refresh-locked sequence, so frame 0 is on screen at the logged onset
        items = json.loads(cfg.MANIFEST.read_text())["items"]
        self.videos = {}
        for c in sorted({r["stimulus"] for r in rows}):
            self.videos[c] = (items[c]["fps"],
                              [visual.ImageStim(self.win, image=str(cfg.STIM_DIR / f),
                                                size=(cfg.STIM_HEIGHT, cfg.STIM_HEIGHT))
                               for f in items[c]["frames"]])
        # preload every probe picture the design can show, each as its own ImageStim
        files = set()
        for r in rows:
            if r["probe"]:
                files.update([r["probe_left_file"], r["probe_right_file"]])
        self.images = {}
        for f in sorted(files):
            with Image.open(cfg.STIM_DIR / f) as im:
                w, h = im.size
            self.images[f] = (visual.ImageStim(self.win, image=str(cfg.STIM_DIR / f)), w / h)
        self.feedback = {k: visual.ImageStim(self.win, image=str(p),
                                             size=(cfg.FEEDBACK_HEIGHT, cfg.FEEDBACK_HEIGHT))
                         for k, p in cfg.FEEDBACK_IMAGES.items()}

    def image(self, f, height, x=0.0):
        stim, aspect = self.images[f]
        stim.size = (height * aspect, height)
        stim.pos = (x, 0)
        return stim

    # -- keys and flips ------------------------------------------------------------------

    def poll(self, keys):
        if self.dry_run:
            return []
        if cfg.KEYBOARD_BACKEND == "ptb":
            return [(k.name, ptb_key_time(k, self.now)) for k in ptb_new_presses(self.kb, list(keys), self._kb_seen)]
        from psychopy import event
        return [(name, self.now()) for name in event.getKeys(list(keys))]

    def flip(self):
        t = self.win.flip()
        watched = list(cfg.KEY_QUIT) + (list(cfg.TRIGGER_KEYS) if self.in_run else [])
        for name, _ in self.poll(watched):
            if name in cfg.KEY_QUIT:
                raise QuitExperiment      # later trigger pulses of a run are swallowed here
        return t

    def clear_keys(self):
        if not self.dry_run:
            self.kb.clearEvents()
            ptb_mark_held(self.kb, self._kb_seen)
            from psychopy import event
            event.clearEvents()

    def present(self, duration, draw):
        """Draw every frame until `duration` (scaled in a dry run) has passed since the first
        flip; returns (onset, measured duration)."""
        target = duration * self.scale
        half = self.frame_dur * 0.5
        onset = None
        while True:
            draw()
            t = self.flip()
            if onset is None:
                onset = t
            if self.now() - onset >= target - half:
                return onset, self.now() - onset

    def present_video(self, item):
        """One video for T_STIM as its frames, refresh-locked: each refresh shows the frame due at
        that refresh's predicted time since onset (frame 0 at onset), so a dropped refresh never
        stretches the video. Returns (onset, measured duration, number of distinct frames shown)."""
        fps, frames = self.videos[item]
        target = cfg.T_STIM * self.scale
        half = self.frame_dur * 0.5
        onset = last = None
        shown = set()
        while True:
            k = 0 if onset is None else min(
                len(frames) - 1,
                math.floor((last + self.frame_dur - onset) / self.scale * fps + 1e-6))
            frames[k].draw()
            t = self.flip()
            shown.add(k)
            if onset is None:
                onset = t
            last = t
            if self.now() - onset >= target - half:
                return onset, self.now() - onset, len(shown)

    def wait_keys(self, keys, draw, max_wait=None):
        """Show `draw` until one of `keys` (or max_wait seconds); returns (key, key time, onset).
        A dry run presses the first key after two frames."""
        self.clear_keys()
        onset, frames = None, 0
        while True:
            draw()
            t = self.flip()
            frames += 1
            if onset is None:
                onset = t
            if self.dry_run and frames >= 2:
                return keys[0], self.now(), onset
            for name, t_down in self.poll(list(keys) + list(cfg.KEY_QUIT)):
                if name in cfg.KEY_QUIT:
                    raise QuitExperiment
                return name, t_down, onset
            if max_wait is not None and self.now() - onset >= max_wait * self.scale:
                return None, None, onset

    def message(self, text, keys=cfg.KEY_CONTINUE, footer=txt.FOOTER_CONTINUE, max_wait=None):
        def draw():
            self.text.text = text
            self.text.draw()
            if footer:
                self.footer.text = footer
                self.footer.draw()
        return self.wait_keys(keys, draw, max_wait)

    # -- probe ---------------------------------------------------------------------------

    def run_probe(self, r):
        """Two pictures until an answer or PROBE_MAX_RT. Returns (onset, response, key time)."""
        left = self.image(r["probe_left_file"], cfg.PROBE_HEIGHT, -cfg.PROBE_X)
        right = self.image(r["probe_right_file"], cfg.PROBE_HEIGHT, cfg.PROBE_X)
        answer_keys = {**{k: "left" for k in cfg.KEY_LEFT}, **{k: "right" for k in cfg.KEY_RIGHT},
                       **{k: "neither" for k in cfg.KEY_NEITHER}}
        sim = None
        if self.dry_run:          # simulated participant: 90 % correct, 5 % too slow
            u = self.rng.random()
            answer = (r["probe_correct"] if u < 0.9
                      else self.rng.choice([a for a in ("left", "right", "neither") if a != r["probe_correct"]]))
            sim = (None if u > 0.95 else answer, self.rng.uniform(0.3, 1.4) * self.scale)
        self.clear_keys()
        half = self.frame_dur * 0.5
        onset = None
        while True:
            left.draw()
            right.draw()
            t = self.flip()
            if onset is None:
                onset = t
            if sim is not None and sim[0] is not None and self.now() - onset >= sim[1]:
                return onset, sim[0], self.now()
            for name, t_down in self.poll(answer_keys):
                return onset, answer_keys[name], t_down
            if self.now() - onset >= cfg.PROBE_MAX_RT * self.scale - half:
                return onset, None, None


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

def file_prefix(subj_id, design):
    """n-NN_sub-CODE, the start of every data file name (user, 2026-11-09): N the design = subject
    number, so the files of all tasks sort by subject; CODE the participant code (sub-NNN without one)."""
    code = subj_id if subj_id.startswith("sub-") else f"sub-{subj_id}"
    return f"n-{int(design):02d}_{code}"


def earlier_probe_results(subj_id, design, start_block):
    """Probe outcomes of blocks before `start_block` from this participant's earlier runs, so the
    bonus after a restart still counts them (latest file wins per trial)."""
    results = {}
    # the files since 2026-11-09 (n-NN_sub-CODE_...) and before (CODE_...)
    paths = set(cfg.DATA_DIR.glob(f"{file_prefix(subj_id, design)}_design-{design}_localizer_*.tsv"))
    paths |= set(cfg.DATA_DIR.glob(f"{subj_id}_design-{design}_localizer_*.tsv"))
    for p in sorted(paths):
        for row in csv.DictReader(open(p, encoding="utf-8"), delimiter="\t"):
            if row["event"] == "probe" and row["block"] and int(row["block"]) < start_block:
                results[(int(row["block"]), int(row["trial"]))] = row["correct"]
    return results


def bonus_percent(outcomes):
    """As the old study: correct / (correct + wrong); timeouts are not counted."""
    scored = [o for o in outcomes if o in ("1", "0", 1, 0)]
    return round(100 * sum(int(o) for o in scored) / len(scored)) if scored else 0


def run(args):
    path = design_path(args.design)
    rows = load_design(path)
    errors = check_design(rows)
    if errors:
        sys.exit("design check failed:\n  " + "\n  ".join(errors[:20]))
    blocks = blocks_of(rows)
    print(f"{path.name}: {len(rows)} trials in {len(blocks)} blocks")
    print(plan_report(rows))
    if args.plan_only:
        return

    if args.keyboard_backend:
        cfg.KEYBOARD_BACKEND = args.keyboard_backend
    cfg.DATA_DIR.mkdir(exist_ok=True)
    subj = args.participant or f"sub-{int(args.design):03d}"
    # the participant database code (2026-10-28, e.g. 27985.cb), the same in every session
    if not re.fullmatch(r"[A-Za-z0-9.\-]+", subj):
        sys.exit(f"--participant {subj!r}: only letters, digits and dots, e.g. 27985.cb")
    design = f"{int(args.design):03d}"
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    tag = "_dryrun" if args.dry_run else ""
    log = Logger(cfg.DATA_DIR / f"{file_prefix(subj, design)}_design-{design}_localizer_{stamp}{tag}.tsv", subj, design)
    for k, v in (("design_file", path.name), ("start_block", args.start_block),
                 ("dry_run", int(args.dry_run)), ("keyboard_backend", cfg.KEYBOARD_BACKEND),
                 ("started", stamp)):
        log.meta(k, v)
    outcomes = dict(earlier_probe_results(subj, design, args.start_block))
    restarted = args.start_block > 1

    pres = Presenter(rows, args.dry_run, args.real_time)
    log.meta("refresh_hz", f"{1 / pres.frame_dur:.2f}")
    try:
        if restarted:
            pres.message(txt.RESTARTED.format(block=args.start_block))
        else:
            for page in txt.INSTRUCTIONS:
                pres.message(page)
            pres.message(txt.CHECK_INTRO)
            for key, accepted in cfg.BUTTON_CHECK:
                name, _, onset = pres.message(txt.BUTTON_CHECK[key], keys=accepted, footer="")
                log.write(event="button_check", time_abs=onset, response=name, note=key)
            pres.message(txt.READY)

        n_total = len(rows)
        for blk in blocks:
            b = blk[0]["block"]
            if b < args.start_block:
                continue
            pres.message(txt.OPERATOR.format(block=b, n_blocks=len(blocks)), keys=cfg.KEY_OPERATOR, footer="")
            _, t_trig, _ = pres.message(txt.WAIT_SCANNER, keys=cfg.TRIGGER_KEYS, footer="")
            t0 = t_trig
            pres.in_run = True
            log.write(block=b, event="trigger", onset=0.0, time_abs=t0)

            on, dur = pres.present(cfg.T_BLOCK_LEAD_IN, pres.fixation.draw)
            log.write(block=b, event="block_lead_in", onset=on - t0, duration=dur, time_abs=on)
            for r in blk:
                on, dur = pres.present(r["stimulus_ITI"], pres.fixation.draw)
                log.trial_row(r, "fixation", on - t0, dur, on)
                on, dur, n_frames = pres.present_video(r["stimulus"])
                log.trial_row(r, "stimulus", on - t0, dur, on, image=r["stimulus_file"],
                              note=f"video_frames={n_frames}")
                if not r["probe"]:
                    continue
                on, dur = pres.present(r["probe_ITI"], pres.fixation.draw)
                log.trial_row(r, "probe_fixation", on - t0, dur, on)
                p_on, resp, t_key = pres.run_probe(r)
                if resp is None:
                    _, _, t_on = pres.message(txt.TIMEOUT, footer="", max_wait=cfg.TIMEOUT_MAX)
                    log.trial_row(r, "probe", p_on - t0, t_on - p_on, p_on, response="timed_out",
                                  correct="timed_out")
                    outcomes[(b, r["trial"])] = "timed_out"
                    log.trial_row(r, "timeout", t_on - t0, pres.now() - t_on, t_on)
                    continue
                correct = int(resp == r["probe_correct"])
                outcomes[(b, r["trial"])] = correct
                fb = pres.feedback["correct" if correct else "incorrect"]
                remaining = max(0.0, cfg.PROBE_TOTAL * pres.scale - (pres.now() - p_on)) / pres.scale
                f_on, f_dur = pres.present(remaining, fb.draw)
                log.trial_row(r, "probe", p_on - t0, f_on - p_on, p_on, response=resp,
                              rt=t_key - p_on, correct=correct)
                log.trial_row(r, "feedback", f_on - t0, f_dur, f_on, correct=correct)

            on, dur = pres.present(cfg.T_BLOCK_LEAD_OUT, pres.fixation.draw)
            log.write(block=b, event="block_lead_out", onset=on - t0, duration=dur, time_abs=on)
            pres.in_run = False
            done = round(100 * blk[-1]["trial"] / n_total)
            block_outcomes = [v for (bb, _), v in outcomes.items() if bb == b]
            if b == blocks[-1][0]["block"]:
                break
            text = txt.BLOCK_DONE.format(done=done, bonus=bonus_percent(block_outcomes))
            _, _, on = pres.message(text)
            log.write(block=b, event="block_feedback", time_abs=on,
                      note=f"bonus_block={bonus_percent(block_outcomes)}")

        on, dur = pres.present(cfg.FINAL_FIXATION, pres.fixation.draw)
        bonus = bonus_percent(outcomes.values())
        log.meta("bonus_percent", bonus)
        bonus_file = cfg.DATA_DIR / f"{file_prefix(subj, design)}_design-{design}_bonus_{stamp}{tag}.txt"
        bonus_file.write_text(f"{bonus}\n")
        pres.message(txt.GOODBYE.format(bonus=bonus), keys=cfg.KEY_OPERATOR, footer="")
        log.meta("session_end", "complete")
    except QuitExperiment:
        log.meta("session_end", "quit")
        print("quit by escape; data saved to", log.path)
    finally:
        log.close()
        pres.win.close()
    print("data:", log.path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", required=True, help="design number N, reads designs/sub-NNN_localizer.csv")
    ap.add_argument("--participant", default="",
                    help="the participant database code, e.g. 27985.cb (letters, digits, dots)")
    ap.add_argument("--start-block", type=int, default=1)
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--real-time", action="store_true",
                    help="with --dry-run: simulated answers but true durations (timing test)")
    ap.add_argument("--keyboard-backend", choices=("ptb", "event"))
    run(ap.parse_args())


if __name__ == "__main__":
    main()
