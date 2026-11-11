# MEG localizer for the alien task (2026-10-13)

Adapted from the MRI localizer (`../Localizer_MRI`, its `OLD_LOCALIZER_NOTES.md` decisions 1 to 7)
following the MEG localizers of the two papers in this folder. Same classes, pictures, ordering
logic and probe as MRI; MEG timing and more presentations.

## What the papers did
| | Kern et al. 2024, eLife 93357 | FASTIMAGES MEG (Kern et al. 2026) | MRI localizer |
|---|---|---|---|
| Classes | 10 | 5 | 12 |
| Presentations per class | 50 (2 runs of 250) | 32 (8 blocks, 30 s breaks) | 55 |
| Order | De Bruijn, equal transitions | De Bruijn, no self repeats | Eulerian circuit, no self repeats |
| Picture | 1.0 s, after a spoken name | 0.5 s, after 0.3 s fixation | 0.75 s |
| ITI | 0.75 to 1.25 s fixation, then 1.25 to 1.75 s fixation with the spoken name: 2.0 to 3.0 s between picture offset and the next onset (onset to onset about 3.5 s, task code) | 0.3 s dot plus an ISI drawn normal(2.5, 0.5) truncated to [1, 5] s in the code (paper: truncated exponential); onset to onset about 3.3 s | makeITI, mean about 3.26 s |
| Attention | about 4% audio/visual mismatch | 20% upside down (dropped from training) | about 9% two-picture probe |
| Decoder | L1 logistic regression at about 210 ms; pre-stimulus data as null class, ratio 1:2; exclude peak accuracy below 30% | same, peak 150 ms, C = 9.1 | |

Takeaways used here: the long MRI jitter only serves the HRF; MEG needs a clean epoch of about
-0.2 to 0.8 s around onset and clean pre-stimulus fixation (also the null class). Sequenceness
detection scales with localizer decoding accuracy (FASTIMAGES), so more presentations per class
are worth the time.

## Decisions (user, 2026-10-13)
1. Folder: `Localizer_MEG`, separate scripts adapted from MRI. Stimuli READ from
   `../Localizer_MRI/stimuli` (manifest, task pictures, replacement views, feedback); no copy.
2. ITI: uniform [1.25, 1.75] s (revised after the code review below; first chosen 0.75 to 1.25),
   drawn stratified per block so each block's mean is 1.5 s. Picture onsets are about 2.25 s
   apart (Kern 2024 about 3.5 s, FASTIMAGES about 3.3 s): a compromise that keeps k = 7.
   Probe ITIs from the same pool.
3. Presentations: every ordered pair of different classes 7 times (k = 7): 924 transitions,
   77 or 78 per class.
4. Picture 0.75 s (as MRI and the main task).
5. Attention: the MRI probe unchanged (match 2/3, neither 1/3, task or replacement views, 1.5 s
   answer window, feedback until 2 s after probe onset), 5 per class = 60 probes (6.5%).
6. Blocks: 6 blocks of 155 trials (about 5.2 min each), 6 different block openers, per block every
   class 11 to 15 times (12 to 14 reached), no ordered pair more than 3 times.
7. Block start: operator screen (space), then the experimenter's 't' = block t0, as MRI.
8. No practice (as MRI): instructions plus button check.
9. Markers: class coded, 8 bit, sent right after the flip that shows the event. Picture = class
   1..12 (aliens_1-3 = 1-3, spaceships_1-3 = 4-6, planets_1-3 = 7-9, money 10, gold 11,
   diamonds 12); ITI fixation 20; probe fixation 30; probe 40 match / 41 neither; response
   50 left / 51 neither (middle button) / 52 right (when the key is read; the same button
   has the same code in the main task since 2026-11-05); feedback 60 correct / 61 wrong;
   timeout 62; block start 100 + block (at t0); block end 110 + block (was 200 + block; changed 2026-10-14, see 13). Backends from the main
   task (dummy, parallel 0x378, serial, LSL); if the backend fails the operator must confirm.
10. NO photodiode.
11. Keys as MRI (b / z / r plus j / k / l), changed only in `config.py` once the MEG response
    pad's key names are known. Superseded by 17 and 18.
12. Picture 0.33 screen height (MRI 0.50), as FASTIMAGES, after the code review; probe pictures
    stay 0.30. Breaks unchanged (6 blocks of about 5.2 min), decided after the code review.
13. MEG lab hardware (technician's mail and a colleague's MATLAB code, 2026-10-14): stimulus PC
    "faecherfisch", PsychoPy under Linux (MATLAB/Psychtoolbox and Presentation run under
    Windows there). Markers via LPT1 = `/dev/parport0`, codes 0..127 only (bit 8 broken), each
    held 20 ms and then set to 0. Responses: 4 buttons via COM2 = `/dev/ttyS1`, 19200 baud, no
    parity, 8 data bits, 2 stop bits, one byte per press. Consequences (user, 2026-10-14):
    block end codes 111..116; the 20 ms reset runs on a timer thread so drawing never sleeps;
    no code before the line has been 0 for 10 ms, and after an answer the probe stays up until
    the response pulse is over, so the feedback appears about 40 to 55 ms after the press (it
    still ends 2 s after probe onset); the serial box is read next to the keyboard
    (`--button-box`).
14. One place for the MEG lab, shared with the main task (user, 2026-10-14): the hardware
    settings and the marker and response box code moved to `../meg_lab/` (settings.py,
    codes.py, markers.py, buttons.py). This folder's `triggers.py` and `responses.py` are thin
    wrappers, `config.py` takes the port, pulse, gap, 127 limit, box settings and the picture
    class codes from there, and the keys use `FINGER_BUTTON` (which byte each finger's button
    sends). Same codes and keys as before; the main task's codes are aligned with these
    (picture = class 1..12, fixation 20, feedback 60/61, timeout 62, block 100+b / 110+b).
    The photodiode is one switch in `meg_lab/settings.py` for both tasks, off. Since 2026-11-11 a
    photodiode CHECK can be ticked in the start dialog (`--photodiode`): a white stripe at the top whose
    middle third is black on every coded flip (`../meg_lab/photodiode.py`).
15. Final stimuli on grey (user, 2026-10-26; supersedes the picture part of 12): the MEG
    localizer shows the new STILL of each item (`final_stimuli/favorites`, cut to the 1080 square
    on grey by the MRI localizer's `stimuli/make_video_stimuli.py`: `probe/<id>.png`) and the
    replacement views moved onto the same grey (`alternatives_grey/`), from
    `localizer_manifest_video.json`. Background mid grey (RGB 128, PsychoPy 0), as the MRI
    localizer and the main task. Picture square 0.50 of the screen height, probe squares 0.50 at
    x = 0.40, all as the MRI localizer (an item has one size everywhere). UPDATE 2026-10-26
    afternoon (main-task session, at the user's request, see ../Localizer_MRI/
    NOTE_FROM_MAIN_TASK_SESSION.md): 0.60 for pictures and probes in both localizers and the main
    task, so the objects (about 30 to 75 % of their square) are as large as on the old cards. Durations unchanged (0.75 s, stills only, no videos in the MEG).
    Designs regenerated with the same seeds: identical order, ITIs, probes and versions, only
    the picture paths changed (old ones in `designs_pictures/`). The online intro's MEG part
    follows (grey, the new stills at 0.50; its text no longer says the pictures are smaller).
16. Videos (user, 2026-10-28, on an MEG colleague's advice; the main task's MEG session too,
    its DESIGN_VERIFICATION 67; supersedes the duration of 4 and "stills only" of 15): each
    picture plays its 1 s video in full, the MRI localizer's pre-decoded frames
    (`localizer_manifest_video.json`, `frames`), refresh-locked like the MRI localizer's
    `present_video`, the class code sent right after the flip of frame 0; `T_STIM` 1.0 s. Probes
    keep the stills. The design's `stimulus_file` still names the still (logged as `image`); the
    runtime plays the class's video, and the log's note says how many distinct frames showed.
    The 60 designs are unchanged: the budget check rises from 45 to 46 min (user's choice over
    shorter ITIs or fewer presentations), and every design was accepted at its first draw under
    either budget, so the generator still reproduces them exactly. The online intro's MEG part
    plays the grey videos too and no longer says the pictures do not move (made in
    `../Localizer_MRI/online_practice/`, synced to the main task).
17. Buttons and trigger port as the colleague's experiment that currently runs in this lab
    (2026-11-04; Evie Coxon's `../Orga_MRI_MEG/Other_experiments/test_sweeps-2-main`, details
    in `../meg_lab/README.md`): the box on COM2, 19200 baud, 8N2 (run_sweeps_test.m:78), blue
    button = byte 4 = left, red button = byte 1 = right (run_sweeps_test.m:109-110), triggers on
    LPT 0x378 = `/dev/parport0` (run_sweeps_test.m:81-83), reset to 0. Here: left picture =
    blue, right picture = red, neither = either button between them (bytes 2 and 3; the colleague
    uses no third button). Replaces the finger placeholders of 13 and 14 (`FINGER_BUTTON` is now
    `POSITION_BUTTONS`); the German instructions and button check name the blue, red and middle
    button. Agrees with the technician's spec of 13 except the pulse: the colleague holds 2 ms
    (its older autosave 20 ms), we keep the technician's 20 ms (reasons in `../meg_lab/README.md`).
18. Unified with the MEG main task (2026-11-05): one button, one key and one code mean the same
    position in both MEG tasks, left to right. Blue / J = left (code 50), middle / K = middle,
    here "neither" (51), red / L = right (52). Before: code 51 right, 52 neither, and the keyboard
    J left, K right, L neither plus the MRI's b / z / r. The button check now runs left, middle,
    right, as the main task's. The online practice (`../Localizer_MRI/online_practice`) and the MRI
    localizer keep their own order (K right, L neither; b / z / r), so the MRI stays as RepChanges.
    The shared response box code ignores a held button's repeated bytes (`../meg_lab/buttons.py`).

Kept from MRI without a separate question: 5 s lead-in and lead-out fixation per block,
30 s planned breaks, timeout message, bonus file. German texts: scanner wording removed, plus one
sentence asking to look at the center and blink only when no picture is shown (and a break text
allowing blinks). Easy to change in `strings_de.py`.

## Session length
Plan per design: 930 trials, about 45.8 min with 30 s breaks, about 43.3 min of recording
(budget cap in the generator: 46 min). With stills (until 2026-10-28): 41.9 and 39.4 min, cap 45.

## Files
| File | Role |
|---|---|
| `generate_localizer_designs.py` | designs; `designs/sub-001..060_localizer_meg.csv` (seed 20261014) |
| `verify_localizer_design.py` | independent design checker; mutation tested (7 of 7 caught) |
| `config.py`, `strings_de.py`, `triggers.py`, `run_localizer.py` | presentation, markers, output |
| `responses.py` | the MEG serial response box (bytes read as `btn1`..`btn4`; blue btn4, red btn1) |
| `test_meg_io.py` | lab check: sends every code once a second, then prints the byte of each button press |
| `check_log.py` | output vs design, event order, every marker code; `--timing` for real-time runs |
| `designs/sub-900_localizer_meg.csv` | TEST design (first 30 trials of blocks 1 and 2 of sub-001), not for participants |
| `screens_meg_de.png` | the changed German screens (old black version) |
| `screens_meg_grey.png` | the screens on grey with the final stills (2026-10-26) |
| `designs_pictures/` | the designs before 2026-10-26 (old card pictures), kept for reference |

## Verified (2026-10-13, after the ITI and size change)
- 60 of 60 designs pass `verify_localizer_design.py` (regenerated with ITI [1.25, 1.75]; the
  first set with [0.75, 1.25] and its dry runs were moved out of this folder).
- Checker mutation tested: 8 of 8 broken designs caught (ITI above and below range, swapped
  pictures, dropped trial, wrong probe answer, probe timing, block ITI mean, removed probe).
- Fast-forward dry run of design 1: `check_log.py` OK (930 trials, every marker code correct;
  a wrong marker in a log is caught).
- Real-time timing test, design 900, 60 Hz: `check_log.py --timing` OK; fixation and picture
  durations within 8.3 ms (half a frame) of plan. ITIs are realized to the frame, so at 60 Hz the
  shown ITI is the design value rounded to 16.7 ms.

## Review (2026-10-26, evening)
- Real-time test failed once: the block 2 start code came 30 ms after the block 1 end code,
  because a dry run auto-presses the break, operator and start screens within frames. Fixed:
  the block start code waits for a free line like every other code (in a real session the wait
  is 0), and a real-time dry run presses screens after 0.3 s, as a person. Since then 3 of 3
  real-time tests and the fast dry run pass `check_log.py` at size 0.60.
- At 0.60 the probe pair spans 1.4 screen heights: it fits 16:9 (1.78) but not 4:3 (1.33) or
  5:4 (1.25), where wide objects reach the screen edge. Check the MEG screen's aspect ratio.

## Verified (2026-10-26, final stimuli on grey)
- 60 of 60 regenerated designs identical to the old ones apart from the picture paths (task/
  to probe/, alternatives/ to alternatives_grey/), and all pass `verify_localizer_design.py`.
- Fast dry run of design 1: `check_log.py` OK. Real-time test of design 900: `check_log.py
  --timing` OK. Screen capture: background exactly (128, 128, 128), no visible square edges.
- Online intro: rebuilt, synced to the main task; in the browser the MEG part showed the stills
  (`probe/`) at 50vh on a 128 page; `tests/smoke_jspsych.mjs` (GRID_STEPS=3, SMOKE_SESSION=online)
  passes.

## Verified (2026-10-14, MEG lab hardware rules)
- Marker unit tests: codes 0, 128, 201 refused; a code sent during a pulse is counted as an
  overlap and the line is reset first; the gap counts from the actual reset (10.4 ms).
- Pulse length in a PsychoPy flip loop (macOS, 80 pulses): 20.3 to 25.5 ms. The reset thread
  waits for the flip to release the interpreter; Python's switch interval made no difference.
- Button reader with pyserial's loopback port: bytes 1, 4, 2 read as btn1, btn4, btn2; clear
  empties the buffer; a missing port falls back to the keyboard after the operator confirms.
  Inside the Presenter, the per-frame quit check leaves button bytes for the probe, an unmapped
  button is ignored on a probe, any button continues a text screen.
- Fast dry run of design 1: `check_log.py` OK. Real-time test of design 900 with
  `--button-box` (port missing, fallback confirmed): `check_log.py --timing` OK, no holds, no
  overlaps, no two codes closer than 30 ms, feedback 43 to 53 ms after the press, durations
  within half a frame. A log with an overlap or two codes 17 ms apart fails.
- `test_meg_io.py --marker-backend dummy` sends the 34 codes 1..12, 20, 30, 40, 41, 50..52,
  60..62, 101..106, 111..116.

## Still open
- The buttons (2026-11-04, see 17): blue btn4 and red btn1 are the colleague's; check them with
  `test_meg_io.py`, find which of btn2 and btn3 the middle finger presses, and remove the other
  from `POSITION_BUTTONS` in `../meg_lab/settings.py` (both tasks follow). Ask the technician
  whether 20 ms pulses are still wanted (the colleague now holds 2 ms).
- On faecherfisch: PsychoPy version, pyparallel and pyserial installed, ppdev loaded, write
  access to `/dev/parport0` and `/dev/ttyS1`; the monitor refresh rate; copy
  `Localizer_MEG`, `Localizer_MRI/stimuli` and `meg_lab` there, side by side.
- First real test with the MEG recording: `test_meg_io.py`, then design 900 with
  `--marker-backend parallel --button-box`; check every code arrives once and cleanly.

## Code review of the two papers' localizers (2026-10-13)
Sources (public, read only): Kern 2024 task `github.com/CIMH-Clinical-Psychology/DeSMRRest-clustered-reactivation`
(`Experiment/1_localizer.sce`, `settings_localizer.pcl`, `create_sequences.py`; analysis
`load_funcs.py`, `run_analysis.py`); FASTIMAGES MEG task `github.com/CIMH-Clinical-Psychology/highspeed-task-MEG`
(`3_fast_replay_main.psyexp`, `create_sequences.py`, `sequences/`). The public code does not
match the paper text everywhere; differences are marked.

| | Kern 2024 (code) | FASTIMAGES MEG (code) | Ours |
|---|---|---|---|
| Trial | fixation 0.75 to 1.25 s (code 98), fixation plus spoken name 1.25 to 1.75 s (99), picture 1.0 s (code = item) | dot 0.3 s, picture 0.5 s (code = item), fixation ISI | fixation 1.25 to 1.75 s (20), picture 0.75 s (class 1..12) |
| Picture offset to next onset | 2.0 to 3.0 s | 0.3 s + ISI, normal(2.5, 0.5) in [1, 5] | 1.25 to 1.75 s |
| Order | 3 De Bruijn walks (no self repeats) concatenated per run: 270 trials, 27 per item; the joins leave a few pairs at 2 or 4 instead of 3 (paper: 250, 25 per item) | one De Bruijn walk per block WITH self repeats (at most 2 in a row), 25 per block, 8 blocks: 200, 40 per class for subjects 0 to 29 (files 30 to 39: 160; paper: 160, no repeats) | one Eulerian circuit, no self repeats, every pair exactly 7 times |
| Attention trials | 3 per item per run (11%; paper about 4%): wrong spoken name; press during the picture; codes 100 + item; spread out by a pseudo count weighting | 1 per class per block (20%): picture upside down, codes 100 + class; never adjacent | 5 probes per class (6.5%) AFTER the picture and its own fixation |
| Training data | only codes 1..10 (attention trials dropped); classes equalized by removing trials | upright, no response trials only (paper) | every picture is usable (probes come later) |
| Null class | epochs at code 98 (start of the pre-audio fixation), samples -0.1 to -0.06 s, so as written the last 100 ms of the PREVIOUS picture, ratio 2:1 to class data | not used for the localizer decoder | not decided; the fixation code 20 marks every picture offset |
| Feedback | green or red mark on the picture (attention trials and false alarms only) | correct or error sound on a press or a miss | correct or false picture after every probe |
| Practice | 5 trials with 1 distractor, repeated until error free | practice block repeated until error free | none (decided) |
| Breaks | self paced, every 40 trials in the code (about 2.3 min; paper: every 80) | self paced after each block (25 localizer plus 8 sequence trials) | 30 s between 6 blocks of 155 (about 5.2 min) |
| Picture size | 125 px | 0.33 screen height, grayscale | 0.33 screen height, color cards (MRI 0.50) |
| Markers | 8 bit, item code on the picture, 255 start and end, no photodiode (19 ms delay measured) | 8 bit, 5 ms pulses via `meg_triggers`, sent in Each Frame at frame 0 (before the flip) | 8 bit, 5 ms, sent right after the flip |
