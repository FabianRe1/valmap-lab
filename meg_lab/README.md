# meg_lab: one place for the MEG lab's hardware

Shared by the main task (`../files (5)`) and the MEG localizer (`../Localizer_MEG`), decided
2026-10-14. Change a lab setting here and both tasks follow. Keep this folder next to both
projects on every machine (the MEG stimulus PC included): each imports it from its parent folder.
It is not under version control (the main repo is the Pavlovia remote and does not hold it), so
copy it along whenever the tasks are copied.

| file | what |
|---|---|
| `settings.py` | THE place to change the lab: trigger port (`/dev/parport0`, 0x378 under Windows), pulse 20 ms, gap 10 ms, codes 1..127, the photodiode switch (off), the response box (COM2 = `/dev/ttyS1`, 19200 8N2) and which buttons answer left, middle, right (`POSITION_BUTTONS`) |
| `codes.py` | codes both tasks share: picture classes 1..12 (aliens 1-3, spaceships 4-6, planets 7-9, treasures 10-12), fixation 20, feedback 60/61, timeout 62, block start 100+b, block end 110+b; `check_codes()` |
| `markers.py` | marker backends (dummy, parallel, serial, LSL): 20 ms pulses reset on a timer thread, `busy()` while the line has not been 0 for the gap |
| `buttons.py` | the serial response box; a byte b arrives as the key name `btn<b>` |

Each task keeps its own event codes (its config) and its own mapping of answers to positions, built
from `POSITION_BUTTONS`. Since 2026-11-05 the two MEG tasks agree on every button: blue / J = left
(answer code 50), middle / K = middle (51; "neither" in the localizer), red / L = right (52).

## Aligned with the colleague's MEG experiment (2026-11-04)
Source: Evie Coxon's SWEEPs (MATLAB/Psychtoolbox), which currently runs in this lab,
`../Orga_MRI_MEG/Other_experiments/test_sweeps-2-main`.

| | colleague (file:line) | here |
|---|---|---|
| response box | `serial('COM2','BaudRate',19200,'Stopbits',2,'Databits',8)`, run_sweeps_test.m:78 | same port (`/dev/ttyS1` under Linux), 19200 8N2, no flow control |
| button bytes | blue = left = 4, red = right = 1, run_sweeps_test.m:109-110, hw/meg_responsebox_test.m:25 | left option btn4, right option btn1; middle btn2 or btn3 (the colleague uses no third button) |
| reading | flush, then read every waiting byte, hw/check_meg_kbd_test.m:16-43; flush again after a press "so held button doesn't auto-repeat", instr/showInstructionBlockNav.m:72-75 | the box is emptied before each answer or continue window and read only there; a byte repeating the previous one within 0.15 s is dropped (`BUTTON_REPEAT_GAP`) |
| trigger port | io64 on 0x378, run_sweeps_test.m:81-83 | LPT1: `/dev/parport0` (Linux), 0x378 if run under Windows |
| pulse | code, 2 ms, then 0, hw/send_trigger_test.m:5-7 (its older .asv: 20 ms) | code, 20 ms, then 0 (technician), see below |
| codes | 5..79 plus a 127 test code, config/sweeps_defaults_test.m | 1..127 |
| keyboard | arrows and space, Esc aborts, run_sweeps_test.m:104-108 | J, K, L and space, Esc quits |
| photodiode, eye tracker | none; EyeLink off (run_sweeps_test.m:74) | none |

Differences, kept on purpose. Pulse: the technician asked for 20 ms and the colleague's own
autosave holds 20 ms; 20 ms is seen at any MEG sampling rate, and our reset runs on a timer
thread, so its length never delays a flip (the colleague's MATLAB wait would, which may be why
it is 2 ms there). Set `MARKER_PULSE_DURATION = 0.002` to match the colleague exactly. Middle
button: bytes 2 and 3 both count until `test_meg_io.py` shows which one participants use.

Lab check before a session: `python ../Localizer_MEG/test_meg_io.py` (sends every code, then
prints the byte of each button press and the answer it maps to).
