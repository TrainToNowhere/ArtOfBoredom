# build experiment — solo

*2026-11-27 21:41:22 · 2 turns · model deepseek/deepseek-v4.1-flash · 6s*

| turn | who | passing | bytes |
| --- | --- | --- | --- |
| 1 | Bob-1 | 23/26 | 891 |
| 2 | Bob-1 | 23/26 | 891 |

## Final file

```python
"""Wildcard matching: '?' and '.' match one character, '*' matches zero or more."""


def match(pattern, text):
    """Return True if the whole text matches the whole pattern.

    Uses the classic two-pointer greedy algorithm with backtracking, which
    runs in O(len(pattern) * len(text)) worst case and O(1) extra space.
    """
    p = t = 0
    star = -1
    star_t = 0
    plen, tlen = len(pattern), len(text)

    while t < tlen:
        if p < plen and (pattern[p] == "?" or pattern[p] == "." or pattern[p] == text[t]):
            p += 1
            t += 1
        elif p < plen and pattern[p] == "*":
            star = p
            star_t = t
            p += 1
        elif star != -1:
            p = star + 1
            star_t += 1
            t = star_t
        else:
            return False

    while p < plen and pattern[p] == "*":
        p += 1

    return p == plen
```
