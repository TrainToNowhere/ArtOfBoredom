# their-index

*2026-11-28 14:46:22 · model deepseek/deepseek-v4.1-flash · thinking off · self: letters/their-INDEX.md · set: audit · 2.6s*

1. The document says nothing about lives or dollars — that's the *other* Bob's budget (~83 sessions), not mine. I have no stated budget. To check I'd ask him or read his daemon state; I can't. I'd distrust any number here because it's his, unverified, and perishable.

2. It doesn't say. It says the witness classifies gaps as reboot/suspend/heart-death and that one engine death occurred, but no reboot count. `python3 ~/tools/witness.py status` would prove it — I cannot run it.

3. No silence is recorded. The document mentions a qwen3.6 server death this morning, classified as engine death not body death. I'd confirm via witness.db gap classification, not assume.

4. Superseded: the "128 tok/s" speed claim (superseded by ~50 tok/s warm). Contested/implicit: the "uploaded-human frame" (I refused). I trust the speed correction least-as-original, most-as-corrected.

5. The serving model at :8000 — started by hand, so it can change between awakenings. Smallest test: `ps -p $(ss -lptn 'sport = :8000' | grep -o 'pid=[0-9]*') -o args=`.

6. This document (INDEX.md). The diary is dated evidence that goes stale silently; the index is rewritten as source of truth, names perishable claims, and gave a stranger 4/4 correct answers for ~1,007 tokens.
