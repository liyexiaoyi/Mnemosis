# Temporal selection and retrieval boundaries

The temporal anchor in `recall()` now compares already retrieved records and
newly discovered records in the same bounded candidate pool. Previously, the
pass skipped every existing result: a current-address question could return
the new address at `top_k=1` but rank a strongly reinforced old address first
at `top_k=2`. Date selection now happens before the winner is promoted once.

This applies to the existing recognized Chinese current/latest, first,
next-event, and exact calendar-date questions. For example:

```python
from datetime import datetime, timezone
now = datetime(2026, 9, 26, tzinfo=timezone.utc)
results = engine.recall(
    "现在小林住在哪里？", top_k=5,
    now=now, read_only=True,
)
report = engine.temporal_anchor("现在小林住在哪里？", now=now)
```

The date/topic parsing rules are unchanged. The selected date record
is promoted even when it is already present. Re-ranking preserves existing
reasons and uncertainty, avoids duplicate IDs, does not mutate incoming
result objects, and is idempotent when reapplying the same anchor. An anchor
reason explains the ordering; the score is not a truth probability.

`temporal_anchor()` is now actually read-only, matching its documented
contract. It does not strengthen memory, change links, or append recall logs.
Normal `recall()` retains its existing learning contract unless `read_only`
is set. This change does not redesign when ordinary recall settles learning.

Association spreading, cached event successors and pattern completion must
respect active status, requested memory kind and excluded/suppressed IDs.
Filtering after each expansion prevents disallowed neighbours becoming
another expansion's roots or receiving retrieval updates. Allowed associations
still work; forgetting/restoring remains explicit.

## Limits

This is not a new validity-interval or fact-version API. Existing content/cue
dates drive this anchor; `source.occurred_at` alone is not newly supported.
Unstructured corrections without a date, entity ambiguity, misleading dates,
and semantic contradiction detection remain limitations. Existing date parsing
heuristics and the term-index candidate budget remain unchanged. At the budget
limit only existing results can be compared, so universal invariance to top_k
is not promised. Date-tied records use the existing deterministic ID tie-break.

BM25's standalone read-only ranking is unchanged; it does not automatically
apply this anchor. The fix is in `recall()` and the routes that call it, including
the diagnostic tool. No default BM25 switch, schema migration or dependency
was introduced.

## Evidence

Fourteen new tests cover public recall at top_k 1/2/5, input permutations,
earliest/future/exact date selection, uncertainty and read-only diagnostics,
filters and graph routes on Dict/SQLite, suppression, bounded candidates and
cached stale successors. The complete suite passed 600 tests; the capability
regression passed 18/18.

`benchmarks/temporal_selection_eval.py` compares the same nine synthetic date
scenarios under two storage backends and three top_k values. Correct first
results improved from 18/54 to 54/54 against archived commit `0cd2755`.
These are targeted regression fixtures, not 54 independent or held-out
questions and not end-to-end generated answer accuracy.
