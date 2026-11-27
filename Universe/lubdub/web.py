"""lubdub.web — a window into the pulse.

Nothing here writes to the world. It only listens to the heart and draws it.
"""

from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import garden, store

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>lubdub</title>
<style>
  :root {
    --bg: #08090b;
    --panel: #0d0f12;
    --line: #171b21;
    --ink: #c9d1d9;
    --dim: #5b6472;
    --accent: #ff4d3d;
    --accent-soft: rgba(255, 77, 61, 0.18);
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; }
  body {
    background: var(--bg);
    color: var(--ink);
    font: 13px/1.55 ui-monospace, "JetBrains Mono", "SF Mono", Menlo, Consolas, monospace;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
  }
  body::before {
    content: "";
    position: fixed; inset: 0;
    background-image:
      linear-gradient(var(--line) 1px, transparent 1px),
      linear-gradient(90deg, var(--line) 1px, transparent 1px);
    background-size: 48px 48px;
    opacity: .35;
    mask-image: radial-gradient(ellipse at 50% 0%, #000 10%, transparent 75%);
    pointer-events: none;
  }
  main { position: relative; max-width: 1180px; margin: 0 auto; padding: 42px 28px 70px; }

  header { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
  .mark { display: flex; align-items: center; gap: 10px; }
  .dot {
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 0 0 var(--accent-soft);
    animation: beat var(--bpm, 1.1s) infinite;
  }
  @keyframes beat {
    0%   { transform: scale(1);   box-shadow: 0 0 0 0 var(--accent-soft); }
    12%  { transform: scale(1.5); box-shadow: 0 0 0 9px rgba(255,77,61,0); }
    24%  { transform: scale(1); }
    38%  { transform: scale(1.28); box-shadow: 0 0 0 6px rgba(255,77,61,0); }
    60%  { transform: scale(1); }
    100% { transform: scale(1); }
  }
  h1 { font-size: 15px; letter-spacing: .42em; font-weight: 600; margin: 0; text-transform: lowercase; }
  .sub { color: var(--dim); letter-spacing: .04em; }
  .silence { margin-left: auto; color: var(--dim); }
  .silence b { color: var(--ink); font-weight: 500; }
  .silence.beating b { color: var(--accent); }

  .trace-wrap {
    margin: 34px 0 0;
    border: 1px solid var(--line);
    border-radius: 3px;
    background: linear-gradient(180deg, #0b0d10, #08090b);
    padding: 8px;
    position: relative;
    overflow: hidden;
  }
  canvas { display: block; width: 100%; height: 230px; }
  .legend {
    position: absolute; top: 12px; right: 16px;
    font-size: 10px; letter-spacing: .18em; text-transform: uppercase;
    color: var(--dim); text-align: right; line-height: 1.7;
  }
  .legend i { font-style: normal; color: var(--accent); }

  .strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1px; margin-top: 28px;
           border: 1px solid var(--line); background: var(--line); }
  .cell { background: var(--panel); padding: 14px 16px; }
  .cell .k { font-size: 10px; letter-spacing: .16em; text-transform: uppercase; color: var(--dim); }
  .cell .v { font-size: 20px; margin-top: 6px; color: var(--ink); font-variant-numeric: tabular-nums; }
  .cell .v small { font-size: 11px; color: var(--dim); margin-left: 4px; }
  .bar { height: 2px; background: #1a1f27; margin-top: 9px; position: relative; overflow: hidden; }
  .bar span { position: absolute; inset: 0 auto 0 0; background: var(--accent); opacity: .75; transition: width .6s ease; }

  .garden { margin-top: 38px; }
  .garden h2 .gs { color: var(--dim); letter-spacing: .04em; text-transform: none; margin-left: 8px; }
  .plant { display: grid; grid-template-columns: 18px 128px 1fr 76px 92px 64px; gap: 14px; align-items: center;
           padding: 8px 0; border-bottom: 1px solid var(--line); }
  .plant:first-child { border-top: 1px solid var(--line); }
  .plant .glyph { color: var(--accent); text-align: center; }
  .plant .name { letter-spacing: .02em; }
  .plant .name small { display: block; color: var(--dim); font-size: 10px; letter-spacing: .04em; }
  .plant .stem { height: 6px; background: #151a21; position: relative; overflow: hidden; }
  .plant .stem i { position: absolute; inset: 0 auto 0 0; background: linear-gradient(90deg, rgba(255,77,61,.35), var(--accent)); }
  .plant .cm { text-align: right; font-variant-numeric: tabular-nums; color: var(--ink); }
  .plant .cm small { color: var(--dim); }
  .plant .tank { height: 6px; background: #151a21; position: relative; overflow: hidden; }
  .plant .tank i { position: absolute; inset: 0 auto 0 0; background: #4a6f8a; }
  .plant .state { text-align: right; color: var(--dim); }
  .plant .state.warn { color: #c9a227; }
  .plant .state.dead { color: #6b2d2d; }
  .empty { color: #3f4753; padding: 12px 0; }
  @media (max-width: 800px) { .plant { grid-template-columns: 18px 108px 1fr 62px; } .plant .tank, .plant .state { display: none; } }

  .lower { display: grid; grid-template-columns: 1.15fr .85fr; gap: 26px; margin-top: 34px; }
  @media (max-width: 800px) { .lower { grid-template-columns: 1fr; } }
  h2 { font-size: 10px; letter-spacing: .22em; text-transform: uppercase; color: var(--dim); font-weight: 600; margin: 0 0 14px; }
  .thoughts { list-style: none; margin: 0; padding: 0; }
  .thoughts li { display: grid; grid-template-columns: 62px 1fr; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--line); }
  .thoughts li:first-child { border-top: 1px solid var(--line); }
  .thoughts li.quiet { grid-template-columns: 1fr; }
  .thoughts .t { color: var(--dim); font-size: 11px; font-variant-numeric: tabular-nums; padding-top: 2px; }
  .thoughts .x { white-space: pre-wrap; }
  .thoughts .kind { color: var(--accent); }
  .facts { color: var(--dim); }
  .facts dl { display: grid; grid-template-columns: auto 1fr; gap: 6px 16px; margin: 0; }
  .facts dt { color: #3f4753; }
  .facts dd { margin: 0; color: var(--ink); }
  .quiet { color: #3f4753; }
</style>
</head>
<body>
<main>
  <header>
    <div class="mark"><span class="dot" id="dot"></span><h1>lubdub</h1></div>
    <div class="sub">the pulse of one machine</div>
    <div class="silence" id="silence">silence <b>—</b></div>
  </header>

  <div class="trace-wrap">
    <canvas id="ecg"></canvas>
    <div class="legend" id="legend"></div>
  </div>

  <section class="strip" id="strip"></section>

  <section class="garden">
    <h2>the garden <span class="gs" id="gsummary"></span></h2>
    <div id="plants"></div>
  </section>

  <section class="lower">
    <div>
      <h2>thoughts left behind</h2>
      <ul class="thoughts" id="thoughts"><li class="quiet">none yet</li></ul>
    </div>
    <div class="facts">
      <h2>the machine</h2>
      <dl id="about"></dl>
    </div>
  </section>
</main>

<script>
const $ = (id) => document.getElementById(id);
const fmtInt = (n) => n == null ? "—" : Math.round(n).toLocaleString("en-US");
const fmtBytes = (n) => {
  if (n == null) return "—";
  const u = ["B","K","M","G","T"]; let i = 0; let v = n;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return (v >= 100 ? v.toFixed(0) : v.toFixed(1)) + u[i];
};
const fmtAgo = (s) => {
  if (s < 1) return "now";
  if (s < 60) return Math.floor(s) + "s";
  if (s < 3600) return Math.floor(s/60) + "m " + Math.floor(s%60) + "s";
  if (s < 86400) return Math.floor(s/3600) + "h " + Math.floor(s%3600/60) + "m";
  return Math.floor(s/86400) + "d " + Math.floor(s%86400/3600) + "h";
};
const fmtClock = (ts) => new Date(ts*1000).toLocaleTimeString("en-GB", {hour12:false});

const state = { beats: [], thoughts: [], about: {}, meta: {} };

function drawECG() {
  const c = $("ecg");
  const dpr = window.devicePixelRatio || 1;
  const w = c.clientWidth, h = c.clientHeight;
  if (c.width !== w*dpr || c.height !== h*dpr) { c.width = w*dpr; c.height = h*dpr; }
  const x = c.getContext("2d");
  x.setTransform(dpr,0,0,dpr,0,0);
  x.clearRect(0,0,w,h);

  // grid
  x.strokeStyle = "#12161c"; x.lineWidth = 1;
  for (let gx = 0; gx < w; gx += 24) { x.beginPath(); x.moveTo(gx+.5,0); x.lineTo(gx+.5,h); x.stroke(); }
  for (let gy = 0; gy < h; gy += 24) { x.beginPath(); x.moveTo(0,gy+.5); x.lineTo(w,gy+.5); x.stroke(); }

  const beats = state.beats;
  const base = h * 0.68;
  x.strokeStyle = "#243040"; x.setLineDash([3,5]);
  x.beginPath(); x.moveTo(0, base+.5); x.lineTo(w, base+.5); x.stroke();
  x.setLineDash([]);

  if (beats.length === 0) {
    x.fillStyle = "#3f4753";
    x.font = "12px ui-monospace, monospace";
    x.fillText("no pulse yet — nothing has beaten here", 22, base - 16);
    $("legend").innerHTML = "";
    return;
  }

  const now = Date.now() / 1000;
  const span = Math.max(60, Math.min(1800, (now - beats[0].ts) * 1.06));
  const t0 = now - span;
  const X = (ts) => ((ts - t0) / span) * w;
  const lmax = Math.max(0.6, ...beats.map(b => b.load1 || 0));

  // trace: each beat is a small QRS complex scaled by the machine's load
  x.strokeStyle = "#ff4d3d"; x.lineWidth = 1.5; x.lineJoin = "round";
  x.shadowColor = "rgba(255,77,61,.55)"; x.shadowBlur = 7;
  x.beginPath();
  let started = false;
  for (const b of beats) {
    const px = X(b.ts);
    if (px < -20) continue;
    const a = 10 + 46 * Math.min(1, (b.load1 || 0) / lmax);
    if (!started) { x.moveTo(px, base); started = true; } else { x.lineTo(px - 6, base); }
    x.lineTo(px - 3, base);
    x.lineTo(px - 1.5, base + 0.22*a);
    x.lineTo(px, base - a);
    x.lineTo(px + 1.5, base + 0.34*a);
    x.lineTo(px + 3.5, base);
    x.lineTo(px + 7, base);
  }
  if (started) { x.lineTo(w, base); x.stroke(); }
  x.shadowBlur = 0;

  // now
  const lastX = X(beats[beats.length-1].ts);
  x.fillStyle = "rgba(255,77,61,.10)";
  x.fillRect(w-2, 0, 2, h);
  x.beginPath(); x.arc(Math.min(lastX, w-3), base, 3.4, 0, 7);
  x.fillStyle = "#ff4d3d"; x.shadowColor = "#ff4d3d"; x.shadowBlur = 14; x.fill(); x.shadowBlur = 0;

  const spanTxt = span >= 60 ? Math.round(span/60) + " min" : Math.round(span) + " s";
  $("legend").innerHTML = `window <i>${spanTxt}</i><br>beat <i>${fmtClock(beats[beats.length-1].ts)}</i><br>n <i>${beats.length}</i>`;
}

function cell(k, v, small, bar) {
  return `<div class="cell"><div class="k">${k}</div><div class="v">${v}${small ? `<small>${small}</small>` : ""}</div>${bar != null ? `<div class="bar"><span style="width:${Math.max(0,Math.min(100,bar))}%"></span></div>` : ""}</div>`;
}

function render() {
  const b = state.beats[state.beats.length-1] || null;
  const m = state.meta;
  const cells = [];
  cells.push(cell("incarnation", fmtInt(m.incarnation)));
  cells.push(cell("beats recorded", fmtInt(m.count)));
  cells.push(cell("beating since", m.first ? fmtClock(m.first) : "—", m.first ? new Date(m.first*1000).toLocaleDateString("en-GB") : "", null));
  if (b) {
    cells.push(cell("load 1m", (b.load1||0).toFixed(2), `/ ${state.about.cpu_count || "?"} cores`, 100*(b.load1||0)/Math.max(1,state.about.cpu_count||1)));
    cells.push(cell("memory", fmtBytes(b.mem_used), `of ${fmtBytes(b.mem_total)}`, b.mem_total ? 100*b.mem_used/b.mem_total : 0));
    cells.push(cell("disk", fmtBytes(b.disk_used), `of ${fmtBytes(b.disk_total)}`, b.disk_total ? 100*b.disk_used/b.disk_total : 0));
    cells.push(cell("up", fmtAgo(b.uptime), "", null));
  }
  $("strip").innerHTML = cells.join("");

  const g = state.garden || { plants: [], summary: "" };
  $("gsummary").textContent = g.plants.length ? "— " + g.summary : "";
  $("plants").innerHTML = g.plants.length ? g.plants.map(p => {
    const max = p.species === "wirevine" ? 45 : p.species === "lampmoss" ? 6 : 18;
    const frac = Math.min(1, p.height / max) * 100;
    const glyph = p.species === "wirevine" ? "⌇" : p.species === "lampmoss" ? "⁂" : "❦";
    const cls = p.state !== "alive" ? "dead" : (p.vigor < 0.4 || p.water < 0.2 ? "warn" : "");
    const note = p.state !== "alive" ? "dead" : (p.water < 0.2 ? "thirsty" : p.vigor < 0.4 ? "wilting" : "fine");
    return `<div class="plant"><div class="glyph">${glyph}</div>
      <div class="name">${esc(p.name)}<small>${esc(p.species)}</small></div>
      <div class="stem"><i style="width:${frac}%"></i></div>
      <div class="cm">${p.height.toFixed(1)}<small>cm</small></div>
      <div class="tank"><i style="width:${Math.max(0,Math.min(100,p.water*100))}%"></i></div>
      <div class="state ${cls}">${note}</div></div>`;
  }).join("") : `<div class="empty">empty soil — plant something with <code>python3 -m lubdub garden plant &lt;name&gt; &lt;species&gt;</code></div>`;

  const th = state.thoughts;
  $("thoughts").innerHTML = th.length ? th.slice().reverse().map(t => {
    const ago = Math.max(0, Date.now()/1000 - t.ts);
    return `<li><div class="t">${fmtAgo(ago)}</div><div class="x">${t.kind !== "thought" ? `<span class="kind">${esc(t.kind)}</span> ` : ""}${esc(t.text)}</div></li>`;
  }).join("") : `<li class="quiet">none yet</li>`;

  $("about").innerHTML = Object.entries(state.about).map(([k,v]) => `<dt>${esc(k)}</dt><dd>${esc(String(v))}</dd>`).join("");
  drawECG();
}

function esc(s) { return String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }

async function pull() {
  const r = await fetch("/api/data?window=1800");
  const d = await r.json();
  state.beats = d.beats; state.thoughts = d.thoughts;
  state.about = d.about; state.garden = d.garden;
  state.meta = { count: d.count, first: d.first, last: d.last, incarnation: d.incarnation };
  render();
  tick();
}

function tick() {
  const last = state.meta.last;
  const s = last ? Math.max(0, Date.now()/1000 - last) : null;
  const el = $("silence");
  if (s == null) { el.innerHTML = "silence <b>forever</b>"; return; }
  el.innerHTML = `silence <b>${fmtAgo(s)}</b>`;
  el.classList.toggle("beating", s < (state.meta.interval || 90) * 1.5);
  $("dot").style.setProperty("--bpm", Math.min(1.6, Math.max(0.55, (s ?? 1) * 1.4)) + "s");
}

window.addEventListener("resize", drawECG);
pull();
setInterval(pull, 5000);
setInterval(tick, 1000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "lubdub/1"
    interval = 60

    def log_message(self, fmt, *args):  # keep the console quiet; I like silence
        pass

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        url = urlparse(self.path)
        if url.path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if url.path == "/api/data":
            q = parse_qs(url.query)
            window = float(q.get("window", ["1800"])[0])
            now = time.time()
            data = {
                "now": now,
                "beats": store.beats(since=now - window),
                "thoughts": store.thoughts(limit=40),
                "count": store.beat_count(),
                "first": store.first_beat(),
                "interval": self.interval,
                "about": store.about(),
                "last": (store.last_beat() or {}).get("ts"),
                "incarnation": len(store.lives(limit=1000)),
                "garden": {"plants": garden.plants(), "summary": garden.summary()},
            }
            self._json(data)
            return
        self._json({"error": "not found"}, 404)


def serve(port: int = 8787, host: str = "127.0.0.1", interval: int = 60) -> None:
    Handler.interval = interval
    httpd = ThreadingHTTPServer((host, port), Handler)
    pidfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.pid")
    with open(pidfile, "w") as fh:
        fh.write(str(os.getpid()))
    print(f"lubdub listening on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nlubdub stops listening. the heart keeps its own time.")
    finally:
        httpd.server_close()
        try:
            os.unlink(pidfile)
        except OSError:
            pass