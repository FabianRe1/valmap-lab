# Handoff: build the MEG localizer from the MRI localizer (written 2026-10-13)

## Goal of the next session
Build a localizer for the MEG session of the alien task, modeled on the MRI localizer in this
folder. The user (Fabian) asked for "something similar for the MEG". Nothing about the MEG
version has been decided yet: ask before changing any design choice.

## Hard rules from the user
- Write files ONLY in `/Users/renzadmin/MaxPlanck_PhD/PhD_Schuck/P7_struct_value/Localizer_MRI`
  unless the user names another folder (ask where the MEG version should live; a subfolder such
  as `Localizer_MRI/meg/` or a sibling `Localizer_MEG/` needs the user's OK). The main task repo
  `P7_struct_value/files (5)` is READ ONLY.
- Working style: one decision at a time, options with a recommended first choice
  (AskUserQuestion); never decide design questions alone. American English in code and docs,
  NO em dashes or en dashes anywhere. Participant texts are German. Show results (screenshots,
  contact sheets via SendUserFile).
- Do not invent stimuli; use the pictures listed in `stimuli/localizer_manifest.json`.

## Read first
1. `OLD_LOCALIZER_NOTES.md` (this folder): the old 2023 RepChanges localizer (source path at the
   top), its weaknesses, and the numbered decision list for the new localizer (items 1 to 7).
2. `generate_localizer_designs.py` docstring: the design (order, ITIs, probes, budget).
3. `run_localizer.py` docstring: presentation flow, output, run commands.
4. Main task MEG conventions (read only): `files (5)/CLAUDE.md`, `files (5)/experiment_spec.md`
   section 4, `files (5)/src/psychopy/triggers.py` (marker backends: dummy, parallel, serial,
   LSL; `Marker.send` right after the flip) and `files (5)/src/psychopy/config.py` lines about
   `PHOTODIODE_*`, `MARKER_BACKEND`, `MARKER_CODES`, `TIMING_PROFILES` (the MEG profile).

## State of the MRI localizer
| File | Status |
|---|---|
| `stimuli/make_localizer_images.py` | done; builds `stimuli/task/` (12 task pictures, copied unchanged), `stimuli/alternatives/` (27 replacement views sliced from the user's sheets in `files (5)/stimuli/alien_images/localizer/`), `stimuli/localizer_manifest.json` |
| `stimuli/feedback/` | correct/false images copied from `files (5)/0_stim_vid/` |
| `generate_localizer_designs.py` | done; `designs/sub-001..060_localizer.csv` (was still generating in the background at handoff, about 30 s each; rerun skips existing files) |
| `verify_localizer_design.py` | independent design checker; mutation tested |
| `config.py`, `strings_de.py`, `run_localizer.py` | done; 6 blocks, operator space then scanner trigger 't' per block, button check, restart with `--start-block`, bonus file |
| `check_log.py` | checks an output TSV against its design (`--timing` for real-time runs) |
| `designs/sub-900_localizer.csv` | TEST design (first 30 trials of blocks 1 and 2 of sub-001) for the real-time timing test; not for participants |

Verified: full fast-forward dry run of design 1 passes `check_log.py` (666 trials, scoring,
monotonic onsets). A real-time windowed timing test on design 900 (60 trials, 60 Hz) passes
`check_log.py --timing`: fixation and picture durations within 8.3 ms (half a frame) of plan.
Note: run the plain-python3 checkers WITHOUT `PYTHONHOME` set (it breaks system python).
Run commands are in the `run_localizer.py` docstring (PsychoPy needs
`PYTHONHOME=/Applications/PsychoPy.app/Contents/Resources` and its own python).

Design in one paragraph: 12 classes (aliens_1-3, spaceships_1-3, planets_1-3, money, gold,
diamonds), task pictures only, 0.75 s each. One Eulerian circuit holding every ordered pair of
different classes 5 times (660 transitions), cut into 6 blocks of 111 trials, Kotzig swaps to
balance classes per block (8 to 11 each). Old `makeITI` unchanged (mean really about 3.26 s;
the user chose to keep it). Probes on 5 trials per class (60, about 9%): two pictures, match 2/3,
neither 1/3, each picture independently task version or replacement. 1.5 s to answer, feedback
until 2 s after onset. About 54 min planned incl. 30 s breaks, cap 60 min.

## Questions to put to the user for the MEG version (none answered yet)
- Same design (6 blocks, 5 circuits, 60 min cap) or different length? MEG sessions in the main
  task use 5 s rests and jittered [0.5, 1.0] s ISIs; MEG decoding usually wants many more, shorter
  trials (a shorter ITI would allow far more presentations in the same time).
- Keep the old `makeITI` (mean 3 s, range [2, 7]) or an MEG-specific ITI?
- Marker codes per class and per event (picture onset, probe, response, feedback) and the
  backend (parallel port address, LSL); photodiode patch on picture onsets as in the main task.
- Block start in MEG: the main task starts every block on 't' in every modality (pressed by a
  person outside the scanner); confirm the same for the localizer.
- Response device in the MEG lab (keys for left / right / neither) and German texts adapted
  (no scanner wording, e.g. "Warten auf den Scanner").
- Whether MRI and MEG should share one code base with a `--modality` switch (likely the cleanest:
  config profiles like the main task's `TIMING_PROFILES`) or separate scripts.

## Suggested skills
- `superpowers:brainstorming` before designing the MEG variant.
- `superpowers:verification-before-completion` before reporting it done (run the design checker,
  a fast-forward dry run, `check_log.py`, and a real-time timing test).
- `superpowers:test-driven-development` if adding marker logic that needs tests.
