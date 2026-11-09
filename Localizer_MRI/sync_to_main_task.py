"""Copy the online localizer intro into the main task repo (2026-10-13).

The main task's online pre-session (?session=online) appends the 20-trial localizer practice after
its last block. Its page is served from the main repo (and pushed to Pavlovia from there), so the
practice has to live inside it. This folder (Localizer_MRI) stays the SOURCE; the copy in
`../files (5)/localizer_intro/` is generated: edit here, then rerun

    python3 sync_to_main_task.py          # copies, prints what changed
    python3 sync_to_main_task.py --check  # exit 1 if the copy is out of date or not in git

Copied, keeping the layout the module expects (base = 'localizer_intro/'):
  online_practice/localizer_practice.js, online_practice/practice_designs.json,
  stimuli/localizer_manifest.json and stimuli/localizer_manifest_video.json with every file the
  intro shows from them (videos_grey/*.mp4 among them), stimuli/feedback/*.png

Every file is copied at full resolution. ONLINE_PX can scale pictures down (it was 540 for one
pilot on 2026-11-09, against a slow connection); set back to None the same day, since the pilot
looked low resolution and the loading problem was the participant's connection.
"""
import io
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ONLINE_PX = None        # None: full resolution; a number scales larger pictures down to it
DEST = HERE.parent / "files (5)" / "localizer_intro"
README = """# localizer_intro (generated, do not edit)

The 20-trial practice of the MRI/MEG localizer, appended to the end of the online pre-session
(`?session=online`; off for every Prolific link). Source and documentation:
`../../Localizer_MRI/` (online_practice/, stimuli/). Update with
`python3 sync_to_main_task.py` in that folder.
"""


def files_to_copy():
    """Both manifests and what the intro shows from them (2026-10-23): the video version (MRI part
    and overview: grey videos, probe images, grey replacement views) and the picture version (MEG
    part: task pictures and replacement cards), plus the feedback pictures."""
    out = ["online_practice/localizer_practice.js", "online_practice/practice_designs.json",
           "stimuli/localizer_manifest.json", "stimuli/localizer_manifest_video.json"]
    pictures = json.loads((HERE / "stimuli" / "localizer_manifest.json").read_text())["items"]
    videos = json.loads((HERE / "stimuli" / "localizer_manifest_video.json").read_text())["items"]
    for item in pictures.values():
        out += ["stimuli/" + item["task"]] + ["stimuli/" + f for f in item["alternatives"]]
    for item in videos.values():
        out += ["stimuli/" + item["video_grey"], "stimuli/" + item["task"]]
        out += ["stimuli/" + f for f in item["alternatives"]]
    out += [f"stimuli/feedback/{p.name}" for p in sorted((HERE / "stimuli" / "feedback").glob("*.png"))]
    return out


def content(rel):
    """The bytes the copy should hold: a picture larger than ONLINE_PX scaled down, else the file."""
    src = HERE / rel
    if ONLINE_PX and src.suffix.lower() == ".png":
        from PIL import Image
        im = Image.open(src)
        if max(im.size) > ONLINE_PX:
            scale = ONLINE_PX / max(im.size)
            im = im.resize((round(im.size[0] * scale), round(im.size[1] * scale)), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "PNG", optimize=True)
            return buf.getvalue()
    return src.read_bytes()


def main():
    check = "--check" in sys.argv
    stale = []
    for rel in files_to_copy():
        dst = DEST / rel
        data = content(rel)
        if dst.exists() and dst.read_bytes() == data:
            continue
        stale.append(rel)
        if not check:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
    readme = DEST / "README.md"
    if not readme.exists() or readme.read_text() != README:
        stale.append("README.md")
        if not check:
            DEST.mkdir(parents=True, exist_ok=True)
            readme.write_text(README)
    # every file must also be TRACKED by the main repo's git: its .gitignore ignores *.png except
    # where allowed, and an untracked picture is missing on Pavlovia (happened on 2026-10-13)
    rels = ["localizer_intro/" + r for r in files_to_copy()]
    tracked = set(subprocess.run(["git", "ls-files", "localizer_intro"], cwd=DEST.parent,
                                 capture_output=True, text=True).stdout.split())
    untracked = [r for r in rels if r not in tracked]
    if untracked:
        print(f"NOT IN GIT ({len(untracked)}), would be missing on Pavlovia: "
              + ", ".join(untracked[:5]) + (" ..." if len(untracked) > 5 else "")
              + "\n  commit them in the main repo (check its .gitignore)")
    if check:
        print("up to date" if not stale else "OUT OF DATE: " + ", ".join(stale))
        sys.exit(1 if stale or untracked else 0)
    print(f"{len(stale)} file(s) copied to {DEST}" + ("" if not stale else ": " + ", ".join(stale[:6])
                                                       + (" ..." if len(stale) > 6 else "")))


if __name__ == "__main__":
    main()
