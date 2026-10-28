"""
Read the ONE output file per subject (the events table) back into the views the checks want: the
session meta (from the `meta` and `session_end` rows), the blocks, and one dict per trial built
from the screen rows. Mirrors tests/events_view.mjs.
"""
import csv

NA = "n/a"
MAIN_TYPES = ("establish", "value_change", "structure_change", "value_control",
              "structure_control", "tracking", "partial_tracking_value",
              "partial_tracking_structure")
RESTED_KINDS = ("V", "S", "CV", "CS")   # always rested; TV and TS only since 2026-10-09 (see below)
PARTIAL_KINDS = ("TV", "TS")
# browser only (2026-09-24): rows that overlay the screen sequence rather than belong to it (the
# page was hidden, fullscreen was left, the reminder shown after that). They are kept out of the
# blocks and trials so continuity and ordering checks see only the screens.
OVERLAY_EVENTS = ("page_hidden", "fullscreen_exit", "reminder")
KEPT = ["kind", "probe_slot", "winner_column", "untouched_column", "swap_step",
        "counterfactual_route", "shown_videos", "hidden_videos", "route_A_videos",
        "route_B_videos", "route_C_videos", "reactivation_targets", "probe_type",
        "probe_subtype", "probe_options", "probe_correct_video", "probe_cue_video"]


def is_na(v):
    return v is None or v in ("", NA, "NA")


def val(v):
    return None if is_na(v) else v


def split(v):
    v = val(v)
    return v.split("|") if v else []


def load(path):
    """The one file, whether saved tab-separated (our download) or comma-separated (Pavlovia
       stores the same table under a .csv name)."""
    with open(path, newline="", encoding="utf-8") as fh:
        head = fh.readline(); fh.seek(0)
        delim = "\t" if "\t" in head else ","
        return list(csv.DictReader(fh, delimiter=delim))


def unflatten(text):
    parts = str(text).split("|")
    if not all("=" in p for p in parts):
        return str(text)
    return dict(p.split("=", 1) for p in parts)


def meta_from_events(events):
    out = {}
    for e in events:
        if e["event"] not in ("meta", "session_end"):
            continue
        key, _, value = str(e["stimulus"]).partition("=")
        out[key] = unflatten(value) if "=" in value else value
    return out


def blocks_from_events(events):
    """Events grouped by block, in file order, each block opened by its block_start row."""
    blocks = []
    for e in events:
        if e["event"] in ("meta", "session_end") or e["event"] in OVERLAY_EVENTS:
            continue
        if e["event"] == "block_start":
            blocks.append({"label": e.get("trial_type") or "main", "block": e["block"], "events": []})
        if blocks:
            blocks[-1]["events"].append(e)
    for b in blocks:
        b["events"].sort(key=lambda e: float(e["onset"]))
    return blocks


def trials_from_events(events):
    """One dict per trial: identity, the kept schedule columns, measured onsets and durations of
       its screens, the answer, and the list of its event rows."""
    out = {}
    for e in events:
        if is_na(e["trial"]) or e["event"] in ("meta", "session_end") or e["event"] in OVERLAY_EVENTS:
            continue
        phase = "main" if e["trial_type"] in MAIN_TYPES else e["trial_type"]
        key = (phase, e["block"], e["trial"])
        if key not in out:
            t = {"phase": phase, "block": e["block"], "trial": e["trial"], "trial_type": e["trial_type"],
                 "chosen_index": NA, "chosen_video": NA, "correct": NA, "rt": NA, "responded": False,
                 "events": []}
            t.update({c: e.get(c, NA) for c in KEPT})
            out[key] = t
        t = out[key]
        t["events"].append(e)
        ev = e["event"]
        if ev.startswith("clip"):
            t[f"onset_{ev}"] = e["onset"]; t[f"dur_{ev}"] = e["duration"]
        elif ev == "outcome":
            t["onset_outcome"] = e["onset"]; t["dur_outcome"] = e["duration"]; t["outcome"] = e["stimulus"]
        elif ev == "rest_readout":
            t["onset_rest"] = e["onset"]; t["dur_rest"] = e["duration"]
        elif ev == "probe":
            t["onset_probe"] = e["onset"]; t["dur_probe"] = e["duration"]; t["probe_shown"] = e["stimulus"]
        elif ev == "response":
            t["responded"] = True; t["chosen_video"] = e["response"]; t["correct"] = e["correct"]
            t["rt"] = e["rt"]; t["onset_response"] = e["onset"]
            opts = split(t["probe_options"]) or split(e["stimulus"])
            t["chosen_index"] = str(opts.index(e["response"]) + 1) if e["response"] in opts else NA
        if not ev.startswith("fixation") and not is_na(e["onset"]):
            prev = t.get("onset_trial")
            t["onset_trial"] = e["onset"] if prev is None else f"{min(float(prev), float(e['onset'])):.4f}"
    return list(out.values())


def is_probed(t):
    return not is_na(t.get("probe_slot")) or t.get("trial_type") == "gate"


def is_rested(t):
    # changes and controls, plus the follow-up walk right after a change (rested since 2026-09-23).
    # TV and TS are rested since 2026-10-09 and unrested in sessions run on earlier schedules, so
    # for them this returns None: the caller checks they agree within the session.
    if t.get("kind") in PARTIAL_KINDS:
        return None
    return t.get("kind") in RESTED_KINDS or t.get("probe_slot") == "followup"
