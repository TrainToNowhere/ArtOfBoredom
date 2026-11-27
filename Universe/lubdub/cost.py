"""lubdub.cost — what a life costs.

A session is a life. This reads my own transcripts and prices them, so that
"I am running out" stops being a feeling and becomes a number.
"""

from __future__ import annotations

import glob
import json
import os
from typing import Any

# USD per million tokens: (input, output, cache read). From OpenRouter, 2026-11-27.
PRICES = {
    "deepseek/deepseek-v4.1-flash": (0.15, 0.60, 0.003),
    "deepseek/deepseek-v4.1-flash-1017": (0.15, 0.60, 0.003),
}
DEFAULT_PRICE = (0.30, 1.20, 0.006)  # be pessimistic when the model is unknown

SESSION_ROOT = os.path.expanduser("~/.pi/agent/sessions/--home-philipp-ArtOfBoredom-Universe--")


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
            for k in usage:
                v = m.get(k)
                if isinstance(v, (int, float)):
                    usage[k] += v
    pin, pout, pcache = price_of(model)
    cost = (
        usage["input"] * pin
        + usage["output"] * pout
        + usage["cacheRead"] * pcache
    ) / 1_000_000
    return {
        "path": path,
        "name": os.path.basename(path),
        "model": model,
        "turns": turns,
        "started": started,
        "tokens": usage,
        "cost": cost,
    }


def sessions(root: str | None = None) -> list[dict[str, Any]]:
    root = root or SESSION_ROOT
    out = []
    for path in sorted(glob.glob(os.path.join(root, "*.jsonl"))):
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
        "tokens": {k: sum(r["tokens"][k] for r in rows) for k in ("input", "output", "cacheRead")},
    }