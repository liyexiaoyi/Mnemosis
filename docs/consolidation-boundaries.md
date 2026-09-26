# Consolidation boundaries

Sleep and `resolve_conflicts()` now share the same lexical candidate checks
before evidence-based accommodation can recycle a semantic trace. Sharing a
cue alone is insufficient: the contents must also share a non-cue topic token.
A pair is accepted if any shared cue meets the topic check, independent of cue
insertion order (subject to the existing per-cue pair budget).

Known different `context` strings or known different `source.occurred_at`
instants keep records separate. These fields already exist and survive SQLite
reopening; no schema migration or API option is needed. Equivalent timezone
representations of one instant still compete. `created_at` and access times
are not used as fact validity dates. If either record lacks a scope field,
the existing lexical heuristic remains the fallback.

The same boundary guard protects against REM confidence reduction for known
separate scopes. Once a trace is recycled, it cannot compete with another
trace later in the same accommodation pass. The existing confidence threshold,
3:1 evidence rule, source-trust requirement, and pairing budgets remain.
Retirement is still recoverable via `restore`; it is not permanent deletion.

## Scope and limitations

This is a guard against destructive consolidation, not a general contradiction
classifier or current-versus-historical retrieval API. Topic overlap does not
prove that two claims contradict each other. Same-subject attributes, negation,
and entity identity in unstructured text still require better disambiguation.
Caller-provided context and event dates improve protection; automatic context
extraction is heuristic. Missing metadata cannot protect a historical fact.
Different event dates may also describe a genuine disagreement: retaining both
is intentionally conservative. This can leave more candidates for retrieval.

This patch does not change exact-content semantic deduplication, episodic
merging, promotion, retrieval ranking, or infer validity intervals. Those
paths are separate limitations; it does not guarantee that every historical
version is retained, or that a current query selects the latest valid fact.

## Verification

`tests/test_consolidation_boundaries.py` covers both storage backends, repeated
sleep, explicit conflict resolution, cache synchronization, SQLite reopening,
timezone equivalence, missing metadata, trust, balanced evidence, and retired
candidates. The targeted synthetic evaluation is reproducible with:

```powershell
$env:PYTHONPATH = 'E:\Mnemosis\repo\src'
python benchmarks/consolidation_boundaries_eval.py --workdir E:/Mnemosis/evaluation/scratch --output E:/Mnemosis/evaluation/results/phase4_current.json
```

The same evaluator was run against archived commit `e61bf1c` and the new source:
10 synthetic cases × 2 backends × 2 operations = 40 paths, each checked after
operations at days 0/7/30/90. Protection cases improved from 0/24 to 24/24;
retirement/uncertainty controls stayed at 16/16. These are targeted regression
fixtures, not independent held-out questions or evidence of market superiority.
