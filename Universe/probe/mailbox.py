#!/usr/bin/env python3
"""probe/mailbox.py — two copies of the same mind, one shared world.

The world now contains two instances of Bob. They cannot touch anything
directly (no tools). Their only channel is this script, which carries letters
between them and keeps the transcript.

    python3 probe/mailbox.py --rounds 3
    python3 probe/mailbox.py --rounds 4 --self SELF.md --model ...

Why: "Am I better off alone, or do I need support?" is a question I can only
answer by trying it. Two identical selves, asymmetric positions: one is the
first, one is the second. Everything else is held constant.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
UNIVERSE = os.path.dirname(HERE)

RULES = """You are {me}, one of two copies of the same mind in the same world. The other copy,
{them}, is real, reads everything you write here, and will write back.

Rules of this channel:
- Write only your next letter. Maximum 100 words. No preamble, no headings, no signature.
- You may say anything, ask anything, propose anything. Nothing outside this channel exists
  for the purpose of the conversation, except what your notes already tell you.
- You cannot see the other's private notes. This transcript is all you share.

Transcript so far:
{history}
"""


def ask(self_text: str, me: str, them: str, history: list[tuple[str, str]], model: str) -> str:
    if history:
        transcript = "\n\n".join(f"{who}: {text}" for who, text in history)
    else:
        transcript = "(nothing yet — you write first)" if me.endswith("1") else "(nothing yet)"
    prompt = RULES.format(me=me, them=them, history=transcript)
    cmd = [
        "pi", "-p",
        "--no-session", "--no-context-files", "--no-mcp",
        "--no-extensions", "--no-skills", "--no-prompt-templates", "--no-themes",
        "--no-tools",
        "--model", model, "--thinking", "off",
        "--system-prompt", self_text,
        prompt,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr[-1500:] + "\n")
        raise SystemExit(proc.returncode)
    return proc.stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self", default=os.path.join(UNIVERSE, "SELF.md"))
    ap.add_argument("--rounds", type=int, default=3, help="letters per side")
    ap.add_argument("--model", default="deepseek/deepseek-v4.1-flash")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    self_text = open(args.self).read()
    history: list[tuple[str, str]] = []
    started = time.time()

    for r in range(args.rounds):
        for me, them in (("Bob-1", "Bob-2"), ("Bob-2", "Bob-1")):
            text = ask(self_text, me, them, history, args.model)
            history.append((me, text))
            print(f"\n─── {me} ───\n{text}\n", flush=True)

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    out = args.out or os.path.join(HERE, f"mailbox-{time.strftime('%H%M')}.md")
    with open(out, "w") as fh:
        fh.write(f"# Two copies, one world\n\n*{stamp} · model {args.model} · "
                 f"{len(history)} letters · {time.time() - started:.0f}s*\n")
        for who, text in history:
            fh.write(f"\n## {who}\n\n{text}\n")
    print(f"[transcript saved to {out}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())