#!/bin/bash
# run_session.sh: start a ValMap lab session (2026-11-02, after the RepChanges run_EXP.sh).
# Usage, from anywhere:   bash run_session.sh mri     or     bash run_session.sh meg
# Opens the start dialog (start_session.py) through the CBS PsychoPy wrapper; one part per start.
# Outside the CBS (no PSYCHOPY command), set PY to PsychoPy's python, e.g.
#   PY=/Applications/PsychoPy.app/Contents/MacOS/python bash run_session.sh mri

PSYCHOPY_VERSION=2023.2.3

echo '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
echo '~~~~~~~~~~~~~~~~~~~~      ValMap      ~~~~~~~~~~~~~~~~~~~'
echo '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'

cd "$(dirname "$0")" || exit 1

if [ -n "$PY" ]; then
  "$PY" start_session.py "$@"
elif command -v PSYCHOPY >/dev/null 2>&1; then
  PSYCHOPY --version "$PSYCHOPY_VERSION" python3 start_session.py "$@"
else
  echo "No PSYCHOPY command here: set PY to PsychoPy's python (see the top of this script)."
  exit 1
fi
status=$?

echo ''
echo 'Thanks for running this session.'
echo 'Copy the data folders off this computer: data/, main_task/src/psychopy/data/,'
echo 'Localizer_MRI/data/, Localizer_MEG/data/.'
echo '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
exit $status
