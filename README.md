# ValMap lab sessions (MEG, MRI)

Private. Built by `make_lab_repo.py` in the main task project; do not edit here, rebuild there.
Content as of 2026-11-04: main task commit cc18692. Tested with PsychoPy 2023.2.3 (standalone).

## Before every session
    git pull

## PsychoPy's python (written PY below)
- macOS: `/Applications/PsychoPy.app/Contents/MacOS/python` (if it complains about its libraries,
  prefix `PYTHONHOME=/Applications/PsychoPy.app/Contents/Resources`)
- Windows: `"C:\Program Files\PsychoPy\python.exe"`

## Starting a part (the usual way)
    bash run_session.sh mri        (or: bash run_session.sh meg)
The dialog asks for the session, the part (localizer or main task), the participant code, the
subject number N, age, gender, handedness, the starting block and notes, then runs that part with
the command below. One part per start: run it again for the main task after the localizer. Every
start adds a row to `data/participant_details/CODE_details.tsv`. It uses the CBS wrapper
`PSYCHOPY --version 2023.2.3`; elsewhere set PY first (`PY=... bash run_session.sh mri`).
On a Linux PC where that wrapper is missing (or lacks pyserial and pyparallel for the MEG):
`bash setup_env_linux.sh` once builds an environment in ~/.valmap (no root needed) and checks the
MEG ports; run_session.sh then uses it by itself. `bash setup_env_linux.sh --check` repeats the checks.
A check without a participant: `bash run_session.sh --no-dialog --session MRI --part localizer
--code TEST --n 1 --age 30 --gender f --dry-run`.

The commands it runs, to type by hand if needed (each from inside the folder named before it):

## Numbers
Subject N uses schedule N in the main task (1 to 100; sub-N is the same person in the online, MEG
and MRI designs) and design N in the localizers (1 to 60). CODE is the participant database code,
e.g. 27985.cb (letters, digits, dots), the same code as in their online link, so the online, MEG
and MRI files match. N and the code are in the lab's subject sheet.

## Planned durations (upper bounds, from `--plan-only`)
MRI: localizer about 54 min, main task about 71 min (6 runs of about 11 to 13.5 min, 20 s rests).
MEG: localizer about 43 min, main task about 48 min (6 blocks of about 7.5 to 8.5 min, 5 s rests).
Add instructions, breaks between blocks and set-up.

## MRI session (localizer first, then the main task)
1. `Localizer_MRI`: `PY run_localizer.py --design N --participant CODE`
   (after a crash: add `--start-block B`)
2. `main_task`: `PY src/psychopy/run_task.py --steps 3 --session mri --schedule N --participant CODE --modality fmri`
   Opens with a short refresher, the button check and the starting overview, then 6 blocks,
   each started by the scanner's trigger "t". Buttons as in RepChanges (2026-11-04): left answer
   b (blue, right index), middle z (yellow, right middle; y also accepted), right r (left
   index); the localizer uses the same three for left picture, right picture, neither. The box
   must send letters and "t" (check before the session).
   (after a crash: add `--start-run R`; a check without a window: add `--plan-only`)

## MEG session (the lab hardware is set in `meg_lab/settings.py`; first `PY test_meg_io.py` in `Localizer_MEG`)
1. `Localizer_MEG`: `PY run_localizer.py --design N --participant CODE --marker-backend parallel --button-box`
2. `main_task`: `PY src/psychopy/run_task.py --steps 3 --session meg --schedule N --participant CODE --modality meg --marker-backend parallel --button-box`

## Data
Written to `main_task/src/psychopy/data/`, `Localizer_MRI/data/`, `Localizer_MEG/data/`, and the
participant details (age, gender, handedness, notes) to `data/participant_details/`. These
folders are ignored by git: copy them off the computer after every session.

## Quick check after cloning (fast-forward, no participant, a few minutes)
- `main_task`: `PY src/psychopy/run_task.py --steps 3 --session mri --schedule 1 --participant TEST --modality fmri --dry-run --keyboard-backend event`
- `Localizer_MRI`: `PY run_localizer.py --design 1 --participant TEST --dry-run --keyboard-backend event`
