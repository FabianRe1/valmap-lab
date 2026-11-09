# The output file: one file per subject, every column and row kind

Decided 2026-09-10: a session writes exactly ONE file, and both arms write the same one.

| arm | file | where |
|---|---|---|
| PsychoPy | `n-<NN>_sub-<code>_task-gridvalstruct_<stamp>.tsv` (N the subject number = schedule; the `n-` prefix since 2026-11-09, as the localizers' files; `_dryrun` before the extension on a dry run) | `src/psychopy/data/` |
| browser | `sub-<code>_task-gridvalstruct_<stamp>.tsv` | a download at the end (or posted with `?sink=post|jatos`); a checkpoint of the same rows sits in `localStorage` after every trial |
| browser on Pavlovia (`?sink=pavlovia`) | `ValMap_<id>_score<pct>pct_SESSION_<date>.csv` (the score since 2026-10-02, for the bonus) | uploaded once, at the end (Pavlovia with credits accepts one upload per session); a tab closed mid-session sends `ValMap_<id>_SESSION_<start>_incomplete.csv` instead, a compact record (meta rows, block starts and ends, every answer; base columns plus `kind`, `probe_slot`), best effort |

`<code>` is the derived participant code (for example `FaRe1995`, names are never stored),
`<stamp>` the session start. The file is tab-separated, opened once and flushed after every row,
so a session that dies mid-run leaves everything up to the last screen change on disk. Blanks are
`n/a`. `tests/check_columns.py` holds the two arms' column lists identical.

**Everything is in this file: the session facts, every screen that was shown with its measured
onset and duration, every answer with its reaction time and correctness, and on every trial row
the schedule ground truth needed to interpret it.** Every onset, duration and reaction time is
MEASURED, never copied from the design: onsets when a screen goes up (the flip in PsychoPy, the
DOM update in the browser), durations when it comes down, reaction times from the key press. The
scheduled values live in the `meta` rows and, for the jitter, on each `fixation_gap` row next to
the measured duration. `tests/reconstruct_session.py` rebuilds a whole session from this file
alone and checks it against itself (section 4).

---

## 1. The 43 columns

The first three name the row, the next eight say what happened, the last thirty two are the
schedule columns kept on every trial row.

| column | content |
|---|---|
| `subj_id` | the participant code: in the study the participant database code (e.g. `27985.cb`), the same in the online, MEG and MRI files |
| `block` | main task: the scanner block 1..6 (the schedule's `block`); familiarization and gate: the attempt number; practice, the overview and the meta rows: 0 |
| `trial` | the trial number within the phase (the schedule's `trial` in the main task, the question number in the gate); blank on block-level and meta rows |
| `onset` | seconds on the block clock when the screen went up; the block clock starts at the trigger key (`block_start` at 0.0000); blank on meta rows |
| `duration` | measured seconds the screen stayed up; 0 for instantaneous markers (responses, block start and end); self-paced screens carry the time until the key press |
| `event` | what happened, see section 2 |
| `trial_type` | `establish`, `value_change`, `structure_change`, `value_control`, `structure_control`, `partial_tracking_value` (TV), `partial_tracking_structure` (TS), `tracking` in the main task (the two partial kinds since 2026-09-23, in the Prolific set only since 2026-11-04); `practice`, `familiarization`, `gate`, `overview` in the intro; `session` on meta and session_end rows |
| `stimulus` | what was shown, encoded per event type (section 2); `key=value` on meta rows |
| `response` | on `response` rows: the clip id chosen |
| `rt` | on `response` rows: seconds from probe onset to the key press |
| `correct` | on `response` and `feedback` rows: 1 or 0 |
| `kind` | `EST` / `V` / `S` / `CV` / `CS` / `TV` / `TS` / `T`: the trial type in short (`TV` and `TS`, the short no-change trials without a probe, since 2026-09-23 and in the Prolific set only since 2026-11-04; `gate` on the gate question rows). Every short trial (V, S, CV, CS, and TV and TS since 2026-10-09) carries a rest, and so does the `T` follow-up right after every change (`probe_slot` = `followup`, since 2026-09-23); the other T do not. TV and TS carry no probe |
| `probe_slot` | `change`, `followup` or `control` when the trial carries a probe; `practice_question` on the rows of the three swap questions of the practice (2026-10-05); blank otherwise |
| `winner_column` | which route (A, B or C) is worth 100 after this trial; the other two are worth 50 |
| `untouched_column` | on a change trial: the route the change did not involve, the within-trial control |
| `swap_step` | on a structure change: `1->2` or `2->3` (also `3->4` in the 4-step variant), the transition at which the two 50 routes exchanged tails (`1->2`: steps 2 and 3 exchanged; `2->3`: step 3 only) |
| `counterfactual_route` | on a structure change: the route whose new tail was NOT shown; the observed leg is the other swapped route, the one holding `shown_videos` |
| `shown_videos` | the clips presented on the trial, in step order: none on `V`, `CV` and `TV` (since 2026-10-05 they show only the outcome; from 2026-09-23 to 2026-10-04 one clip), two adjacent clips on `S`, `CS` and `TS`, the whole route on a full walk (`EST`, `T`) |
| `hidden_videos` | the clips of the walked route that were not presented |
| `route_A_videos`, `route_B_videos`, `route_C_videos` | the three journeys as they stand after this trial, as clips in step order; a route's treasure is the one of the column its last clip belongs to (`layout` and `reward_images` meta rows) |
| `reactivation_targets` | on a change trial: the clips predicted to reactivate in the rest that follows (value change: the new 100 route and the loser route; structure change: the unshown parts of both swapped routes) |
| `probe_type` | `value_unobserved`, `value_established`, `structure_unobserved`, `structure_established`. `structure_established` replaced `structure_observed` on 2026-09-23 and `value_established` replaced `value_observed` on 2026-10-05, so the older names appear in the first pilot rounds (and on some practice rows) |
| `probe_subtype` | on structure-change probes and their follow-ups: `observed_leg` or `counterfactual_leg` |
| `probe_options` | the three option clips in display order, left to right (keys J, K, L); all at one step, one per route |
| `probe_correct_video` | the correct option |
| `probe_cue_video` | the cue still above a same-sequence probe; blank on preference probes |
| `loser_column` | on a value change: the route that dropped from 100 to 50 (since 2026-11-05) |
| `observed_route` | on a structure change: the route whose new transition was shown; on a structure control: the route walked (since 2026-11-05) |
| `gained_videos` ... `untouched_reward` | the change labels by stimulus name, on V and S trials (since 2026-11-05; session sets only, n/a with the Prolific set): `gained_videos`/`_reward`, `lost_videos`/`_reward`, `observed_transition`, `observed_next`, `observed_videos`/`_reward`, `alternative_transition`, `alternative_videos`/`_reward`, `untouched_videos`/`_reward`. Definitions in SCHEDULE_COLUMNS.md, columns 63-75 |

Everything else in a schedule row is derivable, so it is not repeated on every row:

| dropped column | how to get it |
|---|---|
| `event`, `change_domain`, `condition` | functions of `kind` (and of `trial_type`) |
| `break_20s` | 1 exactly when `kind` is V, S, CV, CS, TV or TS (TV and TS since 2026-10-09), or `probe_slot` is `followup`; never on EST or the other T. Equal to `probe` except on TV and TS (Prolific set only), which are rested but not probed |
| `probe` | 1 exactly when `probe_slot` is set |
| `worth_A/B/C` | 100 for `winner_column`, 50 for the others |
| `terminal_image`, `terminal_amount` | on the `outcome` row as `stimulus` (no outcome row on `S`, `CS`, `TS`) |
| `loser_column` | the previous trial's `winner_column` |
| `control_column` | equals `untouched_column` |
| `observed_route` | the route whose videos contain `shown_videos` |
| `transition_change`, `counterfactual_videos` | `shown_videos` plus `swap_step`; `route_<counterfactual_route>_videos` |
| `walk_cells`, `walk_videos`, `shown_cells`, `hidden_cells`, `route_*_path` | cells and clips map one to one through the `layout` meta row; the walk is shown plus hidden in route order |
| `probe_domain`, `probe_observability`, `probe_direction` | all inside `probe_type` (value = preference prompt, structure = same-sequence prompt) |
| `probe_correct_index` | position of `probe_correct_video` in `probe_options` |
| `probe_ref`, `probe_question` | equal to `probe_correct_video`; never displayed |
| `A1`..`C3`, `reward_image_A/B/C` | constant per participant, in the `layout` and `reward_images` meta rows |

The schedule CSV itself stays the source of truth; the `schedule` meta row names it and `trial`
joins back to it.

---

## 2. The row kinds (`event`) and what `stimulus` holds

| `event` | `stimulus` | meaning |
|---|---|---|
| `meta` | `key=value` | one session fact per row, at the top of the file: `subj_id`, `schedule`, `steps`, `modality`, `implementation`, `language`, `dry_run`, `timing_profile`, `layout` (`A1=aliens_3\|A2=spaceships_1\|...` in the 3-step task), `reward_images` (`A=money\|B=gold\|C=diamonds`), `timings` (`T_VIDEO=0.75\|...`), `main_task_feedback`, `skipped_phases`, `data_sink`, `schedule_assignment` (`url` or `hash_of_id`), `prolific_pid`, `prolific_study_id`, `prolific_session_id` (on Prolific), `log_schema`, `started` |
| `block_start` | wall-clock time, ISO 8601 | the trigger; onset 0.0000 by definition |
| `block_lead_in` | | the 3 s fixation before a block's first trial |
| `block_lead_out` | | the 7 s fixation after a block's last trial, right before `block_end` (since 2026-11-05) |
| `fixation_start` | `scheduled=3.1184` | the fixation that opens every trial (mean 3 s, drawn in [2, 4] s; its cross 3 x the normal size since 2026-10-06); `duration` is measured, `stimulus` the scheduled value (in the session sets the schedule's `iti_start`, precomputed by make_itis.py) |
| `clip1` .. `clip4` | clip id | a clip playing (a practice shape id in practice). EVERY trial plays its shown clips, a change included: none on a value change, value control or `partial_tracking_value` (since 2026-10-05; one before), two on a structure change, structure control or `partial_tracking_structure`, the whole route on a full walk |
| `fixation_gap` | `scheduled=0.7321` | a jittered fixation cross inside a trial; `duration` is the measured gap, `stimulus` the value it was scheduled for (in the session sets the schedule's `iti_k`, precomputed by make_itis.py); in the session sets (since 2026-11-05) gaps lie only between a trial's events, so its last event is followed directly by the next trial's `fixation_start`, the rest, or the lead-out; in the Prolific set the last gap of a trial is the interval to the next |
| `outcome` | `<treasure>+<points>`, e.g. `gold+100` | the outcome screen that closes every trial whose row has one: since 2026-10-05 all but the pair format (`S`, `CS`, `TS`), and on `V`, `CV`, `TV` it is the only screen of the trial |
| `rest_readout` | | the rest window, fixation only (20 s in fMRI, 5 s online and in MEG) |
| `probe` | the three options in display order, `a\|b\|c` | the probe screen; `duration` is its actual time up (reaction time plus the 0.4 s highlight, or the full 8 s window on a miss); the cue is `probe_cue_video`, the prompt follows from `probe_type` and `language` |
| `response` | the options again; `response`, `rt`, `correct` filled | the key press |
| `no_response` | the options again | the window ran out with no press |
| `feedback` | | the correct / wrong screen (practice, gate, and the main task while `main_task_feedback` is true) |
| `practice_note` | strings key | a self-paced explanation screen in practice; with the real journeys (2026-10-01) the screen also draws the journeys involved, the first one, `real_study` (2026-10-05), shows the starting journeys to learn them and the last one, `real_reset`, shows them again (both trial blank); after the swap (trial 5) come `real_questions_intro`, the diagram `real_swap_explain` and one review per question (`real_answer_shown`, `real_answer_hidden_next`, `real_answer_hidden_end`, with the question's design columns). The three swap questions themselves are `probe`, `response` / `no_response` and `feedback` rows with `trial_type` `practice`; they count towards neither the score nor the gate |
| `practice_map` | `a\|b\|c;d\|e\|f` | the practice map of the SHAPE practice (`PRACTICE_STIMULI` = `shapes`): both rewired shape journeys, observed first; the real practice (the default since 2026-10-01) logs all its picture screens as `practice_note` instead |
| `structure_overview` | `a\|b\|c;d\|e\|f;g\|h\|i` | the starting-state overview before the main task, journeys A, B, C |
| `break_overview` | `a\|b\|c;d\|e\|f;g\|h\|i` | the overview of the current journeys in a break between blocks (2026-10-01), A, B, C as they stand at the end of the block just finished; in its own `overview` block (block 0, trial blank); the k-th one follows main block k; `duration` runs to the second key press |
| `block_end` | `dropped_frames=N` (PsychoPy) | end of the block |
| `page_hidden` | `n/a` | browser only (2026-09-24): the page was hidden (another tab or window in front, minimized); onset = when, duration = how long. The browser throttles a hidden page (timers slowed to 1 s, after 5 min to 1 min), so every screen overlapping it runs long. Written when it starts, so it can precede the row of the screen it interrupted; `tests/events_view.py` keeps it out of blocks and trials |
| `fullscreen_exit` | `n/a` | browser only: the participant left fullscreen (duration 0) |
| `reminder` | `n/a` | browser only: the reminder at the bottom of the screen after either of the two above; duration = how long it was up (a few seconds after a hidden page, until "Back to fullscreen" after leaving fullscreen) |
| `session_end` | `key=value` | at the bottom: `gate_passed`, `gate_attempts`, `gate_scores`, `n_page_hidden`, `page_hidden_s`, `n_fullscreen_exit` (these three browser only), `n_correct`, `n_questions`, `score_pct` (the performance score over the main-task questions, a miss counts as wrong, since 2026-10-02), `localizer_intro_shown`, `localizer_intro_completed` (browser only, 1 or 0: the MRI/MEG localizer practice after the last block of `session=online`, since 2026-10-13), `status`, `finished` |

Not in the file: the instruction, break and trigger-wait screens between blocks (outside every
block clock; the wall-clock times on `block_start` bracket them), and the prompt text itself
(fixed per `probe_type` and language). The marker codes sent to the MEG port follow from `kind`
(trial onset 2 + 0 / 100 / 200 / 300 / 400 / 500 / 600 / 700 for EST / V / S / CV / CS / T / TV / TS).

A plain-text guide to the same columns for readers of the data, with quick recipes, is
`DATA_COLUMNS.txt`.

---

## 3. Reading it back

`tests/events_view.py` (and `.mjs` for the browser tests) turns the file into the two views an
analysis usually wants: the meta as a dict, and one record per trial with the kept schedule
columns, the measured onset and duration of each of its screens, and the answer. For a per-run
events table in the BIDS sense, filter on `block` and drop the meta rows.

Simulated sessions from `tests/agent_run_jspsych.mjs` are written in exactly this format to
`data/online_agent/`, with the agent's accuracy tables in `data/online_agent/summaries/`.

---

## 4. Reconstruction check

```bash
python3 tests/reconstruct_session.py <session.tsv>
```

rebuilds the block-by-block timeline from the one file alone and checks, for every main-task
trial: the clips rendered are exactly `shown_videos` in step order; no `hidden_videos` clip appears
anywhere; no composite screen is drawn; the one outcome shows the amount that follows from the walked route and the
current winner and, through the `layout` and `reward_images` meta rows, the treasure of the walked
route's terminal; a rest exists exactly on the short trials (V, S, CV, CS, TV, TS) and the change follow-ups, after the last stimulus and before
the probe; a probe exists exactly where `probe_slot` is set, over the row's own options; the logged
`correct` equals whether the response is `probe_correct_video`; the logged `rt` equals the onset
difference; every `fixation_gap` carries its scheduled draw; the kept columns are identical on every
row of a trial; no screen overlaps the next while the whole block clock is covered; and the file
opens with meta rows and closes with session_end rows. It exits 0 only when all of that holds.
