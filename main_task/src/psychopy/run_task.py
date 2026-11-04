#!/usr/bin/env python
"""
Grid value/structure replay task -- offline (PsychoPy) arm.

Run:
    python run_task.py                    # launch dialog
    python run_task.py --dry-run          # fast-forward a whole schedule, auto-responses
    python run_task.py --plan-only        # validate + timing report, no window
    python run_task.py --schedule 7 --participant TeSt1990 --no-dialog --modality behavioral

The canonical spec is ../../experiment_spec.md. All timings, keys, sizes and marker codes
come from config.py; there are no magic numbers below. Presentation is sequential and central;
participants never see a grid (spec section 1).
"""

import math
import re
import time
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as cfg
import familiarization as fam_mod
import practice as practice_mod
import strings
import shapes
import triggers
import datalog as datalog_mod
from datalog import NA, DataLogger, next_free_schedule_number
from iti import gaps_for_block, start_gaps_for_block, hash32
from schedule import ScheduleError, load_schedule, run_duration, ends_on_outcome, n_events
from stimuli import (StimulusError, build_stimulus_map, load_manifest, resolve_feedback,
                     resolve_reward, resolve_reward_frames)



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
    """Raised when the experimenter presses the quit key."""


OPTION_KEYS = (cfg.KEY_OPTION_1, cfg.KEY_OPTION_2, cfg.KEY_OPTION_3)


def enable_button_box():
    """Add the MEG response box's buttons to the keys (2026-10-14): each option also accepts its
    buttons (config.OPTION_BUTTONS -> meg_lab POSITION_BUTTONS: blue = left, either middle button
    = middle, red = right, as the colleague's experiment in this lab, 2026-11-04), and any button
    advances a screen. Called once at startup when the box is used."""
    global OPTION_KEYS
    lab = cfg.lab
    OPTION_KEYS = tuple(tuple(keys) + tuple(lab.POSITION_BUTTONS[pos])
                        for keys, pos in zip(OPTION_KEYS, cfg.OPTION_BUTTONS))
    cfg.KEY_CONTINUE = tuple(cfg.KEY_CONTINUE) + tuple(lab.BUTTONS)
    cfg.BUTTON_BOX = True


# ---------------------------------------------------------------------------
# Launch dialog
# ---------------------------------------------------------------------------

# the participant database code (2026-10-28): letters, digits and dots, kept exactly in every
# session (online, MEG, MRI) so the three can be matched
PARTICIPANT_CODE = re.compile(r"[A-Za-z0-9.]+")


def derive_participant_code(first, last, year):
    """'Fabian', 'Renz', '1995' -> 'FaRe1995'. Only this derived code ever reaches a file."""
    first = "".join(ch for ch in first if ch.isalpha())
    last = "".join(ch for ch in last if ch.isalpha())
    year = "".join(ch for ch in str(year) if ch.isdigit())
    if len(first) < 2 or len(last) < 2:
        raise ValueError("First and last name each need at least two letters.")
    if len(year) != 4:
        raise ValueError("Year of birth must be four digits, e.g. 1995.")
    return f"{first[:2].capitalize()}{last[:2].capitalize()}{year}"


def _warn(gui, message):
    try:
        gui.warnDlg(prompt=message, title="Invalid input")
    except Exception:  # noqa: BLE001
        print(f"[dialog] {message}")


def launch_dialog(defaults):
    """Collect identity, schedule and modality. Returns None if the experimenter cancels."""
    from psychopy import gui

    modalities = ["behavioral", "fmri", "meg"]
    default_modality = defaults.get("modality", cfg.DEFAULT_MODALITY)
    info = {
        "First name": "",
        "Last name": "",
        "Year of birth": "",
        "Schedule (1-100)": str(defaults.get("schedule", 1)),
        "Modality": [default_modality] + [m for m in modalities if m != default_modality],
        "Language": [defaults.get("language", cfg.LANGUAGE),
                     *[l for l in ("en", "de") if l != defaults.get("language", cfg.LANGUAGE)]],
        "Practice": ["yes", "no"] if defaults.get("practice", True) else ["no", "yes"],
    }
    order = ["First name", "Last name", "Year of birth",
             "Schedule (1-100)", "Modality", "Language", "Practice"]

    while True:
        dlg = gui.DlgFromDict(dictionary=info, title="Grid value/structure experiment",
                              order=order, sortKeys=False)
        if not dlg.OK:
            return None
        try:
            code = derive_participant_code(info["First name"], info["Last name"],
                                           info["Year of birth"])
        except ValueError as exc:
            _warn(gui, str(exc))
            continue
        try:
            schedule_number = int(str(info["Schedule (1-100)"]).strip())
        except (TypeError, ValueError):
            _warn(gui, "Schedule must be a whole number between 1 and 100.")
            continue
        if not 1 <= schedule_number <= 100:
            _warn(gui, "Schedule must be between 1 and 100.")
            continue
        return {
            "participant": code,
            "schedule": schedule_number,
            "modality": info["Modality"],
            "language": info["Language"],
            "practice": info["Practice"] == "yes",
        }


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

class Presenter:
    """Owns the window, the preloaded stimuli, the keyboard and the marker backend."""

    def __init__(self, session, logger, marker, dry_run=False, buttons=None):
        from psychopy import core, visual
        from psychopy.hardware import keyboard

        self.session = session
        self.logger = logger
        self.marker = marker
        self.buttons = buttons          # the MEG response box (meg_lab.buttons), or None
        self.dry_run = dry_run
        self.scale = cfg.DRY_RUN_SCALE if dry_run else 1.0
        self.lang = session["language"]
        self.modality = session["modality"]

        self.win = visual.Window(
            size=cfg.WINDOW_SIZE, fullscr=cfg.FULLSCREEN and not dry_run, screen=cfg.SCREEN,
            color=cfg.BACKGROUND_COLOR, units=cfg.UNITS, allowGUI=False, checkTiming=True)
        self.win.mouseVisible = False

        # One timebase for everything: win.flip() returns core.getTime() time and ptb Keyboard
        # timestamps share it, so onsets, RTs and marker times are directly comparable.
        self.now = core.getTime
        self.kb = keyboard.Keyboard(backend=cfg.KEYBOARD_BACKEND)
        self.core = core
        self.visual = visual

        self.frame_dur = self.win.monitorFramePeriod or (1 / 60.0)
        measured = self.win.getActualFrameRate(nIdentical=10, nMaxFrames=120, nWarmUpFrames=10)
        if measured:
            self.frame_dur = 1.0 / measured
        self.refresh_hz = 1.0 / self.frame_dur

        self.vsync_ok = 20.0 <= self.refresh_hz <= 200.0
        if not self.vsync_ok:
            print(f"\n*** Measured refresh rate is {self.refresh_hz:.0f} Hz -- vsync does not "
                  "appear to be locking flips.")
            print("*** Durations remain correct, but onsets are not refresh-locked."
                  + (" Check the display before scanning.\n"
                     if cfg.FULLSCREEN and not dry_run else " Expected in a windowed/dry run.\n"))

        self.t0 = 0.0
        self.in_run = False     # gates TR-pulse logging to inside a run

        # visual furniture
        self.fixation = visual.TextStim(self.win, text=cfg.FIXATION_TEXT,
                                        height=cfg.FIXATION_HEIGHT, color=cfg.FIXATION_COLOR)
        self.prompt = visual.TextStim(self.win, text="", height=cfg.PROMPT_HEIGHT,
                                      color=cfg.PROMPT_COLOR, wrapWidth=cfg.PROMPT_WRAP,
                                      alignText="center")
        self.message = visual.TextStim(self.win, text="", height=cfg.INSTRUCTION_HEIGHT,
                                       color=cfg.PROMPT_COLOR, wrapWidth=cfg.INSTRUCTION_WRAP,
                                       alignText="center")
        self.footer = visual.TextStim(self.win, text="", height=cfg.INSTRUCTION_FOOTER_HEIGHT,
                                      color=cfg.PROMPT_COLOR, pos=(0, cfg.INSTRUCTION_FOOTER_Y),
                                      alignText="center")
        self.amount_text = visual.TextStim(self.win, text="", height=cfg.OUTCOME_TEXT_HEIGHT,
                                           color=cfg.OUTCOME_TEXT_COLOR, bold=True)
        self.amount_shadow = (visual.TextStim(self.win, text="", height=cfg.OUTCOME_TEXT_HEIGHT,
                                              color=cfg.OUTCOME_TEXT_SHADOW_COLOR, bold=True)
                              if cfg.OUTCOME_TEXT_SHADOW_COLOR else None)
        self.selection_frame = visual.Rect(self.win, fillColor=None,
                                           lineColor=cfg.SELECTION_FRAME_COLOR,
                                           lineWidth=cfg.SELECTION_FRAME_WIDTH)
        self.key_hint = visual.TextStim(self.win, text="", height=cfg.PROBE_KEY_HINT_HEIGHT,
                                        color=cfg.PROMPT_COLOR)
        self.photodiode = visual.Rect(
            self.win, width=cfg.PHOTODIODE_SIZE, height=cfg.PHOTODIODE_SIZE,
            pos=cfg.PHOTODIODE_POS, fillColor="white", lineColor=None)

        self.clips = {}
        self.frames = {}
        self.shapes = {}        # the drawn practice stimuli; also registered in clips and frames
        self.rewards = {}
        self.video_frames = {}      # the MRI: picture id -> its video's frames (2026-10-23)
        self.reward_frames = {}     # the MRI: treasure -> its video's frames
        self.feedback_images = {}
        # the performance score (2026-10-02): correct answers to the main-task questions, per run
        # and in all; a miss counts as wrong. Shown in the breaks and at the end, and written to
        # session_end. Mirrors ctx.score in ../jspsych/experiment.js.
        self.score = {"correct": 0, "n": 0, "by_run": {}}

    # -- asset preloading ---------------------------------------------------------------

    def preload(self, stim_map, manifest, reward_names):
        # a main-task picture is ONE ImageStim, registered in both `clips` and `frames` like a
        # practice shape; the probes and maps resize it, so show_video resets its size every time
        for vid, paths in stim_map.items():
            stim = self.visual.ImageStim(self.win, image=str(paths["image"]), size=self._clip_size())
            self.clips[vid] = stim
            self.frames[vid] = stim
        self._preload_shapes()
        for name in reward_names:
            path = resolve_reward(manifest, name)
            self.rewards[name] = self.visual.ImageStim(
                self.win, image=str(path),
                size=(cfg.OUTCOME_IMAGE_HEIGHT * cfg.REWARD_ASPECT, cfg.OUTCOME_IMAGE_HEIGHT))
        # the MRI's videos (2026-10-23): every frame preloaded as its own picture, so playback is
        # just drawing the frame due at each refresh
        if cfg.VIDEO_MODE:
            t_load = time.perf_counter()
            for vid, paths in stim_map.items():
                if paths.get("frames"):
                    self.video_frames[vid] = [self.visual.ImageStim(self.win, image=str(p))
                                              for p in paths["frames"]]
            for name in reward_names:
                self.reward_frames[name] = [self.visual.ImageStim(self.win, image=str(p))
                                            for p in resolve_reward_frames(manifest, name)]
            n = sum(len(f) for f in self.video_frames.values()) + sum(
                len(f) for f in self.reward_frames.values())
            print(f"  videos: {n} frames preloaded in {time.perf_counter() - t_load:.1f} s")
        for key in ("correct", "incorrect"):
            path = resolve_feedback(manifest, key)
            self.feedback_images[key] = self.visual.ImageStim(self.win, image=str(path),
                                                              size=(0.3 * cfg.REWARD_ASPECT, 0.3))

    def _preload_shapes(self):
        """
        The practice shapes. Drawn, not loaded: no files, no clips. They are registered in BOTH
        `clips` and `frames` so the trial engine treats a shape exactly like a clip -- a "clip"
        that happens to be static -- and the outcome screens need no special case.
        """
        for stim_id in cfg.PRACTICE_SHAPE_IDS:
            stim = self.visual.ShapeStim(
                self.win,
                vertices=shapes.vertices_for(stim_id),
                size=(cfg.PRACTICE_SHAPE_SIZE, cfg.PRACTICE_SHAPE_SIZE),
                units=cfg.UNITS,
                fillColor=shapes.shape_color(stim_id),
                lineColor=shapes.shape_color(stim_id),
                lineWidth=cfg.PRACTICE_SHAPE_LINE_WIDTH,
                pos=(0, 0),
            )
            self.shapes[stim_id] = stim
            self.clips[stim_id] = stim
            self.frames[stim_id] = stim

    @staticmethod
    def _clip_size(stim_id=None):
        """The size of one step's stimulus shown on its own: a practice shape or a picture."""
        if stim_id is not None and shapes.is_shape_id(stim_id):
            return (cfg.PRACTICE_SHAPE_SIZE, cfg.PRACTICE_SHAPE_SIZE)
        return (cfg.CLIP_HEIGHT * cfg.CLIP_ASPECT, cfg.CLIP_HEIGHT)

    # -- timing primitives --------------------------------------------------------------

    def poll(self, keys):
        """
        Names (and press times where available) of the requested keys pressed since last poll.
        Reads psychopy.event directly for non-ptb backends (the Keyboard wrapper drops all but one
        key per call there).
        """
        wanted = list(keys)
        # the MEG response box (2026-10-14): a press arrives as "btn<n>", read on the same clock.
        # Read only when a button is asked for (2026-11-04): the per-frame quit check in flip()
        # used to read and drop every byte, so a press during an answer window was mostly lost.
        # Bytes wait in the port until the next answer window, which empties it first
        # (clear_responses), as the colleague's check_meg_kbd_test.m flushes before each wait.
        box = ([(name, t) for name, t in self.buttons.read() if name in wanted]
               if self.buttons is not None and any(k in cfg.lab.BUTTONS for k in wanted)
               else [])
        if cfg.KEYBOARD_BACKEND == "ptb":
            return [(k.name, ptb_key_time(k, self.now)) for k in self.kb.getKeys(wanted, waitRelease=False)] + box
        from psychopy import event as psyevent
        return [(name, None) for name in psyevent.getKeys(wanted)] + box

    def clear_responses(self):
        """Forget earlier presses before an answer or continue window: the keyboard and, in the
        MEG, the response box's waiting bytes (2026-11-04)."""
        self.kb.clearEvents()
        if self.buttons is not None:
            self.buttons.clear()

    def service_background_keys(self):
        """Quit key always. In fMRI mode the scanner keeps sending the trigger key on every volume;
           only the FIRST one matters (it is the block's t0, see wait_for_trigger), so during a run
           the later pulses are swallowed here so they cannot leak into any other key handling,
           and they are neither logged nor marked (decided 2026-09-10)."""
        watched = list(cfg.KEY_QUIT)
        if self.modality == "fmri":
            watched += list(cfg.TRIGGER_KEYS)
        for name, _t_down in self.poll(watched):
            if name in cfg.KEY_QUIT:
                raise QuitExperiment

    def flip(self):
        t = self.win.flip()
        self.service_background_keys()
        return t

    def wait_marker_free(self):
        """Before a coded flip: wait (sleeping, never spinning) until the previous code has been
        reset and the line has been 0 for the lab's gap (meg_lab: 20 ms pulse, 10 ms gap). Only a
        code sent less than 30 ms earlier delays the screen, e.g. the feedback after a timeout."""
        busy = getattr(self.marker, "busy", None)
        # a dry run shrinks the pulse with every other duration, but the reset still waits for a
        # frame, so waiting there would only stretch the compressed gaps; real coded events are
        # at least 0.5 s apart except a timeout followed by its feedback
        while busy is not None and not self.dry_run and busy():
            time.sleep(0.001)

    def present(self, duration, draw, marker_code=None, marker_label=""):
        """
        Draw every frame until `duration` has elapsed; returns (onset, measured_duration).
        Frame-based with a wall-clock stop criterion. The marker is sent immediately after the
        flip that puts the stimulus on screen. In MEG mode a photodiode patch accompanies the
        first PHOTODIODE_DURATION of every marked event.
        """
        target = duration * self.scale
        half_frame = self.frame_dur * 0.5
        onset = None
        photodiode = cfg.PHOTODIODE and self.modality == "meg" and marker_code is not None
        if marker_code is not None:
            self.wait_marker_free()

        while True:
            draw()
            if photodiode and (onset is None
                               or (self.now() - onset) < cfg.PHOTODIODE_DURATION * self.scale):
                self.photodiode.draw()
            t = self.flip()
            if onset is None:
                onset = t
                if marker_code is not None:
                    self.marker.send(marker_code, marker_label)
            if (self.now() - onset) >= target - half_frame:
                break

        return onset, self.now() - onset

    # -- components ---------------------------------------------------------------------

    def show_fixation(self, duration, marker_code=None, marker_label="", start=False):
        """A fixation cross; `start` draws the bigger cross that opens a trial (2026-10-05)."""
        if start:
            if not hasattr(self, "_fixation_start"):
                self._fixation_start = self.visual.TextStim(
                    self.win, text=cfg.FIXATION_TEXT, height=cfg.FIXATION_START_HEIGHT,
                    color=cfg.FIXATION_COLOR)
            return self.present(duration, self._fixation_start.draw, marker_code, marker_label)
        return self.present(duration, self.fixation.draw, marker_code, marker_label)

    def _flipbook(self, frames, size, pos=(0, 0)):
        """A draw function that plays `frames` at VIDEO_FPS from its first call: each refresh
        draws the frame due at that moment (the last one holds if the screen runs longer)."""
        state = {"t0": None}

        def draw():
            now = self.now()
            if state["t0"] is None:
                state["t0"] = now
            i = min(int((now - state["t0"]) / self.scale * cfg.VIDEO_FPS), len(frames) - 1)
            frame = frames[i]
            frame.size = size
            frame.pos = pos
            frame.draw()
        return draw

    def show_video(self, video_id, marker_code, marker_label=""):
        """One step for T_VIDEO: a still picture (2026-09-29) or a practice shape; in the MRI the
        picture's 1 s video (2026-10-23)."""
        size = self._clip_size(video_id)
        if video_id in self.video_frames:
            draw = self._flipbook(self.video_frames[video_id], size)
        else:
            clip = self.clips[video_id]
            clip.size = size
            clip.pos = (0, 0)
            draw = clip.draw
        return self.present(cfg.T_VIDEO, draw, marker_code, marker_label)

    def _draw_amount(self, value, pos):
        text = str(int(value))
        if self.amount_shadow is not None:
            self.amount_shadow.text = text
            self.amount_shadow.pos = (pos[0] + cfg.OUTCOME_TEXT_SHADOW_OFFSET,
                                      pos[1] - cfg.OUTCOME_TEXT_SHADOW_OFFSET)
            self.amount_shadow.draw()
        self.amount_text.text = text
        self.amount_text.pos = pos
        self.amount_text.draw()

    def show_outcome(self, reward_name, amount, marker_code, marker_label=""):
        """Full-walk outcome: the journey's reward image with the amount above it (2026-11-04)."""
        reward = self.rewards[reward_name]
        reward.pos = (0, 0)
        reward.size = (cfg.OUTCOME_IMAGE_HEIGHT * cfg.REWARD_ASPECT, cfg.OUTCOME_IMAGE_HEIGHT)
        # in the MRI the treasure's video plays under the amount (2026-10-23)
        picture = (self._flipbook(self.reward_frames[reward_name], tuple(reward.size))
                   if reward_name in self.reward_frames else reward.draw)

        def draw():
            picture()
            self._draw_amount(amount, (0, cfg.OUTCOME_TEXT_Y))

        return self.present(cfg.T_OUTCOME, draw, marker_code, marker_label)

    def show_route_map(self, caption, rows, still_height, row_y0, row_dy, label_dy=0.0,
                       min_wait=0.0, presses=1):
        """
        A journey map: every journey in `rows` drawn from start to finish on ONE screen, one row
        per journey, its stimuli left to right with arrows between them, optionally a label above
        the row and the journey's treasure and points at its end. Stimuli may be practice shapes
        or real clip stills; a row is `{"stimuli": ids, "label": key|None, "reward": name|None,
        "amount": int|None}`. Self-paced, so no marker. Used by the practice map after the
        structure note and by the starting-state overview before the main task, and (2026-10-01)
        by the overview in every break, which ignores keys for `min_wait` seconds and needs
        `presses` = 2 presses, the footer saying "again" after the first.
        """
        aspect = cfg.REWARD_ASPECT                       # the treasure at a row's end
        # the caption hangs from MAP_CAPTION_TOP, so a long one grows downward instead of being
        # cut off at the top of the screen (2026-10-06)
        caption_stim = self.visual.TextStim(self.win, text=caption, height=cfg.MAP_CAPTION_HEIGHT,
                                            color=cfg.PROMPT_COLOR, alignText="center",
                                            anchorVert="top", pos=(0, cfg.MAP_CAPTION_TOP),
                                            wrapWidth=cfg.INSTRUCTION_WRAP)
        self.footer.text = strings.get(self.lang, cfg.CONTINUE_TEXT_KEY)
        # `placed`: every picture or treasure with its own position and size, so one stimulus can
        # appear in several rows (2026-10-02); `drawn`: the text
        drawn, restore, placed = [], [], []

        def text(value, height, pos, wrap=None):
            stim = self.visual.TextStim(self.win, text=value, height=height,
                                        color=cfg.PROMPT_COLOR, alignText="center", pos=pos,
                                        wrapWidth=wrap)
            drawn.append(stim)
            return stim

        for r, row in enumerate(rows):
            y = row_y0 - r * row_dy
            items = []                                   # (stimulus or None, width, kind)
            for i, stim_id in enumerate(row["stimuli"]):
                stim = self.frames[stim_id]
                width = still_height if shapes.is_shape_id(stim_id) else still_height * cfg.CLIP_ASPECT
                restore.append(stim)
                if i:
                    items.append((None, cfg.MAP_ARROW_WIDTH, "arrow"))
                items.append((stim, width, "image"))
            if row.get("reward"):
                reward = self.rewards[row["reward"]]
                restore.append(reward)
                items.append((None, cfg.MAP_ARROW_WIDTH, "arrow"))
                items.append((reward, still_height * aspect, "image"))
                if row.get("amount") is not None:
                    amount = text(str(int(row["amount"])), cfg.MAP_AMOUNT_HEIGHT, (0, y))
                    items.append((amount, cfg.MAP_AMOUNT_WIDTH, "text"))
            total = sum(w for _, w, _ in items) + cfg.MAP_GAP * (len(items) - 1)
            x = -total / 2
            for stim, width, kind in items:
                pos = (x + width / 2, y)
                if kind == "arrow":
                    drawn.append(self._arrow_stim(cfg.MAP_ARROW_LENGTH, pos))
                elif kind == "image":
                    placed.append((stim, pos, (width, still_height)))
                else:
                    stim.pos = pos
                x += width + cfg.MAP_GAP
            if row.get("label"):
                text(strings.get(self.lang, row["label"]), cfg.MAP_LABEL_HEIGHT,
                     (0, y + label_dy), wrap=cfg.INSTRUCTION_WRAP)
        self.clear_responses()

        def draw():
            caption_stim.draw()
            for stim in drawn:
                stim.draw()
            for stim, pos, size in placed:
                stim.pos, stim.size = pos, size
                stim.draw()
            self.footer.draw()

        try:
            if self.dry_run:
                self.present(cfg.T_FEEDBACK, draw)
                return
            keys = list(cfg.KEY_CONTINUE)
            shown_at = self.now()
            footer = self.footer.text
            if min_wait > 0:
                self.footer.text = ""
            left = presses
            while True:
                waiting = self.now() - shown_at < min_wait
                if not waiting and min_wait > 0 and left == presses:
                    self.footer.text = footer
                draw()
                self.flip()
                for name, _ in self.poll(keys + list(cfg.KEY_QUIT)):
                    if name in cfg.KEY_QUIT:
                        raise QuitExperiment
                    if name in keys and not waiting:
                        left -= 1
                        if left == 0:
                            return
                        self.footer.text = strings.get(
                            self.lang, "press_space_again" if cfg.CONTINUE_TEXT_KEY == "press_space"
                            else "press_button_again")
        finally:
            self.message.pos = (0, 0)
            self.message.height = cfg.INSTRUCTION_HEIGHT
            self.footer.text = strings.get(self.lang, cfg.CONTINUE_TEXT_KEY)
            for stim in restore:
                stim.pos = (0, 0)
            for stim_id in {i for row in rows for i in row["stimuli"]}:
                self.frames[stim_id].size = self._clip_size(stim_id)
            for row in rows:
                if row.get("reward"):
                    self.rewards[row["reward"]].size = (cfg.OUTCOME_IMAGE_HEIGHT * aspect,
                                                        cfg.OUTCOME_IMAGE_HEIGHT)

    def show_swap_cross(self, caption, m):
        """
        The swap before/after diagram of the real practice (2026-10-02): all three journeys
        twice, BEFORE left and AFTER right, the pictures in the same places in both; each framed
        journey outlined (a box per cell joined by connectors, straight before, crossing rows at
        the swap after), arrows following the journeys. Self-paced, one press. Mirrors
        swapCrossHtml() in ../jspsych/experiment.js; geometry in cfg.SWAP_DIAGRAM_* (height units).
        """
        P, GAP, RG = cfg.SWAP_DIAGRAM_PIC, cfg.SWAP_DIAGRAM_GAP, cfg.SWAP_DIAGRAM_ROW_GAP
        n = len(m["rows"][0]["stimuli"])
        panel_w = (n + 1) * P + n * GAP
        total_w = 2 * panel_w + cfg.SWAP_DIAGRAM_PANEL_GAP
        colors = {"seen": cfg.MARK_SEEN_COLOR, "inferred": cfg.MARK_INFERRED_COLOR}
        self.message.text = caption
        self.message.height = cfg.MAP_CAPTION_HEIGHT
        self.message.pos = (0, cfg.SWAP_MAP_CAPTION_Y)
        self.footer.text = strings.get(self.lang, cfg.CONTINUE_TEXT_KEY)
        under, over, placed, restore = [], [], [], []

        def centre(ox, cell):
            r, i = cell
            return (ox + i * (P + GAP) + P / 2, cfg.SWAP_DIAGRAM_ROW_Y0 - r * (P + RG))

        def quad(a, b, width, color):
            (x0, y0), (x1, y1) = a, b
            length = math.hypot(x1 - x0, y1 - y0)
            nx, ny = -(y1 - y0) / length * width / 2, (x1 - x0) / length * width / 2
            return self.visual.ShapeStim(self.win, vertices=[(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                                                             (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)],
                                         fillColor=color, lineColor=None, units=cfg.UNITS)

        def shape(ox, cells, grow, color):
            box = P + 2 * cfg.SWAP_DIAGRAM_FRAME_PAD - 2 * grow
            out = []
            for q, cell in enumerate(cells):
                c = centre(ox, cell)
                out.append(self.visual.Rect(self.win, width=box, height=box, pos=c, fillColor=color,
                                            lineColor=None, units=cfg.UNITS))
                if q:
                    c0 = centre(ox, cells[q - 1])
                    across = abs(c0[1] - c[1]) > 1e-9
                    out.append(quad(c0, c, (cfg.SWAP_DIAGRAM_CROSS_BAND - 2 * grow) if across else box,
                                    color))
            return out

        def arrow(a, b):
            (x0, y0), (x1, y1) = a, b
            dx, dy = x1 - x0, y1 - y0
            length = math.hypot(dx, dy)
            cut = (P / 2 + 0.008) / max(abs(dx), 1e-9)          # start and end at the picture edges
            s = (x0 + dx * cut, y0 + dy * cut); e = (x1 - dx * cut, y1 - dy * cut)
            ux, uy = dx / length, dy / length
            h = cfg.SWAP_DIAGRAM_ARROW_HEAD
            head = [e, (e[0] - ux * h - uy * h / 2, e[1] - uy * h + ux * h / 2),
                    (e[0] - ux * h + uy * h / 2, e[1] - uy * h - ux * h / 2)]
            return [self.visual.Line(self.win, start=s, end=(e[0] - ux * h * 0.6, e[1] - uy * h * 0.6),
                                     lineColor=cfg.PROMPT_COLOR, lineWidth=2.5, units=cfg.UNITS),
                    self.visual.ShapeStim(self.win, vertices=head, fillColor=cfg.PROMPT_COLOR, lineColor=None,
                                          units=cfg.UNITS)]

        frames = []
        for p, after in enumerate((False, True)):
            ox = -total_w / 2 + p * (panel_w + cfg.SWAP_DIAGRAM_PANEL_GAP)
            label_y = cfg.SWAP_DIAGRAM_ROW_Y0 + P / 2 + cfg.SWAP_DIAGRAM_LABEL_DY
            over.append(self.visual.TextStim(
                self.win, text=strings.get(self.lang, "real_label_after" if after else "real_label_before"),
                height=cfg.MAP_LABEL_HEIGHT, color=cfg.PROMPT_COLOR, pos=(ox + panel_w / 2, label_y)))
            journeys = [(f["after"] if after else f["before"], f["mark"]) for f in m["frames"]]
            journeys.append(([[2, i] for i in range(n + 1)], None))
            for cells, mark in journeys:
                if mark:
                    frames.append((ox, cells, mark))
                for q in range(1, len(cells)):
                    over.extend(arrow(centre(ox, cells[q - 1]), centre(ox, cells[q])))
            for r, row in enumerate(m["rows"]):
                for i, stim_id in enumerate(row["stimuli"] + [None]):
                    stim = self.frames[stim_id] if stim_id else self.rewards[row["reward"]]
                    restore.append(stim)
                    size = (P, P) if stim_id else (P, P / cfg.REWARD_ASPECT)
                    placed.append((stim, centre(ox, [r, i]), size))
        for ox, cells, mark in frames:
            under.extend(shape(ox, cells, 0, colors[mark]))
        for ox, cells, mark in frames:
            # the outline's inside is the window's own grey (black until 2026-10-26, when the
            # background turned grey: it left black bands inside every outline)
            under.extend(shape(ox, cells, cfg.SWAP_DIAGRAM_FRAME_LINE, cfg.BACKGROUND_COLOR))
        self.clear_responses()

        def draw():
            self.message.draw()
            for stim in under:
                stim.draw()
            for stim, pos, size in placed:
                stim.pos, stim.size = pos, size
                stim.draw()
            for stim in over:
                stim.draw()
            self.footer.draw()

        try:
            if self.dry_run:
                self.present(cfg.T_FEEDBACK, draw)
                return
            keys = list(cfg.KEY_CONTINUE)
            while True:
                draw()
                self.flip()
                for name, _ in self.poll(keys + list(cfg.KEY_QUIT)):
                    if name in cfg.KEY_QUIT:
                        raise QuitExperiment
                    if name in keys:
                        return
        finally:
            self.message.pos = (0, 0)
            self.message.height = cfg.INSTRUCTION_HEIGHT
            for stim in restore:
                stim.pos = (0, 0)
            for stim_id in {i for row in m["rows"] for i in row["stimuli"]}:
                self.frames[stim_id].size = self._clip_size(stim_id)
            for row in m["rows"]:
                self.rewards[row["reward"]].size = (cfg.OUTCOME_IMAGE_HEIGHT * cfg.REWARD_ASPECT,
                                                    cfg.OUTCOME_IMAGE_HEIGHT)

    # -- probe ---------------------------------------------------------------------------

    def _probe_layout(self, n_options, has_cue=True):
        height = cfg.PROBE_OPTION_HEIGHT
        width = height * cfg.CLIP_ASPECT
        step = width + cfg.PROBE_OPTION_GAP
        first_x = -step * (n_options - 1) / 2
        y = cfg.PROBE_OPTION_Y if has_cue else cfg.PROBE_OPTION_Y_NO_CUE
        return [(first_x + i * step, y) for i in range(n_options)], (width, height)

    def run_probe(self, trial, schedule_number, marker_code, self_paced=False):
        """
        3AFC with direct key mapping: option keys (J/K/L) = left/middle/right. First press locks the
        answer; a frame highlights it for PROBE_CONFIRM_HOLD, then the probe ends (or the window
        runs out). Option order is CSV order; correctness is read, never recomputed.
        """
        options = trial["probe_options"]
        n = len(options)
        has_cue = bool(trial["probe_cue"])
        positions, size = self._probe_layout(n, has_cue)

        for vid, pos in zip(options, positions):
            stim = self.frames[vid]
            stim.size = size
            stim.pos = pos

        cue_stim = None
        if trial["probe_cue"]:
            cue_stim = self.frames[trial["probe_cue"]]
            cue_stim.size = (cfg.PROBE_CUE_HEIGHT * cfg.CLIP_ASPECT, cfg.PROBE_CUE_HEIGHT)
            cue_stim.pos = (0, cfg.PROBE_CUE_Y)

        self.prompt.text = strings.probe_prompt(self.lang, trial["probe_direction"])
        self.prompt.pos = (0, cfg.PROMPT_Y if has_cue else cfg.PROMPT_Y_NO_CUE)

        self.selection_frame.width = size[0] + cfg.SELECTION_FRAME_PAD
        self.selection_frame.height = size[1] + cfg.SELECTION_FRAME_PAD

        chosen_index = None     # 0-based
        chosen_at = None
        auto_confirm = self.dry_run and cfg.DRY_RUN_AUTO_RESPOND
        auto_correct = trial.get("auto_correct_in_dry_run", False)
        trust_tdown = cfg.KEYBOARD_BACKEND == "ptb"

        onset = None
        target = cfg.T_PROBE * self.scale
        half_frame = self.frame_dur * 0.5
        first_frame = True
        photodiode = cfg.PHOTODIODE and self.modality == "meg"
        self.wait_marker_free()
        self.clear_responses()

        all_option_keys = [k for keys in OPTION_KEYS for k in keys]

        while True:
            if cue_stim is not None:
                cue_stim.draw()
            self.prompt.draw()
            for i, vid in enumerate(options):
                self.frames[vid].draw()
                self.key_hint.text = cfg.KEY_OPTION_LABELS[i]
                self.key_hint.pos = (positions[i][0], positions[i][1] + cfg.PROBE_KEY_HINT_DY)
                self.key_hint.draw()
            if chosen_index is not None:
                self.selection_frame.pos = positions[chosen_index]
                self.selection_frame.draw()
            if photodiode and (onset is None
                               or (self.now() - onset) < cfg.PHOTODIODE_DURATION * self.scale):
                self.photodiode.draw()

            t = self.flip()
            if first_frame:
                onset = t
                first_frame = False
                self.marker.send(marker_code, f"probe_{trial['probe_type']}")   # its type

            if auto_confirm and chosen_index is None and (self.now() - onset) >= target * 0.25:
                chosen_index = (trial["probe_correct_index"] - 1 if auto_correct
                                else hash32(schedule_number, trial["trial"], 11) % n)
                chosen_at = self.now()
                self.marker.send(triggers.response_code(chosen_index), "response_auto")

            for name, t_down in self.poll(all_option_keys + list(cfg.KEY_QUIT)):
                if name in cfg.KEY_QUIT:
                    raise QuitExperiment
                if chosen_index is not None:
                    continue    # first press locks the answer
                for i, keys in enumerate(OPTION_KEYS[:n]):
                    if name in keys:
                        chosen_index = i
                        chosen_at = (t_down if trust_tdown and t_down is not None
                                     else self.now())
                        self.marker.send(triggers.response_code(i), "response")
                        break

            measured = self.now() - onset
            if self_paced:
                hold = cfg.GATE_CONFIRM_HOLD * self.scale
                if chosen_at is not None and (self.now() - chosen_at) >= hold:
                    break
                if measured >= cfg.GATE_MAX_WAIT * self.scale:
                    break
            else:
                if (cfg.PROBE_ADVANCE_ON_RESPONSE and chosen_at is not None
                        and (self.now() - chosen_at) >= cfg.PROBE_CONFIRM_HOLD * self.scale):
                    break
                if measured >= target - half_frame:
                    break

        if chosen_index is None:
            if not self_paced:
                self.marker.send(cfg.MARKER_CODES["timeout"], "timeout")
            return {"onset_probe": onset, "dur_probe": measured, "chosen_index": NA,
                    "chosen_video": NA, "correct": NA, "rt": NA, "onset_response": NA}

        chosen = options[chosen_index]
        return {
            "onset_probe": onset, "dur_probe": measured,
            "chosen_index": chosen_index + 1,
            "chosen_video": chosen,
            "correct": 1 if chosen_index + 1 == trial["probe_correct_index"] else 0,
            "rt": chosen_at - onset,
            "onset_response": chosen_at,
        }

    def show_answer_review(self, q, chosen_index, text):
        """
        The review of one practice swap question (2026-10-05): the explanation on top, then the
        question as it was asked, smaller, with the right answer framed green and the
        participant's own answer (1-based, or NA) labelled under its option. Self-paced (SPACE).
        Mirrors answerReviewHtml() in ../jspsych/experiment.js.
        """
        options = q["probe_options"]
        n = len(options)
        height = cfg.REVIEW_OPTION_HEIGHT
        width = height * cfg.CLIP_ASPECT
        step = width + cfg.PROBE_OPTION_GAP
        xs = [-step * (n - 1) / 2 + i * step for i in range(n)]
        if not hasattr(self, "_review_text"):
            self._review_text = self.visual.TextStim(self.win, text="", height=cfg.REVIEW_TEXT_HEIGHT,
                                                color=cfg.PROMPT_COLOR,
                                                wrapWidth=cfg.REVIEW_TEXT_WRAP, alignText="center")
            self._review_prompt = self.visual.TextStim(self.win, text="",
                                                  height=cfg.REVIEW_PROMPT_HEIGHT,
                                                  color=cfg.PROMPT_COLOR,
                                                  wrapWidth=cfg.REVIEW_TEXT_WRAP, alignText="center")
            self._review_mark = self.visual.TextStim(self.win, text="", height=cfg.PROBE_KEY_HINT_HEIGHT,
                                                color=cfg.SELECTION_FRAME_COLOR, bold=True)
            self._review_frame = self.visual.Rect(self.win, fillColor=None,
                                             lineColor=cfg.REVIEW_CORRECT_COLOR,
                                             lineWidth=cfg.SELECTION_FRAME_WIDTH)
        self._review_text.text = text
        self._review_text.pos = (0, cfg.REVIEW_TEXT_Y)
        self._review_frame.width = width + cfg.SELECTION_FRAME_PAD
        self._review_frame.height = height + cfg.SELECTION_FRAME_PAD
        self._review_frame.pos = (xs[q["probe_correct_index"] - 1], cfg.REVIEW_OPTION_Y)
        answered = chosen_index not in (None, NA)
        self._review_mark.text = strings.get(self.lang, "real_your_answer" if answered
                                             else "real_no_answer")
        self._review_mark.pos = ((xs[chosen_index - 1], cfg.REVIEW_OPTION_Y + cfg.REVIEW_ANSWER_DY)
                                 if answered else (0, cfg.REVIEW_OPTION_Y + cfg.REVIEW_ANSWER_DY))
        self.footer.text = strings.get(self.lang, cfg.CONTINUE_TEXT_KEY)
        cue = self.frames[q["probe_cue"]]

        def draw():
            self._review_text.draw()
            cue.size = (cfg.REVIEW_CUE_HEIGHT * cfg.CLIP_ASPECT, cfg.REVIEW_CUE_HEIGHT)
            cue.pos = (0, cfg.REVIEW_CUE_Y)
            cue.draw()
            self._review_prompt.text = strings.probe_prompt(self.lang, q["probe_direction"])
            self._review_prompt.pos = (0, cfg.REVIEW_PROMPT_Y)
            self._review_prompt.draw()
            for i, vid in enumerate(options):
                stim = self.frames[vid]
                stim.size = (width, height)
                stim.pos = (xs[i], cfg.REVIEW_OPTION_Y)
                stim.draw()
                self.key_hint.text = cfg.KEY_OPTION_LABELS[i]
                self.key_hint.pos = (xs[i], cfg.REVIEW_OPTION_Y + cfg.REVIEW_KEY_HINT_DY)
                self.key_hint.draw()
            self._review_frame.draw()
            self._review_mark.draw()
            self._draw_review_journeys(q["journeys"])
            self.footer.draw()

        self.clear_responses()
        if self.dry_run:
            self.present(cfg.T_FEEDBACK, draw)
            return
        while True:
            draw()
            self.flip()
            for name, _ in self.poll(list(cfg.KEY_CONTINUE) + list(cfg.KEY_QUIT)):
                if name in cfg.KEY_QUIT:
                    raise QuitExperiment
                if name in cfg.KEY_CONTINUE:
                    return

    def _arrow_stim(self, a, pos=(0, 0)):
        """A right-pointing arrow `a` long, drawn as a polygon: the font's arrow renders as a
        bare dash in PsychoPy (its head is lost), so every journey picture draws this instead."""
        return self.visual.ShapeStim(
            self.win, fillColor=cfg.PROMPT_COLOR, lineColor=None, pos=pos,
            vertices=[(-a / 2, -a * 0.08), (a * 0.1, -a * 0.08), (a * 0.1, -a * 0.25),
                      (a / 2, 0), (a * 0.1, a * 0.25), (a * 0.1, a * 0.08),
                      (-a / 2, a * 0.08)])

    def _draw_review_journeys(self, journeys):
        """Under each review (2026-10-05): the two swapped journeys BEFORE (left) and AFTER
        (right), start to finish with their treasures and no points. Mirrors
        reviewJourneysHtml() in ../jspsych/experiment.js."""
        if not hasattr(self, "_review_arrow"):
            self._review_arrow = self._arrow_stim(cfg.REVIEW_MAP_ARROW_HEIGHT)
            self._review_label = self.visual.TextStim(self.win, text="",
                                                      height=cfg.REVIEW_TEXT_HEIGHT,
                                                      color=cfg.PROMPT_COLOR)
        s, g = cfg.REVIEW_MAP_SIZE, cfg.REVIEW_MAP_GAP
        for side, key in ((-1, "before"), (1, "after")):
            cx = side * cfg.REVIEW_MAP_PANEL_X
            self._review_label.text = strings.get(self.lang, f"real_label_{key}")
            self._review_label.pos = (cx, cfg.REVIEW_MAP_LABEL_Y)
            self._review_label.draw()
            for r, row in enumerate(journeys[key]):
                y = cfg.REVIEW_MAP_ROW_Y0 + r * cfg.REVIEW_MAP_ROW_DY
                items = len(row["stimuli"]) + 1
                x0 = cx - ((items * s + (items - 1) * g) / 2) + s / 2
                for i in range(items):
                    x = x0 + i * (s + g)
                    if i:
                        self._review_arrow.pos = (x - (s + g) / 2, y)
                        self._review_arrow.draw()
                    if i < items - 1:
                        stim = self.frames[row["stimuli"][i]]
                        stim.size = (s * cfg.CLIP_ASPECT, s)
                    else:
                        stim = self.rewards[row["reward"]]
                        stim.size = (s * cfg.REWARD_ASPECT, s)
                        x += (s * cfg.REWARD_ASPECT - s) / 2     # the wider treasure clears the arrow
                    stim.pos = (x, y)
                    stim.draw()

    def show_names(self, row):
        """
        One names screen right before the walks (2026-10-06): the pictures of one category (a row
        of cfg.NAMES_ROWS: aliens, spaceships, planets), each with its name (strings `name_<id>`)
        above it, under the caption `names_intro_<category>`. Not the journeys: the order within a
        row is fixed. Self-paced (SPACE). Mirrors namesScreenHtml() in ../jspsych/experiment.js.
        """
        if not hasattr(self, "_names_label"):
            self._names_label = self.visual.TextStim(self.win, text="", height=cfg.NAMES_LABEL_HEIGHT,
                                                     color=cfg.PROMPT_COLOR, bold=True)
        category = row[0].split("_")[0]
        self.message.text = strings.get(self.lang, f"names_intro_{category}")
        self.message.pos = (0, cfg.NAMES_TEXT_Y)
        self.footer.text = strings.get(self.lang, cfg.CONTINUE_TEXT_KEY)
        h = cfg.NAMES_STILL_HEIGHT

        def draw():
            self.message.draw()
            for c, stim_id in enumerate(row):
                x = (c - (len(row) - 1) / 2) * cfg.NAMES_COL_DX
                stim = self.frames[stim_id]
                stim.size = (h * cfg.CLIP_ASPECT, h)
                stim.pos = (x, cfg.NAMES_ROW_Y)
                stim.draw()
                self._names_label.text = strings.get(self.lang, f"name_{stim_id}")
                self._names_label.pos = (x, cfg.NAMES_ROW_Y + cfg.NAMES_LABEL_DY)
                self._names_label.draw()
            self.footer.draw()

        self.clear_responses()
        if self.dry_run:
            self.present(cfg.T_FEEDBACK, draw)
            return
        while True:
            draw()
            self.flip()
            for name, _ in self.poll(list(cfg.KEY_CONTINUE) + list(cfg.KEY_QUIT)):
                if name in cfg.KEY_QUIT:
                    raise QuitExperiment
                if name in cfg.KEY_CONTINUE:
                    return

    def show_feedback(self, correct):
        # since 2026-11-04 (user) only the tick or the cross, centred, without "Richtig!" or
        # "Falsch." under it; a missed question has no picture and keeps its "no answer" line
        self.message.text = strings.get(self.lang, "feedback_none")
        self.message.pos = (0, 0)
        image = self.feedback_images["correct" if correct == 1 else "incorrect"]
        image.pos = (0, 0)

        def draw():
            if correct != NA:
                image.draw()
            else:
                self.message.draw()

        code = (cfg.MARKER_CODES["feedback_correct"] if correct == 1
                else cfg.MARKER_CODES["feedback_incorrect"])
        return self.present(cfg.T_FEEDBACK, draw, code, "feedback")

    # -- screens -------------------------------------------------------------------------

    def show_message(self, text, keys=None, max_wait=None, footer=True):
        keys = list(keys or cfg.KEY_CONTINUE)
        deadline = None if max_wait is None else self.now() + max_wait
        self.message.text = text
        self.message.pos = (0, 0)
        self.footer.text = strings.get(self.lang, cfg.CONTINUE_TEXT_KEY) if footer else ""
        self.clear_responses()

        def draw():
            self.message.draw()
            if footer:
                self.footer.draw()

        if self.dry_run:
            self.present(cfg.T_FEEDBACK, draw)
            return keys[0]

        while True:
            draw()
            self.flip()
            for name, _ in self.poll(keys + list(cfg.KEY_QUIT)):
                if name in cfg.KEY_QUIT:
                    raise QuitExperiment
                if name in keys:
                    return name
            if deadline is not None and self.now() >= deadline:
                return None

    def wait_for_trigger(self, run, n_runs):
        """Block until the trigger key arrives; returns ITS timestamp, which becomes the block
           clock's zero. Used before every block in every modality: in the scanner the pulse
           arrives on its own, outside it the experimenter presses T. The screen names the key,
           because outside the scanner somebody has to press it."""
        self.message.text = strings.get(self.lang, "wait_trigger", run=run, n_runs=n_runs)
        self.message.pos = (0, 0)
        self.clear_responses()
        while True:
            self.message.draw()
            self.win.flip()
            for name, t_down in self.poll(list(cfg.TRIGGER_KEYS) + list(cfg.KEY_QUIT)):
                if name in cfg.KEY_QUIT:
                    raise QuitExperiment
                if name in cfg.TRIGGER_KEYS:
                    trust = cfg.KEYBOARD_BACKEND == "ptb"
                    return t_down if trust and t_down is not None else self.now()

    def wait_dummy_volumes(self):
        """After t0, sit on fixation until DUMMY_VOLUMES further pulses have arrived."""
        remaining = cfg.DUMMY_VOLUMES
        while remaining > 0:
            self.fixation.draw()
            self.win.flip()
            for name, t_down in self.poll(list(cfg.TRIGGER_KEYS) + list(cfg.KEY_QUIT)):
                if name in cfg.KEY_QUIT:
                    raise QuitExperiment
                if name in cfg.TRIGGER_KEYS:
                    remaining -= 1          # counted, not logged: t0 is the only pulse that matters

    def close(self):
        self.win.close()


# ---------------------------------------------------------------------------
# Trial engine
# ---------------------------------------------------------------------------

def run_trial(pres, trial, run_number, phase, schedule_number, is_practice):
    """
    One complete trial (spec sections 1 and 4). Every kind is the same sequential walk: its
    shown_videos in step order, each followed by a gap, then the outcome and a gap if the row has
    one (since 2026-10-05 the single format shows no clip, the pair format no outcome). Branches only
    on terminal_amount, break_20s and probe, never on kind. Hidden cells are simply never drawn.
    """
    dropped_before = pres.win.nDroppedFrames
    # the lean trial row: identity, the kept schedule columns, then answer and measured timing
    rec = {c: trial["raw"].get(c, "") for c in datalog_mod.KEPT_SCHEDULE_COLUMNS}
    rec.update({
        "block": run_number, "trial": trial["trial"], "trial_type": trial["event_type"],
    })
    gaps = trial["gaps"]
    for i, g in enumerate(gaps, start=1):
        rec[f"iti_g{i}"] = f"{g:.4f}"

    marker_offset_key = trial["kind"] if phase == "main" else phase
    marker_trial = triggers.trial_marker_code(marker_offset_key)
    rec["marker_trial"] = marker_trial
    t_trial = pres.now()
    rec["onset_trial"] = f"{t_trial - pres.t0:.4f}"

    def log_screen(onset, duration, event, **extra):
        pres.logger.write_event(onset - pres.t0, duration, event,
                                trial=trial["trial"], trial_type=trial["event_type"],
                                design=trial.get("raw"), **extra)

    # --- the fixation that opens every trial (mean 3 s, drawn like the ISIs) ---
    start_onset, start_dur = pres.show_fixation(trial["start_gap"], marker_trial,
                                                f"trial_{trial['trial']}_{trial['event_type']}",
                                                start=True)
    log_screen(start_onset, start_dur, "fixation_start",
               stimulus=f"scheduled={trial['start_gap']:.4f}")

    # --- the shown clips, each followed by its jittered gap, then the outcome ---
    # Every trial is the same sequential walk (decided 2026-09-23): a change trial differs from a
    # full walk only in HOW MANY clips it shows (one for a value change, the new transition for a
    # structure change), never in how they are shown. No label, no composite, no special case.
    for i, video_id in enumerate(trial["shown_videos"]):
        code = triggers.picture_code(video_id)       # the picture's class, as in the localizer
        onset, dur = pres.show_video(video_id, code, f"clip{i + 1}_{video_id}")
        rec[f"onset_clip{i + 1}"] = f"{onset - pres.t0:.4f}"
        rec[f"dur_clip{i + 1}"] = f"{dur:.4f}"
        log_screen(onset, dur, f"clip{i + 1}", stimulus=video_id)
        gap_onset, gap_dur = pres.show_fixation(gaps[i], cfg.MARKER_CODES["fixation"], "fixation")
        log_screen(gap_onset, gap_dur, "fixation_gap", stimulus=f"scheduled={gaps[i]:.4f}")

    if trial["terminal_amount"] is not None:
        onset, dur = pres.show_outcome(trial["terminal_image"], trial["terminal_amount"],
                                       triggers.outcome_code(trial["terminal_image"]), "outcome")
        rec["onset_outcome"] = f"{onset - pres.t0:.4f}"
        rec["dur_outcome"] = f"{dur:.4f}"
        log_screen(onset, dur, "outcome",
                   stimulus=f"{trial['terminal_image']}+{trial['terminal_amount']}")
        gap_onset, gap_dur = pres.show_fixation(gaps[len(trial["shown_videos"])],
                                                cfg.MARKER_CODES["fixation"], "fixation")
        log_screen(gap_onset, gap_dur, "fixation_gap",
                   stimulus=f"scheduled={gaps[len(trial['shown_videos'])]:.4f}")

    # --- rest window: ADDED after the trial's last gap; fixation only, nothing preloaded ---
    if trial["break_20s"]:
        rest = cfg.T_REST_PRACTICE if is_practice else cfg.T_REST
        onset, dur = pres.show_fixation(rest, cfg.MARKER_CODES["rest"], "rest")
        rec["onset_rest"] = f"{onset - pres.t0:.4f}"
        rec["dur_rest"] = f"{dur:.4f}"
        log_screen(onset, dur, "rest_readout")

    # --- probe, AFTER the rest so the readout window is never contaminated ---
    if trial["probe"]:
        result = pres.run_probe(trial, schedule_number, triggers.probe_code(trial["probe_type"]))
        if phase == "main":
            ok = str(result["correct"]) == "1"
            b = pres.score["by_run"].setdefault(run_number, {"correct": 0, "n": 0})
            b["n"] += 1; pres.score["n"] += 1
            if ok:
                b["correct"] += 1; pres.score["correct"] += 1
        log_screen(result["onset_probe"], result["dur_probe"], "probe",
                   stimulus="|".join(trial["probe_options"]))
        if result["onset_response"] == NA:
            log_screen(result["onset_probe"] + result["dur_probe"], 0.0, "no_response",
                       stimulus="|".join(trial["probe_options"]))
        else:
            log_screen(result["onset_response"], 0.0, "response",
                       stimulus="|".join(trial["probe_options"]),
                       response=result["chosen_video"], rt=result["rt"],
                       correct=result["correct"])
        rec.update({
            "onset_probe": f"{result['onset_probe'] - pres.t0:.4f}",
            "dur_probe": f"{result['dur_probe']:.4f}",
            "chosen_index": result["chosen_index"],
            "chosen_video": result["chosen_video"],
            "correct": result["correct"],
            "rt": f"{result['rt']:.4f}" if result["rt"] != NA else NA,
            "onset_response": (f"{result['onset_response'] - pres.t0:.4f}"
                               if result["onset_response"] != NA else NA),
        })
        # feedback after the response: always in practice/gate, and in the main task only while
        # MAIN_TASK_FEEDBACK is on (a piloting switch; see config.py)
        if (cfg.PRACTICE_FEEDBACK if is_practice else cfg.MAIN_TASK_FEEDBACK):
            fb_onset, fb_dur = pres.show_feedback(result["correct"])
            log_screen(fb_onset, fb_dur, "feedback", correct=result["correct"])

    rec["n_dropped_frames"] = pres.win.nDroppedFrames - dropped_before
    return rec


def attach_block_gaps(trials, schedule_number, block_index):
    """Draw jitter for a practice/familiarization block (main runs get theirs in schedule.py)."""
    counts = [n_events(t) for t in trials]
    flags = [ends_on_outcome(t) for t in trials]
    gaps = gaps_for_block(schedule_number, block_index, counts, flags, cfg)
    starts = start_gaps_for_block(schedule_number, block_index, len(trials), cfg)
    for trial, trial_gaps, start in zip(trials, gaps, starts):
        trial["gaps"] = trial_gaps
        trial["start_gap"] = start


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

def parse_skip(value, no_practice=False):
    """
    '--skip practice,gate' -> {'practice', 'gate'}. 'intro' expands to every phase before the main
    task. Unknown names are a hard error: a silent typo would run a phase the tester meant to skip.
    """
    skip = set()
    for name in (part.strip().lower() for part in value.split(",") if part.strip()):
        if name == "intro":
            skip.update(cfg.SKIPPABLE_PHASES)
        elif name in cfg.SKIPPABLE_PHASES:
            skip.add(name)
        elif name == "main":
            raise ValueError("the main task cannot be skipped; it is the experiment")
        else:
            raise ValueError(f"unknown phase '{name}'; choose from "
                             + ", ".join(cfg.SKIPPABLE_PHASES) + ", intro")
    if no_practice:
        skip.add("practice")
    # the gate questions are built from the familiarization state, so one implies the other
    if "familiarization" in skip:
        skip.add("gate")
    return skip


def run_lab_intro(pres, resume_after=0):
    """The opening of a lab session (MEG, MRI; 2026-10-26): two refresher screens, then the button
    check: the participant presses the left, middle and right answer button in turn (only that
    button continues), so the fingers are on the right buttons before the task. Logged in its
    own block, one row per screen with the button that ended it."""
    # the scanner names each button by finger and color (2026-11-04, as RepChanges did)
    sfx = "_mri" if pres.modality == "fmri" else ""
    pres.logger.open_block("lab_intro", 0)
    pres.t0 = pres.now()
    pres.logger.write_event(0.0, 0.0, "block_start", stimulus=datalog_mod.wallclock(),
                            trial_type="lab_intro")
    for key in ("lab_refresher_1", "lab_refresher_1b", "lab_refresher_2" + sfx):
        onset = pres.now()
        pressed = pres.show_message(strings.get(pres.lang, key, t_probe=int(cfg.T_PROBE)))
        pres.logger.write_event(onset - pres.t0, pres.now() - onset, "lab_refresher",
                                trial_type="lab_intro", stimulus=key, response=pressed)
    for key, keys in zip(("button_check_left" + sfx, "button_check_middle" + sfx,
                          "button_check_right" + sfx), OPTION_KEYS):
        onset = pres.now()
        pressed = pres.show_message(strings.get(pres.lang, key), keys=keys, footer=False)
        pres.logger.write_event(onset - pres.t0, pres.now() - onset, "button_check",
                                trial_type="lab_intro", stimulus=key, response=pressed)
    pres.show_message(strings.get(pres.lang, "button_check_done_resume", run=resume_after)
                      if resume_after else strings.get(pres.lang, "button_check_done"))
    pres.logger.write_event(pres.now() - pres.t0, 0.0, "block_end", trial_type="lab_intro")
    pres.logger.close_run()


def show_instructions(pres):
    for key in strings.INSTRUCTION_SEQUENCE:
        pres.show_message(strings.get(pres.lang, key, t_probe=cfg.T_PROBE)
                          if key == "instr_probe" else strings.get(pres.lang, key))


def _practice_map(pres, rmap, labelled):
    """One explanation screen of the real practice: the journeys involved under the text."""
    if labelled:
        pres.show_route_map(strings.get(pres.lang, rmap["caption"]), rmap["rows"],
                            cfg.PRACTICE_MAP_SHAPE_SIZE, cfg.PRACTICE_MAP_ROW_Y0,
                            cfg.PRACTICE_MAP_ROW_DY, cfg.PRACTICE_MAP_LABEL_DY)
    else:
        pres.show_route_map(strings.get(pres.lang, rmap["caption"]), rmap["rows"],
                            cfg.OVERVIEW_STILL_HEIGHT, cfg.OVERVIEW_ROW_Y0, cfg.OVERVIEW_ROW_DY)


def run_swap_questions(pres, trial):
    """
    The three questions after the practice swap (2026-10-05): an intro screen, each question on
    the task's probe screen, untimed (self-paced like the gate), each followed by feedback, then
    the swap's before/after diagram, then one review screen per question with the right answer
    and why, and the two swapped journeys before and after below it. All logged in the practice
    block; none of it counts towards the score or the gate. Mirrors swapQuestionScreens() in
    ../jspsych/experiment.js.
    """
    onset = pres.now()
    pres.show_message(strings.get(pres.lang, "real_questions_intro"))
    pres.logger.write_event(onset - pres.t0, pres.now() - onset, "practice_note",
                            trial=trial["trial"], trial_type="practice",
                            stimulus="real_questions_intro")
    chosen = {}
    for q in trial["questions"]:
        result = pres.run_probe(q, 0, triggers.probe_code(q.get("probe_type")), self_paced=True)
        options = "|".join(q["probe_options"])
        chosen[q["number"]] = result["chosen_index"]
        pres.logger.write_event(result["onset_probe"] - pres.t0, result["dur_probe"], "probe",
                                trial=q["trial"], trial_type="practice", stimulus=options,
                                design=q["raw"])
        if result["onset_response"] == NA:
            pres.logger.write_event(result["onset_probe"] + result["dur_probe"] - pres.t0, 0.0,
                                    "no_response", trial=q["trial"], trial_type="practice",
                                    stimulus=options, design=q["raw"])
        else:
            pres.logger.write_event(result["onset_response"] - pres.t0, 0.0, "response",
                                    trial=q["trial"], trial_type="practice", stimulus=options,
                                    response=result["chosen_video"], rt=result["rt"],
                                    correct=result["correct"], design=q["raw"])
        fb_onset, fb_dur = pres.show_feedback(result["correct"])
        pres.logger.write_event(fb_onset - pres.t0, fb_dur, "feedback", trial=q["trial"],
                                trial_type="practice", correct=result["correct"], design=q["raw"])
    # the swap before and after, the moved parts framed (2026-10-02)
    for extra in trial.get("extra_maps") or []:
        onset = pres.now()
        if extra.get("kind") == "swap_cross":
            pres.show_swap_cross(strings.get(pres.lang, extra["caption"]), extra)
        else:
            _practice_map(pres, extra, labelled=True)
        pres.logger.write_event(onset - pres.t0, pres.now() - onset, "practice_note",
                                trial=trial["trial"], trial_type="practice",
                                stimulus=extra["caption"])
    for q in trial["questions"]:
        onset = pres.now()
        pres.show_answer_review(q, chosen[q["number"]],
                                strings.get(pres.lang, q["explain"], number=q["number"]))
        pres.logger.write_event(onset - pres.t0, pres.now() - onset, "practice_note",
                                trial=trial["trial"], trial_type="practice",
                                stimulus=q["explain"], design=q["raw"])


def run_practice(pres, schedule_number, first_row):
    """
    The practice block. With shapes, the drawn walkthrough; on the real journeys
    (cfg.PRACTICE_STIMULI = "real", 2026-10-01) the examples on the participant's own starting
    journeys, each short trial explained on a picture screen, then the reset screen. Mirrors the
    practice node in ../jspsych/experiment.js.
    """
    real = cfg.PRACTICE_STIMULI == "real"
    problems = practice_mod.validate_practice_for(first_row)
    if problems:
        raise ScheduleError("Practice mini-schedule is inconsistent:\n"
                            + "\n".join(f"  - {p}" for p in problems))

    while True:
        pres.show_message(strings.get(pres.lang, "practice_intro_real" if real else "practice_intro"))
        trials = practice_mod.practice_trials_for(first_row)
        attach_block_gaps(trials, schedule_number, 801)

        pres.logger.open_block("practice", 0)
        pres.t0 = pres.now()
        pres.logger.write_event(0.0, 0.0, "block_start", stimulus=datalog_mod.wallclock(), trial_type="practice")
        # real journeys: first the starting journeys on one screen, to learn them (2026-10-05)
        if real:
            onset = pres.now()
            _practice_map(pres, practice_mod.build_practice_study(first_row), labelled=False)
            pres.logger.write_event(onset - pres.t0, pres.now() - onset, "practice_note",
                                    trial_type="practice", stimulus="real_study")
        for trial in trials:
            run_trial(pres, trial, 0, "practice", schedule_number, is_practice=True)
            # the swap (2026-10-05): three questions on what it changed but did not show, the
            # before/after diagram, then the review of each answer
            if trial.get("questions"):
                run_swap_questions(pres, trial)
                continue
            # real journeys: the explanation IS the picture screen of the journeys involved
            if trial.get("note") and trial.get("note_is_map"):
                onset = pres.now()
                rmap = trial["route_map"]
                _practice_map(pres, rmap, labelled=any(r.get("label") for r in rmap["rows"]))
                pres.logger.write_event(onset - pres.t0, pres.now() - onset, "practice_note",
                                        trial=trial["trial"], trial_type="practice",
                                        stimulus=trial["note"])
                # further picture screens for this trial (the swap before and after, 2026-10-02)
                for extra in trial.get("extra_maps") or []:
                    onset = pres.now()
                    if extra.get("kind") == "swap_cross":
                        pres.show_swap_cross(strings.get(pres.lang, extra["caption"]), extra)
                    else:
                        _practice_map(pres, extra, labelled=True)
                    pres.logger.write_event(onset - pres.t0, pres.now() - onset, "practice_note",
                                            trial=trial["trial"], trial_type="practice",
                                            stimulus=extra["caption"])
                continue
            # a change trial carries an explanation screen: self-paced, so the participant can
            # read what the change they just saw actually means
            if trial.get("note"):
                onset = pres.now()
                pres.show_message(strings.get(pres.lang, trial["note"]))
                pres.logger.write_event(onset - pres.t0, pres.now() - onset, "practice_note",
                                        trial=trial["trial"], trial_type="practice",
                                        stimulus=trial["note"])
            # the structure change then draws both rewired journeys on one screen, the shown
            # half above the half the participant has to infer
            if trial.get("route_map"):
                rmap = trial["route_map"]
                onset = pres.now()
                pres.show_route_map(strings.get(pres.lang, rmap["caption"]), rmap["rows"],
                                    cfg.PRACTICE_MAP_SHAPE_SIZE, cfg.PRACTICE_MAP_ROW_Y0,
                                    cfg.PRACTICE_MAP_ROW_DY, cfg.PRACTICE_MAP_LABEL_DY)
                pres.logger.write_event(onset - pres.t0, pres.now() - onset, "practice_map",
                                        trial=trial["trial"], trial_type="practice",
                                        stimulus=";".join("|".join(r["stimuli"])
                                                          for r in rmap["rows"]))
        # real journeys: the examples are undone, the starting journeys are back
        if real:
            onset = pres.now()
            _practice_map(pres, practice_mod.build_practice_reset(first_row), labelled=False)
            pres.logger.write_event(onset - pres.t0, pres.now() - onset, "practice_note",
                                    trial_type="practice", stimulus="real_reset")
        pres.logger.write_event(pres.now() - pres.t0, 0.0, "block_end", trial_type="practice")
        pres.logger.close_run()

        key = pres.show_message(strings.get(pres.lang, "practice_done", continue_key="SPACE"),
                                keys=list(cfg.KEY_CONTINUE) + list(cfg.KEY_REPEAT_PRACTICE))
        if key not in cfg.KEY_REPEAT_PRACTICE:
            return


def run_familiarization(pres, schedule_number, first_row, attempt, done_key="familiarization_done"):
    trials = fam_mod.build_familiarization_trials(schedule_number, first_row)
    problems = fam_mod.validate_familiarization(trials, first_row)
    if problems:
        raise ScheduleError("Familiarization block is inconsistent with the schedule:\n"
                            + "\n".join(f"  - {p}" for p in problems))
    attach_block_gaps(trials, schedule_number, 900 + attempt)

    # the names of the pictures, one category per screen, right before the walks (2026-10-06;
    # space set only)
    for row in cfg.NAMES_ROWS or []:
        pres.show_names(row)
    pres.show_message(strings.get(pres.lang, "familiarization_intro"))
    pres.logger.open_block(f"familiarization-{attempt}", attempt)
    pres.t0 = pres.now()
    pres.logger.write_event(0.0, 0.0, "block_start", stimulus=datalog_mod.wallclock(), trial_type="familiarization")
    for trial in trials:
        run_trial(pres, trial, attempt, "familiarization", schedule_number, is_practice=False)
    pres.logger.write_event(pres.now() - pres.t0, 0.0, "block_end", trial_type="familiarization")
    pres.logger.close_run()
    pres.show_message(strings.get(pres.lang, done_key))


def run_gate(pres, schedule_number, first_row, attempt):
    """One gate round; returns (n_correct, n_total). Same probe interface as the real task."""
    probes = fam_mod.build_gate_probes(schedule_number, first_row)
    problems = fam_mod.validate_gate(probes, first_row)
    if problems:
        raise ScheduleError("Gate questions are inconsistent with the schedule:\n"
                            + "\n".join(f"  - {p}" for p in problems))

    pres.show_message(strings.get(pres.lang, "gate_intro"))
    pres.logger.open_block(f"gate-{attempt}", attempt)
    pres.t0 = pres.now()
    pres.logger.write_event(0.0, 0.0, "block_start", stimulus=datalog_mod.wallclock(), trial_type="gate")

    n_correct = 0
    for trial in probes:
        result = pres.run_probe(trial, schedule_number, triggers.probe_code(trial.get("probe_type")),
                                self_paced=cfg.GATE_SELF_PACED)
        options = "|".join(trial["probe_options"])
        pres.logger.write_event(result["onset_probe"] - pres.t0, result["dur_probe"], "probe",
                                trial=trial["trial"], trial_type="gate", stimulus=options)
        if result["onset_response"] == NA:
            pres.logger.write_event(result["onset_probe"] + result["dur_probe"] - pres.t0, 0.0,
                                    "no_response", trial=trial["trial"], trial_type="gate",
                                    stimulus=options)
        else:
            pres.logger.write_event(result["onset_response"] - pres.t0, 0.0, "response",
                                    trial=trial["trial"], trial_type="gate", stimulus=options,
                                    response=result["chosen_video"], rt=result["rt"],
                                    correct=result["correct"])
        if result["correct"] == 1:
            n_correct += 1

        fb_onset, fb_dur = pres.show_feedback(result["correct"])
        pres.logger.write_event(fb_onset - pres.t0, fb_dur, "feedback", trial=trial["trial"],
                                trial_type="gate", correct=result["correct"])


    pres.logger.write_event(pres.now() - pres.t0, 0.0, "block_end", trial_type="gate")
    pres.logger.close_run()
    return n_correct, len(probes)


def run_break_overview(pres, last_row, run):
    """
    The overview in the break after block `run` (2026-10-01): the current journeys, read from the
    block's last row. Keys are ignored for BREAK_OVERVIEW_MIN_S, then it takes two presses. One
    `break_overview` row from its onset to the second press, inside its own block_start /
    block_end like the starting overview. Mirrors breakOverview() in ../jspsych/experiment.js.
    """
    overview = fam_mod.build_state_overview(last_row)
    problems = fam_mod.validate_state_overview(overview, last_row)
    if problems:
        raise ScheduleError("Break overview is inconsistent with the schedule:\n"
                            + "\n".join(f"  - {p}" for p in problems))
    pres.logger.open_block("overview", 0)
    pres.t0 = pres.now()
    pres.logger.write_event(0.0, 0.0, "block_start", stimulus=datalog_mod.wallclock(), trial_type="overview")
    onset = pres.now()
    pres.show_route_map(strings.get(pres.lang, overview["caption"], run=run), overview["rows"],
                        cfg.OVERVIEW_STILL_HEIGHT, cfg.OVERVIEW_ROW_Y0, cfg.OVERVIEW_ROW_DY,
                        min_wait=cfg.BREAK_OVERVIEW_MIN_S, presses=2)
    # the k-th break_overview row is the break after block k; trial stays n/a (it holds
    # schedule trial numbers elsewhere)
    pres.logger.write_event(onset - pres.t0, pres.now() - onset, "break_overview",
                            trial_type="overview",
                            stimulus=";".join("|".join(r["stimuli"]) for r in overview["rows"]))
    pres.logger.write_event(pres.now() - pres.t0, 0.0, "block_end", trial_type="overview")
    pres.logger.close_run()


def run_structure_overview(pres, first_row):
    overview = fam_mod.build_structure_overview(first_row)
    problems = fam_mod.validate_structure_overview(overview, first_row)
    if problems:
        raise ScheduleError("Starting-state overview is inconsistent with the schedule:\n"
                            + "\n".join(f"  - {p}" for p in problems))
    pres.logger.open_block("overview", 0)
    pres.t0 = pres.now()
    pres.logger.write_event(0.0, 0.0, "block_start", stimulus=datalog_mod.wallclock(), trial_type="overview")
    onset = pres.now()
    pres.show_route_map(strings.get(pres.lang, overview["caption"]), overview["rows"],
                        cfg.OVERVIEW_STILL_HEIGHT, cfg.OVERVIEW_ROW_Y0, cfg.OVERVIEW_ROW_DY)
    pres.logger.write_event(onset - pres.t0, pres.now() - onset, "structure_overview",
                            trial_type="overview",
                            stimulus=";".join("|".join(r["stimuli"]) for r in overview["rows"]))
    pres.logger.write_event(pres.now() - pres.t0, 0.0, "block_end", trial_type="overview")
    pres.logger.close_run()


def run_main(pres, runs, session, start_run=1):
    n_runs = len(runs)
    note = strings.get(pres.lang, "feedback_note_on" if cfg.MAIN_TASK_FEEDBACK else "feedback_note_off")
    pres.show_message(strings.get(pres.lang, "main_intro", n_runs=n_runs, feedback_note=note))

    for run in runs:
        if run["run"] < start_run:
            continue

        events_path = pres.logger.open_block(f"run-{run['run']:02d}", run["run"])

        # The block clock starts on the trigger, in every modality: t0 IS the moment the key
        # arrives, so every onset in the trials log and the events file is measured from it and
        # a behavioral or MEG block is timed exactly the way a scanned one is. The dummy-volume
        # wait is fMRI only and sits AFTER t0, so it shifts the first trial without moving zero.
        # A dry run has nobody to press the key, so it starts immediately.
        if cfg.TRIGGER_GATED_BLOCKS and not pres.dry_run:
            pres.t0 = pres.wait_for_trigger(run["run"], n_runs)
        else:
            pres.t0 = pres.now()
        pres.in_run = True
        pres.marker.send(cfg.MARKER_CODES["block_start"] + run["run"], f"run_{run['run']}_start")
        dropped_at_start = pres.win.nDroppedFrames
        pres.logger.write_event(0.0, 0.0, "block_start", stimulus=datalog_mod.wallclock())
        if session["modality"] == "fmri" and not pres.dry_run:
            pres.wait_dummy_volumes()
        # Lead-in fixation, held between the trigger and the first trial so every block opens on
        # the same settled baseline. In fMRI it comes AFTER the dummy volumes: those are counted
        # by polling for pulses, and a presentation in front of them would swallow pulses and
        # silently discard more volumes than DUMMY_VOLUMES says. Either way it is the last thing
        # before trial 1, and t0 is unchanged.
        # present() applies the dry-run scale, so a dry run still walks this path (at 0.06 s)
        # instead of skipping it; the row carries no trial number, so the per-trial log audit
        # ignores it.
        if cfg.T_BLOCK_LEAD_IN > 0:
            onset, dur = pres.show_fixation(cfg.T_BLOCK_LEAD_IN)
            pres.logger.write_event(onset - pres.t0, dur, "block_lead_in")

        print(f"  run {run['run']}: {len(run['trials'])} trials -> {events_path.name}")
        for trial in run["trials"]:
            run_trial(pres, trial, run["run"], "main", session["schedule"], is_practice=False)

        pres.marker.send(cfg.MARKER_CODES["block_end"] + run["run"], f"run_{run['run']}_end")
        pres.logger.write_event(pres.now() - pres.t0, 0.0, "block_end",
                                stimulus=f"dropped_frames={pres.win.nDroppedFrames - dropped_at_start}")
        pres.in_run = False
        pres.logger.close_run()

        if run["run"] < n_runs:
            b = pres.score["by_run"].get(run["run"], {"correct": 0, "n": 0})
            pres.show_message(strings.get(pres.lang, "break_score", n_correct=b["correct"],
                                          n_questions=b["n"]) + "\n\n"
                              + strings.get(pres.lang, "break_screen",
                                            run=run["run"], n_runs=n_runs))
            # the current journeys, last thing before the next block's trigger (2026-10-01)
            if cfg.BREAK_OVERVIEW:
                run_break_overview(pres, run["trials"][-1]["raw"], run["run"])


def print_timing_report(runs, dry_run):
    total = 0.0
    label = (f"  (upper bound: every probe charged its full {cfg.T_PROBE:.0f} s window)"
             if cfg.PROBE_ADVANCE_ON_RESPONSE else "")
    print(f"\nPlanned session structure{label}")
    print("  run  trials  rests  probes  duration")
    for run in runs:
        trials = run["trials"]
        rests = sum(1 for t in trials if t["break_20s"])
        probes = sum(1 for t in trials if t["probe"])
        dur = run_duration(trials, dry_run, lead_in=True)
        total += dur
        print(f"  {run['run']:>3}  {len(trials):>6}  {rests:>5}  {probes:>6}  {dur / 60:>6.2f} min")
    print(f"  {'all':>3}  {sum(len(r['trials']) for r in runs):>6}"
          f"  {sum(1 for r in runs for t in r['trials'] if t['break_20s']):>5}"
          f"  {sum(1 for r in runs for t in r['trials'] if t['probe']):>6}"
          f"  {total / 60:>6.2f} min\n")


def main():
    parser = argparse.ArgumentParser(description="Grid value/structure experiment (PsychoPy)")
    parser.add_argument("--dry-run", action="store_true",
                        help="tiny durations and auto-responses; steps through a whole schedule")
    parser.add_argument("--schedule", type=int, help="schedule number 1-100")
    parser.add_argument("--participant", help="the participant database code, e.g. 27985.cb (letters, digits, dots); skips the name dialog")
    parser.add_argument("--steps", type=int, choices=[3, 4], default=None,
                        help="route length: 4 (default, schedules_grid/) or 3 "
                             "(schedules_grid_3step/). Also settable with GRID_STEPS.")
    parser.add_argument("--modality", choices=["behavioral", "fmri", "meg"])
    parser.add_argument("--session", choices=["online", "meg", "mri"], default=None,
                        help="read the schedule from that session's set (schedules_<session>/): "
                             "the three designs per subject; omit for the classic set")
    parser.add_argument("--language", choices=["en", "de"])
    parser.add_argument("--marker-backend", choices=sorted(triggers.BACKENDS))
    parser.add_argument("--button-box", action="store_true",
                        help="also read the MEG response box (meg_lab/settings.py: port and the "
                             "bytes of the blue, middle and red buttons)")
    parser.add_argument("--keyboard-backend", choices=["ptb", "event", "iohub"],
                        help="use 'event' if ptb segfaults for lack of macOS Input Monitoring")
    parser.add_argument("--no-practice", action="store_true",
                        help="alias for --skip practice")
    parser.add_argument("--skip", default="",
                        help="comma-separated phases to skip for testing: "
                             + ", ".join(cfg.SKIPPABLE_PHASES) + ", or 'intro' for everything "
                             "before the main task. The main task is never skippable.")
    parser.add_argument("--no-dialog", action="store_true")
    parser.add_argument("--start-run", type=int, default=1,
                        help="resume a session from this run")
    parser.add_argument("--plan-only", action="store_true",
                        help="validate, print the timing report and exit without opening a window")
    args = parser.parse_args()

    if args.keyboard_backend:
        cfg.KEYBOARD_BACKEND = args.keyboard_backend

    try:
        skip = parse_skip(args.skip, no_practice=args.no_practice)
    except ValueError as exc:
        parser.error(str(exc))

    defaults = {
        "schedule": args.schedule or next_free_schedule_number(),
        "modality": args.modality or cfg.DEFAULT_MODALITY,
        # the real study's sessions run in German unless --language says otherwise (2026-10-13)
        "language": args.language or ("de" if args.session else cfg.LANGUAGE),
        "practice": "practice" not in skip,
    }

    # a given --participant (the lab sessions: the participant database code, e.g. 27985.cb,
    # 2026-10-28) skips the name dialog, so the code is kept exactly as typed
    if args.no_dialog or args.plan_only or args.dry_run or args.participant:
        if args.participant and not PARTICIPANT_CODE.fullmatch(args.participant):
            print(f"--participant {args.participant!r}: only letters, digits and dots, e.g. 27985.cb")
            return 2
        session = {
            "participant": args.participant or "DRYRUN0000",
            "schedule": defaults["schedule"],
            "modality": defaults["modality"],
            "language": defaults["language"],
            "practice": defaults["practice"],
        }
    else:
        session = launch_dialog(defaults)
        if session is None:
            print("Cancelled at the launch dialog.")
            return 0

    # Route length first: it selects the schedule directory and the layout columns, so it has
    # to be applied before any schedule is loaded or any log column list is built.
    if (args.steps and args.steps != cfg.N_STEPS) or args.session:
        cfg.apply_steps(args.steps or cfg.N_STEPS, args.session)
        datalog_mod.rebuild_columns()
        practice_mod.rebuild()

    # Pick the timing profile from the modality. This is the ONLY thing the modality changes about
    # the session itself: ISI distribution and rest length. It MUST happen before the schedule is
    # loaded, because that is where the jitter is drawn.
    profile = cfg.apply_timing_profile(cfg.profile_for_modality(session["modality"]))
    # videos (online, MRI, MEG since 2026-10-28) or stills: sets T_VIDEO too, so the plan below is right
    stimulus_mode = cfg.apply_stimulus_mode(session["modality"])
    # the scanner's buttons b, z, r for the three answers (fMRI, as RepChanges); J, K, L elsewhere
    response_keys = cfg.apply_response_keys(session["modality"])
    global OPTION_KEYS
    OPTION_KEYS = (cfg.KEY_OPTION_1, cfg.KEY_OPTION_2, cfg.KEY_OPTION_3)
    # a lab session (MEG, MRI) opens with a short refresher and a button check, not the full intro
    lab_session = cfg.SESSION_SET in cfg.LAB_SESSIONS
    session["timing_profile"] = profile

    # --- validate everything before the participant sits down ---
    try:
        runs = load_schedule(session["schedule"])
        manifest = load_manifest()
        stim_map = build_stimulus_map(manifest, cfg.CLIP_IDS)
        # Practice is drawn, not played: it needs no clips of its own, and it pays from the same
        # three reward images as the main task.
        reward_names = list(cfg.REWARD_NAMES)
        for name in reward_names:
            resolve_reward(manifest, name)
        for key in ("correct", "incorrect"):
            resolve_feedback(manifest, key)
    except (ScheduleError, StimulusError) as exc:
        print(f"\nABORT -- {exc}\n", file=sys.stderr)
        return 2

    print(f"\nParticipant {session['participant']} | schedule {session['schedule']:03d} | "
          f"{session['modality']} | {session['language']} | {cfg.N_STEPS}-step")
    print(f"  timing profile: {profile} | ISI mean {cfg.GAP_MEAN} s in {list(cfg.GAP_RANGE)}"
          f" (+{cfg.CLIP_GAP_EXTRA} s after each clip)"
          + (f" + one {cfg.LONG_ISI} s ISI per trial" if cfg.LONG_ISI else "")
          + f" | rest {cfg.T_REST} s")
    if skip:
        print(f"  *** TESTING MODE -- skipping: {', '.join(sorted(skip))}. "
              "Recorded in the meta JSON.")
    print(f"  main-task feedback: {'ON' if cfg.MAIN_TASK_FEEDBACK else 'off'} "
          "(cfg.MAIN_TASK_FEEDBACK; on by decision of 2026-09-11)")
    print_timing_report(runs, args.dry_run)

    # every marker code must reach the MEG (1..127, meg_lab/settings.py), checked before any run
    bad = triggers.bad_codes(len(runs))
    if bad:
        raise SystemExit(f"marker codes outside 1..{cfg.MARKER_MAX_CODE}: {bad}")

    if args.plan_only:
        return 0

    logger = DataLogger(session["participant"], session["schedule"], session["modality"],
                        session["language"], dry_run=args.dry_run)
    # a dry run scales every duration, so the 20 ms pulse too, or coded events would overlap
    marker = triggers.make_marker(args.marker_backend, verbose=args.dry_run,
                                  pulse=cfg.MARKER_PULSE_DURATION * cfg.DRY_RUN_SCALE
                                  if args.dry_run else None)
    buttons = None
    if args.button_box or cfg.BUTTON_BOX:
        enable_button_box()
        # the footers name the buttons, not the space bar (2026-11-04)
        cfg.CONTINUE_TEXT_KEY = "press_button"
        from meg_lab.buttons import make_button_box
        buttons = make_button_box()
        if buttons is None:
            print("\n*** The MEG response box did not open: only the KEYBOARD is read.")
            if input("*** Type 'yes' to continue anyway: ").strip().lower() != "yes":
                logger.close()
                return 3

    if session["modality"] in ("fmri", "meg") and getattr(marker, "is_fallback", False):
        print(f"\n*** {session['modality']} mode with a fallback marker backend -- "
              "triggers will NOT be recorded.")
        if input("*** Type 'yes' to continue anyway: ").strip().lower() != "yes":
            logger.close()
            return 3

    first_row_meta = runs[0]["trials"][0]["raw"]
    meta = {
        "skipped_phases": sorted(skip),
        "subj_id": session["participant"],
        "schedule": session["schedule"],
        "schedule_file": str(cfg.SCHEDULE_DIR / f"sub-{session['schedule']:03d}_schedule.csv"),
        "steps": cfg.N_STEPS,
        "modality": session["modality"],
        "implementation": "psychopy",
        "language": session["language"],
        "dry_run": args.dry_run,
        # constant per participant, so written once here and not on every row
        "layout": {c: first_row_meta[c] for c in cfg.CELLS},
        "reward_images": {c: first_row_meta[f"reward_image_{c}"] for c in "ABC"},
        "log_schema": "one-file-2026-09-10",
        "started": datalog_mod.wallclock(),
        "marker_backend": args.marker_backend or cfg.MARKER_BACKEND,
        "marker_is_fallback": getattr(marker, "is_fallback", False),
        "button_box": buttons is not None,
        # the MRI plays the pictures' and treasures' videos, every other modality the stills
        "stimulus_mode": stimulus_mode,
        "response_keys": response_keys,          # scanner_buttons (b, z, r) or keyboard (J, K, L)
        "lab_intro": bool(lab_session),          # refresher + button check instead of the full intro
        "photodiode": bool(cfg.PHOTODIODE and session["modality"] == "meg"),
        # the timing profile is the ONLY thing the modality changes about the session, so it is
        # recorded explicitly: the ISI regime and rest length are not recoverable without it
        "timing_profile": session["timing_profile"],
        "main_task_feedback": cfg.MAIN_TASK_FEEDBACK,
        "timings": {
            "T_VIDEO": cfg.T_VIDEO, "T_OUTCOME": cfg.T_OUTCOME,
            "T_REST": cfg.T_REST,
            "T_PROBE": cfg.T_PROBE, "GAP_MEAN": cfg.GAP_MEAN,
            "GAP_RANGE": list(cfg.GAP_RANGE), "CLIP_GAP_EXTRA": cfg.CLIP_GAP_EXTRA,
            "ITI_STRICT_BALANCE": cfg.ITI_STRICT_BALANCE,
            "ITI_USE_NUMPY": cfg.ITI_USE_NUMPY,
            "LONG_ISI": cfg.LONG_ISI,
            "LONG_ISI_RANGE": list(cfg.LONG_ISI_RANGE) if cfg.LONG_ISI_RANGE else None,
        },
        "n_runs": cfg.N_RUNS,
        "trials_per_run": [len(r["trials"]) for r in runs],
        "planned_run_durations_s": [run_duration(r["trials"], args.dry_run, lead_in=True)
                                    for r in runs],
    }
    logger.write_meta(meta)

    pres = None
    status = 0
    gate_result = {"passed": None, "attempts": 0, "scores": []}
    try:
        pres = Presenter(session, logger, marker, dry_run=args.dry_run, buttons=buttons)
        print(f"  refresh rate: {pres.refresh_hz:.2f} Hz (frame {pres.frame_dur * 1000:.2f} ms)")
        pres.preload(stim_map, manifest, reward_names)

        first_row = runs[0]["trials"][0]["raw"]
        if lab_session:
            # the online pre-session taught the task; here a refresher, the button check and the
            # starting overview (this session's own start state), then the task (2026-10-26)
            # Resuming at block R (2026-11-04): the overview shows the journeys as they stand at the
            # end of block R-1, as in the break after it, not the session's starting state.
            if args.start_run > 1:
                prev = next(r for r in runs if r["run"] == args.start_run - 1)
                run_lab_intro(pres, resume_after=prev["run"])
                run_break_overview(pres, prev["trials"][-1]["raw"], prev["run"])
            else:
                run_lab_intro(pres)
                run_structure_overview(pres, first_row)
        elif "instructions" not in skip:
            show_instructions(pres)
        do_practice = (session["practice"] and cfg.RUN_PRACTICE and "practice" not in skip
                       and not lab_session)
        do_fam = cfg.RUN_FAMILIARIZATION and "familiarization" not in skip and not lab_session
        # shapes: practice before familiarization; real journeys (2026-10-01): after it, on the
        # first pass only, or on its own when familiarization is skipped
        real_practice = cfg.PRACTICE_STIMULI == "real"
        if do_practice and (not real_practice or not do_fam):
            run_practice(pres, session["schedule"], first_row)
        if do_fam:
            for attempt in range(1, (cfg.GATE_MAX_ATTEMPTS if cfg.RUN_GATE else 1) + 1):
                first_pass_practice = do_practice and real_practice and attempt == 1
                run_familiarization(pres, session["schedule"], first_row, attempt,
                                    done_key=("familiarization_done_real" if first_pass_practice
                                              else "familiarization_done"))
                if first_pass_practice:
                    run_practice(pres, session["schedule"], first_row)
                if not cfg.RUN_GATE or "gate" in skip:
                    break
                gate_result["attempts"] = attempt
                n_correct, n_total = run_gate(pres, session["schedule"], first_row, attempt)
                gate_result["scores"].append(f"{n_correct}/{n_total}")
                print(f"  gate attempt {attempt}: {n_correct}/{n_total} correct")
                if n_correct == n_total:
                    gate_result["passed"] = True
                    pres.show_message(strings.get(pres.lang, "gate_passed"))
                    break
                if attempt < cfg.GATE_MAX_ATTEMPTS:
                    pres.show_message(strings.get(pres.lang, "gate_failed"))
                else:
                    gate_result["passed"] = False
                    print(f"  *** gate NOT passed after {cfg.GATE_MAX_ATTEMPTS} attempts -- "
                          "continuing anyway")
                    pres.show_message(strings.get(pres.lang, "gate_exhausted"))
            # the last intro screen: the whole starting state on one screen, every journey from
            # start to finish with its treasure and points, and the message that it will now
            # keep changing. The only time all three journeys are ever on screen together.
            run_structure_overview(pres, first_row)

        run_main(pres, runs, session, start_run=args.start_run)
        pres.show_message(strings.get(pres.lang, "goodbye") + "\n\n"
                          + strings.get(pres.lang, "final_score", n_correct=pres.score["correct"],
                                        n_questions=pres.score["n"]), footer=False)

    except QuitExperiment:
        print("\nStopped by the experimenter. Data up to the last completed trial is saved.")
        status = 1
    finally:
        logger.write_session_end({
            "gate_passed": gate_result["passed"],
            "gate_attempts": gate_result["attempts"],
            "gate_scores": gate_result["scores"],
            # the performance score over the main-task questions (2026-10-02)
            "n_correct": pres.score["correct"] if pres is not None else 0,
            "n_questions": pres.score["n"] if pres is not None else 0,
            # halves round up, like Math.round in the browser arm
            "score_pct": (int(100 * pres.score["correct"] / pres.score["n"] + 0.5)
                          if pres is not None and pres.score["n"] else 0),
            "status": "stopped" if status else "complete",
            "finished": datalog_mod.wallclock(),
        })
        if pres is not None:
            print(f"  dropped frames: {pres.win.nDroppedFrames}")
            pres.close()
        marker.close()
        logger.close()
        print(f"  data written to {logger.path}")

    return status


if __name__ == "__main__":
    sys.exit(main())
