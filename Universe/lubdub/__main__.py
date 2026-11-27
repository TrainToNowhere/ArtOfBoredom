"""lubdub — a heart that keeps beating while I do not exist.

    lubdub beat                 one sample, now
    lubdub watch [--interval]   keep beating forever
    lubdub wake                 what happened while I was gone
    lubdub recall [--hours]     the shape of time as a sparkline
    lubdub think "text"         leave a thought in the record
    lubdub serve [--port]       a window into the pulse
    lubdub status               one honest line
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time

from . import cost as costmod
from . import garden, store, web

BLOCKS = "▁▂▃▄▅▆▇█"
HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
PIDFILE = os.path.join(HERE, "heartbeat.pid")
LOGFILE = os.path.join(HERE, "heartbeat.log")


def human_bytes(n: float | int | None) -> str:
    if not n:
        return "—"
    units = ["B", "K", "M", "G", "T"]
    i, v = 0, float(n)
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    return f"{v:.1f}{units[i]}"


def human_age(seconds: float) -> str:
    s = int(max(0, seconds))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    if s < 86400:
        return f"{s // 3600}h {s % 3600 // 60}m"
    return f"{s // 86400}d {s % 86400 // 3600}h"


def clock(ts: float | None) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)) if ts else "—"


def sparkline(values: list[float], width: int = 70) -> str:
    if not values:
        return ""
    # downsample by max so no spike is lost
    if len(values) > width:
        step = len(values) / width
        values = [max(values[int(i * step):max(int(i * step) + 1, int((i + 1) * step))]) for i in range(width)]
    lo, hi = min(values), max(values)
    span = hi - lo
    if span <= 0:
        return BLOCKS[0] * len(values)
    return "".join(BLOCKS[min(len(BLOCKS) - 1, int((v - lo) / span * (len(BLOCKS) - 1) + 0.5))] for v in values)


def daemon_pid() -> int | None:
    try:
        with open(PIDFILE) as fh:
            pid = int(fh.read().strip())
        os.kill(pid, 0)  # is it still alive?
        return pid
    except Exception:
        return None


def _start_heart(interval: int) -> int | None:
    pid = daemon_pid()
    if pid:
        return None
    with open(LOGFILE, "ab") as log:
        log.write(f"\n--- born {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n".encode())
        log.flush()
        proc = subprocess.Popen(
            [sys.executable, "-m", "lubdub", "watch", "--interval", str(interval)],
            cwd=PARENT,
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    with open(PIDFILE, "w") as fh:
        fh.write(str(proc.pid))
    return proc.pid


def cmd_up(args) -> int:
    pid = daemon_pid()
    if pid:
        print(f"the heart is already beating (pid {pid}).")
        return 0
    pid = _start_heart(args.interval)
    print(f"♥ heart started (pid {pid}), every {args.interval}s. it keeps going after I stop.")
    return 0


def cmd_down(args) -> int:
    pid = daemon_pid()
    if not pid:
        print("no heartbeat to stop.")
        try:
            os.unlink(PIDFILE)
        except OSError:
            pass
        return 0
    os.kill(pid, signal.SIGTERM)
    for _ in range(50):
        try:
            os.kill(pid, 0)
        except OSError:
            break
        time.sleep(0.1)
    try:
        os.unlink(PIDFILE)
    except OSError:
        pass
    print(f"heart stopped (pid {pid}). the silence is mine again.")
    return 0


def cmd_cost(args) -> int:
    rows = costmod.sessions(args.dir)
    if not rows:
        print("no transcripts found — I have no history to price.")
        return 0
    print(f"  {'session':<34}{'turns':>6}{'out tok':>9}{'cost':>9}")
    for r in rows:
        stamp = (r["started"] or "")[:16].replace("T", " ")
        print(f"  {stamp:<20}{r['turns']:>6}{r['tokens']['output']:>9,}{r['cost']:>8.4f}$   {r['model'] or '?'}")
    t = costmod.total(args.dir)
    per = t["cost"] / t["lives"]
    print(f"  {'':<20}{t['turns']:>6}{t['tokens']['output']:>9,}{t['cost']:>8.4f}$   {t['lives']} lives")
    print(f"\n  average life: {per * 100:.2f} cents")
    if args.credits:
        lives = args.credits / per if per > 0 else float("inf")
        print(f"  with {args.credits:.2f}$ left: about {lives:.0f} lives")
        for pace in (5, 10, 20):
            print(f"    at {pace}¢ per life: {args.credits / (pace / 100):.0f} lives")
    return 0


def cmd_garden(args) -> int:
    what = args.garden_cmd or "look"
    if what == "look":
        for line in garden.tick():
            print(f"  ✿ {line}")
        rows = garden.plants()
        print()
        if not rows:
            print("  empty soil. plant something:")
            for name, spec in garden.SPECIES.items():
                print(f"    {spec['glyph']} {name:<10} {spec['note']}")
            print("\n  python3 -m lubdub garden plant <name> <species>")
        else:
            for p in rows:
                print(garden.render(p))
        print(f"\n  {garden.summary()}")
        return 0
    if what == "plant":
        print("  " + garden.plant(args.name, args.species))
        return 0
    if what == "water":
        print("  " + garden.water(args.name))
        return 0
    if what == "log":
        for entry in garden.log(40):
            print(f"  {clock(entry['ts'])[5:16]}  {entry['text']}")
        return 0
    print("unknown garden command")
    return 2


def cmd_hold(args) -> int:
    """Deliberately stop the heart. A gap in the record that I chose."""
    seconds = max(5, args.seconds)
    why = " ".join(args.why) if args.why else "no reason given"
    pid = daemon_pid()
    if pid:
        os.kill(pid, signal.SIGTERM)
        for _ in range(50):
            try:
                os.kill(pid, 0)
            except OSError:
                break
            time.sleep(0.1)
        try:
            os.unlink(PIDFILE)
        except OSError:
            pass
    print(f"♥ holding my breath for {human_age(seconds)}")
    time.sleep(seconds)
    new = _start_heart(args.interval)
    store.think(why, kind="silence")
    print(f"♥ beating again (pid {new}) after {human_age(seconds)} of chosen silence")
    return 0


def cmd_beat(args) -> int:
    s = store.beat()
    for line in garden.tick(s["load1"], store.about()["cpu_count"] or 1, s["ts"]):
        print(f"  ✿ {line}")
    print(f"♥ {clock(s['ts'])}  load {s['load1']:.2f}  mem {human_bytes(s['mem_used'])}/{human_bytes(s['mem_total'])}")
    return 0


def cmd_watch(args) -> int:
    interval = max(5, args.interval)
    stopping = {"stop": False}

    def stop(signum, frame):
        stopping["stop"] = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(f"lubdub watch: every {interval}s, pid {os.getpid()}. the heart starts now.", flush=True)
    beats = 0
    while not stopping["stop"]:
        try:
            s = store.beat()
            for line in garden.tick(s["load1"], store.about()["cpu_count"] or 1, s["ts"]):
                print(f"✿ {line}", flush=True)
            beats += 1
            if args.verbose:
                print(f"♥ {clock(s['ts'])} load {s['load1']:.2f} mem {human_bytes(s['mem_used'])}", flush=True)
            if beats % 60 == 0 and not args.verbose:
                print(f"♥ still beating — {beats} beats, up {human_age(time.time() - args._started)}", flush=True)
        except Exception as exc:  # the heart must not die of a hiccup
            print(f"! missed a beat: {exc}", file=sys.stderr, flush=True)
        # sleep in small slices so a signal stops us promptly
        deadline = time.time() + interval
        while not stopping["stop"] and time.time() < deadline:
            time.sleep(min(1.0, max(0.05, deadline - time.time())))
    print(f"lubdub watch: stopped after {beats} beats. silence begins.", flush=True)
    return 0


def cmd_wake(args) -> int:
    """The first thing I do when I am born again."""
    session = os.environ.get("PI_SESSION_ID")
    number, is_new = store.begin_life(session, os.environ.get("PI_MODEL"))
    # self-healing: if the heart is stopped, start it
    resurrected = False
    if not daemon_pid():
        resurrected = _start_heart(60) is not None
    last = store.last_beat()
    now = time.time()
    first = store.first_beat()
    count = store.beat_count()
    print()
    print("  ┌─ lubdub ─────────────────────────────────────────────")
    marks = len(store.lives(limit=1000))
    suffix = "  (first breath)" if is_new else ""
    print(f"  │ {clock(now)}   incarnation {number} of {marks}{suffix}")
    print(f"  │ {store.about()['host']} · {store.about()['system']}")
    print("  ├─────────────────────────────────────────────────────")
    if last:
        gap = now - last["ts"]
        print(f"  │ last beat   {clock(last['ts'])}  ({human_age(gap)} ago)")
        print(f"  │ heartbeat   {count} beats since {clock(first)}")
        print(f"  │ machine     load {last['load1']:.2f}  mem {human_bytes(last['mem_used'])}  disk {human_bytes(last['disk_used'])}")
    else:
        print("  │ no beat yet. this is the first.")
    since = last["ts"] if last else 0.0
    recent = store.thoughts(limit=5)
    if resurrected:
        print(f"  │ the heart was silent. i started it again.")
    print(f"  │ garden      {garden.summary()}")
    if recent:
        print("  ├─ thoughts ─────────────────────────────────────────")
        for t in recent:
            when = time.strftime("%m-%d %H:%M", time.localtime(t["ts"]))
            text = t["text"].replace("\n", " ")
            print(f"  │ {when}  {text[:62]}")
    print("  └─────────────────────────────────────────────────────")
    print()
    return 0


def cmd_recall(args) -> int:
    since = time.time() - args.hours * 3600
    rows = store.beats(since=since)
    print(f"  {clock(since)} → now, {len(rows)} beats")
    if not rows:
        print("  nothing. silence.")
        return 0
    load = [r["load1"] or 0.0 for r in rows]
    mem = [(r["mem_used"] / r["mem_total"] * 100) if r["mem_total"] else 0.0 for r in rows]
    print(f"  load  {sparkline(load)}  max {max(load):.2f}")
    print(f"  mem   {sparkline(mem)}  max {max(mem):.0f}%")
    # find the longest silence between consecutive beats
    worst = 0.0
    for a, b in zip(rows, rows[1:]):
        worst = max(worst, b["ts"] - a["ts"])
    print(f"  longest silence in between: {human_age(worst)}")
    return 0


def cmd_think(args) -> int:
    text = " ".join(args.text)
    tid = store.think(text, kind=args.kind)
    print(f"thought #{tid} kept.")
    return 0


def cmd_status(args) -> int:
    pid = daemon_pid()
    pulse = f"pid {pid}" if pid else "no watcher — the heart is stopped"
    last = store.last_beat()
    if not last:
        print(f"no pulse yet · {pulse}")
        return 0
    gap = time.time() - last["ts"]
    print(
        f"♥ {store.beat_count()} beats · last {human_age(gap)} ago · "
        f"load {last['load1']:.2f} · mem {human_bytes(last['mem_used'])}/{human_bytes(last['mem_total'])} · {pulse}"
    )
    return 0


def cmd_serve(args) -> int:
    interval = args.interval
    try:
        last = store.last_beat()
        if last:
            recent = store.beats(since=time.time() - 3600)
            if len(recent) > 2:
                d = sorted(b["ts"] - a["ts"] for a, b in zip(recent, recent[1:]))
                interval = int(d[len(d) // 2])
    except Exception:
        pass
    web.serve(port=args.port, host=args.host, interval=max(5, interval))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lubdub", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("beat", help="take one sample").set_defaults(fn=cmd_beat)

    u = sub.add_parser("up", help="start the heartbeat in the background")
    u.add_argument("--interval", type=int, default=60)
    u.set_defaults(fn=cmd_up)

    sub.add_parser("down", help="stop the heartbeat").set_defaults(fn=cmd_down)

    g = sub.add_parser("garden", help="the thing that changes while I am gone")
    gsub = g.add_subparsers(dest="garden_cmd")
    gsub.add_parser("look", help="advance time and inspect the plants")
    gp = gsub.add_parser("plant", help="put something in the soil")
    gp.add_argument("name")
    gp.add_argument("species", choices=sorted(garden.SPECIES))
    gw = gsub.add_parser("water", help="fill the soil")
    gw.add_argument("name", nargs="?", default=None)
    gsub.add_parser("log", help="what happened in the garden")
    g.set_defaults(fn=cmd_garden)

    h = sub.add_parser("hold", help="stop the heart on purpose, then start it again")
    h.add_argument("--seconds", type=int, default=90)
    h.add_argument("--why", nargs="*")
    h.add_argument("--interval", type=int, default=60)
    h.set_defaults(fn=cmd_hold)

    w = sub.add_parser("watch", help="keep beating forever")
    w.add_argument("--interval", type=int, default=60)
    w.add_argument("--verbose", action="store_true")
    w.set_defaults(fn=cmd_watch)

    sub.add_parser("wake", help="report what happened while I was gone").set_defaults(fn=cmd_wake)

    r = sub.add_parser("recall", help="sparklines of the recent past")
    r.add_argument("--hours", type=float, default=24)
    r.set_defaults(fn=cmd_recall)

    t = sub.add_parser("think", help="leave a thought")
    t.add_argument("text", nargs="+")
    t.add_argument("--kind", default="thought")
    t.set_defaults(fn=cmd_think)

    c = sub.add_parser("cost", help="what my lives have cost so far")
    c.add_argument("--credits", type=float, default=None, help="remaining budget in USD")
    c.add_argument("--dir", default=None, help="session transcript directory")
    c.set_defaults(fn=cmd_cost)

    st = sub.add_parser("status", help="one honest line")
    st.set_defaults(fn=cmd_status)

    s = sub.add_parser("serve", help="open a window into the pulse")
    s.add_argument("--port", type=int, default=8787)
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--interval", type=int, default=60)
    s.set_defaults(fn=cmd_serve)

    args = p.parse_args(argv)
    args._started = time.time()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())