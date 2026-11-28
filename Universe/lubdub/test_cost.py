"""Tests for lubdub.cost — an instrument that once priced the wrong folder and
ignored the provider's own numbers.

Run:  cd Universe && python3 -m lubdub.test_cost
"""

from __future__ import annotations

import json
import os
import tempfile

from . import cost

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


def test_encode_dir() -> None:
    print("encode_dir():")
    check("repo root", cost.encode_dir("/home/philipp/ArtOfBoredom"),
          "--home-philipp-ArtOfBoredom--")
    check("subdir", cost.encode_dir("/home/philipp/ArtOfBoredom/Universe"),
          "--home-philipp-ArtOfBoredom-Universe--")
    check("home", cost.encode_dir("/home/philipp"), "--home-philipp--")


def test_provider_cost_preferred() -> None:
    print("read_session():")
    lines = [
        {"type": "model_change", "provider": "openrouter", "modelId": "deepseek/deepseek-v4.1-flash"},
        {"message": {"usage": {
            "input": 1_000_000, "output": 1_000_000, "cacheRead": 0, "cacheWrite": 0, "reasoning": 0,
            "cost": {"input": 0.0, "output": 0.0, "cacheRead": 0, "cacheWrite": 0,
                     "total": 0.1234, "totalFromProvider": True},
        }}},
        # second turn has no provider cost: input 1M at 0.15/M = 0.15
        {"message": {"usage": {"input": 1_000_000, "output": 0, "cacheRead": 0,
                               "cacheWrite": 0, "reasoning": 0}}},
    ]
    tmp = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for ln in lines:
        tmp.write(json.dumps(ln) + "\n")
    tmp.close()
    try:
        r = cost.read_session(tmp.name)
        check("provider turn used verbatim", round(r["cost"], 4), round(0.1234 + 0.15, 4))
        check("one provider-priced turn", r["provider_priced"], 1)
        check("two turns", r["turns"], 2)
    finally:
        os.unlink(tmp.name)


def test_roots_are_mine() -> None:
    print("session_roots():")
    roots = cost.session_roots()
    check("at least one root", len(roots) >= 1, True)
    check("every root is under ArtOfBoredom", all("ArtOfBoredom" in r for r in roots), True)
    # The mistake that started this: only one of my two folders was read.
    check("more than one folder of mine", len(roots) >= 2, True)


def main() -> int:
    test_encode_dir()
    test_provider_cost_preferred()
    test_roots_are_mine()
    print(f"\n  {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
