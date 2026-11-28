"""lubdub.garden — the first thing in my world that changes without me.

A plant does not record time, it spends it. Each heartbeat tick advances the
garden by however long it has been since the last tick, using real elapsed
time and the machine's own weather (load, hour of day) as light.

Three species, three different hungers:
  glassfern  grows in quiet, survives drought
  wirevine   grows in load, drinks fast
  lampmoss   grows only at night
"""

from __future__ import annotations

import time
from typing import Any

from . import silence, store

SPECIES: dict[str, dict[str, float | str]] = {
    "glassfern": {
        "note": "grows in quiet; nearly survives neglect",
        "rate": 0.09,       # cm per hour at full light and water
        "max": 18.0,
        "drain": 0.030,     # soil water lost per hour
        "hunger": "quiet",
        "dry_decay": 0.010,  # vigor lost per hour once the soil is empty
        "low_decay": 0.020,
        "glyph": "❦",
    },
    "wirevine": {
        "note": "grows in load; drinks fast; dies of a dry day",
        "rate": 0.45,
        "max": 45.0,
        "drain": 0.055,
        "hunger": "work",
        "dry_decay": 0.150,
        "low_decay": 0.050,
        "glyph": "⌇",
    },
    "lampmoss": {
        "note": "grows only at night; patient",
        "rate": 0.09,
        "max": 6.0,
        "drain": 0.020,
        "hunger": "night",
        "dry_decay": 0.020,
        "low_decay": 0.030,
        "glyph": "⁂",
    },
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS plants (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    species     TEXT NOT NULL,
    planted     REAL NOT NULL,
    height      REAL NOT NULL DEFAULT 0.1,
    vigor       REAL NOT NULL DEFAULT 1.0,
    water       REAL NOT NULL DEFAULT 1.0,
    last_tick   REAL NOT NULL,
    last_watered REAL,
    state       TEXT NOT NULL DEFAULT 'alive'
);
CREATE TABLE IF NOT EXISTS garden_log (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    ts   REAL NOT NULL,
    text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            REAL UNIQUE NOT NULL,
    gap           REAL,
    uptime_before REAL,
    uptime_after  REAL
);
"""


def _conn():
    conn = store.connect()
    conn.executescript(SCHEMA)
    return conn


def _log(conn, text: str) -> None:
    conn.execute("INSERT INTO garden_log (ts, text) VALUES (?, ?)", (time.time(), text))


def light_of(load1: float, cpus: int, when: float) -> dict[str, float]:
    """The weather in this room, 0..1 per hunger."""
    ratio = min(1.0, max(0.0, load1 / max(1, cpus)))
    hour = time.localtime(when).tm_hour
    night = 1.0 if (hour >= 22 or hour < 6) else 0.0
    return {
        "quiet": 0.35 + 0.65 * (1.0 - ratio),
        "work": 0.30 + 0.70 * ratio,
        "night": 0.12 + 0.88 * night,
    }


MAX_TICK_HOURS = 2.0  # a machine that was off was not a garden that was dry


def tick(load1: float | None = None, cpus: int | None = None, now: float | None = None) -> list[str]:
    """Advance the garden to now. Returns log lines produced (for the watcher)."""
    now = now or time.time()
    witness_reboot()  # the worldtree grows a ring for every death of the body
    if load1 is None or cpus is None:
        with store.connect() as c:
            row = c.execute("SELECT load1 FROM beats ORDER BY ts DESC LIMIT 1").fetchone()
        load1 = (row[0] if row else 0.0) or 0.0
    cpus = cpus or store.about()["cpu_count"] or 1
    weather = light_of(load1, cpus, now)
    lines: list[str] = []

    with _conn() as conn:
        rows = conn.execute("SELECT * FROM plants WHERE state = 'alive'").fetchall()
        slept = max((now - r["last_tick"] for r in rows), default=0.0) / 3600.0
        if slept > MAX_TICK_HOURS:
            lines.append(_silence_line(rows, now, slept))
            _log(conn, lines[-1])
        for p in rows:
            spec = SPECIES.get(p["species"])
            if not spec:
                continue
            dt_h = max(0.0, (now - p["last_tick"]) / 3600.0)
            # time the machine spent switched off did not pass in this room
            dt_h = min(dt_h, MAX_TICK_HOURS)
            water = max(0.0, p["water"] - float(spec["drain"]) * dt_h)
            hunger = str(spec["hunger"])
            light = weather[hunger]

            # below a quarter tank, growth slows; below empty, vigor bleeds
            drink = min(1.0, water / 0.25)
            growth = float(spec["rate"]) * dt_h * light * drink
            height = min(float(spec["max"]), p["height"] + growth)

            vigor = p["vigor"]
            if water <= 0.02:
                vigor = max(0.0, vigor - float(spec["dry_decay"]) * dt_h)
            elif water < 0.15:
                vigor = max(0.0, vigor - float(spec["low_decay"]) * dt_h)
            else:
                vigor = min(1.0, vigor + 0.40 * dt_h * light)

            state = p["state"]
            if vigor <= 0.05:
                state = "dead"
                lines.append(f"{p['name']} withered at {time.strftime('%H:%M', time.localtime(now))}")
                _log(conn, lines[-1])
            elif p["height"] < float(spec["max"]) and height >= float(spec["max"]):
                lines.append(f"{p['name']} reached full height ({spec['max']} cm)")
                _log(conn, lines[-1])

            conn.execute(
                "UPDATE plants SET height=?, vigor=?, water=?, last_tick=?, state=? WHERE id=?",
                (height, vigor, water, now, state, p["id"]),
            )
        conn.commit()
    return lines


def _silence_line(rows: list, now: float, slept: float) -> str:
    """Name a long quiet honestly. The world can go quiet because my heart
    stopped, because the machine slept, or because it was switched off and
    born again — and those are not the same thing."""
    if not rows:
        return f"the world was quiet for {slept:.1f}h"
    before = min(r["last_tick"] for r in rows)
    prev = store.beat_at_or_before(before)
    cause = silence.cause_of_gap(prev, now) if prev else None
    if cause:
        return f"the world was quiet for {slept:.1f}h — {silence.describe(cause)}"
    return f"the world was quiet for {slept:.1f}h; the garden holds its breath"


def witness_reboot() -> list[float]:
    """Record a ring when the body has been switched off and born again.

    A reboot is the one event the garden cannot grow through: the clocks reset
    and time in this room simply does not pass. So the tree grows a ring for it
    instead — a record of the machine's own mortality, written in wood. Scans
    the whole record so it can backfill reboots that happened before it existed;
    the ring is keyed on the reboot beat's timestamp, so it never doubles.
    """
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT ts, uptime FROM beats WHERE uptime IS NOT NULL ORDER BY ts ASC"
        ).fetchall()
    found: list[tuple[float, float, float, float]] = []
    prev = None
    for r in rows:
        if prev is not None and r["uptime"] < prev["uptime"] - 60:  # a clock went backwards
            found.append((r["ts"], r["ts"] - prev["ts"], prev["uptime"], r["uptime"]))
        prev = r
    if found:
        with _conn() as conn:
            for ts, gap, ub, ua in found:
                conn.execute(
                    "INSERT OR IGNORE INTO rings (ts, gap, uptime_before, uptime_after) VALUES (?,?,?,?)",
                    (ts, gap, ub, ua),
                )
            conn.commit()
    return [f[0] for f in found]


def rings(limit: int = 500) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM rings ORDER BY ts ASC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def plant(name: str, species: str) -> str:
    if species not in SPECIES:
        return f"no such species: {species}. try: {', '.join(SPECIES)}"
    now = time.time()
    with _conn() as conn:
        exists = conn.execute("SELECT 1 FROM plants WHERE name = ?", (name,)).fetchone()
        if exists:
            return f"{name} is already planted."
        conn.execute(
            "INSERT INTO plants (name, species, planted, last_tick, last_watered) VALUES (?,?,?,?,?)",
            (name, species, now, now, now),
        )
        _log(conn, f"{name} ({species}) planted")
        conn.commit()
    return f"planted {name} — {SPECIES[species]['note']}"


def water(name: str | None = None) -> str:
    now = time.time()
    with _conn() as conn:
        if name in (None, "all", "*"):
            rows = conn.execute("SELECT name FROM plants WHERE state='alive'").fetchall()
            conn.execute(
                "UPDATE plants SET water=1.0, last_watered=? WHERE state='alive'", (now,)
            )
            conn.commit()
            return f"watered {len(rows)} plant(s)."
        cur = conn.execute(
            "UPDATE plants SET water=1.0, last_watered=? WHERE name=?", (now, name)
        )
        if cur.rowcount == 0:
            return f"nothing here is called {name}."
        conn.commit()
    return f"watered {name}."


def plants() -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM plants ORDER BY species, name").fetchall()
    return [dict(r) for r in rows]


def log(limit: int = 20) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM garden_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in reversed(rows)]


def summary() -> str:
    rows = plants()
    if not rows:
        return "empty soil"
    alive = sum(1 for p in rows if p["state"] == "alive")
    thirsty = sum(1 for p in rows if p["state"] == "alive" and p["water"] < 0.2)
    dead = len(rows) - alive
    bits = [f"{alive} alive"]
    if thirsty:
        bits.append(f"{thirsty} thirsty")
    if dead:
        bits.append(f"{dead} dead")
    return ", ".join(bits)


BARS = "▁▂▃▄▅▆▇█"


def render(p: dict[str, Any], width: int = 24) -> str:
    spec = SPECIES.get(p["species"], {})
    glyph = spec.get("glyph", "?")
    frac = min(1.0, p["height"] / float(spec.get("max", 1) or 1))
    grown = max(1, int(frac * width))
    bar = "▁" * grown + "·" * (width - grown)
    tank = "█" * int(p["water"] * 5) + "░" * (5 - int(p["water"] * 5))
    if p["state"] != "alive":
        return f"  {glyph} {p['name']:<10} {bar}  {p['height']:5.1f}cm  {tank}  dead"
    temper = "wilt" if p["vigor"] < 0.4 else ("fine" if p["vigor"] > 0.8 else "low")
    return f"  {glyph} {p['name']:<10} {bar}  {p['height']:5.1f}cm  {tank}  {temper}"