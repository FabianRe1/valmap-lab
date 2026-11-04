"""
Central configuration for the grid value/structure task (PsychoPy / offline arm).

Every timing value, key, path and marker code lives here; the trial loop in run_task.py contains
no magic numbers. The canonical specification these values implement is ../../experiment_spec.md.

Mirrored by ../jspsych/config.js -- if you change one, change the other and re-run
tests/check_parity.py.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# repository root = two levels up from this file (src/psychopy/config.py)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# The MEG lab's hardware (trigger port, 20 ms pulses, codes 1..127, response box, which byte each
# button sends, the photodiode switch) is shared with the MEG localizer in
# P7_struct_value/meg_lab, next to this repo (2026-10-14): change it THERE, both tasks follow.
import sys                                                                    # noqa: E402
sys.path.insert(0, str(REPO_ROOT.parent))
from meg_lab import settings as lab                                           # noqa: E402
from meg_lab.codes import CLASS_CODES, SHARED_CODES                           # noqa: E402

# ---------------------------------------------------------------------------
# Route length. The design forks here: 4 is the original, 3 the shorter variant.
# Everything below derives from it, so selecting a variant is a single knob.
# ---------------------------------------------------------------------------
N_STEPS = int(os.environ.get("GRID_STEPS", "4"))


# the session sets (2026-10-09): three designs per subject from one starting constellation, in
# schedules_online/, schedules_meg/, schedules_mri/ (generate_schedules_grid.py, GRID_SESSIONS=1).
# None = the classic set. GRID_SESSION selects one for the checkers, --session for a run.
SESSION_SETS = ("online", "meg", "mri")
SESSION_SET = os.environ.get("GRID_SESSION") or None


def _schedule_dir(n, session_set=None):
    if session_set:
        return REPO_ROOT / (f"schedules_{session_set}" + ("" if n == 3 else f"_{n}step"))
    return REPO_ROOT / ("schedules_grid" if n == 4 else f"schedules_grid_{n}step")


def cells_for(n):
    return tuple(f"{c}{s}" for c in "ABC" for s in range(1, n + 1))


# Clip ids ARE the picture file stems in stimuli/images/, so a schedule row can be read without a
# lookup table: animals_1 is stimuli/images/animals_1.png (2026-09-29; the main-task stimuli are
# still pictures, no longer videos). One category per step, three exemplars each; the 3-step task
# uses the first three categories. stimuli/manifest.json is keyed by these names, and
# generate_schedules_grid.py builds the same alphabet. Mirrored by ../jspsych/config.js.
CLIP_CATEGORIES = ("animals", "vehicles", "food", "music")
# the 3-step task's space set (2026-10-05), in this fixed order for everyone: aliens travel by
# spaceship to planets
SPACE_CATEGORIES = ("aliens", "spaceships", "planets")


def names_rows_for(n):
    """The names screen before the walks (2026-10-06): the pictures of each category in one row,
    in the order the user gave (lizard, bird, whale; boat, car, rocket; city, volcano, forest),
    each with its name (strings `name_<id>`) above it. Only the space set of the 3-step task has
    names; elsewhere the screen is skipped. Mirrors namesRowsFor() in ../jspsych/config.js."""
    if n != 3:
        return None
    return [["aliens_3", "aliens_2", "aliens_1"], ["spaceships_1", "spaceships_2", "spaceships_3"],
            ["planets_2", "planets_1", "planets_3"]]


def clip_ids_for(n):
    cats = SPACE_CATEGORIES if n == 3 else CLIP_CATEGORIES[:n]
    return tuple(f"{cat}_{i}" for cat in cats for i in range(1, 4))


def shape_ids_for(n):
    return tuple(f"shp{i:02d}" for i in range(1, 3 * n + 1))


def apply_steps(n, session_set=None):
    """Select the 3-step or 4-step variant, and optionally a session set (online, meg, mri).
    Call once at startup, before any schedule is loaded."""
    if n not in (3, 4):
        raise ValueError(f"N_STEPS must be 3 or 4, got {n}")
    if session_set is not None and session_set not in SESSION_SETS:
        raise ValueError(f"session must be one of {SESSION_SETS}, got {session_set}")
    g = globals()
    g["N_STEPS"] = n
    g["WALK_LENGTH"] = n
    g["SESSION_SET"] = session_set or SESSION_SET
    g["SCHEDULE_DIR"] = _schedule_dir(n, g["SESSION_SET"])
    g["CELLS"] = cells_for(n)
    g["CLIP_IDS"] = clip_ids_for(n)
    g["NAMES_ROWS"] = names_rows_for(n)
    g["PRACTICE_SHAPE_IDS"] = shape_ids_for(n)
    return n


SCHEDULE_DIR = _schedule_dir(N_STEPS, SESSION_SET)
CELLS = cells_for(N_STEPS)
SCHEDULE_PATTERN = "sub-{:03d}_schedule.csv"
MANIFEST_PATH = REPO_ROOT / "stimuli" / "manifest.json"

DATA_DIR = Path(__file__).resolve().parent / "data"

TASK_NAME = "gridvalstruct"

# ---------------------------------------------------------------------------
# Timing (seconds) -- experiment_spec.md section 4
# ---------------------------------------------------------------------------

T_VIDEO = 0.75          # each picture; apply_stimulus_mode() sets it from the modality (videos 1.0 s)
T_OUTCOME = 1.0         # reward image + amount, closing EVERY trial (a change trial included)
# Every trial is one sequential walk: its shown clips, then the outcome (decided 2026-09-23). A
# change is recognisable only from what the clips and the outcome say, never from a separate
# screen or label, and the same partial formats also occur without any change.
T_PROBE = 8.0           # probe response window (a cap: the probe ends on response); 8 s since 2026-09-11
# The fixation that opens EVERY trial (decided 2026-09-11): mean 3 s, drawn per block with the
# same jitter machinery as the ISIs (see iti.start_gaps_for_block), logged as fixation_start.
TRIAL_START_MEAN = 3.0
TRIAL_START_RANGE = (2.0, 4.0)

# ---------------------------------------------------------------------------
# Timing profiles -- the ONLY thing that differs between the modalities
# ---------------------------------------------------------------------------
# Everything else about the session (trials, order, stimuli, probes, logging) is identical; picking
# a profile only changes the ISI distribution and the rest length. Selected from the modality at
# startup via apply_timing_profile(); see experiment_spec.md section 4.
TIMING_PROFILES = {
    # online (behavioral) and MEG: short jittered ISIs, short rest
    "online_meg": {
        "GAP_MEAN": 0.75,
        "GAP_RANGE": (0.5, 1.0),
        "LONG_ISI": None,               # no long ISI outside the scanner
        "LONG_ISI_RANGE": None,
        "T_REST": 5.0,
        "LONGEST_GAP_BEFORE_OUTCOME": False,
        # added to every gap that FOLLOWS A CLIP (not the one after the outcome), on top of the
        # drawn value: those gaps run [1.0, 1.5] s, mean 1.25 (2026-09-24)
        "CLIP_GAP_EXTRA": 0.5,
    },
    # fMRI: ~1 s ISIs plus EXACTLY ONE ~3 s ISI per trial, at a randomly chosen slot, to
    # decorrelate responses to successive events. Long rest for the replay readout.
    "mri": {
        "GAP_MEAN": 1.0,
        "GAP_RANGE": (0.5, 1.5),
        "LONG_ISI": 3.0,
        "LONG_ISI_RANGE": (2.5, 3.5),
        "T_REST": 20.0,
        "LONGEST_GAP_BEFORE_OUTCOME": False,   # superseded by the random long-ISI slot
        "CLIP_GAP_EXTRA": 0.0,
    },
}

MODALITY_PROFILE = {"behavioral": "online_meg", "meg": "online_meg", "fmri": "mri"}
DEFAULT_TIMING_PROFILE = "online_meg"


def apply_timing_profile(name):
    """Overwrite the module-level timing constants from TIMING_PROFILES[name]. Called once at
       startup from the chosen modality, before any schedule is loaded."""
    if name not in TIMING_PROFILES:
        raise KeyError(f"unknown timing profile '{name}'; have {sorted(TIMING_PROFILES)}")
    globals().update(TIMING_PROFILES[name])
    globals()["TIMING_PROFILE"] = name
    return name


def apply_response_keys(modality):
    """The scanner's keys (MRI_OPTION_KEYS) in fMRI; everything else keeps J, K, L. Called once at
       startup; run_task.OPTION_KEYS follows KEY_OPTION_1..3."""
    if modality != "fmri":
        return "keyboard"
    g = globals()
    g["KEY_OPTION_1"], g["KEY_OPTION_2"], g["KEY_OPTION_3"] = MRI_OPTION_KEYS
    g["KEY_OPTION_LABELS"] = MRI_OPTION_LABELS
    g["KEY_CONTINUE"] = MRI_CONTINUE_KEYS
    g["CONTINUE_TEXT_KEY"] = "press_button"
    return "scanner_buttons"


# The lab sessions (MEG, MRI; 2026-10-26, user): the online pre-session teaches the task in full,
# so a lab session opens with a short refresher, a button check and the starting overview, then
# the task: no instructions, practice, familiarization or gate.
LAB_SESSIONS = ("meg", "mri")


def apply_stimulus_mode(modality):
    """Videos or stills, from the modality (see VIDEO_MODALITIES); sets VIDEO_MODE and T_VIDEO.
       Called once at startup, after the timing profile and before any schedule is loaded."""
    g = globals()
    g["VIDEO_MODE"] = modality in VIDEO_MODALITIES
    g["T_VIDEO"] = T_VIDEO_PLAYING if g["VIDEO_MODE"] else T_VIDEO_STILL
    return "video" if g["VIDEO_MODE"] else "still"


def profile_for_modality(modality):
    return MODALITY_PROFILE.get(modality, DEFAULT_TIMING_PROFILE)

# Whether a probe ends as soon as an option key is pressed. False makes every probe run its full
# T_PROBE so run durations are fully determined by the schedule.
PROBE_ADVANCE_ON_RESPONSE = True
PROBE_CONFIRM_HOLD = 0.4    # how long the chosen option stays highlighted before moving on

# Jitter: every gap (after each clip and after the outcome) is one makeITI draw.
# Draws are balanced per RUN, seeded from (schedule_number, run_index).
# defaults; apply_timing_profile() replaces these from the selected profile
GAP_MEAN = 0.75
GAP_RANGE = (0.5, 1.0)
CLIP_GAP_EXTRA = 0.5        # see TIMING_PROFILES
LONG_ISI = None
LONG_ISI_RANGE = None
T_REST = 5.0
TIMING_PROFILE = DEFAULT_TIMING_PROFILE
GAP_MAX_DEVIATION = 0.01

# On full-walk trials the LONGEST of the trial's drawn gaps is permuted into the slot after the
# last clip and before the outcome (decorrelates sequence-evoked from outcome-evoked BOLD).
# Permutation only; the trial's total duration is unchanged. Change trials are untouched.
LONGEST_GAP_BEFORE_OUTCOME = False

# Reproduce the lab's makeITI acceptance test faithfully (unsigned; only rejects sums that are
# too small). True uses abs() and holds each run's gap total to +/- GAP_MAX_DEVIATION.
ITI_STRICT_BALANCE = False
ITI_USE_NUMPY = False   # True gives up cross-arm ITI parity, nothing else

# Practice-only: the rest window is shortened so it can be experienced without costing 20 s.
T_REST_PRACTICE = 5.0
T_FEEDBACK = 1.2

# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

# The run split is NOT computed here. Every schedule row states its run in the `block` column
# (1..6), assigned by the generator so that each block opens immediately before a value change, the
# establish trial sits in block 1, and no structure change is separated from its reinforcing
# cluster. The arms group trials by that column; validate_schedule.py checks the column's
# invariants on every load. N_RUNS is therefore only the expected number of blocks, used for the
# break screens and as a sanity check against the file.
N_RUNS = 6

# ---------------------------------------------------------------------------
# Schedule validation -- the run aborts unless these hold
# ---------------------------------------------------------------------------

# EVERY per-session count is READ FROM THE FILE. The design is retuned from time to time (the trial
# count has been 145, 162 and 156-169 across generations, and rests/probes 90 and 108), so no count
# is hard-coded here: a fixed number is a guaranteed abort at the next regeneration. The only guard
# is a wide plausibility band that catches a truncated or wrong file. The per-row design rules
# (which kinds carry a rest, what a probe may look like) belong to validate_schedule.py, which runs
# on every load.
EXPECTED_N_TRIALS_RANGE = (100, 220)
KINDS = ("EST", "V", "S", "CV", "CS", "T")
PROBE_DIRECTIONS = ("preference", "same_sequence")
WALK_LENGTH = N_STEPS
CLIP_IDS = clip_ids_for(N_STEPS)
NAMES_ROWS = names_rows_for(N_STEPS)
REWARD_NAMES = ("money", "gold", "diamonds")

# kind -> BIDS-style event type used in the events file and for marker offsets
KIND_EVENT_TYPE = {
    "EST": "establish",
    "V": "value_change",
    "S": "structure_change",
    "CV": "value_control",
    "CS": "structure_control",
    "T": "tracking",
    # the change formats without a change, unrested (2026-09-23)
    "TV": "partial_tracking_value",
    "TS": "partial_tracking_structure",
}

# ---------------------------------------------------------------------------
# Modality / hardware
# ---------------------------------------------------------------------------

# 'behavioral' (default) | 'fmri' | 'meg'. Behavioral is the first-class, tested path this round.
DEFAULT_MODALITY = "behavioral"

# EVERY block of the main task starts on this key, in every modality, and its timestamp is the
# block clock's zero: every onset in the trials log and the events file is measured from it. In
# the scanner the pulse arrives on its own; outside it the experimenter presses T. Keeping the
# gate in all modalities means a behavioral or MEG session has the same block structure and the
# same t0 definition as a scanned one. 't' comes from the lab's previous fMRI experiment.
TRIGGER_KEYS = ("t", "T")
TRIGGER_GATED_BLOCKS = True     # set False only for an unattended session with no experimenter
# Fixation held between the trigger and the block's first trial, so every block opens on the
# same settled baseline. It sits INSIDE the block clock: t0 is still the key press, the lead-in
# runs from 0.0 to T_BLOCK_LEAD_IN, and trial 1 starts after it.
T_BLOCK_LEAD_IN = 3.0
# fMRI: the site's scanner records its own dummy volumes and sends the trigger key ONCE, after
# them, so nothing is waited out here (decided 2026-09-10): the trigger is t0 and the lead-in
# fixation follows at once. Raise this only for a scanner that sends a pulse on every volume
# including the dummies; the wait then counts pulses after t0 before the lead-in.
DUMMY_VOLUMES = 0

# MEG photodiode: one switch for both tasks, in meg_lab/settings.py (off since 2026-10-14). When on,
# a white patch flashes in a corner at each coded onset in MEG mode, alongside the port code.
PHOTODIODE = lab.PHOTODIODE
PHOTODIODE_DURATION = lab.PHOTODIODE_DURATION
PHOTODIODE_SIZE = lab.PHOTODIODE_SIZE
PHOTODIODE_POS = lab.PHOTODIODE_POS

# Marker backend: 'dummy' | 'parallel' | 'lsl' | 'serial'; port, pulse (20 ms), gap and the 1..127
# limit come from meg_lab/settings.py (the MEG lab, 2026-10-14)
MARKER_BACKEND = lab.MARKER_BACKEND
PARALLEL_PORT_ADDRESS = lab.PARALLEL_PORT_ADDRESS
SERIAL_PORT = lab.SERIAL_PORT
SERIAL_BAUDRATE = lab.SERIAL_BAUDRATE
LSL_STREAM_NAME = "gridvalstruct_markers"
MARKER_PULSE_DURATION = lab.MARKER_PULSE_DURATION
MARKER_MAX_CODE = lab.MARKER_MAX_CODE

# Marker codes (2026-10-14), aligned with the MEG localizer and all within 1..127. Each is sent
# right after the flip that shows its event (a response when the key is read):
#   picture onset = its class, as in the localizer (meg_lab.codes.CLASS_CODES): aliens 1-3,
#   spaceships 4-6, planets 7-9; the outcome screen = its treasure, money 10, gold 11, diamonds 12;
#   a practice shape 13; the trial-opening fixation = the trial type (TRIAL_START_CODES);
#   a fixation gap 20, the rest 30, the question by its type (PROBE_CODES), the answer 50 / 51 / 52
#   (left / middle / right option), no answer in time 62, feedback 60 / 61, block start 100 + block
#   (at the trigger, t0), block end 110 + block.
MARKER_CODES = {
    "fixation": SHARED_CODES["fixation"],
    "practice_shape": 13,
    "rest": 30,
    "response_1": 50,
    "response_2": 51,
    "response_3": 52,
    "timeout": SHARED_CODES["timeout"],
    "feedback_correct": SHARED_CODES["feedback_correct"],
    "feedback_incorrect": SHARED_CODES["feedback_incorrect"],
    "block_start": SHARED_CODES["block_start"],
    "block_end": SHARED_CODES["block_end"],
}

# The trial-opening fixation carries the trial type, so the type is in the marker stream alone.
TRIAL_START_CODES = {
    "familiarization": 19,
    "EST": 21, "V": 22, "S": 23, "CV": 24, "CS": 25, "T": 26, "TV": 27, "TS": 28,
    "practice": 29,
}

# The question's onset carries its type (the older names of the first pilots map to the same codes).
PROBE_CODES = {
    "value_unobserved": 40, "value_established": 41, "value_observed": 41,
    "structure_unobserved": 42, "structure_established": 43, "structure_observed": 43,
}

# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

# Keyboard backend: 'ptb' (best timing; needs macOS Input Monitoring permission or it segfaults),
# 'event' (no permission needed), 'iohub'.
KEYBOARD_BACKEND = "ptb"

# Direct 3AFC mapping, left to right = options 1/2/3. Formerly the number row, JKL and the MRI
# button box in parallel (blue 'b', yellow 'z', green 'r' from the lab's RepChanges setup), so the
# same build runs on a laptop and in the scanner unchanged.
# THE ONE PLACE TO CHANGE THE RESPONSE KEYS (decided 2026-09-10: J, K, L only for now). Each
# option accepts every key in its tuple, so to add a scanner button box just append its key
# names, for example KEY_OPTION_1 = ("j", "b"). The labels drawn under the three options come
# from KEY_OPTION_LABELS and do not have to match the key names (a button box may send "1"
# while the screen still says J). Mirror any change in ../jspsych/config.js; check_parity
# verifies the two arms agree.
KEY_OPTION_1 = ("j",)
KEY_OPTION_2 = ("k",)
KEY_OPTION_3 = ("l",)
KEY_OPTION_LABELS = ("J", "K", "L")   # shown under the options, left to right
KEY_CONTINUE = ("space", "b")   # advance instruction screens; blue works inside the scanner
CONTINUE_TEXT_KEY = "press_space"   # the footer on self-paced screens (the scanner: any button)
# The scanner (MPI CBS Leipzig) INSTEAD of J, K, L; apply_response_keys() sets them. Settled
# 2026-11-04 from RepChanges, run on the same scanner (config_shared.py:35-38 and its button
# check, instruction_texts_shared.py:4-7), which sent and logged these keys:
#   b = blue, right index    -> LEFT option
#   z = yellow, right middle -> MIDDLE option
#   r = green, left index    -> RIGHT option
#   g = red, left middle     -> no answer (RepChanges never used it for answers either)
# Same three buttons, in the same order, as RepChanges' localizer (left, right picture, neither)
# and its three-option code (utils_shared.py:810-827, b/z/r = left/middle/right). The user's
# "b, y, g" (2026-10-26) are the colors blue, yellow, green, i.e. keys b, z, r; "g" is the red
# button, so it no longer answers. "y" stays on the middle option ONLY as a layout fallback (a
# German layout is the one place y and z swap; no other button sends y). Any button or the space
# bar advances a screen, as in RepChanges; no letters under the options.
MRI_OPTION_KEYS = (("b",), ("z", "y"), ("r",))
MRI_OPTION_LABELS = ("", "", "")
MRI_CONTINUE_KEYS = ("b", "z", "y", "r", "g", "space")
# MEG response box (--button-box, 2026-10-14): its buttons are read next to the keyboard (J, K, L
# and space keep working). Since 2026-11-04 as the experiment that currently runs in this MEG lab
# (Evie Coxon's test_sweeps-2-main, run_sweeps_test.m:109-110): left option = BLUE button (byte 4),
# right option = RED button (byte 1); the colleague uses no third button, so the middle option
# takes either button between them (bytes 2, 3; confirm in the lab). The bytes are in
# meg_lab/settings.py (POSITION_BUTTONS, shared with the localizer). Any button advances a screen.
BUTTON_BOX = False
OPTION_BUTTONS = ("left", "middle", "right")   # left, middle, right option -> POSITION_BUTTONS
# The overview of the current journeys in every break between blocks (2026-10-01): keys are
# ignored for its first BREAK_OVERVIEW_MIN_S seconds, then it takes TWO presses to move on, so it
# cannot be skipped by accident. Mirrors ../jspsych/config.js.
BREAK_OVERVIEW = True
BREAK_OVERVIEW_MIN_S = 1.0
KEY_REPEAT_PRACTICE = ("p",)
KEY_QUIT = ("escape",)

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

FULLSCREEN = True
SCREEN = 0
BACKGROUND_COLOR = (0.00392, 0.00392, 0.00392)   # mid-grey 128, the final stimuli's background (2026-10-23)
WINDOW_SIZE = (1280, 720)           # only used when FULLSCREEN is False
UNITS = "height"

CLIP_HEIGHT = 0.60                  # a main-task picture: its grey square; 0.60 since 2026-10-26 (0.50 before)
                                    # so the objects are as large as on the old cards (they fill less of the square)
CLIP_ASPECT = 1.0
REWARD_ASPECT = 1.0                 # the final treasure images are square (2026-10-23; before 640x360)
# Videos (2026-10-23; the online sessions since 2026-10-26, the MEG since 2026-10-28, user): in
# these modalities every picture of a walk (familiarization and practice included) and the treasure
# on the outcome screen play their 1 s video in full; a modality left out would show the stills
# for 0.75 s (none does since 2026-10-28). PsychoPy shows the video frame
# by frame from the manifest's 'frames' / 'reward_frames' (24 frames at VIDEO_FPS), timed by the
# screen refreshes. Questions, names screens and journey maps always show the stills.
VIDEO_MODALITIES = ("fmri", "behavioral", "meg")
VIDEO_FPS = 24
T_VIDEO_STILL = 0.75            # a still picture (a modality outside VIDEO_MODALITIES)
T_VIDEO_PLAYING = 1.0           # a video, played in full
VIDEO_MODE = False              # set by apply_stimulus_mode()

OUTCOME_IMAGE_HEIGHT = 0.60        # the square treasure (2026-10-23; the treasure fills about half of it)
OUTCOME_TEXT_HEIGHT = 0.14
OUTCOME_TEXT_COLOR = "black"        # black like all text since 2026-11-04 (white with a shadow before)
OUTCOME_TEXT_SHADOW_COLOR = None    # None draws no shadow
OUTCOME_TEXT_SHADOW_OFFSET = 0.006
# the amount sits ABOVE the treasure since 2026-11-04 (user: they overlapped; -0.02, over it, before).
# Centred on the picture's top edge: the treasures, their videos included, keep to the lower 84 %
# of the square, so the number stays clear of them and close above them.
OUTCOME_TEXT_Y = OUTCOME_IMAGE_HEIGHT / 2

# The map overview draws its arrows with this glyph.
TRANSITION_ARROW_TEXT = "\u2192"

FIXATION_TEXT = "+"
FIXATION_HEIGHT = 0.10
FIXATION_START_HEIGHT = 0.30        # the trial-opening fixation, 3 x the normal cross (1.5 x on 2026-10-05, 2 x early 2026-10-06)
FIXATION_COLOR = "white"

PROMPT_HEIGHT = 0.055
PROMPT_COLOR = "black"              # every text, black since 2026-11-04 (user; white before)
PROMPT_WRAP = 1.4
PROMPT_Y = 0.02                     # probe prompt sits between the cue and the options

PROBE_OPTION_HEIGHT = 0.29         # 0.24 until 2026-10-26: the objects fill less of the new squares
PROBE_OPTION_Y = -0.26
PROBE_OPTION_GAP = 0.06
PROBE_CUE_HEIGHT = 0.29
PROBE_CUE_Y = 0.28
PROBE_KEY_HINT_HEIGHT = 0.035      # the KEY_OPTION_LABELS under the options
PROBE_KEY_HINT_DY = -0.19
# a question without a cue picture (the value question, "preference") sits higher since 2026-11-04
# (user): the options just below the middle of the screen instead of near the bottom
PROMPT_Y_NO_CUE = 0.10
PROBE_OPTION_Y_NO_CUE = -0.16

SELECTION_FRAME_COLOR = "yellow"    # drawn around the chosen option during the confirm hold
SELECTION_FRAME_WIDTH = 6
SELECTION_FRAME_PAD = 0.018

# the answer review after the practice swap questions (2026-10-05): the explanation on top, the
# question below it at a smaller size, the right answer framed green, the own answer labelled
REVIEW_TEXT_HEIGHT = 0.030
REVIEW_TEXT_WRAP = 1.5
REVIEW_TEXT_Y = 0.36
REVIEW_CUE_HEIGHT = 0.11
REVIEW_CUE_Y = 0.21
REVIEW_PROMPT_Y = 0.125
REVIEW_PROMPT_HEIGHT = 0.032
REVIEW_OPTION_HEIGHT = 0.11
REVIEW_OPTION_Y = 0.03
REVIEW_KEY_HINT_DY = -0.08
REVIEW_ANSWER_DY = -0.115           # "your answer", under the key hint of the chosen option
REVIEW_CORRECT_COLOR = "#3fcf5f"
# the names screens before the walks (2026-10-06): one category per screen, each name above its picture
NAMES_TEXT_Y = 0.32
NAMES_STILL_HEIGHT = 0.31          # 0.26 until 2026-10-26
NAMES_ROW_Y = -0.13                 # the pictures' centre
NAMES_COL_DX = 0.42
NAMES_LABEL_DY = 0.17               # the name sits this far above its picture's centre
NAMES_LABEL_HEIGHT = 0.05
# the two swapped journeys BEFORE and AFTER under each review (2026-10-05)
REVIEW_MAP_SIZE = 0.065
REVIEW_MAP_GAP = 0.05               # room for the arrow between two pictures
REVIEW_MAP_ARROW_HEIGHT = 0.04     # the arrow's length
REVIEW_MAP_PANEL_X = 0.42           # panel centres at -x (before) and +x (after)
REVIEW_MAP_LABEL_Y = -0.165
REVIEW_MAP_ROW_Y0 = -0.225
REVIEW_MAP_ROW_DY = -0.085

INSTRUCTION_HEIGHT = 0.05
INSTRUCTION_WRAP = 1.35
INSTRUCTION_FOOTER_HEIGHT = 0.040
INSTRUCTION_FOOTER_Y = -0.42

# ---------------------------------------------------------------------------
# Language / blocks
# ---------------------------------------------------------------------------

LANGUAGE = "en"

# Phases that can be skipped for testing, in session order. `main` is never skippable: it IS the
# experiment. Anything skipped is recorded in the meta JSON, so a session's data always says what
# the participant actually saw.
SKIPPABLE_PHASES = ("instructions", "practice", "familiarization", "gate")

# mirrors the generator's stable_per_change: every change is followed by this many
# fully observed stable trials, one per route, before the next change
STABLE_PER_CHANGE = 3

RUN_PRACTICE = True
# What the practice uses (2026-10-01): "real" = the participant's own starting journeys, after
# familiarization, with a reset to the starting state at its end; "shapes" = the drawn walkthrough
# before familiarization (the version up to 2026-09-30). Mirrors ../jspsych/config.js.
PRACTICE_STIMULI = "real"
PRACTICE_FEEDBACK = True    # feedback in the practice walkthrough and the mastery gate

# Correct/wrong feedback after EVERY probe response in the main task too. ON by decision of the
# owner (2026-09-11): participants are told after each question whether they were right, and the
# main-task intro says so. Recorded in the meta rows as main_task_feedback and printed at session
# start. Mirrors ../jspsych/config.js.
MAIN_TASK_FEEDBACK = True

# ---------------------------------------------------------------------------
# Practice stimuli: ABSTRACT SHAPES, never video
# ---------------------------------------------------------------------------
# Practice explains the LOGIC of the task and must not teach any video material, so it uses drawn
# shapes instead of clips: one COLOR per journey and one SHAPE per step, giving a 3 x 4 set
# `shp01`..`shp12` (shp01-04 = journey 1 step 1-4, shp05-08 = journey 2, shp09-12 = journey 3).
# Nothing is loaded from disk: the shapes are drawn, so practice adds no assets and no clips.
# A journey therefore reads as one colour walking through star, square, circle, triangle, and a
# structure change is visible as a journey that changes colour part way through.
PRACTICE_SHAPE_STEPS = ("star", "square", "circle", "triangle")     # step 1..4
PRACTICE_SHAPE_COLORS = ("#E8A33D", "#4C9BE8", "#C266C9")           # journey 1..3
PRACTICE_SHAPE_IDS = shape_ids_for(N_STEPS)
PRACTICE_SHAPE_SIZE = 0.34          # height units, the drawn shape's bounding box
PRACTICE_SHAPE_LINE_WIDTH = 0
# Journey map screens: whole journeys drawn start to finish on ONE screen, one row per journey,
# stimuli left to right with arrows between, optionally a label above the row and the journey's
# treasure and points at its end. Used twice: the practice map after the structure note (drawn
# shapes) and the starting-state overview before the main task (real stills). Self-paced.
MAP_CAPTION_TOP = 0.47             # the caption's top edge; it grows downward
MAP_CAPTION_HEIGHT = 0.040
MAP_GAP = 0.02                      # horizontal gap between neighbouring items in a row
MAP_ARROW_LENGTH = 0.06            # a drawn arrow (the font's arrow loses its head)
MAP_ARROW_WIDTH = 0.07
MAP_AMOUNT_HEIGHT = 0.07
MAP_AMOUNT_WIDTH = 0.13
MAP_LABEL_HEIGHT = 0.036
PRACTICE_MAP_SHAPE_SIZE = 0.13      # the practice map: two rows of shapes with a label each
PRACTICE_MAP_ROW_Y0 = 0.06
PRACTICE_MAP_ROW_DY = 0.34
PRACTICE_MAP_LABEL_DY = 0.12
# the swap's before/after diagram in the real practice (2026-10-02): frame colours (seen = the
# journey whose new continuation was shown, inferred = the one to be worked out) and layout
SWAP_MAP_CAPTION_Y = 0.33           # its caption is long, so it sits lower than the map caption
# the before/after diagram (height units; mirrors SWAP_DIAGRAM in ../jspsych/config.js)
SWAP_DIAGRAM_PIC = 0.085
SWAP_DIAGRAM_GAP = 0.07
SWAP_DIAGRAM_ROW_GAP = 0.045
SWAP_DIAGRAM_PANEL_GAP = 0.10
SWAP_DIAGRAM_ROW_Y0 = 0.05
SWAP_DIAGRAM_LABEL_DY = 0.035
SWAP_DIAGRAM_FRAME_PAD = 0.010
SWAP_DIAGRAM_FRAME_LINE = 0.0055
SWAP_DIAGRAM_CROSS_BAND = 0.038
SWAP_DIAGRAM_ARROW_HEAD = 0.014
MARK_SEEN_COLOR = "#F2C230"
MARK_INFERRED_COLOR = "#4C9BE8"
OVERVIEW_STILL_HEIGHT = 0.12        # the overview: three rows of stills, treasure and points
OVERVIEW_ROW_Y0 = 0.13
OVERVIEW_ROW_DY = 0.20

RUN_FAMILIARIZATION = True
# Familiarization: passes through the three identity routes with their rewards, each walked in full
# with its reward image and amount. The worth-100 route is FIXED at the schedule's actual starting
# winner for every pass, so the participant learns one stable 100 journey and the block ends in
# exactly the state trial 1 begins in. Route order within each pass is a seeded shuffle with no
# immediate repeats.
FAMILIARIZATION_PASSES = 1

RUN_GATE = True
GATE_N_STRUCTURE = 3        # one same-sequence question per route
GATE_N_VALUE = 2
GATE_SELF_PACED = True
GATE_CONFIRM_HOLD = 0.4
GATE_MAX_WAIT = 120.0       # backstop so a lost keypress can never strand a participant
GATE_MAX_ATTEMPTS = 3

# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------

DRY_RUN_SCALE = 0.02
DRY_RUN_AUTO_RESPOND = True

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_FRAME_INTERVALS = True
FRAME_DROP_THRESHOLD = 0.004
