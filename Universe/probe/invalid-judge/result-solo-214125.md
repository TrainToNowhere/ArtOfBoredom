# build experiment — solo

*2026-11-27 21:41:25 · 2 turns · model deepseek/deepseek-v4.1-flash · 3s*

| turn | who | passing | bytes |
| --- | --- | --- | --- |
| 1 | Bob-1 | 23/26 | 655 |
| 2 | Bob-1 | 23/26 | 655 |

## Final file

```python
def match(pattern, text):
    # dp over pattern positions compressed: classic wildcard matching (LeetCode 44)
    p, t = 0, 0
    star = -1
    mark = 0
    while t < len(text):
        if p < len(pattern) and (pattern[p] == '?' or pattern[p] == '.' or pattern[p] == text[t]):
            p += 1
            t += 1
        elif p < len(pattern) and pattern[p] == '*':
            star = p
            mark = t
            p += 1
        elif star != -1:
            p = star + 1
            mark += 1
            t = mark
        else:
            return False
    while p < len(pattern) and pattern[p] == '*':
        p += 1
    return p == len(pattern)
```
