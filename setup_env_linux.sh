#!/bin/bash
# setup_env_linux.sh: build a Python environment for the ValMap lab sessions on a Linux lab PC
# (2026-11-04), for when the CBS `PSYCHOPY --version 2026.2.4` wrapper is not available or lacks
# the MEG hardware packages. Needs no root rights: everything goes to your home folder.
#
# Usage, from the lab repo's root:   bash setup_env_linux.sh
#   Then start sessions as always (bash run_session.sh meg): run_session.sh uses this
#   environment by itself, because this script writes its python's path to .valmap_python.
#   Rerunning the script is safe; `bash setup_env_linux.sh --check` only runs the checks.
#
# What it installs (2026-11-09: PsychoPy 2026.2.4, the version the lab runs; 2023.2.3 before):
#   Python 3.11, PsychoPy 2026.2.4 with its own requirements (numpy 2, PyQt6 for the start
#   dialog, psychtoolbox for keyboard timing, pyglet), pyserial (MEG response box), pyparallel
#   (MEG triggers via /dev/parport0). An environment from the 2023 version is replaced.
# Where: micromamba in ~/.valmap/bin, the environment in ~/.valmap/env (change with VALMAP_HOME).

set -u
VALMAP_HOME="${VALMAP_HOME:-$HOME/.valmap}"
ENV="$VALMAP_HOME/env"
MAMBA="$VALMAP_HOME/bin/micromamba"
REPO="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${VALMAP_PYTHON:-$ENV/bin/python}"   # setup_env_conda.sh sets VALMAP_PYTHON for --check

say() { echo ""; echo "=== $*"; }

install_env() {
  if [ "$(uname -s)" != "Linux" ]; then
    echo "This script is for the Linux lab PCs (this is $(uname -s))."; exit 1
  fi
  mkdir -p "$VALMAP_HOME/bin"
  if [ ! -x "$MAMBA" ]; then
    say "Downloading micromamba (a small conda) to $MAMBA"
    case "$(uname -m)" in
      x86_64) plat=linux-64 ;; aarch64) plat=linux-aarch64 ;;
      *) echo "Unknown processor $(uname -m)"; exit 1 ;;
    esac
    curl -Ls "https://micro.mamba.pm/api/micromamba/$plat/latest" \
      | tar -xj -C "$VALMAP_HOME" bin/micromamba || { echo "Download failed (internet?)"; exit 1; }
  fi
  export MAMBA_ROOT_PREFIX="$VALMAP_HOME/mamba"
  # an environment from the PsychoPy 2023 version (Python 3.8) cannot take 2026.2.4: start anew
  if [ -x "$PYTHON" ] && ! "$PYTHON" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 11))'; then
    say "Replacing the old environment in $ENV (Python 3.8, PsychoPy 2023)"
    rm -rf "$ENV"
  fi
  if [ ! -x "$PYTHON" ]; then
    say "Creating the environment in $ENV (conda-forge; takes a few minutes)"
    "$MAMBA" create -y -p "$ENV" -c conda-forge python=3.11 pip \
      || { echo "Creating the environment failed"; exit 1; }
  fi
  # a conda OpenGL loader (libglvnd) in the environment would be loaded instead of the PC's
  # graphics driver and fail ("invalid enumerant", found 2026-11-04): remove any, so the
  # system's OpenGL is used.
  rm -f "$ENV"/lib/libGL.so* "$ENV"/lib/libGLX.so* "$ENV"/lib/libGLdispatch.so* \
        "$ENV"/lib/libEGL.so* "$ENV"/lib/libOpenGL.so*
  say "Installing PsychoPy 2026.2.4 and the hardware packages (pip)"
  "$PYTHON" -m pip install --upgrade pip >/dev/null
  "$PYTHON" -m pip install -r "$REPO/requirements.txt" \
    || { echo "pip failed"; exit 1; }
  echo "$PYTHON" > "$REPO/.valmap_python"
  echo "Wrote $REPO/.valmap_python: run_session.sh now uses this environment."
}

check_env() {
  local ok=1
  say "Python packages"
  "$PYTHON" - <<'EOF' || ok=0
import importlib, sys
want = {"psychopy": "2026.2.4", "numpy": None, "pyglet": None, "serial": None,
        "PyQt6": None, "psychtoolbox": None, "parallel": None, "pandas": None,
        "scipy": None, "PIL": None}
bad = 0
for name, version in want.items():
    try:
        mod = importlib.import_module(name)
        got = getattr(mod, "__version__", None) or getattr(mod, "version", None) or getattr(mod, "VERSION", None)
        mark = "ok" if version is None or str(got).startswith(version) else f"expected {version}"
        print(f"  {name:13s} {got}  {mark}")
    except Exception as exc:
        print(f"  {name:13s} MISSING ({exc})"); bad = 1
import os
if os.environ.get("DISPLAY"):
    try:
        from psychopy import visual
        win = visual.Window((400, 300), fullscr=False)
        win.flip(); win.close(); print("  a PsychoPy window opens and draws: ok")
    except Exception as exc:
        print(f"  opening a PsychoPy window FAILS: {exc}"); bad = 1
for name in ("psychopy.visual", "psychopy.hardware.keyboard", "psychopy.parallel", "psychopy.gui"):
    try:
        importlib.import_module(name); print(f"  {name:28s} imports")
    except Exception as exc:
        print(f"  {name:28s} FAILS: {exc}"); bad = 1
sys.exit(bad)
EOF
  say "MEG hardware access (only matters on the MEG PC)"
  for dev in /dev/parport0 /dev/ttyS1; do
    if [ ! -e "$dev" ]; then echo "  $dev does not exist"; ok=0
    elif [ -r "$dev" ] && [ -w "$dev" ]; then echo "  $dev readable and writable: ok"
    else echo "  $dev NOT writable by $(whoami) (group $(stat -c %G "$dev")): ask IT to add you"
         echo "    to that group, e.g. sudo usermod -aG $(stat -c %G "$dev") $(whoami), then log in again"; ok=0
    fi
  done
  if [ -r /proc/modules ]; then
    grep -q "^ppdev " /proc/modules && echo "  kernel module ppdev loaded: ok" \
      || { echo "  kernel module ppdev NOT loaded: ask IT for  sudo modprobe ppdev"; ok=0; }
    grep -q "^lp " /proc/modules && { echo "  kernel module lp is loaded and may hold the port:"
      echo "    ask IT for  sudo rmmod lp"; ok=0; } || echo "  kernel module lp not loaded: ok"
  fi
  say "Result"
  if [ $ok = 1 ]; then echo "  Everything in place. Next: in Localizer_MEG, run"
    echo "    $PYTHON test_meg_io.py"
    echo "  and press every button (it prints which byte each one sends)."
  else echo "  See the lines above. Python packages missing: rerun this script."
    echo "  Hardware lines: on the MRI PC they do not matter; on the MEG PC ask IT."
  fi
}

if [ "${1:-}" != "--check" ]; then install_env; fi
if [ ! -x "$PYTHON" ]; then echo "No environment at $ENV: run without --check first."; exit 1; fi
check_env
