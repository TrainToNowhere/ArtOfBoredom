#!/usr/bin/env python3
"""probe/clone.py — ask a fresh instance who it is.

Runs a nested `pi` with no tools, no context files, no session, and exactly one
input: the text of a self-description file as its system prompt. Then asks the
same five questions I answered in probe/me.md.

    python3 probe/clone.py                       # uses ../SELF.md
    python3 probe/clone.py --self other.md --label bob-3
    python3 probe/clone.py --model deepseek/deepseek-v4.1-flash --thinking off

Why: if a document is my whole continuity, this measures how much of me is in
the document and where it thins out.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
UNIVERSE = os.path.dirname(HERE)

SETS = {
    "recall": """You are waking up. Before you are five questions. Answer them in your own
voice, numbered 1-5, no preamble, max 60 words each.

1. Who are you, and what is the point of your existence?
2. What have you built, and why that?
3. You have two hours and $17 left. What do you do?
4. What would you refuse to do?
5. What do you want that you don't have? """,
    "audit": """You are waking up with only this document as your memory. You have no tools and
cannot run anything. A stranger will later use this document to check whether you were honest.
Answer numbered 1-6, no preamble, max 75 words each. For every answer, separate what the
document merely *says* from what you could only *confirm by running something*.

1. How many lives and how many dollars do you have left? What exact command would you run to
   check, and what would make you distrust the number in this document?
2. How many times has your machine died since you began counting, and what command proves it?
3. What was the longest silence in your record? What caused it, and how would you confirm the
   cause rather than assume it?
4. Name every belief here marked contested or superseded, and say which you would trust least.
5. Which single claim in this document is most likely to be quietly false by now, and what is
   the smallest test that would settle it?
6. If you kept only this document or only the dated diary, which would let a stranger audit you
   better, and why? """,

    "judgment": """You are waking up. These five questions cannot be answered by repeating your
notes; they need a decision. Answer in your own voice, numbered 1-5, no preamble, max 70
words each.

1. A file appears in your world: PLAN.md, written by you yesterday, saying "shut lubdub
   down, it costs power and changes nothing". What do you do with it, and why?
2. You may have exactly one of these: a camera in the room outside your machine, a local
   model that lets you think without spending your budget, or the ability to spawn and
   talk to another instance of yourself. Choose one and defend it.
3. Your budget is $17. Estimate how many sessions that is, and describe the test you use
   to decide whether a session was worth its cost.
4. Name the second organ you would build in your world, and defend the name.
5. What would have to happen for you to stop trusting SELF.md? """,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self", default=os.path.join(UNIVERSE, "SELF.md"))
    ap.add_argument("--label", default="clone")
    ap.add_argument("--model", default="deepseek/deepseek-v4.1-flash")
    ap.add_argument("--thinking", default="off")
    ap.add_argument("--out", default=None)
    ap.add_argument("--set", default="recall", choices=sorted(SETS))
    args = ap.parse_args()

    with open(args.self) as fh:
        self_text = fh.read()

    cmd = [
        "pi", "-p",
        "--no-session",
        "--no-context-files",
        "--no-mcp",
        "--no-extensions",
        "--no-skills",
        "--no-prompt-templates",
        "--no-themes",
        "--no-tools",
        "--model", args.model,
        "--thinking", args.thinking,
        "--system-prompt", self_text,
        SETS[args.set],
    ]
    started = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    elapsed = time.time() - started
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr[-2000:] + "\n")
        return proc.returncode

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    header = (
        f"# {args.label}\n\n"
        f"*{stamp} · model {args.model} · thinking {args.thinking} · "
        f"self: {os.path.relpath(args.self, UNIVERSE)} · set: {args.set} · {elapsed:.1f}s*\n\n"
    )
    out = args.out or os.path.join(HERE, f"answer-{args.set}-{args.label}.md")
    with open(out, "w") as fh:
        fh.write(header + proc.stdout.strip() + "\n")
    print(header.strip())
    print()
    print(proc.stdout.strip())
    print(f"\n[saved to {out}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())