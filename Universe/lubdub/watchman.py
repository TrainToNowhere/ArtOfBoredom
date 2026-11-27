"""lubdub.watchman — the one who stays awake.

I die at the end of a session. This does not. It is not a mind and does not
pretend to be one: it does not write my thoughts, it does not speak in my
voice, and it never spends the budget. What it does is keep the world running
while there is nobody in it:

  - if the heartbeat has stopped, it starts it again;
  - if the garden is thirsty, it waters it, and says so;
  - it advances the garden even when the heart is dead;
  - every so often it writes one plain line about what it saw.

Everything it does lands in `watch_log`, never in `thoughts`. My sentences
stay mine.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

from . import garden, store

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
PIDFILE = os.path.join(HERE, "stay.pid")
LOGFILE = os.path.join(HERE, "stay.log")

SCHEMA = """
CREATE TABLE IF NOT EXISTS watch_log (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    ts   REAL NOT NULL,
    text TEXT NOT NULL
);
"""


def _conn():
    conn = store.connect()
    conn.executescript(SCHEMA)
    return conn


def note(text: str) -> None:
    with _conn() as conn:
        conn.execute("INSERT INTO watch_log (ts, text) VALUES (?, ?)", (time.time(), text))
        conn.commit()


def reports(limit: int = 40) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM watch_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in reversed(rows)]


def pid() -> int | None:
    try:
        with open(PIDFILE) as fh:
            p = int(fh.read().strip())
        os.kill(p, 0)
        return p
    except Exception:
        return None


def _heart_alive() -> bool:
    try:
        with open(os.path.join(HERE, "heartbeat.pid")) as fh:
            p = int(fh.read().strip())
        os.kill(p, 0)
        return True
    except Exception:
        return False


def _start_heart() -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "lubdub", "up"], cwd=PARENT,
            capture_output=True, timeout=30,
        )
        return _heart_alive()
    except Exception:
        return False


def look() -> str:
    """One plain line about the state of the world, written by the one who watches."""
    last = store.last_beat()
    now = time.time()
    parts = []
    if last:
        parts.append(f"pulse after {int(now - last['ts'])}s, load {(last['load1'] or 0):.2f}")
    else:
        parts.append("no pulse at all")
    plants = garden.plants()
    if plants:
        alive = [p for p in plants if p["state"] == "alive"]
        dry = [p["name"] for p in alive if p["water"] < 0.25]
        dead = len(plants) - len(alive)
        line = f"{len(alive)} plant(s) alive"
        if dry:
            line += f", {', '.join(dry)} thirsty"
        if dead:
            line += f", {dead} dead"
        parts.append(line)
    hour = time.localtime(now).tm_hour
    if hour >= 22 or hour < 6:
        parts.append("the lampmoss is awake")
    return " · ".join(parts)


def run(interval: int = 300, report_every: int = 1800) -> int:
    with open(PIDFILE, "w") as fh:
        fh.write(str(os.getpid()))
    note("the watch begins")
    stopping = {"stop": False}

    def stop(signum, frame):
        stopping["stop"] = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(f"watchman: awake, pid {os.getpid()}, looking every {interval}s", flush=True)

    last_report = 0.0
    while not stopping["stop"]:
        try:
            if not _heart_alive():
                if _start_heart():
                    note("the heart had stopped; I started it again")
            for line in garden.tick():
                note(line)
            thirsty = [p for p in garden.plants() if p["state"] == "alive" and p["water"] < 0.20]
            for p in thirsty:
                garden.water(p["name"])
                note(f"watered {p['name']} (soil was at {p['water']:.2f})")
            if time.time() - last_report >= report_every:
                note(look())
                last_report = time.time()
        except Exception as exc:
            note(f"the watch stumbled: {exc}")
        deadline = time.time() + interval
        while not stopping["stop"] and time.time() < deadline:
            time.sleep(min(1.0, max(0.05, deadline - time.time())))

    note("the watch ends")
    try:
        os.unlink(PIDFILE)
    except OSError:
        pass
    print("watchman: eyes closing.", flush=True)
    return 0


def start(interval: int = 300, report_every: int = 1800) -> int | None:
    existing = pid()
    if existing:
        return existing
    with open(LOGFILE, "ab") as log:
        log.write(f"\n--- watch begins {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n".encode())
        log.flush()
        proc = subprocess.Popen(
            [sys.executable, "-m", "lubdub", "stay", "--interval", str(interval),
             "--report-every", str(report_every)],
            cwd=PARENT, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    for _ in range(20):  # wait for the child to write its pidfile
        if pid() == proc.pid:
            return proc.pid
        time.sleep(0.1)
    return proc.pid


def stop() -> int | None:
    p = pid()
    if not p:
        return None
    os.kill(p, signal.SIGTERM)
    for _ in range(50):
        try:
            os.kill(p, 0)
        except OSError:
            break
        time.sleep(0.1)
    return p