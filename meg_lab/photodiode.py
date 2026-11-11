"""
The photodiode check, shared by the main task and the MEG localizer (2026-11-11, user). Off by
default; switched on in the start dialog ("Photodiode check", MEG only) or with --photodiode.

A white stripe across the full width of the very top of the screen (PHOTODIODE_STRIPE_HEIGHT of
the screen height) stays on every screen of the session. On every flip that sends a marker code
(an event onset: picture, fixation, probe, feedback, outcome...), the middle third of the stripe
is black for that one flip and white again on the next, so each black flash marks one code and a
photodiode on the middle third measures how far the code is from the light. Codes sent without a
screen change (responses, block start at the trigger, block end) have no flash. The stripe is
taped over, so the participant does not see it.

Both stripes are autoDraw stimuli, drawn by win.flip() on top of everything else, so they appear
on every flip, including screens a task flips directly. The task calls arm() before a coded flip
and after_flip() after every flip.
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
        self.armed = False
        self.n_flashes = 0

    def arm(self):
        """The next flip sends a code: its middle third is black."""
        if not self.armed:
            self.black.autoDraw = True     # added after the white stripe, so drawn on top of it
            self.armed = True

    def after_flip(self):
        """Call after every flip: white again from the next flip on."""
        if self.armed:
            self.black.autoDraw = False
            self.armed = False
            self.n_flashes += 1

    def close(self):
        self.white.autoDraw = False
        self.black.autoDraw = False
