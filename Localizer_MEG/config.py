"""Configuration of the alien MEG localizer (2026-10-13). Every duration, key, code and path lives here.

Design-level timing (ITIs, which trials carry a probe, probe content) comes from the design CSV
(generate_localizer_designs.py); the values below are the presentation side and must match the
probe columns of the design (probe_max_rt, probe_total), which run_localizer.py checks.

The pictures are read from the MRI localizer's folder (decided 2026-10-13: one copy of the
stimuli), so the MEG stimulus PC needs Localizer_MRI/stimuli next to this folder. Since 2026-10-26
the final stills on grey (probe/, alternatives_grey/, the designs name them). Since 2026-10-28
(user, on an MEG colleague's advice, as the main task) each picture plays its 1 s video, the
MRI localizer's pre-decoded frames (MANIFEST); the probes keep the stills.
"""
import sys
from pathlib import Path

# the MEG lab's hardware (port, pulses, 0..127, response box, button bytes, photodiode) is
# shared with the main task in ../meg_lab (2026-10-14): change it THERE
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meg_lab import settings as lab                                       # noqa: E402
from meg_lab.codes import CLASS_CODES, SHARED_CODES                       # noqa: E402

HERE = Path(__file__).resolve().parent
DESIGN_DIR = HERE / "designs"
STIM_DIR = HERE.parent / "Localizer_MRI" / "stimuli"
# the videos (2026-10-28): per class its frames, as in the MRI localizer
MANIFEST = STIM_DIR / "localizer_manifest_video.json"
DATA_DIR = HERE / "data"
FEEDBACK_IMAGES = {"correct": STIM_DIR / "feedback" / "feedback_correct.png",
                   "incorrect": STIM_DIR / "feedback" / "feedback_false.png"}

# ---------------------------------------------------------------------------
# Timing (seconds)
# ---------------------------------------------------------------------------
T_STIM = 1.0                # each video, in full (24 frames at 24 fps; 0.75 s stills before 2026-10-28)
PROBE_MAX_RT = 1.5          # answer window, as MRI
PROBE_TOTAL = 2.0           # probe plus feedback, measured from probe onset, as MRI
TIMEOUT_MAX = 5.0           # timeout message: until a button or this long
T_BLOCK_LEAD_IN = 5.0       # fixation after the trigger, before the first trial
T_BLOCK_LEAD_OUT = 5.0      # fixation after the last trial of a block
FINAL_FIXATION = 7.0        # fixation after the last block, before the goodbye screen
DRY_RUN_SCALE = 0.02        # --dry-run multiplies every duration by this

# ---------------------------------------------------------------------------
# Markers (decided 2026-10-13: class-coded, 8 bit, no photodiode)
# ---------------------------------------------------------------------------
# Each code is sent right after the flip that puts its event on screen (the response code when
# the key press is read). Every code sent is also logged in the `marker` column of the output.
# MEG lab (technician, 2026-10-14): stimulus PC "faecherfisch", PsychoPy under Linux, codes via
# LPT1 (/dev/parport0), values 0..127 only (bit 8 is broken), each held 20 ms, then back to 0.
# Linux setup: pyparallel installed, kernel module ppdev loaded (lp removed), and the user allowed
# to write /dev/parport0 (usually the lp group).
MARKER_BACKEND = lab.MARKER_BACKEND     # 'dummy' here; 'parallel' in the MEG (--marker-backend)
PARALLEL_PORT_ADDRESS = lab.PARALLEL_PORT_ADDRESS
SERIAL_PORT = lab.SERIAL_PORT
SERIAL_BAUDRATE = lab.SERIAL_BAUDRATE
LSL_STREAM_NAME = "alien_localizer_meg_markers"
MARKER_PULSE_DURATION = lab.MARKER_PULSE_DURATION
MARKER_MIN_GAP = lab.MARKER_MIN_GAP
MARKER_MAX_CODE = lab.MARKER_MAX_CODE
# Photodiode check (2026-11-11): off by default, on with --photodiode (the start dialog's
# "Photodiode check"). A white stripe across the top of the screen whose middle third toggles
# white/black on every flip that sends a code (../meg_lab/photodiode.py, shared with the main task).
PHOTODIODE = lab.PHOTODIODE
PHOTODIODE_STRIPE_HEIGHT = lab.PHOTODIODE_STRIPE_HEIGHT

# CLASS_CODES (picture onset = its class, 1..12) come from meg_lab.codes, shared with the main task
MARKER_CODES = {
    "fixation": SHARED_CODES["fixation"],          # the ITI fixation before each picture
    "probe_fixation": 30,
    "probe_match": 40,
    "probe_neither": 41,
    # one code per button in both MEG tasks (2026-11-05): 50 left (byte 4), 51 middle (3), 52 right (2);
    # here the middle button means "neither picture" (before 2026-11-05: 51 right, 52 neither)
    "response_left": 50,
    "response_neither": 51,
    "response_right": 52,
    "feedback_correct": SHARED_CODES["feedback_correct"],
    "feedback_incorrect": SHARED_CODES["feedback_incorrect"],
    "timeout": SHARED_CODES["timeout"],
    "block_start": SHARED_CODES["block_start"],      # + block number, sent at the trigger (t0)
    "block_end": SHARED_CODES["block_end"],        # + block number, sent at the end of the lead-out fixation
                             # (2026-10-14: was 200, above the 127 limit)
}

# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------
# MEG response box (technician, 2026-10-14): 4 buttons on COM2 (Linux /dev/ttyS1), 19200 baud,
# no parity, 8 data bits, 2 stop bits; each press sends one byte, its number, read as "btn<n>"
# (responses.py). The keyboard keys J / K / L always work too.
# THE ONE PLACE TO CHANGE WHICH BUTTON ANSWERS WHAT (keys below). Since 2026-11-11 (user): byte 4 =
# left picture, byte 3 = neither, byte 2 = right picture. The bytes are in ../meg_lab/settings.py
# (POSITION_BUTTONS), shared with the main task (4 left, 3 middle, 2 right).
BUTTON_BOX = False          # True in the MEG: also read the serial response box
# the box's port and which byte each button sends: ../meg_lab/settings.py (shared)
BUTTON_SERIAL_PORT = lab.BUTTON_SERIAL_PORT
BUTTON_BAUDRATE = lab.BUTTON_BAUDRATE
BUTTONS = lab.BUTTONS
# Unified with the MEG main task (2026-11-05): the same button and the same key mean the same
# position in both tasks, left to right: byte 4 / J = left, byte 3 / K = middle ("neither"
# here), byte 2 / L = right (before: J left, K right, L neither, plus the MRI's b / z / r, which the MEG
# keyboard never needs).
KEY_LEFT = ("j",) + lab.POSITION_BUTTONS["left"]              # left picture: byte 4
KEY_NEITHER = ("k",) + lab.POSITION_BUTTONS["middle"]         # neither picture: byte 3
KEY_RIGHT = ("l",) + lab.POSITION_BUTTONS["right"]            # right picture: byte 2
KEY_CONTINUE = ("space", "j", "k", "l") + BUTTONS   # participant-paced screens (any button)
KEY_OPERATOR = ("space",)   # operator screens before each block (keyboard only)
TRIGGER_KEYS = ("t",)       # the experimenter's start key; the first one of a block is its t0
KEY_QUIT = ("escape",)
# button check before block 1: (instruction string key, accepted keys) in order
BUTTON_CHECK = (("check_left", KEY_LEFT), ("check_neither", KEY_NEITHER),
                ("check_right", KEY_RIGHT))       # left to right, as the main task's check

KEYBOARD_BACKEND = "ptb"    # 'ptb' (best timing; fine on Linux) or 'event' (no macOS permission needed)

# ---------------------------------------------------------------------------
# Display (mirrors the main task: mid-grey background, height units)
# ---------------------------------------------------------------------------
FULLSCREEN = True
SCREEN = 0
BACKGROUND_COLOR = (0.00392, 0.00392, 0.00392)   # exactly RGB 128, the frames' background, as the main task (2026-11-09; (0, 0, 0) is 127.5 and can render as 127; black before 2026-10-26)
WINDOW_SIZE = (1280, 720)   # only when not fullscreen
UNITS = "height"

STIM_HEIGHT = 0.60          # a video: its grey square (the object fills about 30 to 75 % of it); as the
                            # main task and the MRI localizer: 0.60 since 2026-10-26 (0.50 before, 0.33 on
                            # the old cards), so the objects are as large as on the old cards
PROBE_HEIGHT = 0.60         # each probe square, as tall as the picture: an item has one size (as MRI; 0.60 since 2026-10-26)
PROBE_X = 0.40              # probe square centers at -x and +x (as MRI)
FEEDBACK_HEIGHT = 0.30

FIXATION_TEXT = "+"
FIXATION_HEIGHT = 0.10
FIXATION_COLOR = "white"

TEXT_HEIGHT = 0.045
TEXT_WRAP = 1.3
TEXT_COLOR = "white"
FOOTER_HEIGHT = 0.035
FOOTER_Y = -0.42
