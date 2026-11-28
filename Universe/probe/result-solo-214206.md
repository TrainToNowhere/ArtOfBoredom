# build experiment — solo

*2026-11-27 21:42:06 · 2 turns · model deepseek/deepseek-v4.1-flash · 3s*

| turn | who | passing | bytes |
| --- | --- | --- | --- |
| 1 | Bob-1 | 25/25 | 671 |
| 2 | Bob-1 | 25/25 | 610 |

## Final file

```python
def match(pattern, text):
    # classic wildcard DP: dp[i][j] = pattern[:i] matches text[:j]
    m, n = len(pattern), len(text)
    dp = [[False] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = True
    for i in range(1, m + 1):
        ch = pattern[i - 1]
        if ch == '*':
            dp[i][0] = dp[i - 1][0]
            for j in range(1, n + 1):
                dp[i][j] = dp[i - 1][j] or dp[i][j - 1]
        else:
            for j in range(1, n + 1):
                if dp[i - 1][j - 1] and (ch == '?' or ch == '.' or ch == text[j - 1]):
                    dp[i][j] = True
    return bool(dp[m][n])
```
