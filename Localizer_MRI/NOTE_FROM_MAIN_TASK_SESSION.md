# Note from the main-task session (2026-10-26)

Done in the main task (branch localizer-videos, local, not pushed): every journey picture and
the treasure play their 1 s video ONLINE and in the MRI; the MEG shows the stills (the user's
choice when asked on 2026-10-26: "MRI and online, MEG stills"; not every modality). Pictures
grew 20% in the main task (squares 0.60 of the screen height instead of 0.50).

At the user's request this session also changed, in the localizers:
- Localizer_MRI/config.py and Localizer_MEG/config.py: STIM_HEIGHT and PROBE_HEIGHT 0.60 (0.50).
- Localizer_MRI/online_practice/make_practice_designs.py: stim_height 0.60 for both parts;
  practice_designs.json regenerated (only the two size values changed) and synced into
  files (5)/localizer_intro with sync_to_main_task.py.
Both localizers' fast dry runs pass check_log at the new size.
The deleted files (5)/stimuli/rewards/treasure_diamonds.png was left as it is (user).

Later the same day (user): the scanner box may read as b / y / g or b / z / r depending on the
keyboard layout, so this session made Localizer_MRI/config.py accept both: KEY_RIGHT z or y,
KEY_NEITHER r or g, KEY_CONTINUE all of them. The main task does the same (b; y or z; g or r).
The dry run still passes check_log.

Update 2026-11-04 (from RepChanges, the earlier study on the same scanner): the box sends b (blue,
right index), z (yellow, right middle), r (left index) and g (left middle), four separate buttons.
"b / y / g" meant the colors blue, yellow, green. KEY_NEITHER is now r only (g dropped); "y" stays
on KEY_RIGHT as a layout fallback. The main task answers left, middle, right with b, z (or y), r.
