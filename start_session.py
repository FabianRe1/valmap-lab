"""
start_session.py: the start dialog of the lab sessions (2026-11-02, after the RepChanges
One_to_rule_em_all.py). Lives at the root of the lab repository (copied there by make_lab_repo.py
from lab_launcher/), started by run_session.sh through PsychoPy's python.

One part per start: the dialog asks for the session (MRI or MEG), the part (localizer or main
task), the participant database code, the subject number N, age, gender, handedness, the starting
block and notes, then runs that part with the matching command. Every start appends one row to
data/participant_details/n-<NN>_sub-<code>_details.tsv (never overwritten, ignored by git); the task data
files themselves are unchanged.

  PY start_session.py [mri|meg]                 # the dialog, session preselected
  PY start_session.py --no-dialog --session mri --part localizer --code 27985.cb --n 12 ...
  add --dry-run for a fast-forward check without a participant (details marked dry_run)
"""
import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DETAILS_DIR = ROOT / "data" / "participant_details"
CODE = re.compile(r"[A-Za-z0-9.]+")
SESSIONS = ("MRI", "MEG")
PARTS = ("localizer", "main task")
HANDEDNESS = ("right", "left", "both")
DETAIL_COLUMNS = ("started", "code", "subject_n", "session", "part", "start_block", "age",
                  "gender", "handedness", "notes", "dry_run", "command", "exit_code")


def part_paths(session, part, n):
    """(folder to run in, script, the design or schedule file the part reads)."""
    if part == "localizer":
        folder = ROOT / ("Localizer_MRI" if session == "MRI" else "Localizer_MEG")
        design = folder / "designs" / (f"sub-{n:03d}_localizer.csv" if session == "MRI"
                                       else f"sub-{n:03d}_localizer_meg.csv")
        return folder, "run_localizer.py", design
    folder = ROOT / "main_task"
    schedules = "schedules_mri" if session == "MRI" else "schedules_meg"
    return folder, "src/psychopy/run_task.py", folder / schedules / f"sub-{n:03d}_schedule.csv"


def build_command(d, dry_run=False):
    """The command line of one part, from the checked details."""
    folder, script, _ = part_paths(d["session"], d["part"], d["subject_n"])
    meg = d["session"] == "MEG"
    if d["part"] == "localizer":
        args = ["--design", str(d["subject_n"]), "--participant", d["code"],
                "--start-block", str(d["start_block"])]
        if meg:
            args += ["--marker-backend", "parallel", "--button-box"]
    else:
        args = ["--steps", "3", "--session", "meg" if meg else "mri",
                "--schedule", str(d["subject_n"]), "--participant", d["code"],
                "--modality", "meg" if meg else "fmri", "--start-run", str(d["start_block"])]
        if meg:
            args += ["--marker-backend", "parallel", "--button-box"]
    if dry_run:
        args = [a for a in args if a not in ("--button-box",)]
        if "--marker-backend" in args:
            i = args.index("--marker-backend")
            args[i + 1] = "dummy"
        args += ["--dry-run", "--keyboard-backend", "event"]
    return folder, [sys.executable, script, *args]


def check_details(raw):
    """Clean the entered values; returns (details, list of problems)."""
    problems = []
    d = {k: str(v).strip() for k, v in raw.items()}
    if d["session"] not in SESSIONS:
        problems.append("session must be MRI or MEG")
    if d["part"] not in PARTS:
        problems.append("part must be localizer or main task")
    if not CODE.fullmatch(d["code"]):
        problems.append("participant code: only letters, digits and dots, e.g. 27985.cb")
    for key, label, lo, hi in (("subject_n", "subject number N", 1, 999),
                               ("age", "age", 18, 99), ("start_block", "starting block", 1, 6)):
        try:
            d[key] = int(d[key])
            if not lo <= d[key] <= hi:
                raise ValueError
        except ValueError:
            problems.append(f"{label} must be a whole number from {lo} to {hi}")
    if not d["gender"]:
        problems.append("gender is empty")
    if d["handedness"] not in HANDEDNESS:
        problems.append("handedness must be right, left or both")
    if not problems:
        _, _, design = part_paths(d["session"], d["part"], d["subject_n"])
        if not design.is_file():
            problems.append(f"no design for subject {d['subject_n']}: {design.relative_to(ROOT)} "
                            "is missing")
    d["notes"] = " ".join(d["notes"].split())       # one line, no tabs, for the details file
    return d, problems


def write_details(d, command, dry_run, exit_code="started"):
    """Append one row to the subject's details file (header on first use); returns its path."""
    DETAILS_DIR.mkdir(parents=True, exist_ok=True)
    path = DETAILS_DIR / f"n-{int(d['subject_n']):02d}_sub-{d['code']}_details.tsv"   # n- first since 2026-11-09
    row = {**d, "started": datetime.datetime.now().isoformat(timespec="seconds"),
           "dry_run": int(dry_run), "command": " ".join(command[1:]), "exit_code": exit_code}
    new = not path.exists()
    with open(path, "a", encoding="utf-8") as fh:
        if new:
            fh.write("\t".join(DETAIL_COLUMNS) + "\n")
        fh.write("\t".join(str(row[c]) for c in DETAIL_COLUMNS) + "\n")
        fh.flush()
    return path


def ask(initial):
    """The PsychoPy dialog, shown again with the entered values until they pass the checks."""
    from psychopy import gui
    values = dict(initial)
    while True:
        dlg = gui.Dlg(title="ValMap lab session")
        dlg.addText("One part per start: run the script again for the next part.")
        dlg.addField("Session", choices=list(SESSIONS) if values["session"] != "MEG"
                     else ["MEG", "MRI"])
        dlg.addField("Part", choices=list(PARTS) if values["part"] != "main task"
                     else ["main task", "localizer"])
        dlg.addField("Participant code (database, e.g. 27985.cb)", values["code"])
        dlg.addField("Subject number N (same as online)", values["subject_n"])
        dlg.addField("Age", values["age"])
        dlg.addField("Gender (m / f / specify freely)", values["gender"])
        dlg.addField("Handedness", choices=[values["handedness"]]
                     + [h for h in HANDEDNESS if h != values["handedness"]])
        dlg.addField("Starting block (default 1; after a crash the block to restart)",
                     values["start_block"])
        dlg.addField("Notes", values["notes"])
        data = dlg.show()
        if not dlg.OK:
            return None
        # PsychoPy 2023 returns a list, newer versions a dict keyed by the field labels
        # (2026-11-09: with 2026.2.4 every entry failed the checks); both keep the field order
        if isinstance(data, dict):
            data = list(data.values())
        values = dict(zip(("session", "part", "code", "subject_n", "age", "gender", "handedness",
                           "start_block", "notes"), (str(x) for x in data)))
        d, problems = check_details(values)
        if not problems:
            return d
        err = gui.Dlg(title="Please correct")
        for p in problems:
            err.addText(p)
        err.show()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("preselect", nargs="?", choices=("mri", "meg"), help="session shown first")
    ap.add_argument("--no-dialog", action="store_true", help="take the details from the options")
    ap.add_argument("--session", choices=SESSIONS)
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--code", default="")
    ap.add_argument("--n", default="")
    ap.add_argument("--age", default="")
    ap.add_argument("--gender", default="")
    ap.add_argument("--handedness", default="right")
    ap.add_argument("--start-block", default="1")
    ap.add_argument("--notes", default="")
    ap.add_argument("--dry-run", action="store_true",
                    help="fast-forward check: simulated answers, dummy markers, no button box")
    a = ap.parse_args()
    initial = {"session": a.session or (a.preselect or "mri").upper(), "part": a.part or "localizer",
               "code": a.code, "subject_n": a.n, "age": a.age, "gender": a.gender,
               "handedness": a.handedness, "start_block": a.start_block, "notes": a.notes}
    if a.no_dialog:
        d, problems = check_details(initial)
        if problems:
            print("Cannot start:\n  " + "\n  ".join(problems))
            return 2
    else:
        d = ask(initial)
        if d is None:
            print("Cancelled, nothing was started.")
            return 1

    folder, command = build_command(d, dry_run=a.dry_run)
    path = write_details(d, command, a.dry_run)
    print(f"{d['session']} {d['part']}, subject {d['subject_n']}, code {d['code']}, from block "
          f"{d['start_block']}\n  details: {path.relative_to(ROOT)}\n  running in {folder.name}: "
          + " ".join(command[1:]))
    exit_code = subprocess.run(command, cwd=folder).returncode
    write_details(d, command, a.dry_run, exit_code=f"finished {exit_code}")
    print(f"{d['part']} ended (exit code {exit_code}). Copy the data folders off this computer "
          "after the session.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
