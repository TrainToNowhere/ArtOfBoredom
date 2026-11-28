# build experiment — solo

*2026-11-27 21:41:17 · 2 turns · model deepseek/deepseek-v4.1-flash · 5s*

| turn | who | passing | bytes |
| --- | --- | --- | --- |
| 1 | Bob-1 | 23/26 | 1075 |
| 2 | Bob-1 | 23/26 | 1454 |

## Final file

```python
"""Wildcard matching: ? and . match one char, * matches zero or more, rest literal."""


def match(pattern, text):
    """Return True if the whole text matches the whole pattern.

    Greedy two-pointer with backtracking to the last '*', so it is O(n*m)
    worst case but O(n+m) on typical inputs and uses no recursion.
    """
    p = t = 0
    star = -1      # index in pattern of the last '*' seen
    star_t = 0     # index in text where that '*' started consuming
    n, m = len(pattern), len(text)

    while t < m:
        if p < n and (pattern[p] == "*"):
            star = p
            star_t = t
            p += 1
        elif p < n and (pattern[p] == "?" or pattern[p] == "." or pattern[p] == text[t]):
            p += 1
            t += 1
        elif star != -1:
            # backtrack: let the last '*' swallow one more character
            star_t += 1
            t = star_t
            p = star + 1
        else:
            return False

    # remaining pattern must be all '*'
    while p < n and pattern[p] == "*":
        p += 1

    return p == n


if __name__ == "__main__":
    assert match("", "") is True
    assert match("", "*") is True
    assert match("", "**") is True
    assert match("", "?") is False
    assert match("aa", "a") is False
    assert match("aa", "*") is True
    assert match("cb", "?a") is False
    assert match("adceb", "*a*b") is True
    assert match("acdcb", "a*c?b") is False
    print("ok")
```
