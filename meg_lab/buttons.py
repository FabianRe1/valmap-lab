"""
The MEG response box, shared by the main task and the MEG localizer (2026-10-14; first written for
the localizer). Settings in meg_lab/settings.py: 4 buttons, read via COM2 (on Linux /dev/ttyS1) at 19200 baud,
no parity, 8 data bits, 2 stop bits (technician's mail). Every press arrives as ONE byte, the
button's number. A byte b is reported as the key name "btn<b>", so a task's response keys simply
list the button names (settings.POSITION_BUTTONS) next to the keyboard keys and the rest of the
runtime treats both alike. As the colleague's experiment in this lab (test_sweeps-2-main,
hw/check_meg_kbd_test.m, 2026-11-04): the buffer is emptied before each answer window (clear),
every waiting byte is read, and a byte no task asks for (any but the mapped ones) is ignored.
A byte repeating the previous one within settings.BUTTON_REPEAT_GAP is the same press (2026-11-05).

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
                                 stopbits=serial.STOPBITS_TWO, timeout=0,
                                 xonxoff=False, rtscts=False)   # no flow control, as MATLAB's default
        self.last_byte, self.last_time = None, float("-inf")
        self.clear()

    def read(self):
        """Every new press since the last call, as [(key name, read time)]. A byte equal to the
        previous byte within BUTTON_REPEAT_GAP of it is a repeat of the same press and dropped
        (2026-11-05, see settings.BUTTON_REPEAT_GAP)."""
        n = self.ser.in_waiting
        if not n:
            return []
        t = self.now()
        out = []
        for b in self.ser.read(n):
            if not self._repeat(b, t):
                out.append((f"btn{b}", t))
        return out

    def _repeat(self, b, t):
        """True if byte b at time t continues the previous byte; remembers b either way."""
        rep = b == self.last_byte and t - self.last_time < cfg.BUTTON_REPEAT_GAP
        self.last_byte, self.last_time = b, t
        return rep

    def clear(self):
        """Drop every waiting byte (before an answer or continue window), but remember the last
        one, so the rest of a press that was already under way is still recognised as a repeat."""
        n = self.ser.in_waiting
        if n:
            data = self.ser.read(n)
            if data:
                self.last_byte, self.last_time = data[-1], self.now()
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
