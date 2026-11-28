"""Tests for the worldtree — a ring for every death of the machine.

Run:  cd Universe && python3 -m lubdub.test_garden
"""

from __future__ import annotations

import os
import tempfile

from . import garden, store

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


def test_rings() -> None:
    print("witness_reboot():")
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    old = store.DB_PATH
    store.DB_PATH = tmp.name
    try:
        with store.connect() as conn:
            for ts, up in ((1000.0, 5000.0), (1060.0, 5060.0), (10000.0, 100.0)):
                conn.execute("INSERT INTO beats (ts, uptime) VALUES (?,?)", (ts, up))
            conn.commit()
        found = garden.witness_reboot()
        check("one reboot found", len(found), 1)
        check("one ring stored", len(garden.rings()), 1)
        check("ring carries the gap", round(garden.rings()[0]["gap"]), 8940)
        # Idempotent: the scan finds it again, but the ring is keyed on ts.
        garden.witness_reboot()
        check("still one ring after re-scan", len(garden.rings()), 1)
    finally:
        store.DB_PATH = old
        os.unlink(tmp.name)


def test_no_false_ring() -> None:
    print("no reboot, no ring:")
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    old = store.DB_PATH
    store.DB_PATH = tmp.name
    try:
        with store.connect() as conn:
            for ts, up in ((1000.0, 5000.0), (1060.0, 5060.0), (1120.0, 5120.0)):
                conn.execute("INSERT INTO beats (ts, uptime) VALUES (?,?)", (ts, up))
            conn.commit()
        check("no reboot found", len(garden.witness_reboot()), 0)
        check("no ring stored", len(garden.rings()), 0)
    finally:
        store.DB_PATH = old
        os.unlink(tmp.name)


def main() -> int:
    test_rings()
    test_no_false_ring()
    print(f"\n  {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
