"""
Marker codes the main task and the MEG localizer SHARE (2026-10-14), so a code means the same in
both recordings. Every code must lie in 1..settings.MARKER_MAX_CODE (127).

* A picture's onset sends its class: the same picture has the same code in the localizer and in
  the task (aliens_1-3 = 1-3, spaceships_1-3 = 4-6, planets_1-3 = 7-9, treasures 10-12).
* Feedback, the answer timeout and the block start and end are shared too.
Each task adds its own codes for its own events (see its config); keep them clear of these.
"""
from . import settings

CLASS_CODES = {
    "aliens_1": 1, "aliens_2": 2, "aliens_3": 3,
    "spaceships_1": 4, "spaceships_2": 5, "spaceships_3": 6,
    "planets_1": 7, "planets_2": 8, "planets_3": 9,
    "money": 10, "gold": 11, "diamonds": 12,
}

SHARED_CODES = {
    "fixation": 20,             # a fixation cross between pictures
    "feedback_correct": 60,
    "feedback_incorrect": 61,
    "timeout": 62,              # no answer in time
    "block_start": 100,         # + block number (1..9), sent at the trigger (t0)
    "block_end": 110,           # + block number (1..9)
}


def check_codes(codes):
    """The codes outside 1..MARKER_MAX_CODE (empty when all are fine)."""
    return sorted(c for c in codes if not 0 < int(c) <= settings.MARKER_MAX_CODE)
