"""Alien MEG localizer, PsychoPy (2026-10-13).

The MRI localizer's runtime (../Localizer_MRI/run_localizer.py) with MEG markers. Presents a
pre-generated design (designs/sub-XXX_localizer_meg.csv, built by generate_localizer_designs.py):
instructions, a button check, then 6 blocks, each started by the operator (space) and the
experimenter's 't' (the block's t0). Per trial a fixation for `stimulus_ITI`, the picture's video
for T_STIM (its pre-decoded frames, refresh-locked, as in the MRI localizer; stills before
2026-10-28); on probe trials a fixation for `probe_ITI`, two pictures (left / right / neither), feedback
until PROBE_TOTAL after probe onset, or a timeout message. Everything the trial shows comes from
the design row; nothing is recomputed.

Markers (config.py): a code right after the flip that shows each event (picture = its class
1..12, fixation, probe fixation, probe, feedback, timeout), a response code when the key press is
read, 100 + block at t0 and 110 + block at the block's end. No photodiode. MEG lab rules
(2026-10-14): codes 1..127 only, each held 20 ms on a timer (the drawing loop never sleeps), and
no code before the line has been back at 0 for MARKER_MIN_GAP; the feedback after an answer waits
for that (the probe stays up meanwhile). If the marker backend or the button box cannot start,
the operator must confirm before anything runs without them.

Responses: the keyboard always; with --button-box (or config.BUTTON_BOX) also the MEG's serial
response box (responses.py), whose bytes arrive as "btn1".."btn4".

Output: ONE tab-separated file per run in data/ (never overwritten, flushed after every row), one
row per screen change with the MEASURED onset (flip time, seconds from the block's t0), duration
and the marker code sent.

Run (PsychoPy's own Python, as the main task):
  export PYTHONHOME=/Applications/PsychoPy.app/Contents/Resources
  PY=/Applications/PsychoPy.app/Contents/MacOS/python
  $PY run_localizer.py --design 1 --participant FaRe1995 --marker-backend parallel

In the MEG lab (Linux PC "faecherfisch", PsychoPy installed there; use its python, no PYTHONHOME):
  python run_localizer.py --design 1 --participant FaRe1995 --marker-backend parallel --button-box
  python test_meg_io.py          # first: check codes reach the MEG and read the button bytes
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
import time
from pathlib import Path

import config as cfg
import strings_de as txt

VIDEO_ITEMS = json.loads(cfg.MANIFEST.read_text())["items"]
DESIGN_FLOATS = ("stimulus_ITI", "probe_ITI", "probe_max_rt", "probe_total")
DESIGN_INTS = ("block", "trial", "trial_in_block", "probe")
KEPT_DESIGN_COLUMNS = ("prev_stimulus", "stimulus_ITI", "probe", "probe_ITI", "probe_kind",
                       "probe_correct", "probe_left_class", "probe_left_version", "probe_left_file",
                       "probe_right_class", "probe_right_version", "probe_right_file")
LOG_COLUMNS = (("subj_id", "design", "block", "trial", "trial_in_block", "event", "onset",
                "duration", "time_abs", "marker", "stimulus", "image", "response", "rt", "correct")
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

class QuitExperiment(Exception):
    pass


# ---------------------------------------------------------------------------
# Design
# ---------------------------------------------------------------------------

def design_path(number):
    return cfg.DESIGN_DIR / f"sub-{int(number):03d}_localizer_meg.csv"


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
        frames = VIDEO_ITEMS.get(r["stimulus"], {}).get("frames")
        if not frames or not all((cfg.STIM_DIR / f).exists() for f in frames):
            errors.append(f"trial {r['trial']}: missing video frames of {r['stimulus']}")
        if r["stimulus"] not in cfg.CLASS_CODES:
            errors.append(f"trial {r['trial']}: no marker code for {r['stimulus']}")
    for k in cfg.FEEDBACK_IMAGES.values():
        if not k.exists():
            errors.append(f"missing {k}")
    n_blocks = max(r["block"] for r in rows)
    codes = list(cfg.CLASS_CODES.values()) + [v for k, v in cfg.MARKER_CODES.items()
                                              if not k.startswith("block_")]
    codes += [cfg.MARKER_CODES[k] + b for k in ("block_start", "block_end") for b in range(1, n_blocks + 1)]
    for c in codes:
        if not 0 < c <= cfg.MARKER_MAX_CODE:
            errors.append(f"marker code {c} outside 1..{cfg.MARKER_MAX_CODE}")
    if len(set(codes)) != len(codes):
        errors.append("marker codes not unique")
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
    lines.append(f"  recording total {total / 60:.1f} min (plus pauses, timeouts and start waits)")
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
    def __init__(self, rows, dry_run, real_time=False, marker=None, buttons=None):
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
        self.frame_dur = self.win.monitorFramePeriod or (1 / 60.0)
        measured = self.win.getActualFrameRate(nIdentical=10, nMaxFrames=120, nWarmUpFrames=10)
        if measured:
            self.frame_dur = 1.0 / measured
        self.in_run = False
        self.rng = random.Random(1)
        self.marker = marker
        self.buttons = buttons
        self.marker_holds = 0     # coded flips that had to wait for the previous pulse

        self.fixation = visual.TextStim(self.win, text=cfg.FIXATION_TEXT, height=cfg.FIXATION_HEIGHT,
                                        color=cfg.FIXATION_COLOR)
        self.text = visual.TextStim(self.win, text="", height=cfg.TEXT_HEIGHT, color=cfg.TEXT_COLOR,
                                    wrapWidth=cfg.TEXT_WRAP, alignText="center")
        self.footer = visual.TextStim(self.win, text="", height=cfg.FOOTER_HEIGHT,
                                      color=cfg.TEXT_COLOR, pos=(0, cfg.FOOTER_Y))
        # every video as its pre-decoded frames, one ImageStim each (2026-10-28, as the MRI
        # localizer): shown as a refresh-locked sequence, so frame 0 is on screen at the onset
        self.videos = {}
        for c in sorted({r["stimulus"] for r in rows}):
            self.videos[c] = (VIDEO_ITEMS[c]["fps"],
                              [visual.ImageStim(self.win, image=str(cfg.STIM_DIR / f),
                                                size=(cfg.STIM_HEIGHT, cfg.STIM_HEIGHT))
                               for f in VIDEO_ITEMS[c]["frames"]])
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
        """Presses of `keys` since the last poll, as [(name, time)]. Button box names ("btn<n>")
        are read from the serial box only when `keys` asks for one, so the per-frame quit check
        in flip() never swallows a button press."""
        if self.dry_run:
            return []
        board = [k for k in keys if k not in cfg.BUTTONS]
        out = []
        if self.buttons is not None and len(board) < len(keys):
            out = [(n, t) for n, t in self.buttons.read() if n in keys]
        if cfg.KEYBOARD_BACKEND == "ptb":
            out += [(k.name, ptb_key_time(k, self.now)) for k in self.kb.getKeys(board, waitRelease=False)]
        else:
            from psychopy import event
            out += [(name, self.now()) for name in event.getKeys(board)]
        return out

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
            from psychopy import event
            event.clearEvents()
            if self.buttons is not None:
                self.buttons.clear()

    def send(self, code, label):
        if self.marker is not None and code is not None:
            self.marker.send(code, label)

    def marker_busy(self):
        return self.marker is not None and self.marker.busy()

    def hold_marker(self, draw):
        """Keep showing `draw` until the previous marker pulse is over and the line has been 0
        for MARKER_MIN_GAP, so the next coded flip gets a clean code of its own."""
        while self.marker_busy():
            draw()
            self.flip()

    def wait_marker(self):
        """Last resort before a coded flip: wait (without flipping) for a pulse still up. The
        design never needs this; it is counted and reported at the end."""
        if self.marker_busy():
            self.marker_holds += 1
            while self.marker_busy():
                time.sleep(0.0005)    # yields, so the reset thread can run

    def present(self, duration, draw, code=None, label=""):
        """Draw every frame until `duration` (scaled in a dry run) has passed since the first
        flip, sending marker `code` right after that flip; returns (onset, measured duration)."""
        target = duration * self.scale
        half = self.frame_dur * 0.5
        onset = None
        if code is not None:
            self.wait_marker()
        while True:
            draw()
            t = self.flip()
            if onset is None:
                onset = t
                self.send(code, label)
            if self.now() - onset >= target - half:
                return onset, self.now() - onset

    def present_video(self, item, code=None, label=""):
        """One video for T_STIM as its frames, refresh-locked: each refresh shows the frame due at
        that refresh's predicted time since onset (frame 0 at onset), so a dropped refresh never
        stretches the video. Marker `code` goes out right after the first flip. Returns (onset,
        measured duration, number of distinct frames shown)."""
        fps, frames = self.videos[item]
        target = cfg.T_STIM * self.scale
        half = self.frame_dur * 0.5
        onset = last = None
        shown = set()
        if code is not None:
            self.wait_marker()
        while True:
            k = 0 if onset is None else min(
                len(frames) - 1,
                math.floor((last + self.frame_dur - onset) / self.scale * fps + 1e-6))
            frames[k].draw()
            t = self.flip()
            shown.add(k)
            if onset is None:
                onset = t
                self.send(code, label)
            last = t
            if self.now() - onset >= target - half:
                return onset, self.now() - onset, len(shown)

    def wait_keys(self, keys, draw, max_wait=None, code=None, label=""):
        """Show `draw` until one of `keys` (or max_wait seconds); returns (key, key time, onset).
        Marker `code` goes out right after the first flip. A dry run presses the first key itself
        (see below)."""
        self.clear_keys()
        onset, frames = None, 0
        if code is not None:
            self.wait_marker()
        while True:
            draw()
            t = self.flip()
            frames += 1
            if onset is None:
                onset = t
                self.send(code, label)
            # a dry run presses the first key: after two frames when fast, after 0.3 s (as a person
            # would) in a real-time test, so screens between blocks never take 3 frames there
            if self.dry_run and (frames >= 2 if self.scale < 1 else self.now() - onset >= 0.3):
                return keys[0], self.now(), onset
            for name, t_down in self.poll(list(keys) + list(cfg.KEY_QUIT)):
                if name in cfg.KEY_QUIT:
                    raise QuitExperiment
                return name, t_down, onset
            if max_wait is not None and self.now() - onset >= max_wait * self.scale:
                return None, None, onset

    def message(self, text, keys=cfg.KEY_CONTINUE, footer=txt.FOOTER_CONTINUE, max_wait=None,
                code=None, label=""):
        def draw():
            self.text.text = text
            self.text.draw()
            if footer:
                self.footer.text = footer
                self.footer.draw()
        return self.wait_keys(keys, draw, max_wait, code, label)

    # -- probe ---------------------------------------------------------------------------

    def run_probe(self, r):
        """Two pictures until an answer or PROBE_MAX_RT, the probe code after the first flip and
        the response code as soon as the key is read. Returns (onset, response, key time)."""
        left = self.image(r["probe_left_file"], cfg.PROBE_HEIGHT, -cfg.PROBE_X)
        right = self.image(r["probe_right_file"], cfg.PROBE_HEIGHT, cfg.PROBE_X)

        def draw():
            left.draw()
            right.draw()
        self.probe_draw = draw
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
        self.wait_marker()
        while True:
            draw()
            t = self.flip()
            if onset is None:
                onset = t
                self.send(probe_code(r), "probe")
            if sim is not None and sim[0] is not None and self.now() - onset >= sim[1]:
                self.send(cfg.MARKER_CODES["response_" + sim[0]], "response")
                return onset, sim[0], self.now()
            for name, t_down in self.poll(answer_keys):
                self.send(cfg.MARKER_CODES["response_" + answer_keys[name]], "response")
                return onset, answer_keys[name], t_down
            if self.now() - onset >= cfg.PROBE_MAX_RT * self.scale - half:
                return onset, None, None


def probe_code(r):
    return cfg.MARKER_CODES["probe_" + r["probe_kind"]]


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

def earlier_probe_results(subj_id, design, start_block):
    """Probe outcomes of blocks before `start_block` from this participant's earlier runs, so the
    bonus after a restart still counts them (latest file wins per trial)."""
    results = {}
    for p in sorted(cfg.DATA_DIR.glob(f"{subj_id}_design-{design}_localizer_meg_*.tsv")):
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
    if args.marker_backend:
        cfg.MARKER_BACKEND = args.marker_backend
    from triggers import make_marker
    fast = args.dry_run and not args.real_time
    marker = make_marker(cfg.MARKER_BACKEND, verbose=False,
                         pulse=cfg.MARKER_PULSE_DURATION * cfg.DRY_RUN_SCALE if fast else None)
    if args.button_box:
        cfg.BUTTON_BOX = True
    buttons = None
    if cfg.BUTTON_BOX:
        from responses import make_button_box
        buttons = make_button_box()
    log = Logger(cfg.DATA_DIR / f"{subj}_design-{design}_localizer_meg_{stamp}{tag}.tsv", subj, design)
    for k, v in (("design_file", path.name), ("start_block", args.start_block),
                 ("dry_run", int(args.dry_run)), ("keyboard_backend", cfg.KEYBOARD_BACKEND),
                 ("marker_backend", cfg.MARKER_BACKEND), ("marker_fallback", int(marker.is_fallback)),
                 ("marker_pulse_s", marker.pulse), ("button_box", int(buttons is not None)),
                 ("started", stamp)):
        log.meta(k, v)
    outcomes = dict(earlier_probe_results(subj, design, args.start_block))
    restarted = args.start_block > 1

    pres = Presenter(rows, args.dry_run, args.real_time, marker, buttons)
    log.meta("refresh_hz", f"{1 / pres.frame_dur:.2f}")
    try:
        if marker.is_fallback:
            pres.message(f"Marker backend '{cfg.MARKER_BACKEND}' failed: NO MARKERS will be sent.\n\n"
                         "Space: continue without markers. Escape: quit.",
                         keys=cfg.KEY_OPERATOR, footer="")
            log.meta("marker_fallback_confirmed", 1)
        if cfg.BUTTON_BOX and buttons is None:
            pres.message(f"Button box on '{cfg.BUTTON_SERIAL_PORT}' failed: only the KEYBOARD is read.\n\n"
                         "Space: continue with the keyboard. Escape: quit.",
                         keys=cfg.KEY_OPERATOR, footer="")
            log.meta("button_box_fallback_confirmed", 1)
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
            _, t_trig, _ = pres.message(txt.WAIT_START, keys=cfg.TRIGGER_KEYS, footer="")
            t0 = t_trig
            pres.in_run = True
            code = cfg.MARKER_CODES["block_start"] + b
            pres.wait_marker()    # only a dry run reaches t0 within 30 ms of the last block end code
            pres.send(code, f"block_{b}_start")
            log.write(block=b, event="trigger", onset=0.0, time_abs=t0, marker=code)

            on, dur = pres.present(cfg.T_BLOCK_LEAD_IN, pres.fixation.draw)
            log.write(block=b, event="block_lead_in", onset=on - t0, duration=dur, time_abs=on)
            for r in blk:
                code = cfg.MARKER_CODES["fixation"]
                on, dur = pres.present(r["stimulus_ITI"], pres.fixation.draw, code, "fixation")
                log.trial_row(r, "fixation", on - t0, dur, on, marker=code)
                code = cfg.CLASS_CODES[r["stimulus"]]
                on, dur, n_frames = pres.present_video(r["stimulus"], code, r["stimulus"])
                log.trial_row(r, "stimulus", on - t0, dur, on, marker=code, image=r["stimulus_file"],
                              note=f"video_frames={n_frames}")
                if not r["probe"]:
                    continue
                code = cfg.MARKER_CODES["probe_fixation"]
                on, dur = pres.present(r["probe_ITI"], pres.fixation.draw, code, "probe_fixation")
                log.trial_row(r, "probe_fixation", on - t0, dur, on, marker=code)
                p_on, resp, t_key = pres.run_probe(r)
                if resp is None:
                    code = cfg.MARKER_CODES["timeout"]
                    _, _, t_on = pres.message(txt.TIMEOUT, footer="", max_wait=cfg.TIMEOUT_MAX,
                                              code=code, label="timeout")
                    log.trial_row(r, "probe", p_on - t0, t_on - p_on, p_on, marker=probe_code(r),
                                  response="timed_out", correct="timed_out")
                    outcomes[(b, r["trial"])] = "timed_out"
                    log.trial_row(r, "timeout", t_on - t0, pres.now() - t_on, t_on, marker=code)
                    continue
                correct = int(resp == r["probe_correct"])
                outcomes[(b, r["trial"])] = correct
                fb = pres.feedback["correct" if correct else "incorrect"]
                pres.hold_marker(pres.probe_draw)     # the response pulse ends before feedback
                remaining = max(0.0, cfg.PROBE_TOTAL * pres.scale - (pres.now() - p_on)) / pres.scale
                code = cfg.MARKER_CODES["feedback_correct" if correct else "feedback_incorrect"]
                f_on, f_dur = pres.present(remaining, fb.draw, code, "feedback")
                log.trial_row(r, "probe", p_on - t0, f_on - p_on, p_on, marker=probe_code(r),
                              response=resp, rt=t_key - p_on, correct=correct)
                log.trial_row(r, "response", t_key - t0, 0.0, t_key,
                              marker=cfg.MARKER_CODES["response_" + resp], response=resp)
                log.trial_row(r, "feedback", f_on - t0, f_dur, f_on, marker=code, correct=correct)

            on, dur = pres.present(cfg.T_BLOCK_LEAD_OUT, pres.fixation.draw)
            log.write(block=b, event="block_lead_out", onset=on - t0, duration=dur, time_abs=on)
            code = cfg.MARKER_CODES["block_end"] + b
            pres.send(code, f"block_{b}_end")
            log.write(block=b, event="block_end", onset=pres.now() - t0, time_abs=pres.now(), marker=code)
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
        bonus_file = cfg.DATA_DIR / f"{subj}_design-{design}_bonus_{stamp}{tag}.txt"
        bonus_file.write_text(f"{bonus}\n")
        pres.message(txt.GOODBYE.format(bonus=bonus), keys=cfg.KEY_OPERATOR, footer="")
        log.meta("marker_holds", pres.marker_holds)
        log.meta("marker_overlaps", marker.overlaps)
        log.meta("session_end", "complete")
    except QuitExperiment:
        log.meta("session_end", "quit")
        print("quit by escape; data saved to", log.path)
    finally:
        log.close()
        marker.close()
        if buttons is not None:
            buttons.close()
        pres.win.close()
    print("data:", log.path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", required=True, help="design number N, reads designs/sub-NNN_localizer_meg.csv")
    ap.add_argument("--participant", default="",
                    help="the participant database code, e.g. 27985.cb (letters, digits, dots)")
    ap.add_argument("--start-block", type=int, default=1)
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--real-time", action="store_true",
                    help="with --dry-run: simulated answers but true durations (timing test)")
    ap.add_argument("--keyboard-backend", choices=("ptb", "event"))
    ap.add_argument("--button-box", action="store_true",
                    help="also read the MEG serial response box (config.BUTTON_SERIAL_PORT)")
    ap.add_argument("--marker-backend", choices=("dummy", "parallel", "serial", "lsl"),
                    help="overrides config.MARKER_BACKEND")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
