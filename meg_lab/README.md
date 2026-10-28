# meg_lab: one place for the MEG lab's hardware

Shared by the main task (`../files (5)`) and the MEG localizer (`../Localizer_MEG`), decided
2026-10-14. Change a lab setting here and both tasks follow. Keep this folder next to both
projects on every machine (the MEG stimulus PC included): each imports it from its parent folder.
It is not under version control (the main repo is the Pavlovia remote and does not hold it), so
copy it along whenever the tasks are copied.

| file | what |
|---|---|
| `settings.py` | THE place to change the lab: trigger port (`/dev/parport0`), pulse 20 ms, gap 10 ms, codes 1..127, the photodiode switch (off), the response box (COM2 = `/dev/ttyS1`, 19200 8N2) and which byte each finger's button sends (`FINGER_BUTTON`, placeholders until tested) |
| `codes.py` | codes both tasks share: picture classes 1..12 (aliens 1-3, spaceships 4-6, planets 7-9, treasures 10-12), fixation 20, feedback 60/61, timeout 62, block start 100+b, block end 110+b; `check_codes()` |
| `markers.py` | marker backends (dummy, parallel, serial, LSL): 20 ms pulses reset on a timer thread, `busy()` while the line has not been 0 for the gap |
| `buttons.py` | the serial response box; a byte b arrives as the key name `btn<b>` |

Each task keeps its own event codes (its config) and its own mapping of answers to fingers, built
from `FINGER_BUTTON`.

Lab check before a session: `python ../Localizer_MEG/test_meg_io.py` (sends every code, then
prints the byte of each button press).
