# Note for the session working on the main task's final stimuli (2026-10-26)

From the MRI localizer session (P7_loc_mri). The user's decisions below were made there on
2026-10-23/24 and apply to the MAIN TASK in `files (5)`; the user asked that YOUR session carries them
out (the localizer session does not touch the main task).

## The user's decisions for the main task
1. Every clip of a journey plays its video in FULL, 1.0 s, in EVERY modality (online, MEG, MRI),
   so the browser arm needs video too (today it shows stills only; PsychoPy plays videos only for
   `fmri`, `VIDEO_MODALITIES = ("fmri",)`, and `T_VIDEO` is 0.75 s outside the `mri` profile).
2. The treasure on the outcome screen plays its video too, with the points over it.
3. Every screen is grey (RGB 128) and every still is the new still image (maps, names screens,
   probes, reviews): already done in your commit 03e8e9e.
4. The MEG LOCALIZER is left to its own session (P7_loc_meg).

## Two bugs that show on grey (found by an exploration of HEAD 03e8e9e)
- Swap diagram outlines are hollowed out with black: `src/psychopy/run_task.py:609` (`"black"`)
  and `src/jspsych/experiment.js:478` (`'#000'`); on grey this leaves black bands inside every
  colored outline. Use the background color. Also `experiment.js:453` `<rect fill="#111">` behind
  the treasure (dark-card leftover; would show around a transparent or video treasure).
- Low contrast on 128 grey: `MARK_SEEN_COLOR #F2C230` (2.4:1), `MARK_INFERRED_COLOR #4C9BE8`
  (1.35:1), selection yellow (2.8:1), correct green (1.9:1); the shape colors only matter with
  `PRACTICE_STIMULI = "shapes"`. Smaller leftovers in `index.html`: `.vs-review-row img
  { background:#fff }` (:121), `.vs-probe-cue` border `#666` (:104).

## Useful from the localizer work (all in ../Localizer_MRI)
- Browser video with an exact-grey background: H.264 540x540, 24 fps, encoded from frames whose
  background was set to exactly 128, color tagged (`-vf scale=out_color_matrix=bt709:out_range=tv
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv`); the stored luma is
  126 and browsers decode it to 128 (verified with a canvas read in Chrome). The raw final videos
  have a 128 to 131 background, which shows as a lighter square on a 128 page.
  See `stimuli/make_video_stimuli.py` and the copies in `files (5)/localizer_intro/stimuli/videos_grey/`.
- PsychoPy: a reused MovieStim (2023.2.3, ffpyplayer) showed the previous run's last frame at onset
  and frame 0 only after about 85 ms, so the localizer plays pre-decoded frames, refresh-locked
  (the same approach as your flipbook). Real-time test: 1.0 s +/- 8 ms, all 24 frames shown.

## Coordination
- You committed 03e8e9e on the branch `localizer-videos`, on top of the localizer's 18cb703. Both
  are local only; nothing is pushed (push only on the user's "push").
- `files (5)/localizer_intro/` is GENERATED from ../Localizer_MRI (`sync_to_main_task.py`): please
  do not edit it there. Its MRI part plays videos on grey; its MEG part mirrors the MEG localizer
  (pictures, 0.75 s, black).
- The main repo's working tree shows `stimuli/rewards/treasure_diamonds.png` deleted and
  `.claude/launch.json` modified (the latter is the localizer session's local preview servers).
