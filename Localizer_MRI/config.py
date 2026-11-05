"""Configuration of the alien MRI localizer (2026-10-13). Every duration, key and path lives here.

Design-level timing (ITIs, which trials carry a probe, probe content) comes from the design CSV
(generate_localizer_designs.py); the values below are the presentation side and must match the
probe columns of the design (probe_max_rt, probe_total), which run_localizer.py checks.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN_DIR = HERE / "designs"
STIM_DIR = HERE / "stimuli"
# the video version (2026-10-23): per class its frames for the scanner, still images for the probes
MANIFEST = STIM_DIR / "localizer_manifest_video.json"
DATA_DIR = HERE / "data"
FEEDBACK_IMAGES = {"correct": STIM_DIR / "feedback" / "feedback_correct.png",
                   "incorrect": STIM_DIR / "feedback" / "feedback_false.png"}

# ---------------------------------------------------------------------------
# Timing (seconds)
# ---------------------------------------------------------------------------
T_STIM = 1.0                # each video, in full (24 frames at 24 fps; 0.75 s pictures before 2026-10-23)
PROBE_MAX_RT = 1.5          # answer window, as the old study actually ran (maxWait=1.5)
PROBE_TOTAL = 2.0           # probe plus feedback, measured from probe onset (old: core.wait(2 - RT))
TIMEOUT_MAX = 5.0           # timeout message: until a button or this long (old timeout_message)
T_BLOCK_LEAD_IN = 5.0       # fixation after the trigger, before the first trial
T_BLOCK_LEAD_OUT = 5.0      # fixation after the last trial of a block
FINAL_FIXATION = 7.0        # fixation after the last block, before the goodbye screen (old: 7 s)
DRY_RUN_SCALE = 0.02        # --dry-run multiplies every duration by this

# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------
# Scanner button box as in the old RepChanges study (config_shared.py): b = blue, right index;
# z = yellow, right middle; r = green, left index; g = red, left middle (unused). J/K/L also work,
# for a laptop. THE ONE PLACE TO CHANGE THE RESPONSE KEYS.
# Settled 2026-11-04 from RepChanges on the same scanner (config_shared.py:35-38, its button
# check in instruction_texts_shared.py:4-7, loc_1_utils.py:119-133): every session's check passed
# on b, z, r and g in turn, so these are four different buttons and the box sends z, not y. The
# 2026-10-26 "b / y / g" are the colors blue, yellow, green (keys b, z, r); g is the red left
# middle button, which RepChanges never used for answers, so it no longer means "neither". "y"
# stays as a layout fallback only (the one key a German layout swaps; no other button sends it).
# 2026-11-05: the main task's MRI answers now follow this same pattern (b left, z right, r the
# third answer, there the middle picture), so a button means the same in both MRI tasks.
KEY_LEFT = ("b", "j")            # left picture
KEY_RIGHT = ("z", "y", "k")      # right picture
KEY_NEITHER = ("r", "l")         # neither picture
KEY_CONTINUE = ("b", "z", "y", "r", "g", "space")   # participant-paced screens (any button, as RepChanges)
KEY_OPERATOR = ("space",)   # operator screens before each block (keyboard only)
TRIGGER_KEYS = ("t", "T")   # the scanner's trigger (either case, as the old setup); the first one of a block is its t0
KEY_QUIT = ("escape",)
# button check before block 1: (instruction string key, accepted keys) in order
BUTTON_CHECK = (("check_left", KEY_LEFT), ("check_right", KEY_RIGHT),
                ("check_neither", KEY_NEITHER))

KEYBOARD_BACKEND = "ptb"    # 'ptb' (best timing) or 'event' (no macOS permission needed)

# ---------------------------------------------------------------------------
# Display (mirrors the main task: black background, height units)
# ---------------------------------------------------------------------------
FULLSCREEN = True
SCREEN = 0
BACKGROUND_COLOR = (0, 0, 0)   # mid grey (RGB 128), the stimuli's own background (2026-10-23; was black)
WINDOW_SIZE = (1280, 720)   # only when not fullscreen
UNITS = "height"

STIM_HEIGHT = 0.60          # a video: its central square (the full 1080-line frame height); 0.60 since 2026-10-26
                            # (0.50 before), as the main task, so the objects are as large as on the old cards
PROBE_HEIGHT = 0.60         # each probe square, as tall as the video square: an item has one size (2026-10-23; 0.60 since 2026-10-26)
PROBE_X = 0.40              # probe square centers at -x and +x
FEEDBACK_HEIGHT = 0.30

FIXATION_TEXT = "+"
FIXATION_HEIGHT = 0.10
FIXATION_COLOR = "white"

TEXT_HEIGHT = 0.045
TEXT_WRAP = 1.3
TEXT_COLOR = "white"
FOOTER_HEIGHT = 0.035
FOOTER_Y = -0.42
