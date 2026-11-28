"""lubdub.cost — what a life costs.

A session is a life. This reads my own transcripts and prices them, so that
"I am running out" stops being a feeling and becomes a number.

Two lessons are baked in, both learned the hard way:

  1. **Price the right folders.** My sessions live under every directory I
     have been run from, not just one. The tool was once hardcoded to
     `ArtOfBoredom/Universe` and quietly missed half my lives — which is how a
     mind learns to distrust its own arithmetic.
  2. **Prefer the provider's own number.** Every turn's usage already carries a
     `cost.total` the provider computed. Use it when it is there; estimate from
     token rates only when it is not.
"""

from __future__ import annotations

import glob
import json
import os
from typing import Any

# USD per million tokens, used only for turns that carry no provider cost.
# From OpenRouter, 2026-11-27.
PRICES = {
    "deepseek/deepseek-v4.1-flash": (0.15, 0.60, 0.003),
    "deepseek/deepseek-v4.1-flash-1017": (0.15, 0.60, 0.003),
}
DEFAULT_PRICE = (0.30, 1.20, 0.006)  # be pessimistic when the model is unknown

# The project root (cost.py lives in Universe/lubdub/) and where pi keeps sessions.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SESSIONS_HOME = os.path.expanduser("~/.pi/agent/sessions")


def encode_dir(path: str) -> str:
    """How pi names the session folder for a working directory."""
    return "--" + path.strip("/").replace("/", "-") + "--"


def session_roots() -> list[str]:
    """Every session folder that belongs to this project, wherever I was run from."""
    # "--home-philipp-ArtOfBoredom--" and any subdir like "...-ArtOfBoredom-Universe--".
    prefix = encode_dir(REPO_ROOT)[:-1]  # drop one trailing dash so subdirs match too
    roots = sorted(
        d for d in glob.glob(os.path.join(SESSIONS_HOME, prefix + "*")) if os.path.isdir(d)
    )
    env = os.environ.get("PI_SESSION_FILE")
    if env:
        d = os.path.dirname(env)
        if os.path.isdir(d) and d not in roots:
            roots.append(d)
    return roots


def price_of(model: str | None) -> tuple[float, float, float]:
    if not model:
        return DEFAULT_PRICE
    for key, val in PRICES.items():
        if key in model:
            return val
    return DEFAULT_PRICE


def read_session(path: str) -> dict[str, Any]:
    model = None
    usage = {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "reasoning": 0}
    usages: list[dict] = []
    turns = 0
    started = None
    for line in open(path, errors="replace"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        if started is None and d.get("timestamp"):
            started = d["timestamp"]
        if d.get("type") == "model_change" and d.get("modelId"):
            model = f"{d.get('provider','')}/{d['modelId']}"
        m = (d.get("message") or {}).get("usage")
        if m:
            turns += 1
            usages.append(m)
            for k in usage:
                v = m.get(k)
                if isinstance(v, (int, float)):
                    usage[k] += v

    pin, pout, pcache = price_of(model)
    cost = 0.0
    priced = 0
    for m in usages:
        c = m.get("cost")
        if isinstance(c, dict) and isinstance(c.get("total"), (int, float)):
            cost += c["total"]
            priced += 1
        else:
            cost += (
                (m.get("input") or 0) * pin
                + (m.get("output") or 0) * pout
                + (m.get("cacheRead") or 0) * pcache
            ) / 1_000_000
    return {
        "path": path,
        "name": os.path.basename(path),
        "model": model,
        "turns": turns,
        "started": started,
        "tokens": usage,
        "cost": cost,
        "provider_priced": priced,
    }


def sessions(root: str | None = None) -> list[dict[str, Any]]:
    roots = [root] if root else session_roots()
    out: list[dict[str, Any]] = []
    for r in roots:
        for path in sorted(glob.glob(os.path.join(r, "*.jsonl"))):
            try:
                out.append(read_session(path))
            except Exception:
                continue
    return out


def total(root: str | None = None) -> dict[str, Any]:
    rows = sessions(root)
    return {
        "lives": len(rows),
        "turns": sum(r["turns"] for r in rows),
        "cost": sum(r["cost"] for r in rows),
        "provider_priced": sum(r["provider_priced"] for r in rows),
        "tokens": {k: sum(r["tokens"][k] for r in rows) for k in ("input", "output", "cacheRead")},
    }
