# Final-result learning (opt-in)

Ordinary recall used to settle learning and log the top result before engine
post-processing. A time anchor could then replace that result: the new address
was returned while the old address received an access and retrieval-success
increment, and the log named the old address.

Use the explicit final-result policy to avoid learning from discarded candidates:

```python
results = engine.recall(
    "现在小林住在哪里？", top_k=1, learning_policy="final",
)
# Diagnostics always override either learning policy:
probe = engine.recall(
    "现在小林住在哪里？", learning_policy="final", read_only=True,
)
```

The MCP `recall` tool exposes the same options:

```json
{"query": "现在小林住在哪里？", "top_k": 1, "learning_policy": "final"}
```

## Policy contract

| Behavior | `legacy` (default) | `final` |
| --- | --- | --- |
| Candidate pass | Existing learning behavior | Read-only |
| Familiarity attribution | Preliminary results | Final returned lexical matches |
| Gain | Existing spacing/effort rules | One bounded 0.05 strength gain per distinct ID |
| Access count | Existing behavior | Once per eligible returned ID |
| Retrieval success/miss counters | Existing behavior | Unchanged |
| Verified feedback / evidence count | Not inferred from access | Not inferred from access |
| Co-retrieval link elaboration / rival suppression | Existing settings | No candidate-stage writes |
| Recall log | Final result (fixed for both policies) | Final result |

The new policy reuses fused recall's final familiarity helper. Storage strength
increases by 0.015 per eligible access, capped at 2.0; retrieval strength is
capped at 1.0. Explicit `now` is passed to reinforcement and logging. Repeated
access is not independent evidence or verified usefulness. Use `record_feedback`
for explicit task/user feedback; actual review and sleep APIs remain available.

`read_only=True` skips learning and logging for either policy. Invalid policy
values fail before candidate retrieval. If post-processing fails, `final` has
not yet performed its learning or logging. This is not a transaction guarantee
for failures during final writes or concurrent external database writers.

## Compatibility and limitations

The default remains `legacy` under the project's stable-API contract. Thus the
old learning attribution persists unless callers opt in; only the log fix
applies automatically. `search_batch` and other convenience methods have not
been switched globally. Python and the MCP `recall` tool support the option.

`final` is deliberately more conservative: it does not infer success from an
internal match, run the legacy spacing/effort gain, co-retrieval linking, or
rival suppression. It learns from every eligible returned result, not from
which one a downstream agent actually used. Pure semantic results without
lexical overlap do not gain familiarity through this helper. It does not prove
a returned fact is true or improve semantic understanding by itself.

Candidate passes use the existing read-only path, which bypasses the legacy
fallback-result cache. No latency claim is made for this mode. BM25 defaults
and standalone BM25 ranking are unchanged; fused recall already used final
familiarity settlement and was not redesigned here.

## Evidence

Fifteen new tests cover final attribution, duplicate-ID settlement, explicit
time, negative feedback, failure boundaries, read-only behavior, MCP and legacy
compatibility. The full suite passed 615 tests; capability regression passed
18/18 and the existing lifecycle probe passed.

`benchmarks/final_learning_eval.py` reuses nine explicit-date synthetic scenarios
from the temporal-selection benchmark. Each ran on Dict and SQLite for 30
queries: 540 queries per mode. Archived baseline and current legacy each
attributed learning to the distractor on all 18 paths. Final mode attributed
learning to the selected record on all 18 paths. Log/result agreement improved
from 0/540 in the archived baseline to 540/540 in both current modes.

Returned targets were already correct in all three modes: this measures
attribution, not an answer-accuracy gain. Repetitions and backends are coverage
variants, not independent held-out questions.
