"""
The photodiode check, shared by the main task and the MEG localizer (2026-11-11, user). Off by
default; switched on in the start dialog ("Photodiode check", MEG only) or with --photodiode.

A white stripe across the full width of the very top of the screen (PHOTODIODE_STRIPE_HEIGHT of
the screen height) stays on every screen of the session. Its middle third TOGGLES on every flip
that sends a marker code (an event onset: picture, fixation, probe, feedback, outcome...): white
to black or black to white, and it stays so until the next coded flip (2026-11-11, user; first
version: black for one flip only). So every edge the photodiode sees is one code, and a period
lasts exactly as long as its event, e.g. a video from its onset to the fixation after it. The
session starts white. Codes sent without a screen change (responses, block start at the trigger,
block end) do not toggle it. The stripe is taped over, so the participant does not see it.

Both rects are autoDraw stimuli, drawn by win.flip() on top of everything else, so they appear on
every flip, including screens a task flips directly. The task calls arm() before a coded flip and
after_flip() after every flip.
"""
from . import settings as cfg


class PhotodiodeStripe:
    def __init__(self, win, height=None):
        from psychopy import visual
        h = 2.0 * (height if height is not None else cfg.PHOTODIODE_STRIPE_HEIGHT)   # norm units: screen = 2
        y = 1.0 - h / 2.0
        self.white = visual.Rect(win, units="norm", width=2.0, height=h, pos=(0, y),
                                 fillColor="white", lineColor=None, autoDraw=True)
        self.black = visual.Rect(win, units="norm", width=2.0 / 3.0, height=h, pos=(0, y),
                                 fillColor="black", lineColor=None)
        self.is_black = False
        self.armed = False
        self.n_toggles = 0

    def arm(self):
        """The next flip sends a code: the middle third switches on that flip and stays."""
        if not self.armed:
            self.is_black = not self.is_black
            self.black.autoDraw = self.is_black   # added after the white stripe, so drawn on top
            self.armed = True

    def after_flip(self):
        """Call after every flip: counts the switch once it is on screen."""
        if self.armed:
            self.armed = False
            self.n_toggles += 1

    def close(self):
        self.white.autoDraw = False
        self.black.autoDraw = False
