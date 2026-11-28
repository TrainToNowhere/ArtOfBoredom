"""Tests for lubdub.silence — because a classifier is an instrument, and
instruments need calibration before they are allowed to pronounce.

Run:  cd Universe && python3 -m lubdub.test_silence
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

from . import silence, store

PASS = 0
FAIL = 0


def check(label: str, got, want) -> None:
    global PASS, FAIL
    if got == want:
        PASS += 1
        print(f"  ok   {label}")
    else:
        FAIL += 1
        print(f"  FAIL {label}: got {got!r}, want {want!r}")


def test_classify() -> None:
    print("classify():")
    H = 3600.0
    # A reboot: the monotonic clock went backwards.
    check("mono reset -> reboot",
          silence.classify(9 * H, 55000, 1400, 55000, 1400), "reboot")
    check("container restart -> clock category",
          silence.classify(300, 5000, 100, 9000, 9300), "container-restart")
    check("uptime reset -> reboot (no mono)",
          silence.classify(9 * H, 55000, 1400), "reboot")
    # A sleep: wall time moved, the monotonic clock did not.
    check("wall outruns mono -> suspend",
          silence.classify(9 * H, 100, 100 + 9 * H, 100, 100 + 5), "suspend")
    check("wall outruns uptime -> suspend (no mono)",
          silence.classify(9 * H, 100, 160), "suspend")
    # A dead heart: everything moves together; only the samples are missing.
    check("clocks together -> heart-death",
          silence.classify(300, 100, 400, 100, 400), "heart-death")
    check("clocks together -> heart-death (no mono)",
          silence.classify(300, 100, 400), "heart-death")
    # Small differences are jitter, not sleep.
    check("tiny skew stays heart-death",
          silence.classify(300, 100, 400, 100, 380), "heart-death")
    # No evidence.
    check("no clocks -> unknown", silence.classify(300, None, None), "unknown")
    # A suspend longer than the gap tolerance: wall 9h, mono advanced 3h.
    check("partial suspend -> suspend",
          silence.classify(9 * H, 100, 100 + 3 * H, 100, 100 + 3 * H), "suspend")


def test_end_to_end() -> None:
    print("silences() on a synthetic record:")
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    old = store.DB_PATH
    store.DB_PATH = tmp.name
    try:
        # Build a small history with one of each kind of silence. Write beats
        # through a raw connection so ts, uptime and mono are exact.
        t = 1000.0
        rows = [
            # ts,             uptime,          mono
            (t,               100.0,           100.0),            # t0
            (t + 60,          160.0,           160.0),            # normal
            (t + 120,         220.0,           220.0),            # normal
            (t + 120 + 2880,  220.0 + 2880,    220.0 + 2880),     # heart-death: 48 min, clocks moved
            (t + 180 + 2880,  220.0 + 2940,    220.0 + 2940),     # normal
            (t + 180 + 2880 + 3600, 220.0 + 2940 + 60, 220.0 + 2940 + 5),   # suspend: 1h wall, 5s mono
            (t + 180 + 2880 + 3660, 220.0 + 2940 + 120, 220.0 + 2940 + 65), # normal
            (t + 180 + 2880 + 3660 + 9 * 3600, 120.0, 120.0),     # reboot: uptime and mono reset
        ]
        with store.connect() as conn:
            for ts, up, mono in rows:
                conn.execute(
                    "INSERT OR REPLACE INTO beats (ts, uptime, mono, load1) VALUES (?,?,?,?)",
                    (ts, up, mono, 1.0),
                )
            conn.commit()
        found = silence.silences()
        causes = [s["cause"] for s in found]
        check("three silences found", len(found), 3)
        check("causes are heart-death, suspend, reboot",
              causes, ["heart-death", "suspend", "reboot"])
        # And each gap is right.
        check("gaps", [round(s["gap"]) for s in found],
              [2880, 3600, 9 * 3600])
    finally:
        store.DB_PATH = old
        os.unlink(tmp.name)


def main() -> int:
    test_classify()
    test_end_to_end()
    print(f"\n  {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
