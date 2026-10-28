"""
The MEG response box for the localizer: since 2026-10-14 it lives in ../meg_lab/buttons.py,
shared with the main task (settings in ../meg_lab/settings.py). This module keeps the
localizer's imports working.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # P7_struct_value, holds meg_lab

from meg_lab.buttons import ButtonBox, make_button_box      # noqa: E402,F401
