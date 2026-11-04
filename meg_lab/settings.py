"""
THE ONE PLACE for the MEG lab's hardware (2026-10-14). Used by the main task (files (5)) and the
MEG localizer (Localizer_MEG): change a value here and both follow.

What lives here is the LAB, not a task: the trigger port and its limits, the pulse timing, the
response box and which byte each button sends, and whether a photodiode is used. Each task keeps
its own event codes and its own roles for the buttons (which button answers which option) in its
own config, built from the names below.

MEG lab (technician's mail and a colleague's MATLAB code, 2026-10-14): stimulus PC "faecherfisch",
PsychoPy under Linux. Codes via LPT1 = /dev/parport0, values 0..127 only (bit 8 of the trigger
input is broken), each held 20 ms and then set back to 0. Responses: 4 buttons on COM2 =
/dev/ttyS1, 19200 baud, no parity, 8 data bits, 2 stop bits, one byte per press (the button's
number). Linux setup: pyparallel installed, kernel module ppdev loaded (lp removed), the user
allowed to write /dev/parport0 (usually the lp group).

2026-11-04, aligned with the experiment that currently runs in this lab (Evie Coxon's SWEEPs,
MATLAB/Psychtoolbox, Orga_MRI_MEG/Other_experiments/test_sweeps-2-main):
  run_sweeps_test.m:78    response box serial('COM2', 19200 baud, 8 data bits, 2 stop bits)
  run_sweeps_test.m:81-83 triggers via io64 on LPT 0x378 (= LPT1 = /dev/parport0 under Linux)
  run_sweeps_test.m:109-110  BLUE button (left) sends byte 4, RED button (right) sends byte 1
  hw/send_trigger_test.m:5-7 code, wait 2 ms, then 0 (its older autosave .asv: 20 ms)
  hw/check_meg_kbd_test.m  flush the box, then read every byte waiting; only 4 and 1 count
It uses only those two buttons. Same port, address, baud rate, framing and reset to 0 as here;
the pulse stays 20 ms (see MARKER_PULSE_DURATION).
"""
import sys

_WINDOWS = sys.platform.startswith("win")   # the same PC also boots Windows (MATLAB, Presentation)

# ---------------------------------------------------------------------------
# Trigger port
# ---------------------------------------------------------------------------
MARKER_BACKEND = "dummy"            # default backend; the tasks set 'parallel' in the MEG (--marker-backend)
# LPT1: /dev/parport0 under Linux; the colleague's Windows code writes the same port at 0x378
PARALLEL_PORT_ADDRESS = 0x0378 if _WINDOWS else "/dev/parport0"
SERIAL_PORT = "COM3"                # only for the 'serial' marker backend (not used in the MEG lab)
SERIAL_BAUDRATE = 115200
# A code is held this long, then 0. Technician: 20 ms. The colleague's current send_trigger_test.m
# holds 2 ms (its older .asv 20 ms); kept at 20 ms on 2026-11-04 because the technician asked for
# it, it is safely seen at any MEG sampling rate, and our reset runs on a timer thread, so the
# length never delays a flip (the colleague's MATLAB wait does). Set 0.002 to match the colleague.
MARKER_PULSE_DURATION = 0.020
MARKER_MIN_GAP = 0.010              # the line stays 0 at least this long before the next code
MARKER_MAX_CODE = 127               # bit 8 of the MEG trigger input is broken

# ---------------------------------------------------------------------------
# Photodiode: one switch for both tasks (decided 2026-10-14: off; the colleague uses none either)
# ---------------------------------------------------------------------------
PHOTODIODE = False                  # True: a white patch in a corner at every coded onset
PHOTODIODE_DURATION = 0.1           # seconds the patch stays white from each coded onset
PHOTODIODE_SIZE = 0.08              # height units, square
PHOTODIODE_POS = (0.85, -0.45)      # bottom-right corner, height units

# ---------------------------------------------------------------------------
# Response box (as the colleague: COM2, 19200 baud, 8 data bits, no parity, 2 stop bits)
# ---------------------------------------------------------------------------
BUTTON_SERIAL_PORT = "COM2" if _WINDOWS else "/dev/ttyS1"   # COM2; /dev/ttyS1 under Linux
BUTTON_BAUDRATE = 19200
BUTTONS = ("btn1", "btn2", "btn3", "btn4")   # a byte b arrives as the key name "btn<b>"
# Which buttons answer the left, middle and right option (2026-11-04, from the colleague's code):
# left = the BLUE button, byte 4, and right = the RED button, byte 1, exactly as the colleague
# (run_sweeps_test.m:109-110, "BLUE (LEFT)" and "RED (RIGHT)" in hw/meg_responsebox_test.m).
# The colleague uses no third button, so middle accepts EITHER remaining button (bytes 2 and 3):
# confirm in the lab with test_meg_io.py and drop the one nobody uses. Both tasks follow.
POSITION_BUTTONS = {
    "left": ("btn4",),              # blue (colleague: codeLeft = 4)
    "middle": ("btn2", "btn3"),     # the buttons between blue and red; bytes not yet seen in the lab
    "right": ("btn1",),             # red (colleague: codeRight = 1)
}
