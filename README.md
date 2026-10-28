# ValMap lab sessions (MEG, MRI)

Private. Built by `make_lab_repo.py` in the main task project; do not edit here, rebuild there.
Content as of 2026-10-28: main task commit a5b64e1. Tested with PsychoPy 2023.2.3 (standalone).

## Before every session
    git pull

## PsychoPy's python (written PY below)
- macOS: `/Applications/PsychoPy.app/Contents/MacOS/python` (if it complains about its libraries,
  prefix `PYTHONHOME=/Applications/PsychoPy.app/Contents/Resources`)
- Windows: `"C:\Program Files\PsychoPy\python.exe"`

Run each command from inside the folder named before it.

## Numbers
Subject N uses schedule N in the main task (1 to 100; sub-N is the same person in the online, MEG
and MRI designs) and design N in the localizers (1 to 60). The link from N to the person is in the
lab's subject sheet.

## MRI session (localizer first, then the main task)
1. `Localizer_MRI`: `PY run_localizer.py --design N --participant CODE`
   (after a crash: add `--start-block B`)
2. `main_task`: `PY src/psychopy/run_task.py --steps 3 --session mri --schedule N --participant CODE --modality fmri`
   Opens with a short refresher, the button check (left, middle, right button: b, y or z, g or r)
   and the starting overview, then 6 blocks, each started by the scanner's trigger "t".
   (after a crash: add `--start-run R`; a check without a window: add `--plan-only`)

## MEG session (the lab hardware is set in `meg_lab/settings.py`; first `PY test_meg_io.py` in `Localizer_MEG`)
1. `Localizer_MEG`: `PY run_localizer.py --design N --participant CODE --marker-backend parallel --button-box`
2. `main_task`: `PY src/psychopy/run_task.py --steps 3 --session meg --schedule N --participant CODE --modality meg --marker-backend parallel --button-box`

## Data
Written to `main_task/src/psychopy/data/`, `Localizer_MRI/data/`, `Localizer_MEG/data/`. These
folders are ignored by git: copy them off the computer after every session.

## Quick check after cloning (fast-forward, no participant, a few minutes)
- `main_task`: `PY src/psychopy/run_task.py --steps 3 --session mri --schedule 1 --participant TEST --modality fmri --dry-run --keyboard-backend event`
- `Localizer_MRI`: `PY run_localizer.py --design 1 --participant TEST --dry-run --keyboard-backend event`
