# build experiment — solo

*2026-11-27 21:41:02 · 2 turns · model deepseek/deepseek-v4.1-flash · 3s*

| turn | who | passing | bytes |
| --- | --- | --- | --- |
| 1 | Bob-1 | 15/26 | 611 |
| 2 | Bob-1 | 15/26 | 611 |

## Final file

```python
def match(pattern, text):
    # classic wildcard match: ? and . match exactly one char, * matches zero or more
    p, t = 0, 0
    star_p = star_t = -1
    while t < len(text):
        if p < len(pattern) and pattern[p] in "?.":
            p += 1
            t += 1
        elif p < len(pattern) and pattern[p] == "*":
            star_p, star_t = p, t
            p += 1
        elif star_p != -1:
            p = star_p + 1
            t = star_t + 1
            star_t += 1
        else:
            return False
    while p < len(pattern) and pattern[p] == "*":
        p += 1
    return p == len(pattern)
```
