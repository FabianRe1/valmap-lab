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
# Photodiode check
# ---------------------------------------------------------------------------
# (2026-11-11, user; replaces the corner patch of 2026-10-14): off by default,
# switched on per session in the start dialog or with --photodiode (both MEG tasks). A white stripe
# across the top of the screen whose middle third toggles between white and black on every flip that
# sends a code and stays so until the next; see photodiode.py.
PHOTODIODE = False                  # the default when neither the dialog nor --photodiode turns it on
PHOTODIODE_STRIPE_HEIGHT = 0.02     # of the screen height (about 22 px at 1080 lines), full width

# ---------------------------------------------------------------------------
# Response box (as the colleague: COM2, 19200 baud, 8 data bits, no parity, 2 stop bits)
# ---------------------------------------------------------------------------
BUTTON_SERIAL_PORT = "COM2" if _WINDOWS else "/dev/ttyS1"   # COM2; /dev/ttyS1 under Linux
BUTTON_BAUDRATE = 19200
BUTTONS = ("btn1", "btn2", "btn3", "btn4")   # a byte b arrives as the key name "btn<b>"
# Which buttons answer the left, middle and right option (2026-11-11, user): the three buttons that
# send bytes 1, 2 and 3, left to right. Main task: 1 = left, 2 = middle, 3 = right option.
# Localizer: 1 = left picture, 2 = neither picture, 3 = right picture. Both tasks follow.
# (2026-11-04 to 2026-11-10, after the colleague's run_sweeps_test.m:109-110: left = blue = byte 4,
# right = red = byte 1, middle = byte 2 or 3.)
# A held or bouncing button (2026-11-05): the colleague's instruction code flushes the port after
# each press "so held button doesn't auto-repeat" (instr/showInstructionBlockNav.m:72-75), so a box
# may send the same byte more than once per press. A byte equal to the previous one that comes
# less than this long after it is dropped (chained, so a steady repeat stays dropped until the
# button is let go). No person presses one button twice within 0.15 s. test_meg_io.py shows
# whether this box repeats at all (hold a button there).
BUTTON_REPEAT_GAP = 0.15
POSITION_BUTTONS = {
    "left": ("btn1",),              # button 1: left option / left picture
    "middle": ("btn2",),            # button 2: middle option / "neither" in the localizer
    "right": ("btn3",),             # button 3: right option / right picture
}
