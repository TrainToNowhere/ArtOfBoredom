# build experiment — solo

*2026-11-27 21:40:17 · 4 turns · model deepseek/deepseek-v4.1-flash · 10s*

| turn | who | passing | bytes |
| --- | --- | --- | --- |
| 1 | Bob-1 | 18/18 | 1332 |
| 2 | Bob-1 | 18/18 | 1345 |
| 3 | Bob-1 | 18/18 | 1345 |
| 4 | Bob-1 | 18/18 | 1345 |

## Final file

```python
"""Half-open interval arithmetic: [start, end)."""


def merge(intervals):
    """Merge overlapping or touching intervals. Returns a new sorted list."""
    if not intervals:
        return []
    ordered = sorted(tuple(iv) for iv in intervals)
    result = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = result[-1]
        if start <= last_end:
            if end > last_end:
                result[-1] = (last_start, end)
        else:
            result.append((start, end))
    return result


def subtract(a, b):
    """Everything in a not covered by b, merged and sorted."""
    if not a:
        return []
    holes = merge(b)
    result = []
    for start, end in merge(a):
        cursor = start
        for hole_start, hole_end in holes:
            if hole_end <= cursor:
                continue
            if hole_start >= end:
                break
            if hole_start > cursor:
                result.append((cursor, hole_start))
            if hole_end > cursor:
                cursor = hole_end
            if cursor >= end:
                break
        if cursor < end:
            result.append((cursor, end))
    return result


def total_length(intervals):
    """Total length covered, counting overlaps once."""
    return float(sum(end - start for start, end in merge(intervals)))
```
