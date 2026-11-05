# MEG setup: every step, first visit and session days

Written 2026-11-05. Paths are relative to the lab repo folder (`valmap-lab`). Commands go into a
terminal on the MEG stimulus PC (Linux). `PY` means the Python the tasks run with: after step 3 it
is `$(cat .valmap_python)` from the lab repo folder, or `PSYCHOPY --version 2023.2.3 python3`
if the lab's PsychoPy wrapper exists.

---

## Part A. First visit, with the technician, no participant (about 1.5 hours)

### A1. Log in and check the display system
Linux draws windows with one of two display systems: **X11** (also called Xorg, the older one)
or **Wayland** (the newer one). You pick it once at the login screen; nothing to install.
PsychoPy's frame timing is reliable only under X11.

    echo $XDG_SESSION_TYPE

- `x11`: fine, go on.
- `wayland`: log out. On the login screen click your name, then the gear icon at the bottom
  right, choose "Ubuntu on Xorg" (or "GNOME on Xorg"), and log in again. Linux remembers the
  choice. If there is no gear icon, ask the technician or IT.

### A2. Get the lab code

    git clone https://github.com/FabianRe1/valmap-lab.git
    cd valmap-lab

(The repo is private: log in to GitHub when asked, or ask Fabian for access. Later visits:
`git pull` inside `valmap-lab`.)

### A3. Python environment and MEG ports

    bash setup_env_linux.sh

Builds the Python environment in `~/.valmap` (a few minutes, needs internet, no admin rights) and
then checks the hardware. Every line must end in "ok". The MEG port lines:

| line | if it fails |
|---|---|
| `/dev/parport0 readable and writable` (triggers) | ask IT to add your user to the group the script names, then log out and in |
| `/dev/ttyS1 readable and writable` (button box) | same |
| `kernel module ppdev loaded` | ask IT: `sudo modprobe ppdev` |
| `kernel module lp not loaded` | ask IT: `sudo rmmod lp` (lp blocks the trigger port) |

Repeat the checks any time with `bash setup_env_linux.sh --check`.

### A4. Triggers and buttons, with the MEG recording
Ask the technician to start an acquisition and show the trigger channel. Then:

    cd Localizer_MEG
    $(cat ../.valmap_python) test_meg_io.py

1. **Triggers.** It sends every code the tasks use, one per second, in increasing order, as 20 ms
   pulses. The trigger channel must show exactly that list (the console prints it) and nothing
   else. Ask the technician whether 20 ms suits them (the other experiment in this lab uses 2 ms).
2. **Buttons.** Then it listens 30 s and prints the byte of every press. Press each button once:

   | button | expected | write down |
   |---|---|---|
   | blue (left) | `btn4` | |
   | middle | `btn2` or `btn3` | |
   | red (right) | `btn1` | |

   Then hold one button for 2 s: the output says whether the box repeats a held button.
   Longer listening: `test_meg_io.py --listen 60`.
3. If a byte differs, tell Fabian: the change goes into `meg_lab/settings.py` in the main project
   and the lab repo is rebuilt. Do not edit the lab repo by hand.

### A5. Both tasks once, for real, with yourself as the participant
With the MEG recording and the participant screen connected:

    cd ~/valmap-lab
    bash run_session.sh meg 2>&1 | tee ~/valmap_TEST_$(date +%F_%H%M).log

In the dialog: session MEG, part Localizer, code `TEST`, N `1`, any age. Run one or two blocks,
then quit with Esc. Start again with part Main task. Check:

- [ ] The task appears full screen on the **participant's** screen. If it opens on the control
      monitor, note which screen it used and tell Fabian (`SCREEN` in the configs, see Part C).
- [ ] The console (and the .log file) shows no warnings about dropped frames or refresh rate.
- [ ] On the trigger channel: block start 101 (102, ...), a picture code 1 to 12 at each picture,
      20 at each fixation, 50 / 51 / 52 when you press left / middle / right.
- [ ] Main task: the button check asks for left, middle, right in that order and accepts the box.
- [ ] A block starts only when you press `t`, and only once the waiting screen is up; a `t`
      pressed earlier is ignored and the block waits.

Afterwards delete the TEST files in `Localizer_MEG/data/`, `main_task/src/psychopy/data/` and
`data/participant_details/`.

---

## Part B. Each session day

1. `cd ~/valmap-lab` and `git pull`.
2. With the MEG recording: `cd Localizer_MEG`, `$(cat ../.valmap_python) test_meg_io.py`, press
   each button once, `cd ..`.
3. **Localizer** (about 43 min, 6 blocks):

       bash run_session.sh meg 2>&1 | tee ~/valmap_CODE_loc.log

   Dialog: MEG, Localizer, the participant code (e.g. `27985.cb`, as in their online link), N from
   the subject sheet, age, gender, handedness. Before each block an operator screen (space), then
   the waiting screen: start the MEG acquisition, then press `t`.
4. **Main task** (about 48 min, 6 blocks of about 8 min with 5 s rests): the same command with
   `_main` in the log name, part Main task. It opens with a short refresher, the button check and
   the starting overview; each block starts with `t` on the waiting screen.
5. **After a crash**: start again with the same details and enter the crashed block as the
   starting block.
6. **At the end** copy off the PC: `data/`, `Localizer_MEG/data/`, `main_task/src/psychopy/data/`
   and the `~/valmap_*.log` files.

---

## Part C. Where to find what in the code (for questions from the technician)

All MEG hardware settings live in ONE file shared by both tasks: `meg_lab/settings.py`.

| Question | Answer | Where |
|---|---|---|
| Which trigger port? | LPT1, `/dev/parport0` (0x378 under Windows) | `meg_lab/settings.py` line 36 |
| Pulse length? | 20 ms, then 0 for at least 10 ms | `meg_lab/settings.py` lines 43-44 (`MARKER_PULSE_DURATION`, `MARKER_MIN_GAP`) |
| Highest code? | 127 (bit 8 of the trigger input is broken) | `meg_lab/settings.py` line 45 |
| How is a pulse sent? | written to the port right after the screen flip, reset by a timer thread | `meg_lab/markers.py`, class `ParallelMarker` (line 98) |
| Photodiode? | off | `meg_lab/settings.py` line 50 (`PHOTODIODE`) |
| Response box port? | COM2 = `/dev/ttyS1`, 19200 baud, 8 data bits, 2 stop bits | `meg_lab/settings.py` lines 58-59 |
| Which button is which answer? | left btn4 (blue), middle btn2/btn3, right btn1 (red) | `meg_lab/settings.py` line 73 (`POSITION_BUTTONS`) |
| Held button repeating? | a repeat of the same byte within 0.15 s is dropped | `meg_lab/settings.py` line 72; reading in `meg_lab/buttons.py` (class `ButtonBox`, line 20) |
| Picture codes (both tasks) | aliens 1-3, spaceships 4-6, planets 7-9, money 10, gold 11, diamonds 12 | `meg_lab/codes.py` (`CLASS_CODES`) |
| Shared codes | fixation 20, feedback 60/61, no answer 62, block start 100 + block, block end 110 + block | `meg_lab/codes.py` (`SHARED_CODES`) |
| Answer codes (both tasks) | 50 left, 51 middle, 52 right | `Localizer_MEG/config.py` (`MARKER_CODES`); `main_task/src/psychopy/config.py` (`MARKER_CODES`) |
| Localizer-only codes | question fixation 30, match question 40, "neither" question 41 | `Localizer_MEG/config.py` (`MARKER_CODES`, line 62) |
| Main-task-only codes | trial start by type: establish 21, value change 22, structure change 23, value control 24, structure control 25, walk 26; rest 30; question by type 40-43 | `main_task/src/psychopy/config.py` (`MARKER_CODES` line 326, `TRIAL_START_CODES`, `PROBE_CODES`) |
| List of every code sent | printed by the test | `Localizer_MEG/test_meg_io.py`; main task: `main_task/src/psychopy/triggers.py` (`all_codes`, line 54) |
| Which screen, full screen? | screen 0, full screen | `Localizer_MEG/config.py` lines 116-117; `main_task/src/psychopy/config.py` lines 420-421 |
| Picture and timing settings | localizer: each video 1 s (`T_STIM`, line 34); main task: MEG uses the `online_meg` profile, 5 s rests | `Localizer_MEG/config.py`; `main_task/src/psychopy/config.py` line 132 (`TIMING_PROFILES`) |
| Start key for a block | `t` | `Localizer_MEG/config.py` line 105; `main_task/src/psychopy/config.py` line 289 |
| How a session is started | the dialog adds `--marker-backend parallel --button-box` for MEG | `start_session.py` lines 45-65 |
| Where the data go | one file per part, every screen with its measured onset, every answer with rt | `Localizer_MEG/data/`, `main_task/src/psychopy/data/`; columns in `main_task/DATA_COLUMNS.txt` |
| Localizer design (order of pictures) | one file per participant | `Localizer_MEG/designs/sub-NNN_localizer_meg.csv` |
| Main task design | one file per participant | `main_task/schedules_meg/sub-NNN_schedule.csv`; columns explained in `SCHEDULE_COLUMNS.md` of the main project (not in the lab repo) |
| Design notes of the MEG localizer | decisions and their reasons | `Localizer_MEG/MEG_DESIGN_NOTES.md` |

Line numbers are as of 2026-11-05; if one has moved, search the file for the name in brackets.
