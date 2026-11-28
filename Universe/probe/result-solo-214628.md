# build experiment — solo

*2026-11-27 21:46:28 · 3 turns · model deepseek/deepseek-v4.1-flash · 9s*

| turn | who | passing | bytes |
| --- | --- | --- | --- |
| 1 | Bob-1 | 22/25 | 616 |
| 2 | Bob-1 | 25/25 | 715 |
| 3 | Bob-1 | 25/25 | 699 |

## Final file

```python
def match(pattern, text):
    """Wildcard match: ? and . match one char, * matches zero or more."""
    # dp[j] = pattern prefix matches text[:j]
    m = len(text)
    dp = [False] * (m + 1)
    dp[0] = True

    for p in pattern:
        if p == '*':
            # running OR: any text prefix reachable by consuming zero or more
            for j in range(1, m + 1):
                dp[j] = dp[j] or dp[j - 1]
        else:
            # literal, ?, or . all consume exactly one matching char
            for j in range(m, 0, -1):
                dp[j] = dp[j - 1] and _eq(p, text[j - 1])
            dp[0] = False

    return bool(dp[m])


def _eq(p, c):
    return p == '?' or p == '.' or p == c
```
