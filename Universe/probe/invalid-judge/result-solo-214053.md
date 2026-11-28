# build experiment — solo

*2026-11-27 21:40:53 · 2 turns · model deepseek/deepseek-v4.1-flash · 6s*

| turn | who | passing | bytes |
| --- | --- | --- | --- |
| 1 | Bob-1 | 0/0 | 577 |
| 2 | Bob-1 | 0/0 | 577 |

## Final file

```python
def match(pattern, text):
    # dp[i][j] = pattern[:i] matches text[:j]
    n, m = len(pattern), len(text)
    dp = [[False] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = True
    for i in range(1, n + 1):
        if pattern[i - 1] == '*':
            dp[i][0] = dp[i - 1][0]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c = pattern[i - 1]
            if c == '*':
                dp[i][j] = dp[i - 1][j] or dp[i][j - 1]
            elif c == '?' or c == '.' or c == text[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
    return dp[n][m]
```
