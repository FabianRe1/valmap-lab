#!/bin/bash
# setup_env_conda.sh: build the ValMap Python environment with an existing Anaconda or Miniconda
# (2026-11-11). The same packages and checks as setup_env_linux.sh, which downloads its own small
# conda instead. Use one of the two. Needs no root rights.
#
# Usage, from the lab repo's root:   bash setup_env_conda.sh
#   Then start sessions as always (bash run_session.sh meg): run_session.sh uses this
#   environment by itself, because this script writes its python's path to .valmap_python.
#   Rerunning the script is safe; `bash setup_env_conda.sh --check` only runs the checks.
#   By hand:  conda activate valmap  then  python run_localizer.py ...
#
# What it installs: an environment "valmap" (change with VALMAP_ENV_NAME) with Python 3.11 from
#   conda-forge, then requirements.txt: PsychoPy 2026.2.4 with its own requirements, PyQt6 (start dialog),
#   psychtoolbox (keyboard timing), pyserial (MEG response box), pyparallel (MEG triggers via
#   /dev/parport0) and python-xlib. Only conda-forge is used, so Anaconda's default channels
#   (and their terms of service) are never needed. An environment with another Python is replaced.
# Finding conda: the `conda` command, else ~/anaconda3, ~/miniconda3, ~/miniforge3, /opt/anaconda3,
#   /opt/conda; or set CONDA=/path/to/bin/conda.

set -u
ENV_NAME="${VALMAP_ENV_NAME:-valmap}"
REPO="$(cd "$(dirname "$0")" && pwd)"

say() { echo ""; echo "=== $*"; }

find_conda() {
  if [ -n "${CONDA:-}" ] && [ -x "$CONDA" ]; then echo "$CONDA"; return; fi
  if [ -n "${CONDA_EXE:-}" ] && [ -x "$CONDA_EXE" ]; then echo "$CONDA_EXE"; return; fi
  if command -v conda >/dev/null 2>&1 && [ -x "$(command -v conda)" ]; then command -v conda; return; fi
  for c in "$HOME"/anaconda3/bin/conda "$HOME"/miniconda3/bin/conda "$HOME"/miniforge3/bin/conda \
           /opt/anaconda3/bin/conda /opt/miniconda3/bin/conda /opt/conda/bin/conda; do
    [ -x "$c" ] && { echo "$c"; return; }
  done
}

CONDA_BIN="$(find_conda)"
if [ -z "$CONDA_BIN" ]; then
  echo "No conda found. Install Anaconda or Miniconda, or set CONDA=/path/to/bin/conda,"
  echo "or use bash setup_env_linux.sh, which brings its own."; exit 1
fi
echo "Using conda: $CONDA_BIN"

env_prefix() {   # the environment's folder, empty if it does not exist
  "$CONDA_BIN" env list 2>/dev/null | awk -v n="$ENV_NAME" '$1 == n {print $NF}'
}

install_env() {
  local prefix; prefix="$(env_prefix)"
  # an environment with another Python (e.g. 3.8 from PsychoPy 2023) cannot take 2026.2.4
  if [ -n "$prefix" ] && ! "$prefix/bin/python" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 11))' 2>/dev/null; then
    say "Replacing the environment $ENV_NAME (not Python 3.11)"
    "$CONDA_BIN" env remove -y -n "$ENV_NAME" || { echo "Removing it failed"; exit 1; }
    prefix=""
  fi
  if [ -z "$prefix" ]; then
    say "Creating the environment $ENV_NAME (conda-forge, Python 3.11; takes a few minutes)"
    "$CONDA_BIN" create -y -n "$ENV_NAME" --override-channels -c conda-forge python=3.11 pip \
      || { echo "Creating the environment failed"; exit 1; }
    prefix="$(env_prefix)"
  fi
  PYTHON="$prefix/bin/python"
  [ -x "$PYTHON" ] || { echo "No python in $prefix"; exit 1; }
  if [ "$(uname -s)" = "Linux" ]; then
    # a conda OpenGL loader (libglvnd) would be loaded instead of the PC's graphics driver and
    # fail ("invalid enumerant", found 2026-11-04): remove any, so the system's OpenGL is used.
    rm -f "$prefix"/lib/libGL.so* "$prefix"/lib/libGLX.so* "$prefix"/lib/libGLdispatch.so* \
          "$prefix"/lib/libEGL.so* "$prefix"/lib/libOpenGL.so*
  fi
  say "Installing PsychoPy 2026.2.4 and the hardware packages (pip)"
  "$PYTHON" -m pip install --upgrade pip >/dev/null
  "$PYTHON" -m pip install -r "$REPO/requirements.txt" \
    || { echo "pip failed"; exit 1; }
  echo "$PYTHON" > "$REPO/.valmap_python"
  echo "Wrote $REPO/.valmap_python: run_session.sh now uses this environment."
}

if [ "${1:-}" != "--check" ]; then install_env; fi
prefix="$(env_prefix)"
if [ -z "$prefix" ]; then echo "No environment $ENV_NAME: run without --check first."; exit 1; fi
# the checks are the same as setup_env_linux.sh's (packages, a test window, the MEG ports)
VALMAP_PYTHON="$prefix/bin/python" exec bash "$REPO/setup_env_linux.sh" --check
