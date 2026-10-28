"""
The practice block: a guided walkthrough of the task's LOGIC, drawn in abstract shapes.

Practice never uses video. It must not teach any clip material, real or extra, so its three
journeys are drawn: one COLOR per journey and one SHAPE per step (`shp01`..`shp12`, see
../psychopy/shapes.py). A journey therefore reads as one colour moving through star, square,
circle, triangle, and a structure change is visible as a journey that changes colour part way
through -- which is exactly the inference the real task asks for.

It is a WALKTHROUGH, not a rehearsal: full walks with their reward outcomes, then one value change
and one structure change, each followed by the walk that shows what the change implies. There are
no probes and no rest windows here; the probe screen is met in the mastery gate, which gives
feedback, and the rest window is a plain fixation cross.

The three reward images are the real ones, so "each journey ends at its own treasure" is learned
once and carries over. The treasure follows the TERMINAL journey, so after the structure change the
rewired journey ends at the other one's treasure -- the same column-tied rule the schedule uses.

Trials are in the same format as schedule.parse_row, so practice runs through the identical trial
engine. Mirrored by ../jspsych/practice.js; tests/check_parity.py compares the two trial for trial.
"""

import config as cfg

# The three practice journeys, one colour each: shp01-04, shp05-08, shp09-12.
def rebuild():
    """Recompute the practice journeys for the currently selected route length. Called at import
       and again by run_task after config.apply_steps() has chosen the 3-step or 4-step variant."""
    n = cfg.N_STEPS
    g = globals()
    g["ROUTE_X"] = list(cfg.PRACTICE_SHAPE_IDS[0:n])
    g["ROUTE_Y"] = list(cfg.PRACTICE_SHAPE_IDS[n:2 * n])
    g["ROUTE_Z"] = list(cfg.PRACTICE_SHAPE_IDS[2 * n:3 * n])
    g["PRACTICE_SHAPE_IDS"] = tuple(g["ROUTE_X"] + g["ROUTE_Y"] + g["ROUTE_Z"])
    # the demo swap: the last step, so the walk afterwards visibly diverges at the end
    g["SWAP_STEP"] = n - 1
    k = g["SWAP_STEP"] - 1        # slice index: the tails from this step onward are exchanged
    g["ROUTE_X_AFTER"] = g["ROUTE_X"][:k] + g["ROUTE_Z"][k:]
    g["ROUTE_Z_AFTER"] = g["ROUTE_Z"][:k] + g["ROUTE_X"][k:]


rebuild()

# One reward image per practice journey, in journey order. The real three, so the rule "a journey
# ends at its own treasure" is taught once. Which image goes with which practice colour is
# arbitrary and unrelated to the real columns, since the practice shapes are not the real clips.
PRACTICE_REWARDS = dict(zip(("X", "Y", "Z"), cfg.REWARD_NAMES))

# The practice structure change: X and Z (both worth 50, never the 100 journey, as in the real
# schedules) exchange their tails at step 3. X keeps its first two shapes and continues into Z's
# last two, so it visibly changes colour mid-journey and now ends at Z's treasure.


def _trial(number, kind, shown, amount=None, reward=None, walk=None, note=None,
           route_map=None):
    """
    One walkthrough trial. No rests and no probes: this block only explains the logic.
    `walk` is the underlying journey when it differs from what is SHOWN, which is the case on
    every short trial: one shape, or one transition, of it, then its treasure.
    `note` names a strings key shown as a self-paced screen straight after the trial, so the
    walkthrough can spell out what a short trial meant, with or without a change.
    `route_map` is an optional second self-paced screen after the note: whole journeys drawn
    start to finish, one row each, `{"caption": key, "rows": [{"label": key, "stimuli": ids}]}`.
    The structure change uses it to put the shown half and the inferred half side by side.
    """
    walk = list(walk if walk is not None else shown)
    return {
        "raw": {"trial": number, "kind": kind, "event": "practice",
                "walk_videos": "|".join(walk), "shown_videos": "|".join(shown),
                "break_20s": "0", "probe": "0",
                "terminal_amount": "" if amount is None else str(amount),
                "terminal_image": reward or ""},
        "trial": number,
        "kind": kind,
        "event_type": "practice",
        "break_20s": False,
        "probe": False,
        "shown_videos": list(shown),
        "hidden_videos": [],
        "terminal_amount": amount,
        "terminal_image": reward,
        "probe_type": "", "probe_subtype": "", "probe_question": "",
        "probe_options": [], "probe_correct_video": "", "probe_correct_index": None,
        "probe_cue": None, "probe_direction": "",
        "note": note,
        "route_map": route_map,
    }


def build_practice_trials():
    """
    The fixed 9-trial practice walkthrough. Trial numbers are practice-local (1..9).

    Storyline: walk the three journeys and see that each ends at its own treasure, one worth 100
    and two worth 50. Then each SHORT format appears twice, first with no change and then with
    one, because a short trial on its own says nothing about a change (decided 2026-09-23):
    one X shape and "100" (X was already the 100 journey: nothing new), then one Y shape and "100"
    (the 100 has moved to Y), confirmed by a full walk of Y. Then two Z shapes in a row that have
    always followed each other (nothing new), then an X shape followed by a Z shape (new: X and Z
    swap tails), confirmed by a full walk of X that now runs into Z's colour and treasure.
    """
    reward_x, reward_y, reward_z = (PRACTICE_REWARDS[k] for k in ("X", "Y", "Z"))
    n = len(ROUTE_Z)
    return [
        # 1-3: the three journeys, their treasures and their amounts. X starts worth 100.
        _trial(1, "EST", ROUTE_X, amount=100, reward=reward_x),
        _trial(2, "T", ROUTE_Y, amount=50, reward=reward_y),
        _trial(3, "T", ROUTE_Z, amount=50, reward=reward_z),

        # 4: SHORT, one shape, NO change: an X shape and X's treasure with "100". X was already
        # worth 100, so nothing is new.
        _trial(4, "TV", [ROUTE_X[1]], amount=100, reward=reward_x, walk=ROUTE_X,
               note="practice_note_same_value"),
        # 5: SHORT, one shape, value CHANGE: a Y shape and Y's treasure with "100". Y was worth
        # 50, so the 100 has moved to Y and X has dropped to 50.
        _trial(5, "V", [ROUTE_Y[0]], amount=100, reward=reward_y, walk=ROUTE_Y,
               note="practice_note_value"),
        # 6: Y walked in full, paying 100. The inference made concrete.
        _trial(6, "T", ROUTE_Y, amount=100, reward=reward_y),

        # 7: SHORT, one transition, NO change: Z's last two shapes, which have always followed
        # each other, and Z's treasure with "50".
        _trial(7, "TS", [ROUTE_Z[n - 2], ROUTE_Z[n - 1]], amount=50, reward=reward_z,
               walk=ROUTE_Z, note="practice_note_same_structure"),
        # 8: SHORT, one transition, structure CHANGE: X's shape at the swap followed by Z's next
        # shape, then the outcome of the journey X now is: Z's treasure, still 50.
        _trial(8, "S", [ROUTE_X[SWAP_STEP - 2], ROUTE_Z[SWAP_STEP - 1]], amount=50,
               reward=reward_z, walk=ROUTE_X_AFTER,
               note="practice_note_structure",
               # then ONE screen with both rewired journeys from start to finish: the half
               # that was shown (X now runs into Z's tail) above the half that was not (Z
               # now runs into X's tail), so the unobserved change is made visible once
               route_map={"caption": "practice_map_structure",
                          "rows": [{"label": "practice_map_shown",
                                    "stimuli": list(ROUTE_X_AFTER)},
                                   {"label": "practice_map_hidden",
                                    "stimuli": list(ROUTE_Z_AFTER)}]}),
        # 9: X walked in full under the rewired graph: it changes colour at the swap and ends at
        # Z's treasure, still worth 50.
        _trial(9, "T", ROUTE_X_AFTER, amount=50, reward=reward_z),
    ]


def validate_practice():
    """Internal consistency of the hand-authored walkthrough; run before every session."""
    problems = []
    trials = build_practice_trials()
    ids = set(PRACTICE_SHAPE_IDS)

    for t in trials:
        for stim in t["shown_videos"]:
            if stim not in ids:
                problems.append(f"practice trial {t['trial']}: unknown shape {stim}")
        # the same formats as the main task: one shape then 100 (V, TV), one transition then 50
        # (S, TS), every trial ending on an outcome
        want = {"V": (1, 100), "TV": (1, 100), "S": (2, 50), "TS": (2, 50)}.get(t["kind"])
        if want and (len(t["shown_videos"]) != want[0] or t["terminal_amount"] != want[1]):
            problems.append(f"practice trial {t['trial']}: {t['kind']} must show {want[0]} "
                            f"shape(s) then {want[1]}")
        if t["terminal_amount"] is None:
            problems.append(f"practice trial {t['trial']}: no outcome")
        if t["probe"] or t["break_20s"]:
            problems.append(f"practice trial {t['trial']}: the walkthrough carries no probes "
                            "or rests")
        if t["terminal_amount"] is not None and not t["terminal_image"]:
            problems.append(f"practice trial {t['trial']}: outcome without a reward image")
        if t["kind"] in ("EST", "T") and len(t["shown_videos"]) != cfg.WALK_LENGTH:
            problems.append(f"practice trial {t['trial']}: full walk must show "
                            f"{cfg.WALK_LENGTH} shapes")

    # each change must carry the note that explains what it means
    for t in trials:
        if t["kind"] in ("V", "S", "TV", "TS") and not t.get("note"):
            problems.append(f"practice trial {t['trial']}: short {t['kind']} trial without an "
                            "explanation screen")
        # the structure change must also carry the map of both rewired journeys, exactly the
        # two post-swap paths the walkthrough goes on to use
        if t["kind"] == "S":
            rows = (t.get("route_map") or {}).get("rows") or []
            if [r["stimuli"] for r in rows] != [list(ROUTE_X_AFTER), list(ROUTE_Z_AFTER)]:
                problems.append(f"practice trial {t['trial']}: structure map must draw the two "
                                "rewired journeys, observed first")
            for r in rows:
                for stim in r["stimuli"]:
                    if stim not in ids:
                        problems.append(f"practice trial {t['trial']}: map shape {stim} unknown")
        elif t.get("route_map"):
            problems.append(f"practice trial {t['trial']}: only the structure change carries a map")

    # the walkthrough must demonstrate both change types, each followed by the walk that shows
    # what it implies
    kinds = [t["kind"] for t in trials]
    # each short format must first be shown WITHOUT a change, so a short trial is never taught
    # as the signal of a change
    for same, change in (("TV", "V"), ("TS", "S")):
        if same not in kinds or change not in kinds or kinds.index(same) > kinds.index(change):
            problems.append(f"practice: a no-change {same} must come before the {change} change")
    for kind, label in (("V", "value change"), ("S", "structure change")):
        if kind not in kinds:
            problems.append(f"practice does not demonstrate a {label}")
        else:
            i = kinds.index(kind)
            if i + 1 >= len(trials) or trials[i + 1]["kind"] in ("V", "S"):
                problems.append(f"practice: the {label} is not followed by a confirming walk")

    # every practice journey must be seen before anything changes
    first_change = next((i for i, k in enumerate(kinds) if k in ("V", "S")), len(trials))
    starts = {t["shown_videos"][0] for t in trials[:first_change]}
    for route, name in ((ROUTE_X, "X"), (ROUTE_Y, "Y"), (ROUTE_Z, "Z")):
        if route[0] not in starts:
            problems.append(f"practice: journey {name} is never walked before the first change")

    # the structure change must not involve the journey currently worth 100 (as in the schedules)
    swap = next((t for t in trials if t["kind"] == "S"), None)
    if swap:
        hundred = None
        for t in trials[:trials.index(swap)]:
            if t["terminal_amount"] == 100:
                walk = t["raw"]["walk_videos"].split("|")
                hundred = walk[0] if walk and walk[0] else hundred
        moved = {ROUTE_X[0], ROUTE_Z[0]}
        if hundred in moved:
            problems.append("practice: the structure change moves the 100 journey")
    return problems


# ---------------------------------------------------------------------------------------------
# The practice on the participant's OWN journeys (2026-10-01), cfg.PRACTICE_STIMULI = "real".
# It runs after familiarization, on the three starting journeys of the schedule's first row:
# W is the journey worth 100 at the start, L1 and L2 the two worth 50 (in column order). The same
# storyline as the shapes, minus the three opening walks (familiarization just showed them):
#   1 TV  W's treasure with 100, no picture      no change      (formats of 2026-10-05)
#   2 V   L1's treasure with 100, no picture     the 100 moves from W to L1
#   3 T   L1 walked in full, 100
#   4 TS  the last transition of L2, no treasure no change
#   5 S   W's head into L2's tail at the swap step, no treasure (W and L2 are the two 50 journeys)
#   (6 T  the rewired W walked in full: dropped 2026-10-05, the reset screen follows the swap's
#         reviews directly)
# Before trial 1 a study screen (build_practice_study, 2026-10-05) shows the three starting
# journeys with their treasures and points, self-paced, to learn them. Right after the swap of
# trial 5 come three untimed questions about what it changed but did not show (swap_questions),
# each with feedback, then one screen per question with the right answer and why, and only then
# the explanation pictures of the swap.
# Every explanation is ONE picture screen: the journeys involved as rows with their treasure and
# points under a short caption, so the text never has to name a journey. The demonstrated changes
# are examples only: the reset screen (build_practice_reset) then shows the starting state again,
# and the gate and the main task start from it. Mirrors ../jspsych/practice.js.
# ---------------------------------------------------------------------------------------------

COLS = ("A", "B", "C")


def _starting_journeys(first_row):
    return {c: {"clips": first_row[f"route_{c}_videos"].split("|"),
                "reward": first_row[f"reward_image_{c}"]} for c in COLS}


def _real_roles(first_row):
    w = first_row["winner_column"]
    l1, l2 = [c for c in COLS if c != w]
    return w, l1, l2


def _map_row(clips, reward, amount, label=None):
    return {"label": label, "stimuli": list(clips), "reward": reward, "amount": amount}


def _swap_cross(j, w, l1, l2, k):
    """
    The swap before and after (2026-10-02): ONE diagram, all three journeys twice, BEFORE on the
    left and AFTER on the right, the pictures in the same places in both. A frame outlines each of
    the two swapping journeys, picture by picture, treasure (column n) included: straight along its
    row BEFORE, crossing into the other row at index k AFTER (row 0's head continues in row 1's
    tail and the other way round), and the arrows follow the frames. Yellow ("seen") is the old 100
    journey, whose new continuation was shown; blue ("inferred") the journey whose new end had to be
    worked out. The third journey has no frame. No points. Mirrors swapCross() in
    ../jspsych/practice.js.
    """
    n = len(j[w]["clips"])

    def cells(row, other):
        return [[other if other is not None and i >= k else row, i] for i in range(n + 1)]

    return {
        "kind": "swap_cross", "caption": "real_swap_explain", "k": k, "cross": [0, 1],
        "rows": [{"stimuli": list(j[c]["clips"]), "reward": j[c]["reward"]} for c in (w, l2, l1)],
        "frames": [
            {"mark": "seen", "before": cells(0, None), "after": cells(0, 1)},
            {"mark": "inferred", "before": cells(1, None), "after": cells(1, 0)},
        ],
    }


# The three swap questions (2026-10-05): which correct answer sits at which key (1-based), so the
# three answers fall on three different keys.
SWAP_QUESTION_POSITIONS = (3, 1, 2)


def _swap_question(number, cue, correct, stale, other, subtype, explain, position, shown,
                   journeys):
    """One untimed question after the practice swap, in the shape of a gate probe."""
    options = [stale, other]
    options.insert(position - 1, correct)
    return {
        "trial": 5, "number": number, "kind": "S", "event_type": "practice", "probe": True,
        "probe_type": "structure_unobserved", "probe_subtype": subtype,
        "probe_question": "practice swap question", "probe_direction": "same_sequence",
        "probe_options": options, "probe_correct_video": correct,
        "probe_correct_index": position, "probe_cue": cue, "probe_stale_video": stale,
        "explain": explain, "auto_correct_in_dry_run": True,
        # drawn under the review (2026-10-05): the two swapped journeys before and after, with
        # their treasures and no points, so the participant can trace the answer
        "journeys": journeys,
        "raw": {"trial": 5, "kind": "S", "event": "practice", "probe": "1", "break_20s": "0",
                "probe_slot": "practice_question", "shown_videos": "|".join(shown),
                "probe_type": "structure_unobserved", "probe_subtype": subtype,
                "probe_options": "|".join(options), "probe_correct_video": correct,
                "probe_question": "practice swap question", "probe_direction": "same_sequence",
                "probe_cue_video": cue},
    }


def swap_journeys(W, L2, rw, rl2, k):
    """The two swapped journeys before and after the swap, treasures, no points (2026-10-05)."""
    return {"before": [_map_row(W, rw, None), _map_row(L2, rl2, None)],
            "after": [_map_row(W[:k] + L2[k:], rl2, None), _map_row(L2[:k] + W[k:], rw, None)]}


def swap_questions(W, L1, L2, k, shown, journeys):
    """
    The three questions after the practice swap (user, 2026-10-05), on what the swap changed but
    did not show. The swap took W's head into L2's tail at index k (shown: W[k-1] then L2[k]), so
    from index k on W and L2 have exchanged their remaining parts. Cues are the FIRST pictures:
      1 W[0]  -> last step: L2's end     (where the shown journey now leads; stale: W's own end)
      2 L2[0] -> step k+1:  W[k]         (the half that was NOT shown; stale: L2[k])
      3 L2[0] -> last step: W's end      (the far end of that hidden half; stale: L2's end)
    In the 3-step task, with the journeys A (= W) and B (= L2) and the shown pair A1 B2: A1 with
    B3, B1 with A2, B1 with A3. The third option is L1's picture at that step.
    """
    last = len(W) - 1
    p1, p2, p3 = SWAP_QUESTION_POSITIONS
    return [
        _swap_question(1, W[0], L2[last], W[last], L1[last], "observed_leg",
                       "real_answer_shown", p1, shown, journeys),
        _swap_question(2, L2[0], W[k], L2[k], L1[k], "counterfactual_leg",
                       "real_answer_hidden_next", p2, shown, journeys),
        _swap_question(3, L2[0], W[last], L2[last], L1[last], "counterfactual_leg",
                       "real_answer_hidden_end", p3, shown, journeys),
    ]


def build_practice_study(first_row):
    """The first practice screen (2026-10-05): the starting journeys with treasures and points,
    self-paced, to learn them before the examples."""
    j = _starting_journeys(first_row)
    return {"caption": "real_study",
            "rows": [_map_row(j[c]["clips"], j[c]["reward"],
                              100 if c == first_row["winner_column"] else 50) for c in COLS]}


def build_real_practice_trials(first_row):
    j = _starting_journeys(first_row)
    w, l1, l2 = _real_roles(first_row)
    W, L1, L2 = j[w]["clips"], j[l1]["clips"], j[l2]["clips"]
    n = len(W)
    k = n - 2                                    # tails from this index on are exchanged
    w_after = W[:k] + L2[k:]

    def with_map(t, key, rows):
        t["note"] = key
        t["route_map"] = {"caption": key, "rows": rows}
        t["note_is_map"] = True
        return t

    return [
        # the short formats of 2026-10-05: a value trial is only a treasure with its points, a
        # pair trial only its two pictures, with no treasure
        with_map(_trial(1, "TV", [], amount=100, reward=j[w]["reward"], walk=W),
                 "real_note_same_value", [_map_row(W, j[w]["reward"], 100)]),
        with_map(_trial(2, "V", [], amount=100, reward=j[l1]["reward"], walk=L1),
                 "real_note_value",
                 [_map_row(L1, j[l1]["reward"], 100, "real_label_value_new"),
                  _map_row(W, j[w]["reward"], 50, "real_label_value_old")]),
        _trial(3, "T", L1, amount=100, reward=j[l1]["reward"]),
        with_map(_trial(4, "TS", [L2[n - 2], L2[n - 1]], walk=L2),
                 "real_note_same_structure", [_map_row(L2, j[l2]["reward"], 50)]),
        # the swap (2026-10-05): three questions on what it changed but did not show, then the
        # before/after diagram (the moved parts framed, 2026-10-02), then one review per
        # question with the two journeys before and after under it. Treasures but NO points on
        # the swap screens (user, 2026-10-02): "50" on both would hint that swaps only ever
        # happen between the 50 journeys. The labelled picture of the two rewired journeys
        # (real_note_structure) was dropped on 2026-10-05.
        {**_trial(5, "S", [W[k - 1], L2[k]], walk=w_after),
         "extra_maps": [_swap_cross(j, w, l1, l2, k)],
         "questions": swap_questions(W, L1, L2, k, [W[k - 1], L2[k]],
                                     swap_journeys(W, L2, j[w]["reward"], j[l2]["reward"], k))},
    ]


def build_practice_reset(first_row):
    """The last practice screen: the examples are undone, the starting journeys are back."""
    j = _starting_journeys(first_row)
    return {"caption": "real_reset",
            "rows": [_map_row(j[c]["clips"], j[c]["reward"],
                              100 if c == first_row["winner_column"] else 50) for c in COLS]}


def validate_real_practice(first_row):
    problems = []
    trials = build_real_practice_trials(first_row)
    j = _starting_journeys(first_row)
    w, l1, l2 = _real_roles(first_row)
    known = {x for c in COLS for x in j[c]["clips"]}
    for t in trials:
        for stim in t["shown_videos"]:
            if stim not in known:
                problems.append(f"practice trial {t['trial']}: {stim} is not a starting picture")
        # since 2026-10-05: the value formats show no picture and the treasure with 100, the
        # pair formats two pictures and no treasure
        want = {"V": (0, 100), "TV": (0, 100), "S": (2, None), "TS": (2, None)}.get(t["kind"])
        if want and (len(t["shown_videos"]) != want[0] or t["terminal_amount"] != want[1]):
            problems.append(f"practice trial {t['trial']}: {t['kind']} must show {want[0]} "
                            f"picture(s) then {want[1] or 'no treasure'}")
        if t["probe"] or t["break_20s"]:
            problems.append(f"practice trial {t['trial']}: no probes or rests")
        if t["kind"] == "S" and not (t.get("questions") and t.get("extra_maps")):
            problems.append(f"practice trial {t['trial']}: the swap needs its questions and diagram")
        if t["kind"] in ("V", "TV", "TS") and not (t.get("note") and t.get("route_map")):
            problems.append(f"practice trial {t['trial']}: short {t['kind']} trial without its "
                            "picture explanation")
        if t["kind"] == "T" and len(t["shown_videos"]) != cfg.WALK_LENGTH:
            problems.append(f"practice trial {t['trial']}: full walk must show {cfg.WALK_LENGTH} pictures")
    by_kind = {t["kind"]: t for t in trials}
    v = by_kind["V"]
    if v["raw"]["walk_videos"] != "|".join(j[l1]["clips"]) or v["terminal_image"] != j[l1]["reward"]:
        problems.append("practice: the value change must show the treasure of a 50 journey")
    walk = by_kind["S"]["raw"]["walk_videos"].split("|")
    steps = [next(j[c]["clips"].index(x) for c in COLS if x in j[c]["clips"]) for x in walk]
    if steps != list(range(len(walk))):
        problems.append("practice: the swapped journey moves a picture to another step")
    if walk[0] != j[w]["clips"][0] or walk[-1] != j[l2]["clips"][-1]:
        problems.append("practice: the swap must take the old 100 journey into the other 50 journey")
    if walk == j[w]["clips"]:
        problems.append("practice: the swap changes nothing")
    # the before/after diagram: the three starting journeys, the swapping two first, the crossing
    # at the swap step, frames exactly on the exchanged ends (seen = L2's, inferred = W's)
    extra = by_kind["S"].get("extra_maps") or []
    if not extra or extra[0].get("kind") != "swap_cross" or len(extra[0]["rows"]) != 3:
        problems.append("practice: the swap has no before/after diagram")
    else:
        ba = extra[0]
        k_swap = len(j[w]["clips"]) - 2
        if [r["stimuli"] for r in ba["rows"]] != [j[c]["clips"] for c in (w, l2, l1)]:
            problems.append("practice: the diagram rows are not the swapping journeys, then the third")
        if ba["k"] != k_swap or ba["cross"] != [0, 1]:
            problems.append("practice: the crossing is not at the swap")
        crossed = ba["rows"][0]["stimuli"][:ba["k"]] + ba["rows"][1]["stimuli"][ba["k"]:]
        if crossed != walk:
            problems.append("practice: the crossing does not draw the swap's walk")
        # the frames: straight along rows 0 and 1 before, crossing at k after, so the yellow one
        # traces the swap's walk
        def seq(cs):
            return [ba["rows"][r]["stimuli"][i] if i < len(ba["rows"][r]["stimuli"])
                    else ba["rows"][r]["reward"] for r, i in cs]
        fr = ba.get("frames") or []
        ok = (len(fr) == 2 and fr[0]["mark"] == "seen" and fr[1]["mark"] == "inferred"
              and seq(fr[0]["before"])[:-1] == j[w]["clips"]
              and seq(fr[1]["before"])[:-1] == j[l2]["clips"]
              and seq(fr[0]["after"])[:-1] == walk
              and seq(fr[0]["after"])[-1] == j[l2]["reward"]
              and seq(fr[1]["after"])[-1] == j[w]["reward"])
        if not ok:
            problems.append("practice: the diagram frames do not trace the journeys before and after")
    # no points on the swap screens: they would hint at the 50-journeys rule
    for m in [by_kind["S"].get("route_map")] + list(by_kind["S"].get("extra_maps") or []):
        if m and any(r.get("amount") is not None for r in m["rows"]):
            problems.append(f"practice: the swap screen {m['caption']} shows points")
    reset = build_practice_reset(first_row)
    if [r["stimuli"] for r in reset["rows"]] != [j[c]["clips"] for c in COLS]:
        problems.append("practice: the reset screen does not show the starting journeys")
    # the study screen: the starting journeys with their points (2026-10-05)
    study = build_practice_study(first_row)
    if ([r["stimuli"] for r in study["rows"]] != [j[c]["clips"] for c in COLS]
            or [r["amount"] for r in study["rows"]]
            != [100 if c == w else 50 for c in COLS]):
        problems.append("practice: the study screen does not show the starting journeys and points")
    problems += _check_swap_questions(by_kind["S"], j, w, l1, l2, walk)
    # the swap is the last example: its reviews lead straight to the reset (2026-10-05)
    if trials[-1]["kind"] != "S":
        problems.append("practice: the swap must be the last example, followed by the reset")
    return problems


def _check_swap_questions(s, j, w, l1, l2, walk):
    """The three swap questions (2026-10-05), checked against the journeys before and after."""
    problems = []
    qs = s.get("questions") or []
    if len(qs) != 3:
        return ["practice: the swap needs exactly three questions"]
    n = len(j[w]["clips"])
    k = n - 2
    before = {c: j[c]["clips"] for c in COLS}
    after = dict(before)
    after[w] = walk
    after[l2] = j[l2]["clips"][:k] + j[w]["clips"][k:]

    def answer(state, cue, options):
        route = next(c for c in COLS if cue in state[c])
        hits = [o for o in options if o in state[route]]
        return hits[0] if len(hits) == 1 else None

    seen = set(s["shown_videos"])
    for q in qs:
        opts = q["probe_options"]
        tag = f"practice question {q['number']}"
        steps = {next(before[c].index(o) for c in COLS if o in before[c]) for o in opts}
        if len(opts) != 3 or len(set(opts)) != 3 or len(steps) != 1:
            problems.append(f"{tag}: needs three pictures of one step")
            continue
        if opts[q["probe_correct_index"] - 1] != q["probe_correct_video"]:
            problems.append(f"{tag}: correct index mismatch")
        if answer(after, q["probe_cue"], opts) != q["probe_correct_video"]:
            problems.append(f"{tag}: the answer does not follow from the swapped journeys")
        if answer(before, q["probe_cue"], opts) != q["probe_stale_video"]:
            problems.append(f"{tag}: the stale option is not the answer before the swap")
        if q["probe_stale_video"] == q["probe_correct_video"]:
            problems.append(f"{tag}: the swap does not change the answer")
        if q["probe_correct_video"] in seen:
            problems.append(f"{tag}: the answer was shown in the swap trial")
        if q["probe_cue"] in opts:
            problems.append(f"{tag}: the cue is among its own options")
        jr = q.get("journeys") or {}
        if ([r["stimuli"] for r in jr.get("before", [])] != [before[w], before[l2]]
                or [r["stimuli"] for r in jr.get("after", [])] != [after[w], after[l2]]
                or [r["reward"] for r in jr.get("before", [])] != [j[w]["reward"], j[l2]["reward"]]
                or [r["reward"] for r in jr.get("after", [])] != [j[l2]["reward"], j[w]["reward"]]
                or any(r.get("amount") is not None for r in jr.get("before", []) + jr.get("after", []))):
            problems.append(f"{tag}: the journeys under the review are not the swap before and after")
    if sorted(q["probe_correct_index"] for q in qs) != [1, 2, 3]:
        problems.append("practice: the three answers must fall on three different keys")
    if [q["probe_subtype"] for q in qs] != ["observed_leg", "counterfactual_leg", "counterfactual_leg"]:
        problems.append("practice: the questions must ask the shown journey first, then the hidden one twice")
    return problems


def practice_trials_for(first_row):
    """The practice for the configured stimuli: shapes (no schedule needed) or the real journeys."""
    return (build_real_practice_trials(first_row) if cfg.PRACTICE_STIMULI == "real"
            else build_practice_trials())


def validate_practice_for(first_row):
    return (validate_real_practice(first_row) if cfg.PRACTICE_STIMULI == "real"
            else validate_practice())
