"""
Asset resolution through stimuli/manifest.json: clip id -> picture path (a practice clip: video and
frame), reward name -> image.

Strict by design. A missing id or file aborts before the participant sits down, naming the id and
the path; there is never a fallback clip or a silent substitution. Mirrored by
../jspsych/stimuli.js, which resolves against the same manifest.
"""

import json

import config as cfg


class StimulusError(Exception):
    """Missing or inconsistent stimulus. Always fatal."""


def load_manifest(path=None):
    path = path or cfg.MANIFEST_PATH
    if not path.exists():
        raise StimulusError(f"Manifest not found: {path}")
    with open(path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    for section in ("clips", "rewards", "practice_clips", "feedback"):
        if section not in manifest:
            raise StimulusError(f"Manifest {path} is missing the '{section}' section")
    return manifest


def _resolve_clip_entry(name, entry, problems):
    resolved = {}
    # a main-task picture has one `image` (2026-09-29); a practice clip keeps its video and frame
    for key in (("image",) if "image" in entry else ("video", "frame")):
        rel = entry.get(key)
        if not rel:
            problems.append(f"clip '{name}' has no '{key}' entry")
            continue
        path = cfg.REPO_ROOT / rel
        if not path.exists():
            problems.append(f"clip '{name}' {key} file missing: {path}")
        resolved[key] = path
    # the video's frames, played in the MRI (2026-10-23)
    if entry.get("frames"):
        frames = _frame_files(entry["frames"])
        if not frames:
            problems.append(f"clip '{name}' has no frames in {entry['frames']}")
        resolved["frames"] = frames
    return resolved


def _frame_files(rel):
    """The frame images of one video, in order (NN.png in the manifest's folder)."""
    folder = cfg.REPO_ROOT / rel
    return sorted(folder.glob("*.png")) if folder.is_dir() else []


def resolve_reward_frames(manifest, name):
    """The frames of a treasure's video, for the MRI's outcome screen (2026-10-23)."""
    rel = manifest.get("reward_frames", {}).get(name)
    frames = _frame_files(rel) if rel else []
    if not frames:
        raise StimulusError(f"No video frames for treasure '{name}' (manifest 'reward_frames')")
    return frames


def build_stimulus_map(manifest, clip_ids, section="clips"):
    """
    Resolve every requested clip id to absolute paths, all up front, so a broken asset fails before
    the session starts, not on trial 97. Returns {id: {'image': Path}} for the main-task pictures
    ({id: {'video': Path, 'frame': Path}} for a practice clip).
    """
    entries = manifest[section]
    problems = []
    stim_map = {}
    for cid in clip_ids:
        entry = entries.get(cid)
        if entry is None:
            problems.append(f"clip id '{cid}' not in manifest section '{section}'")
            continue
        stim_map[cid] = _resolve_clip_entry(cid, entry, problems)
    if problems:
        raise StimulusError("Stimulus resolution failed:\n"
                            + "\n".join(f"  - {p}" for p in problems))
    return stim_map


def resolve_reward(manifest, name):
    rel = manifest["rewards"].get(name) or manifest.get("practice_rewards", {}).get(name)
    if rel is None:
        raise StimulusError(f"Reward image '{name}' not in manifest "
                            f"(have: {sorted(manifest['rewards'])})")
    path = cfg.REPO_ROOT / rel
    if not path.exists():
        raise StimulusError(f"Reward image file missing: {path}")
    return path


def resolve_feedback(manifest, key):
    rel = manifest["feedback"].get(key)
    if rel is None:
        raise StimulusError(f"Feedback image '{key}' not in manifest")
    path = cfg.REPO_ROOT / rel
    if not path.exists():
        raise StimulusError(f"Feedback image file missing: {path}")
    return path
