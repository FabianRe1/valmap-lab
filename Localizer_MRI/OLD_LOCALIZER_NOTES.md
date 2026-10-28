# Notes on the old RepChanges localizer (Leipzig fMRI, 2023)

Source (read only):
`P1_ReplayedReps/Leipzig_finsihed_collection/RepChanges_code_used_for_fMRI_datacollection/repchanges_experiment_leipzig_deutsch/1_localizer_oddball`
plus the shared helpers one level up (`utils_shared.py`, `config_shared.py`, `One_to_rule_em_all.py`).
Written 2026-10-13 as the reference for the new alien localizer in this folder.

## Purpose
Measure the brain pattern evoked by each task stimulus, outside any task structure, to train
decoders for the replay analysis of the main task. Ran in the scanner before the main task on
day 1 (`Session 1`) and again on day 2 (`Session 3`, same design file), plus a short practice
outside the scanner (`intro1`, 20 trials) and an optional single extra block after the main task
(`extra_loc`).

## Files
| File | Role |
|---|---|
| `loc_1_localizer_1.py` | main scanner localizer (`localizer_session_1(dict_ID)`) |
| `loc_1_intro.py` | practice outside the scanner, first 20 rows of `Localizer_design_intro.csv` |
| `loc_1_extra_localizer_1.py` | one extra block (block 1 of subj 0's design), windowed |
| `loc_2_intro.py`, `loc_2_instruction_texts.py` | day 2 warm-up: one main task block, then localizer practice |
| `loc_1_utils.py` | `present_stim`, `present_probe`, `block_completed_text_localizer` |
| `loc_1_instruction_texts.py` | German instruction texts (English kept as comments) |
| `loc_1_config.py` | stimulus dir, mouse visibility, 4 buttons |
| `0_Generate_design/localizer_balanced_sequences/fin_localizer_seq.py` | builds the counterbalanced stimulus orders |
| `0_Generate_design/Create_design_v16_localizer_task_1.py` | turns each order into a per-subject design CSV |

## Design (per subject CSV, `Localizer_design_subj_N.csv`)
- 17 stimuli: 16 task videos (`Aimg1`..`Limg1`, 750 ms, 30 frames) plus `reward`.
- 579 trials in 6 scanner blocks of 96, 96, 96, 97, 97, 97 trials (about 9.2 min each).
- Each stimulus 34 times (the first one 35). Order is FIRST ORDER COUNTERBALANCED: every ordered
  pair of the 17 x 17 = 289 transitions (self repeats included) occurs exactly twice; built by
  chaining Eulerian style walks over all transitions and filtering. Every item at least 4 times
  per block.
- Pre-stimulus ITI: truncated exponential, mean 3 s, range [2, 7] s, resampled in batches of 10
  until the batch mean is at most 3 s (so block length is stable).
- Probes on about 30% of trials (29 per block, shuffled), each after a second ITI from the same
  distribution.
- Probe types (two pictures left/right, answer left, right, or "neither" = down):
  1. exact frame of the item just seen vs a foil (33%)
  2. a DIFFERENT picture of the same item (Midjourney "alternative") vs an alternative foil (33%)
  3. two frames, neither matching (17%), answer down
  4. two alternatives, neither matching (17%), answer down
  So about 37% of probes are "neither". Foils are balanced by a counter and never the current or
  the next item; "neither" foils also exclude the item's sibling (same letter).
- Correct side balanced via a shuffled left/right list.

## Trial and block flow (scanner)
1. Instructions (head still, button mapping), button box check of all 4 buttons.
2. Per block: operator screen (space), then "waiting for scanner" until 't'; block clock reset;
   5 s countdown; 5 s fixation.
3. Trial: fixation for `stimulus_ITI` (minus any video overrun), video 750 ms; if probe:
   fixation `probe_ITI`, probe until key or timeout, feedback image (correct/false) for 2 s minus RT,
   timeout text screen if no answer.
4. Block end: 5 s fixation, feedback "x% done, y% of bonus collected", then the next trigger wait.
   A T1 structural scan was slotted between blocks 3 and 4.
5. End: % correct saved to `percent_bonus_collected_*.txt` (bonus), final fixation until space.
- Buttons (`config_shared.py`): b blue right index = left image, z yellow right middle = right
  image, r green left index = neither, g red left middle unused. Arrow keys also accepted.
- Restart support: `starting_block` and `restarted` from the dialog.

## Output
Per subject: `localizer_block_k_*.csv` after each block, `localizer_complete_*.csv` at the end
(semicolon separated, one row per trial: stimulus, ITIs, video onset vs t0/block/trial clocks,
probe info, response, RT, correctness), a parallel `fixation_localizer_*` file with fixation
onsets, and the bonus txt.

## Observed performance
79 complete files (sessions 1 and 3): mean probe accuracy 0.94, minimum 0.72. Measured block
lengths about 545 to 562 s.

## Weaknesses worth not copying
- Timing by `core.wait` and pre-flip clock reads, not by flip time stamps; the stimulus onset is
  read BEFORE the first flip of the video.
- The probe answer window is `maxWait=1.5` in code while the design column and the instructions
  say 2 s.
- Data only written at block ends (a crash loses the block); no per-row flush.
- Two output files per subject plus per block copies; no schedule columns besides the design.
- Hard coded paths relative to the launcher's working directory; durations hard coded.
- The probe uses `clock` (instructions clock) for its fixation onset, so that onset is on a
  different clock than the stimulus onset.
- Foil choice for the last trial uses a stale `upcoming_stim`.

# Decisions for the new alien localizer (2026-10-13)
1. Stimuli: all 12 main-task items of the 3-step task, the 9 pictures (aliens_1-3,
   spaceships_1-3, planets_1-3) plus the 3 treasures (money, gold, diamonds).
2. Probe: the old probe INCLUDING the "different picture of the same item" types, so every item
   needs one alternative picture. Existing candidates in `files (5)/stimuli/`:
   aliens_2 (task uses alien2b) -> alien2; planets_1 (planet1) -> planet1b;
   planets_2 (planet2) -> planet2b or planet2c; planets_3 (planet4) -> planet4b (a flat scene,
   not a sphere). Missing: aliens_1, aliens_3, spaceships_1-3, money, gold, diamonds (8 items).
3. Replacement pictures (user, 2026-10-13): `files (5)/stimuli/alien_images/localizer/`. The
   three-view sheets are sliced into every view and the probes rotate through them
   (`stimuli/make_localizer_images.py` -> `stimuli/alternatives/`, `stimuli/localizer_manifest.json`).
   Each replacement sits on the same card as its task picture (white square or dark treasure card).
4. Probe mix: every probe picture is independently the task version or a replacement, balanced.
   Match probes (2/3: the class just seen plus a foil) and neither probes (1/3: two foils).
5. Order: every picture equally often, and preceded equally often by every other picture; no self
   repeats. Probes rarer than in the old study, only to keep attention (about 9%: 5 per class).
6. One session, 6 blocks, at most 1 h of scanning plus breaks (instructions and practice before),
   as many presentations as fit. makeITI kept EXACTLY as old (real ITI mean about 3.26 s, because its
   acceptance test is one sided). Probe timing as the old study actually ran: 1.5 s to answer,
   feedback until 2 s after probe onset.
7. Plan: one Eulerian circuit of 5 x 132 ordered pairs, cut into 6 blocks of 110 transitions
   (111 trials), no buffer trials (a block's first trial has no preceding picture). Each pair
   exactly 5 times, each picture preceded 55 times; 666 trials, about 54 min planned. Per block
   each class 8..11 times, a pair at most twice, 6 different block openers.
   `generate_localizer_designs.py` -> `designs/sub-XXX_localizer.csv`; independent check
   `verify_localizer_design.py`.
8. Scanner script (`run_localizer.py`): German only; old box mapping b (right index) = left,
   z (right middle) = right, r (left index) = neither, J/K/L accepted too; in the scanner only a
   button check before block 1 (no practice); restart with `--start-block`; bonus as the old
   study (correct / answered, timeouts not counted) on every block screen and in a bonus file.
9. Online practice (`online_practice/`, part of the ONLINE pre-session, not yet wired into the
   main task's online session): one overview screen of every class with all its views, 20 trials
   with 6 probes (old 30 percent rate), keys J/K/L, repeated once with a second sequence if fewer
   than 5 of 6 are correct (the user's "6 of 8" scaled to 6 probes).
10. The online practice is appended to the end of the main task's online pre-session
    (`?session=online` only, never with a Prolific id), German also inside an English session,
    texts naming both scanning days (MRT und MEG). Saved there: only `localizer_intro_shown` and
    `localizer_intro_completed` (session_end rows). The main repo holds a GENERATED copy in
    `files (5)/localizer_intro/`: edit here, then `python3 sync_to_main_task.py`
    (`--check` tells whether the copy is current). Main repo decision record: DESIGN_VERIFICATION.md
    section 61.
11. The online intro prepares for BOTH scanning-day localizers (user, 2026-10-13: a participant
    may start with MEG or MRI). After the shared intro, overview and keys: an MRI part, then an MEG
    part, 12 trials each (every class once) with 4 probes (3 match, 1 neither), each repeated once
    with a second sequence if fewer than 3 of 4 are right. The parts differ exactly as the two
    localizers do: MRI ITIs from makeITI and pictures at 0.50 screen height; MEG ITIs uniform
    [1.25, 1.75] s (read from `../Localizer_MEG/generate_localizer_designs.py`) and pictures at
    0.33; the MEG page asks to look at the center and blink only when no picture is shown.
    Tested end to end in the browser (wrong MRI answers: 0 of 4 and the repeat; MEG 4 of 4, no repeat).
12. Block start checked against the old scripts (user, 2026-10-13): operator space, then the
    scanner's first trigger, whose key-press time is the block's t0 for every logged onset; later
    pulses are swallowed. The trigger accepts `t` and `T` as the old setup did. After the trigger
    stays a 5 s fixation (no countdown text as in the old version). Unlike the old script, a
    restarted block also waits for space and the trigger.
13. Videos (user, 2026-10-23): the final stimuli in `files (5)/final_stimuli/favorites` (per item a
    1.0 s video, 24 fps, and a still picture, both on mid grey) replace the still pictures. The
    video plays in full (1.0 s) at half the screen height; spaceship2 uses v1. Probes: the new still
    picture center-cropped to a 1080 square (task version) and the OLD replacement views cut out of
    their cards onto the same grey square at the same object size; probe squares as tall as the
    video (0.50). Grey (RGB 128, PsychoPy 0) is the new background. Built by
    `stimuli/make_video_stimuli.py` into videos/, video_frames/, videos_grey/, probe/,
    alternatives_grey/ and `localizer_manifest_video.json`; the picture version (task/,
    alternatives/, localizer_manifest.json) is untouched because the MEG localizer reads it.
    The scanner shows each video as its 24 pre-decoded frames, refresh-locked (a reused MovieStim
    showed the previous run's last frame at onset and frame 0 only after about 85 ms); frame
    backgrounds made exactly 128 (the encoded videos are 128 to 131, which showed as a lighter
    square). Designs regenerated with the same seed (identical order, ITIs and probes; old ones in
    designs_pictures/), about 56 min planned. Real-time test: 60 videos 0.992 to 1.006 s, all 24
    frames shown. Online intro: MRI part plays videos_grey/ (color tagged, decodes to 128 in the
    browser) on a grey page; the MEG part mirrors the MEG localizer (pictures, 0.75 s, black).
14. MEG localizer on grey (user, 2026-10-26): the MEG localizer now reads this folder's
    `localizer_manifest_video.json` too (the stills in probe/ and alternatives_grey/), grey
    background, squares 0.50 as here; so the online intro's MEG part shows the stills at 0.50 on
    grey (make_practice_designs.py, localizer_practice.js; its text drops "die Bilder sind etwas
    kleiner"). The picture version (task/, alternatives/, localizer_manifest.json) is no longer
    read by either localizer; kept for reference. Details: ../Localizer_MEG/MEG_DESIGN_NOTES.md 15.
