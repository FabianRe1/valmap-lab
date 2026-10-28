"""
Marker backends for the MEG localizer: since 2026-10-14 they live in ../meg_lab/markers.py,
shared with the main task (one place for the MEG lab's hardware: ../meg_lab/settings.py). This
module keeps the localizer's imports working and adds its LSL stream name.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # P7_struct_value, holds meg_lab

from meg_lab import markers as _markers                     # noqa: E402
from meg_lab.markers import (BACKENDS, DummyMarker, LSLMarker, Marker,   # noqa: E402,F401
                             ParallelMarker, SerialMarker)

import config as cfg                                        # noqa: E402


def make_marker(backend=None, logger=None, verbose=False, pulse=None):
    """The configured backend (see meg_lab.markers.make_marker), with this task's LSL name."""
    return _markers.make_marker(backend or cfg.MARKER_BACKEND, logger=logger, verbose=verbose,
                                pulse=pulse, lsl_stream_name=cfg.LSL_STREAM_NAME)
