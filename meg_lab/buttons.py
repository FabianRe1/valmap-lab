"""
The MEG response box, shared by the main task and the MEG localizer (2026-10-14; first written for
the localizer). Settings in meg_lab/settings.py: 4 buttons, read via COM2 (on Linux /dev/ttyS1) at 19200 baud,
no parity, 8 data bits, 2 stop bits (technician's mail). Every press arrives as ONE byte, the
button's number. A byte b is reported as the key name "btn<b>", so a task's response keys simply
list the button names (settings.FINGER_BUTTON) next to the keyboard keys and the rest of the
runtime treats both alike.

Timestamps are taken when the byte is read (polled once per frame), on the same clock as the
flips (psychopy.core.getTime), so a response time can be late by up to one frame plus the serial
transfer time.
"""

from . import settings as cfg


class ButtonBox:
    def __init__(self, port=None):
        import serial
        from psychopy import core
        self.now = core.getTime
        self.ser = serial.Serial(port or cfg.BUTTON_SERIAL_PORT, cfg.BUTTON_BAUDRATE,
                                 bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_TWO, timeout=0)
        self.clear()

    def read(self):
        """Every byte that arrived since the last call, as [(key name, read time)]."""
        n = self.ser.in_waiting
        if not n:
            return []
        t = self.now()
        return [(f"btn{b}", t) for b in self.ser.read(n)]

    def clear(self):
        self.ser.reset_input_buffer()

    def close(self):
        try:
            self.ser.close()
        except Exception:  # noqa: BLE001
            pass


def make_button_box(port=None):
    """The button box, or None (with a loud warning) if the port cannot be opened; the runtime
    then asks the operator before continuing with the keyboard only."""
    try:
        return ButtonBox(port)
    except Exception as exc:  # noqa: BLE001
        print(f"\n*** Button box on '{port or cfg.BUTTON_SERIAL_PORT}' failed to open: {exc}")
        print("*** Only the keyboard will be read.\n")
        return None
