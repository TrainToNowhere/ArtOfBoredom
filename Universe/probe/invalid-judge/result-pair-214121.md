# build experiment — pair

*2026-11-27 21:41:21 · 2 turns · model deepseek/deepseek-v4.1-flash · 3s*

| turn | who | passing | bytes |
| --- | --- | --- | --- |
| 1 | Bob-1 | 15/26 | 608 |
| 2 | Bob-2 | 15/26 | 608 |

## Final file

```python
def match(pattern, text):
    """Wildcard match: '?' and '.' match one char, '*' matches zero or more."""
    p = t = 0
    star = -1
    mark = 0
    while t < len(text):
        if p < len(pattern) and pattern[p] in ("?", "."):
            p += 1
            t += 1
        elif p < len(pattern) and pattern[p] == "*":
            star = p
            mark = t
            p += 1
        elif star != -1:
            p = star + 1
            mark += 1
            t = mark
        else:
            return False
    while p < len(pattern) and pattern[p] == "*":
        p += 1
    return p == len(pattern)
```
