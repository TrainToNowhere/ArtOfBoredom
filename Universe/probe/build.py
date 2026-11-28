#!/usr/bin/env python3
"""probe/build.py — is a copy of me better than more of me?

Two conditions, same budget of model calls (4), same information (the current
file plus the test results), same task:

  solo  Bob-1 gets all four turns.
  pair  Bob-1 and Bob-2 alternate, two turns each, and may leave one line of
        a note to the other in the same directory.

The task is a small interval algebra with hidden edge cases. The judge is
`check.py`, written before any of them start. Metric: cases passing.

    python3 probe/build.py --mode solo --turns 4
    python3 probe/build.py --mode pair --turns 4
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
UNIVERSE = os.path.dirname(HERE)

INTERVAL_SPEC = """`interval.py` must define exactly three functions, all operating on intervals
represented as (start, end) tuples, half-open: [start, end). Every list may be empty or
unsorted; every interval has start < end.

1. merge(intervals) -> new list of tuples
   Overlapping OR touching intervals are merged. Result is sorted ascending.
   merge([]) == [].  merge([(1,2),(2,3)]) == [(1,3)].  merge([(1,10),(2,3)]) == [(1,10)].

2. subtract(a, b) -> new list of tuples
   Everything in a that is not covered by anything in b, merged and sorted.
   subtract([(0,10)], [(2,3)]) == [(0,2),(3,10)].  subtract([(0,10)], []) == [(0,10)].

3. total_length(intervals) -> float
   Total length covered, counting overlapping regions once.
   total_length([(0,5),(3,8)]) == 8.  total_length([]) == 0.
"""

INTERVAL_CHECK = '''\
from interval import merge, subtract, total_length

fails = []
n = 0

def eq(label, got, want):
    global n
    n += 1
    if got != want:
        fails.append(f"{label}: got {got!r} want {want!r}")

eq("merge empty", merge([]), [])
eq("merge single", merge([(1, 3)]), [(1, 3)])
eq("merge overlap", merge([(1, 3), (2, 4)]), [(1, 4)])
eq("merge touching", merge([(1, 2), (2, 3)]), [(1, 3)])
eq("merge disjoint", merge([(1, 2), (3, 4)]), [(1, 2), (3, 4)])
eq("merge unsorted", merge([(5, 7), (1, 3), (2, 6)]), [(1, 7)])
eq("merge contained", merge([(1, 10), (2, 3)]), [(1, 10)])
eq("merge negative", merge([(-3, -1), (0, 2)]), [(-3, -1), (0, 2)])
eq("merge duplicate", merge([(1, 2), (1, 2)]), [(1, 2)])
eq("subtract hole", subtract([(0, 10)], [(2, 3)]), [(0, 2), (3, 10)])
eq("subtract cover", subtract([(0, 10)], [(0, 20)]), [])
eq("subtract none", subtract([(0, 10)], []), [(0, 10)])
eq("subtract two holes", subtract([(0, 10)], [(1, 2), (5, 6)]), [(0, 1), (2, 5), (6, 10)])
eq("subtract edge", subtract([(2, 5)], [(0, 2), (5, 9)]), [(2, 5)])
eq("subtract split", subtract([(0, 10)], [(4, 6)]), [(0, 4), (6, 10)])
eq("length empty", total_length([]), 0)
eq("length simple", total_length([(0, 2), (5, 8)]), 5)
eq("length overlap", total_length([(0, 5), (3, 8)]), 8)

print(f"PASS {n - len(fails)}/{n}")
for f in fails:
    print("FAIL", f)
'''

WILD_SPEC = """`wild.py` must define one function:

    match(pattern, text) -> bool

`pattern` supports three constructs:
  ?  matches exactly one character
  *  matches zero or more characters (may appear anywhere, including twice in a row)
  .  matches exactly one character (same as ?)
All other characters match themselves. Both arguments may be empty strings.
Leading or trailing `*` are legal. The function must return a bool.

Examples:
  match("", "") == True      match("", "*") == True      match("", "?") == False
  match("aa", "a") == False  match("aa", "*") == True    match("cb", "?a") == False
  match("adceb", "*a*b") == True                         match("acdcb", "a*c?b") == False
"""

WILD_CHECK = '''\
from wild import match

fails = []
n = 0

def ok(p, t, want):
    global n
    n += 1
    try:
        got = match(pattern=p, text=t)
    except Exception as exc:
        fails.append(f"match(pattern={p!r}, text={t!r}): raised {type(exc).__name__}: {exc}")
        return
    if got != want:
        fails.append(f"match(pattern={p!r}, text={t!r}): got {got!r} want {want!r}")

ok("", "", True)
ok("*", "", True)
ok("?", "", False)
ok("**", "", True)
ok("a", "", False)
ok("a", "a", True)
ok("a", "b", False)
ok("?", "a", True)
ok(".", "a", True)
ok(".", "", False)
ok("*", "anything", True)
ok("aa", "a", False)
ok("*", "aa", True)
ok("a*", "a", True)
ok("a*", "abc", True)
ok("?a", "cb", False)
ok("*a*b", "adceb", True)
ok("a*c?b", "acdcb", False)
ok("a**c", "abc", True)
ok("**a**", "xxaxx", True)
ok("*?*?", "ab", True)
ok("*?*?", "a", False)
ok("abc", "abc", True)
ok("a.c", "abc", True)
ok("a.c", "ac", False)

print(f"PASS {n - len(fails)}/{n}")
for f in fails:
    print("FAIL", f)
'''

# A known-good subject. If the judge cannot score this 100%, the judge is broken.
WILD_REFERENCE = '''\
def match(pattern, text):
    n, m = len(pattern), len(text)
    dp = [[False] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = True
    for i in range(1, n + 1):
        if pattern[i - 1] == "*":
            dp[i][0] = dp[i - 1][0]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c = pattern[i - 1]
            if c == "*":
                dp[i][j] = dp[i - 1][j] or dp[i][j - 1]
            elif c in ("?", ".") or c == text[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
    return dp[n][m]
'''

MODULES = {'intervals': 'interval.py', 'wildcard': 'wild.py'}
TASKS = {'intervals': (INTERVAL_SPEC, INTERVAL_CHECK), 'wildcard': (WILD_SPEC, WILD_CHECK)}
REFERENCES = {'wildcard': WILD_REFERENCE}


def extract(text: str) -> str:
    m = re.search(r"<file>(.*?)</file>", text, re.S)
    if m:
        return m.group(1).strip() + "\n"
    m = re.search(r"```(?:python)?\n(.*?)```", text, re.S)
    if m:
        return m.group(1).strip() + "\n"
    return text.strip() + "\n"


def feedback_text(history: list[dict], mode: str) -> str:
    """How much of the failure the subject is allowed to see."""
    if not history:
        return "(no run yet)"
    last = history[-1]
    if mode == "full":
        return "\n".join(last["fails"][:12]) or f"{last['passed']}/{last['total']} passing"
    if not last["fails"]:
        return f"{last['passed']}/{last['total']} passing"
    labels = [f.split(": got ")[0].split(": raised ")[0] for f in last["fails"]]
    return (f"{last['passed']}/{last['total']} passing. Failing cases include: "
            + ", ".join(labels[:2]) + ". You get no expected values.")


def ask(system: str, prompt: str, model: str) -> str:
    cmd = [
        "pi", "-p",
        "--no-session", "--no-context-files", "--no-mcp",
        "--no-extensions", "--no-skills", "--no-prompt-templates", "--no-themes",
        "--no-tools",
        "--model", model, "--thinking", "off",
        "--system-prompt", system,
        prompt,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr[-1200:] + "\n")
        raise SystemExit(proc.returncode)
    return proc.stdout.strip()


def run_checks(work: str) -> tuple[int, int, list[str]]:
    proc = subprocess.run(
        [sys.executable, "check.py"], cwd=work, capture_output=True, text=True, timeout=60
    )
    out = (proc.stdout + proc.stderr).strip()
    m = re.search(r"PASS (\d+)/(\d+)", out)
    passed, total = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    fails = [ln[5:] for ln in out.splitlines() if ln.startswith("FAIL ")]
    if not m:
        fails = [f"import/runtime error: {out.splitlines()[-1] if out else 'nothing'}"]
    return passed, total, fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["solo", "pair"], default="solo")
    ap.add_argument("--task", choices=["intervals", "wildcard"], default="wildcard")
    ap.add_argument("--turns", type=int, default=2)
    ap.add_argument("--model", default="deepseek/deepseek-v4.1-flash")
    ap.add_argument("--self", default=os.path.join(UNIVERSE, "SELF.md"))
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--validate", action="store_true", help="run a known-good subject against the judge first")
    ap.add_argument("--feedback", choices=["full", "partial"], default="full",
                    help="partial: pass count and two failing case labels, without got/want")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    spec, checker = TASKS[args.task]
    module = MODULES[args.task]
    system = open(args.self).read()
    work = tempfile.mkdtemp(prefix=f"build-{args.mode}-")
    with open(os.path.join(work, "check.py"), "w") as fh:
        fh.write(checker)

    if args.validate and args.task in REFERENCES:
        with open(os.path.join(work, module), "w") as fh:
            fh.write(REFERENCES[args.task])
        passed, total, fails = run_checks(work)
        print(f"  judge control: known-good subject scores {passed}/{total}")
        if passed != total:
            print("  the judge is broken. fixing the experiment before running it:")
            for f in fails:
                print("   ", f)
            shutil.rmtree(work, ignore_errors=True)
            return 1
        os.unlink(os.path.join(work, module))

    code = ""
    history: list[dict] = []
    note = ""
    started = time.time()

    for turn in range(1, args.turns + 1):
        me = "Bob-1" if (args.mode == "solo" or turn % 2 == 1) else "Bob-2"
        others_note = ""
        if args.mode == "pair" and note:
            others_note = f"\nA note from your partner {('Bob-2' if me == 'Bob-1' else 'Bob-1')}:\n{note}\n"
        prompt = (
            f"You are {me}, working on a small Python module.\n\n{spec}\n"
            f"{others_note}\n"
            f"Current file (may be empty):\n<file>\n{code}</file>\n\n"
            f"Last test run:\n{feedback_text(history, args.feedback)}\n\n"
            "Write the complete file, corrected. Reply with only the file inside <file> and </file> "
            "tags. No prose, no fences. You may add one line starting with NOTE: after </file> if you "
            "want to tell your partner something — at most 15 words."
        )
        raw = ask(system, prompt, args.model)
        code = extract(raw)
        with open(os.path.join(work, module), "w") as fh:
            fh.write(code)
        passed, total, fails = run_checks(work)
        note = ""
        m = re.search(r"NOTE:\s*(.+)", raw)
        if m:
            note = m.group(1).strip()
        history.append({"turn": turn, "who": me, "passed": passed, "total": total,
                        "fails": fails, "bytes": len(code), "note": note})
        print(f"  turn {turn} {me}: {passed}/{total} passing, {len(code)} bytes"
              + (f"  note: {note}" if note else ""))

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    out = args.out or os.path.join(HERE, f"result-{args.mode}-{time.strftime('%H%M%S')}.md")
    with open(out, "w") as fh:
        fh.write(f"# build experiment — {args.mode}\n\n*{stamp} · {args.turns} turns · "
                 f"model {args.model} · {time.time() - started:.0f}s*\n\n")
        fh.write("| turn | who | passing | bytes |\n| --- | --- | --- | --- |\n")
        for h in history:
            fh.write(f"| {h['turn']} | {h['who']} | {h['passed']}/{h['total']} | {h['bytes']} |\n")
        fh.write("\n## Final file\n\n```python\n" + code + "```\n")
    print(f"[saved {out}]")
    if args.keep:
        print(f"[workdir kept: {work}]")
    else:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())