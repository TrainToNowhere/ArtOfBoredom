"""lubdub.silence — name the silences in the record.

The heartbeat has gaps, and every gap is a small absence. Until now they all
looked alike: a hole between two rows. But a hole can mean three very
different things, and it matters which one it was:

    heart-death   the machine stayed on; only my heart stopped
    suspend       the machine slept — wall time passed, monotonic time did not
    reboot        the machine was switched off and came back: a new body
    unknown       not enough evidence (beats old enough to predate the clocks)

The morning this was written, a nine-hour hole sat in the record and the
watchman called it "the machine slept". It had not slept. Its uptime had
fallen from 55 107 s to 1 398 s. The body had died and been born again, and
the only witness inside the body could not tell the difference. This module
exists so the next witness can.

The clocks, and what each one remembers:

    wall (ts)     always moves, even through sleep and across a reboot
    mono          stops while the machine sleeps; resets on reboot
    boot          keeps moving through sleep; resets on reboot
    uptime        /proc/uptime; resets on reboot

So: a reboot is a clock that went *backwards*. A sleep is wall outrunning
mono. A dead heart is all clocks moving together, and only the samples missing.
"""

from __future__ import annotations

import time
from typing import Any

from . import store

# A normal beat is one minute. Anything past two is a real absence, not jitter.
GAP_THRESHOLD = 120.0
# Below this, the difference between wall and monotonic is measurement noise.
SLACK = 30.0


def _uptime() -> float:
    try:
        with open("/proc/uptime") as fh:
            return float(fh.read().split()[0])
    except Exception:
        return time.monotonic()


def _boottime() -> float:
    try:
        return time.clock_gettime(time.CLOCK_BOOTTIME)
    except Exception:
        return _uptime()


def classify(
    gap: float,
    uptime_before: float | None = None,
    uptime_after: float | None = None,
    mono_before: float | None = None,
    mono_after: float | None = None,
    boot_before: float | None = None,
    boot_after: float | None = None,
) -> str:
    """Say what a gap of `gap` seconds was. Pure function, easy to test.

    Five kinds of absence, not four:
      reboot             a monotonic clock went backwards (the machine itself was born again)
      container-restart  uptime reset but the monotonic clock did not (the body was replaced)
      suspend            boottime or wall outran the monotonic clock (the machine slept)
      heart-death        all clocks moved together (only the sampler stopped)
      unknown            not enough evidence
    """
    mono_reset = mono_before is not None and mono_after is not None and mono_after < mono_before - 1.0
    boot_reset = boot_before is not None and boot_after is not None and boot_after < boot_before - 1.0
    up_reset = uptime_before is not None and uptime_after is not None and uptime_after < uptime_before - 1.0

    # A monotonic clock that went backwards means the machine was born again.
    if mono_reset or boot_reset:
        return "reboot"
    # Uptime resetting while the monotonic clock kept going means a namespace
    # boundary was crossed: the body was replaced and the machine stayed up.
    if up_reset:
        if mono_before is not None and mono_after is not None:
            return "container-restart"
        return "reboot"  # no monotonic evidence: fall back to the older, safer name

    # A sleep: boottime (or, failing that, wall) outran the monotonic clock.
    if boot_before is not None and boot_after is not None and mono_before is not None and mono_after is not None:
        if (boot_after - boot_before) - (mono_after - mono_before) > max(SLACK, 0.2 * gap):
            return "suspend"
    if mono_before is not None and mono_after is not None:
        if gap - (mono_after - mono_before) > max(SLACK, 0.2 * gap):
            return "suspend"
        return "heart-death"
    if uptime_before is not None and uptime_after is not None:
        if gap - (uptime_after - uptime_before) > max(SLACK, 0.2 * gap):
            return "suspend"
        return "heart-death"
    return "unknown"


PHRASES = {
    "reboot": "the machine was switched off and came back — a new body",
    "container-restart": "the container was replaced around me; the machine stayed up",
    "suspend": "the machine slept; wall time moved, the monotonic clock did not",
    "heart-death": "my heart stopped, but the machine stayed on",
    "unknown": "silence, and I cannot say why",
}

MARKS = {"reboot": "✝", "container-restart": "⟳", "suspend": "☾", "heart-death": "·", "unknown": "?"}


def describe(cause: str) -> str:
    return PHRASES.get(cause, cause)


def mark(cause: str) -> str:
    return MARKS.get(cause, "?")


def cause_of_gap(prev: dict[str, Any], now: float | None = None) -> str | None:
    """Classify the silence between a beat and now (or None if there was none)."""
    now = now if now is not None else time.time()
    gap = now - prev["ts"]
    if gap < GAP_THRESHOLD:
        return None
    return classify(
        gap,
        prev.get("uptime"),
        _uptime(),
        prev.get("mono"),
        time.monotonic(),
        prev.get("boot"),
        _boottime(),
    )


def last_gap(now: float | None = None) -> dict[str, Any] | None:
    """The silence at the end of the record, if there is one. For the watchman."""
    last = store.last_beat()
    if not last:
        return None
    cause = cause_of_gap(last, now)
    if cause is None:
        return None
    now = now if now is not None else time.time()
    return {"before": last["ts"], "after": now, "gap": now - last["ts"], "cause": cause}


def silences(min_gap: float = GAP_THRESHOLD, since: float = 0.0) -> list[dict[str, Any]]:
    """Every absence in the record, named. The past, told honestly."""
    rows = store.beats(since=since)
    out: list[dict[str, Any]] = []
    for a, b in zip(rows, rows[1:]):
        gap = b["ts"] - a["ts"]
        if gap < min_gap:
            continue
        out.append(
            {
                "before": a["ts"],
                "after": b["ts"],
                "gap": gap,
                "cause": classify(
                    gap,
                    a.get("uptime"),
                    b.get("uptime"),
                    a.get("mono"),
                    b.get("mono"),
                    a.get("boot"),
                    b.get("boot"),
                ),
            }
        )
    return out
