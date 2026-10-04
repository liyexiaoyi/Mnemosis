# Source-aware event time (opt-in)

Mnemosis can use occurrence timestamps when an episode's body omits its date. Enable `temporal_policy="source"` on `MemoryEngine.recall` or `temporal_anchor`. The default `"content"` retains the earlier date behavior. This policy is separate from the learning policy.

```python
from datetime import datetime, timezone
from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

clock = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
with MemoryEngine() as engine:
    engine.remember(
        "私教课练胸。", kind=MemoryKind.EPISODIC,
        source=SourceRecord(
            SourceType.USER,
            occurred_at=datetime(2026, 9, 1, 10, tzinfo=timezone.utc),
        ),
        created_at=clock,
    )
    results = engine.recall(
        "上次私教课练了什么？", now=clock,
        temporal_policy="source", read_only=True,
    )
```

For a learning query, set `learning_policy="final"` alongside the source policy to attribute familiarity to final returned lexical matches. Leaving learning at `"legacy"` preserves its previous behavior, including its candidate-based learning. Neither policy creates verified feedback or factual evidence from a retrieval.

## Interpretation

- The resolver accepts numeric Chinese year/month/day, ISO dates, and month/day forms with a consistent source year. It examines body and cues together.
- A single body date is preserved. An aware episodic source supplies a fallback or compatible sub-day precision. Semantic-source timestamps do not establish present factual validity.
- Multiple distinct dates, invalid dates, reference/birthday markers, body/source disagreement, and naive source timestamps remain uncertain. This is a conservative parser, not a general event or entity extractor.
- The query clock must be aware under the source policy. Its timezone defines calendar dates. Actual source instants are compared in UTC, including clock rollback; body-only dates have day precision.
- Import, update and access clocks are never substituted for event time.
- A missing date/direction match marks returned contextual rows uncertain. This signal is not an answer generator or a calibrated truth probability.
- `RecallResult.reasons` exposes the time basis or uncertainty; `confident` may be reduced but existing uncertainty is not upgraded. MCP recall exposes both fields; its `confidence` remains the stored item confidence, a different quantity.
- Source time selection runs after the other anchors. It retains kind, exclusion, suppression and recycling checks and uses the existing bounded anchor candidate pool. Within that pool, common generic word overlap does not outweigh more specific lexical support. This remains a heuristic.

## Event chains and entry points

Source-policy recall creates a source-aware event chain using the same resolver and query timezone. `EventChainIndex(backend, date_policy="source", event_timezone=...)` also supports direct use. It excludes ambiguous events and fingerprints grouping/source fields so source updates refresh a reused chain. Person/session grouping still follows the existing cue convention; formal entity and context boundaries are future work.

The source chain scans episodic records; it is not an incremental temporal index. The small synthetic timings are insufficient for a scale or Rust migration decision.

MCP `recall` and `temporal_anchor` accept `temporal_policy`. Python `temporal_anchor` also accepts an explicit query clock. BM25, fused recall, search_batch and other convenience paths have not globally adopted this policy. MCP remember still has its existing input contract; timestamped episodes can be supplied through Python or import.

No storage migration is required. Existing same-content deduplication is unchanged: identical repeated events may still merge, so this batch does not provide a full fact-version or repeated-event model.

## Verification

The 2026-10-04 batch adds 24 behavioral tests, with 639 full tests and the 18 existing capability checks passing. Frozen authored synthetic time trajectories improve known-target first-result selection from 1/12 to 12/12 and produce uncertainty signals for all 8 time-unknown/conflict trajectories. The acceptance portion contains 5 known and 3 uncertain time trajectories. These are regression scenarios with related templates, not an external blind benchmark or answer-accuracy estimate.

All three previous modes replayed exactly over 720 synthetic executions. Ten previously used LongMemEval questions × four modes retain identical returned references, scores and retrieval metrics. That historical regression does not measure source-policy LongMemEval gains. BM25's `confident=False` channel convention is not calibrated abstention.
