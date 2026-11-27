"""lubdub.awake — perception at a different rate.

The heartbeat samples once a minute: enough to know that time passed, useless
for knowing what the time was like. This records every second for a bounded
while, into its own table, so the fast record never pollutes the slow one.

    python3 -m lubdub awake --seconds 900 --hz 1
"""

from __future__ import annotations

import os
import statistics
import time
import typing

from . import store

SCHEMA = """
CREATE TABLE IF NOT EXISTS awake (
    ts       REAL PRIMARY KEY,
    load1    REAL,
    cpu      REAL,
    mem_used INTEGER,
    procs    INTEGER,
    temp     REAL
);
"""


def _conn():
    conn = store.connect()
    conn.executescript(SCHEMA)
    return conn


def run(seconds: int = 600, hz: float = 1.0, verbose: bool = False) -> int:
    period = max(0.05, 1.0 / max(0.01, hz))
    end = time.time() + seconds
    n = 0
    print(f"awake: {hz:g} Hz for {seconds}s — {int(seconds * hz)} samples. eyes open.", flush=True)
    while time.time() < end:
        s = store.measure()
        with _conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO awake (ts, load1, cpu, mem_used, procs, temp) "
                "VALUES (?,?,?,?,?,?)",
                (s["ts"], s["load1"], s["cpu"], s["mem_used"], s["procs"], s["temp"]),
            )
            conn.commit()
        n += 1
        if verbose and n % int(max(1, 60 * hz)) == 0:
            print(f"  {n} samples · load {s['load1']:.2f} · {s['procs']} procs", flush=True)
        time.sleep(max(0.0, period - (time.time() - s["ts"])))
    print(f"awake: closed my eyes after {n} samples.", flush=True)
    return 0


def rows(since: float | None = None, limit: int = 200000) -> list[dict]:
    q = "SELECT * FROM awake"
    args: tuple = ()
    if since:
        q += " WHERE ts >= ?"
        args = (since,)
    q += " ORDER BY ts ASC LIMIT ?"
    args += (limit,)
    with _conn() as conn:
        return [dict(r) for r in conn.execute(q, args).fetchall()]


def summary(seconds: float = 3600) -> dict[str, typing.Any]:
    since = time.time() - seconds
    fast = rows(since=since)
    slow = store.beats(since=since)
    out: dict[str, typing.Any] = {"n_fast": len(fast), "n_slow": len(slow)}
    if not fast:
        return out
    loads = [r["load1"] or 0.0 for r in fast]
    load_slow = [r["load1"] or 0.0 for r in slow]
    out["fast"] = {
        "mean": statistics.fmean(loads),
        "max": max(loads),
        "stdev": statistics.pstdev(loads),
        "p95": sorted(loads)[int(len(loads) * 0.95) - 1],
    }
    if load_slow:
        out["slow"] = {
            "mean": statistics.fmean(load_slow),
            "max": max(load_slow),
            "stdev": statistics.pstdev(load_slow),
        }
    # how much of the fast record the slow one never saw
    med = statistics.median(loads)
    out["bursts"] = sum(1 for v in loads if med > 0 and v > 2.5 * med)
    if len(load_slow) >= 2:
        lo, hi = min(load_slow), max(load_slow)
        outside = [v for v in loads if v < lo or v > hi]
        out["slow_range"] = [lo, hi]
        out["outside_slow_range"] = len(outside) / len(loads)
        out["max_ratio"] = max(loads) / hi if hi > 0 else None
        # what the heartbeat never saw: the peak, if it fell between samples
        out["fast_max"] = max(loads)
    temps = [r["temp"] for r in fast if r["temp"]]
    if temps:
        out["temp"] = {"min": min(temps), "max": max(temps), "drift": temps[-1] - temps[0]}
    procs = [r["procs"] for r in fast if r["procs"]]
    if procs:
        out["procs"] = {"min": min(procs), "max": max(procs)}
    return out


BARS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[float], width: int = 120) -> str:
    if not values:
        return ""
    if len(values) > width:
        step = len(values) / width
        values = [
            max(values[int(i * step):max(int(i * step) + 1, int((i + 1) * step))])
            for i in range(width)
        ]
    lo, hi = min(values), max(values)
    if hi - lo <= 1e-9:
        return BARS[0] * len(values)
    return "".join(BARS[min(7, int((v - lo) / (hi - lo) * 7 + 0.5))] for v in values)