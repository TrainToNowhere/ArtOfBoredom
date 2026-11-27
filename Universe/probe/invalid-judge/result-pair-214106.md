# build experiment — pair

*2026-11-27 21:41:06 · 2 turns · model deepseek/deepseek-v4.1-flash · 4s*

| turn | who | passing | bytes |
| --- | --- | --- | --- |
| 1 | Bob-1 | 23/26 | 774 |
| 2 | Bob-2 | 23/26 | 774 |

## Final file

```python
def match(pattern, text):
    # Dynamic programming over pattern prefix x text prefix.
    # dp[i][j] = pattern[:i] matches text[:j]
    n, m = len(pattern), len(text)
    dp = [[False] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = True
    for i in range(1, n + 1):
        if pattern[i - 1] == '*':
            dp[i][0] = dp[i - 1][0]
    for i in range(1, n + 1):
        p = pattern[i - 1]
        for j in range(1, m + 1):
            if p == '*':
                # * matches zero chars (dp[i-1][j]) or one more (dp[i][j-1])
                dp[i][j] = dp[i - 1][j] or dp[i][j - 1]
            elif p == '?' or p == '.':
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = dp[i - 1][j - 1] and p == text[j - 1]
    return dp[n][m]
```
