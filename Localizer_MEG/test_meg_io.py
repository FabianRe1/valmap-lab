"""Check the MEG lab connections before a session (2026-10-14). No window, no participant data.

1. Markers: sends every code the localizer can send, one per second in increasing order, through
   the configured backend (20 ms pulses). While the MEG records, check its trigger channel shows
   exactly this list and nothing else.
2. Button box: then listens on the serial response box and prints the byte of every press, so the
   button of each finger can be entered in ../meg_lab/settings.py (FINGER_BUTTON, shared with
   the main task).

Usage (on the MEG PC, PsychoPy's python):
  python test_meg_io.py                       # parallel port and button box, as in the MEG
  python test_meg_io.py --listen 60           # listen 60 s for button presses (default 30)
  python test_meg_io.py --marker-backend dummy --no-buttons   # dry check anywhere
"""
import argparse
import time

import config as cfg


def all_codes(n_blocks=6):
    codes = set(cfg.CLASS_CODES.values())
    codes |= {v for k, v in cfg.MARKER_CODES.items() if not k.startswith("block_")}
    codes |= {cfg.MARKER_CODES[k] + b for k in ("block_start", "block_end") for b in range(1, n_blocks + 1)}
    return sorted(codes)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--marker-backend", default="parallel", choices=("dummy", "parallel", "serial", "lsl"))
    ap.add_argument("--no-buttons", action="store_true")
    ap.add_argument("--listen", type=float, default=30.0, help="seconds to listen for button presses")
    ap.add_argument("--spacing", type=float, default=1.0, help="seconds between codes")
    a = ap.parse_args()

    from triggers import make_marker
    marker = make_marker(a.marker_backend, verbose=True)
    if marker.is_fallback:
        print("!!! marker backend failed: no codes reach the MEG (see the error above)")
    codes = all_codes()
    print(f"sending {len(codes)} codes, {a.spacing:.1f} s apart, each held {marker.pulse * 1000:.0f} ms:")
    print("  " + " ".join(map(str, codes)))
    for c in codes:
        marker.send(c, "test")
        time.sleep(a.spacing)
    marker.close()
    print("done sending. Expected on the MEG trigger channel, in this order:", codes)

    if a.no_buttons:
        return
    from responses import make_button_box
    box = make_button_box()
    if box is None:
        print("!!! button box failed to open; nothing to listen to")
        return
    print(f"\nlistening {a.listen:.0f} s on {cfg.BUTTON_SERIAL_PORT}: press right index, right middle, "
          "left index (and the 4th button), one at a time")
    end = time.time() + a.listen
    while time.time() < end:
        for name, t in box.read():
            print(f"  {name}  (t = {t:.3f} s)")
        time.sleep(0.005)
    box.close()
    print("enter the names into ../meg_lab/settings.py, FINGER_BUTTON (right_index, right_middle, "
          "left_index, left_middle); both tasks read them from there")


if __name__ == "__main__":
    main()
