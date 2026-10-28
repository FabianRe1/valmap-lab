"""
Markers for the main task. The backends (dummy / parallel / serial / LSL, 20 ms pulses reset on a
timer thread, codes 1..127) live in ../../../meg_lab/markers.py since 2026-10-14, shared with the
MEG localizer; the lab's hardware settings are in meg_lab/settings.py (config.py imports them).

The experiment only ever calls Marker.send(code, label), immediately after the win.flip() that
puts the event on screen. This module adds the task's code lookups (config.MARKER_CODES,
TRIAL_START_CODES, PROBE_CODES and the shared picture classes), so every code is chosen here.
"""

import config as cfg                      # puts meg_lab on the path

from meg_lab import markers as _markers
from meg_lab.codes import check_codes
from meg_lab.markers import (BACKENDS, DummyMarker, LSLMarker, Marker,   # noqa: F401
                             ParallelMarker, SerialMarker)


def make_marker(backend=None, logger=None, verbose=False, pulse=None):
    """The configured backend (meg_lab.markers.make_marker) with this task's LSL stream name.
    `pulse` overrides the pulse length (a dry run scales it with every other duration)."""
    return _markers.make_marker(backend or cfg.MARKER_BACKEND, logger=logger, verbose=verbose,
                                pulse=pulse, lsl_stream_name=cfg.LSL_STREAM_NAME)


def trial_marker_code(kind):
    """The code of the trial-opening fixation: the trial type (or practice / familiarization)."""
    return cfg.TRIAL_START_CODES[kind]


def picture_code(stim_id):
    """A picture's onset: its class, as in the localizer; a practice shape has one shared code."""
    return cfg.CLASS_CODES.get(stim_id, cfg.MARKER_CODES["practice_shape"])


def outcome_code(reward_name):
    """The outcome screen: its treasure's class (money 10, gold 11, diamonds 12)."""
    return cfg.CLASS_CODES[reward_name]


def probe_code(probe_type):
    """The question's onset: its type."""
    if probe_type in cfg.PROBE_CODES:
        return cfg.PROBE_CODES[probe_type]
    return cfg.PROBE_CODES["value_unobserved" if str(probe_type).startswith("value")
                           else "structure_unobserved"]


def response_code(option_index):
    """The answer (0-based option index, left to right)."""
    return cfg.MARKER_CODES[f"response_{option_index + 1}"]


def all_codes(n_blocks=6):
    """Every code this task can send, for the range check at startup and the lab check."""
    codes = set(cfg.CLASS_CODES.values()) | set(cfg.TRIAL_START_CODES.values())
    codes |= set(cfg.PROBE_CODES.values())
    codes |= {v for k, v in cfg.MARKER_CODES.items() if not k.startswith("block_")}
    codes |= {cfg.MARKER_CODES[k] + b for k in ("block_start", "block_end")
              for b in range(1, n_blocks + 1)}
    return sorted(codes)


def bad_codes(n_blocks=6):
    """The codes outside 1..MARKER_MAX_CODE (empty when every code can reach the MEG)."""
    return check_codes(all_codes(n_blocks))
