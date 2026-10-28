"""
THE ONE PLACE for the MEG lab's hardware (2026-10-14). Used by the main task (files (5)) and the
MEG localizer (Localizer_MEG): change a value here and both follow.

What lives here is the LAB, not a task: the trigger port and its limits, the pulse timing, the
response box and which byte each finger's button sends, and whether a photodiode is used. Each
task keeps its own event codes and its own roles for the buttons (which finger answers which
option) in its own config, built from the names below.

MEG lab (technician's mail and a colleague's MATLAB code, 2026-10-14): stimulus PC "faecherfisch",
PsychoPy under Linux. Codes via LPT1 = /dev/parport0, values 0..127 only (bit 8 of the trigger
input is broken), each held 20 ms and then set back to 0. Responses: 4 buttons on COM2 =
/dev/ttyS1, 19200 baud, no parity, 8 data bits, 2 stop bits, one byte per press (the button's
number). Linux setup: pyparallel installed, kernel module ppdev loaded (lp removed), the user
allowed to write /dev/parport0 (usually the lp group).
"""

# ---------------------------------------------------------------------------
# Trigger port
# ---------------------------------------------------------------------------
MARKER_BACKEND = "dummy"            # default backend; the tasks set 'parallel' in the MEG (--marker-backend)
PARALLEL_PORT_ADDRESS = "/dev/parport0"   # Linux device of LPT1 (a Windows PC would use 0x378)
SERIAL_PORT = "COM3"                # only for the 'serial' marker backend (not used in the MEG lab)
SERIAL_BAUDRATE = 115200
MARKER_PULSE_DURATION = 0.020       # a code is held this long, then 0 (technician: 20 ms)
MARKER_MIN_GAP = 0.010              # the line stays 0 at least this long before the next code
MARKER_MAX_CODE = 127               # bit 8 of the MEG trigger input is broken

# ---------------------------------------------------------------------------
# Photodiode: one switch for both tasks (decided 2026-10-14: off until the lab confirms one)
# ---------------------------------------------------------------------------
PHOTODIODE = False                  # True: a white patch in a corner at every coded onset
PHOTODIODE_DURATION = 0.1           # seconds the patch stays white from each coded onset
PHOTODIODE_SIZE = 0.08              # height units, square
PHOTODIODE_POS = (0.85, -0.45)      # bottom-right corner, height units

# ---------------------------------------------------------------------------
# Response box
# ---------------------------------------------------------------------------
BUTTON_SERIAL_PORT = "/dev/ttyS1"   # COM2 under Linux
BUTTON_BAUDRATE = 19200
BUTTONS = ("btn1", "btn2", "btn3", "btn4")   # a byte b arrives as the key name "btn<b>"
# Which button each finger presses. UNCONFIRMED placeholders: run the localizer's test_meg_io.py
# in the lab, press each finger's button and enter the printed names here. Both tasks map their
# answers to these fingers, so a correction here reaches both.
FINGER_BUTTON = {
    "right_index": "btn1",
    "right_middle": "btn2",
    "left_index": "btn3",
    "left_middle": "btn4",
}
