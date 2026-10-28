"""
Marker backends (dummy / parallel / serial / LSL), shared by the main task and the MEG localizer
(2026-10-14; first written for the localizer). Hardware settings come from meg_lab/settings.py.
A task only ever calls Marker.send(code, label), immediately after the win.flip() that puts the
event on screen.

MEG lab rules (technician, 2026-10-14): the stimulus PC writes codes 0..127 to LPT1 (bit 8 is
broken), each code held MARKER_PULSE_DURATION (20 ms) and then set back to 0. The reset runs on a
timer thread, so the drawing loop never sleeps; a new code must wait until the line has been 0 for
MARKER_MIN_GAP (`busy()`), which the runtime respects before every coded flip. Never spin on
busy() without sleeping: a spinning main thread starves the reset thread. Measured in a PsychoPy
flip loop (2026-10-14, macOS): pulses held 20.3 to 25.5 ms, the reset waiting for the flip to
release the interpreter; Python's thread switch interval made no difference.
"""

import threading
import time

from . import settings as cfg


class Marker:
    """Base interface. Subclasses implement _set (and _clear for pulse lines); send() adds the
    pulse timing, range check, timestamping and logging."""

    def __init__(self, logger=None, pulse=None):
        self.logger = logger
        self.log = []
        self.pulse = cfg.MARKER_PULSE_DURATION if pulse is None else pulse
        self.gap = cfg.MARKER_MIN_GAP if pulse is None else pulse * cfg.MARKER_MIN_GAP / cfg.MARKER_PULSE_DURATION
        self.up = False             # a code is on the line
        self.cleared_at = -1.0      # perf_counter time of the last reset to 0
        self.overlaps = 0           # codes sent while the previous pulse was still up (should stay 0)
        self._timer = None

    def busy(self):
        """True while a code is up, and for MARKER_MIN_GAP after its (actual) reset."""
        return self.up or time.perf_counter() < self.cleared_at + self.gap

    def send(self, code, label=""):
        code = int(code)
        if not 0 < code <= cfg.MARKER_MAX_CODE:
            raise ValueError(f"marker code {code} outside 1..{cfg.MARKER_MAX_CODE}")
        if self.busy():
            self.overlaps += 1
            print(f"[marker] code {code} ({label}) sent while the previous pulse was still up")
            self._cancel_and_clear()
        t = time.perf_counter()
        try:
            self._set(code)
            self.up = True
            self._timer = threading.Timer(self.pulse, self._clear_safe)
            self._timer.daemon = True
            self._timer.start()
        except Exception as exc:  # noqa: BLE001 - never let a marker failure kill a session
            print(f"[marker] backend error on code {code} ({label}): {exc}")
        self.log.append((t, code, label))
        if self.logger:
            self.logger(t, code, label)
        return t

    def _clear_safe(self):
        try:
            self._clear()
        except Exception as exc:  # noqa: BLE001
            print(f"[marker] backend error on reset: {exc}")
        self.cleared_at = time.perf_counter()
        self.up = False

    def _cancel_and_clear(self):
        if self._timer is not None:
            self._timer.cancel()
        self._clear_safe()

    def _set(self, code):
        raise NotImplementedError

    def _clear(self):
        pass                        # event backends (serial, LSL) have no line to reset

    def close(self):
        self._cancel_and_clear()


class DummyMarker(Marker):
    """No hardware, but the same pulse timing, so a dry run exercises busy() and the holds.
    Prints codes when verbose."""

    def __init__(self, logger=None, verbose=False, pulse=None):
        super().__init__(logger, pulse)
        self.verbose = verbose

    def _set(self, code):
        if self.verbose:
            print(f"[marker] {code}")


class ParallelMarker(Marker):
    def __init__(self, address=None, logger=None, pulse=None):
        super().__init__(logger, pulse)
        from psychopy import parallel
        self.port = parallel.ParallelPort(address=address or cfg.PARALLEL_PORT_ADDRESS)
        self.port.setData(0)

    def _set(self, code):
        self.port.setData(code & cfg.MARKER_MAX_CODE)

    def _clear(self):
        self.port.setData(0)


class SerialMarker(Marker):
    def __init__(self, port=None, baudrate=None, logger=None, pulse=None):
        super().__init__(logger, pulse)
        import serial
        self.ser = serial.Serial(port or cfg.SERIAL_PORT, baudrate or cfg.SERIAL_BAUDRATE,
                                 timeout=0)

    def _set(self, code):
        self.ser.write(bytes([code & 0xFF]))

    def close(self):
        super().close()
        try:
            self.ser.close()
        except Exception:  # noqa: BLE001
            pass


class LSLMarker(Marker):
    def __init__(self, stream_name="meg_markers", logger=None, pulse=None):
        super().__init__(logger, pulse)
        from pylsl import StreamInfo, StreamOutlet
        info = StreamInfo(stream_name, "Markers", 1, 0, "int32", f"{stream_name}_outlet")
        self.outlet = StreamOutlet(info)

    def _set(self, code):
        self.outlet.push_sample([code])


BACKENDS = {
    "dummy": DummyMarker,
    "parallel": ParallelMarker,
    "serial": SerialMarker,
    "lsl": LSLMarker,
}


def make_marker(backend=None, logger=None, verbose=False, pulse=None, lsl_stream_name=None):
    """
    Build the configured backend. A backend that cannot initialise falls back to dummy with a loud
    warning rather than aborting: losing markers is recoverable, losing the session is not. Both
    tasks check marker.is_fallback and ask the operator before continuing. `pulse` overrides
    MARKER_PULSE_DURATION (the fast dry run scales it with every other duration).
    """
    backend = (backend or cfg.MARKER_BACKEND).lower()
    if backend not in BACKENDS:
        raise ValueError(f"Unknown marker backend '{backend}'. Options: {sorted(BACKENDS)}")

    if backend == "dummy":
        m = DummyMarker(logger=logger, verbose=verbose, pulse=pulse)
        m.is_fallback = False
        return m

    try:
        extra = {"stream_name": lsl_stream_name} if backend == "lsl" and lsl_stream_name else {}
        m = BACKENDS[backend](logger=logger, pulse=pulse, **extra)
        m.is_fallback = False
        return m
    except Exception as exc:  # noqa: BLE001
        print(f"\n*** Marker backend '{backend}' failed to initialise: {exc}")
        print("*** Falling back to the dummy backend -- NO TRIGGERS WILL BE RECORDED.\n")
        m = DummyMarker(logger=logger, verbose=verbose, pulse=pulse)
        m.is_fallback = True
        return m
