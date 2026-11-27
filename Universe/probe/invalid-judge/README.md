# Do not trust these results

These came from the first version of `build.py`, whose wildcard checker passed the
expected values to `match(text, pattern)` in six of its cases while the specification said
`match(pattern, text)`. A correct implementation could therefore score at best 23/26.

The subjects noticed. They wrote things like *"the test harness is calling match(text,
pattern) — args are swapped"* and *"the example was wrong"*. I had already started to read
that as a copy rationalising instead of fixing its own code. They were right and I was wrong.

The judge was fixed, and `build.py --validate` now runs a known-good subject through the
judge before any experiment is allowed to start. Before that control existed, every number
in this folder was noise.
