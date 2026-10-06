# Optional quota candidate admission

`MemoryEngine.recall(..., candidate_policy="quota")` only changes the initial candidate membership. The default is `"legacy"`; existing callers neither require nor search a vector index.

Let L be the original lexical preselection ranking (at most 100 distinct IDs), and D the first 36 eligible IDs from a single independent index lookup of at most 100 hits. Admit

```text
P = L[:64] union D
A = P plus the earliest IDs in L[64:] not already in P, until size 100
```

Duplicates across channels occupy one slot. The returned ID order from the pure helper is an admission report, not a relevance score. Recall loads the union in sorted ID order and applies its existing scoring and completion stages.

Since |L[:64]| <= 64 and |D| <= 36, |P| <= 100. Refill only adds unused IDs and never exceeds 100, so L[:64] and D are both protected, and |A| = min(100, |L union D|). Empty channels do not invent candidates. These guarantees concern admission, not the final Top-k or the 64 reranking slots.

For a zero lexical hit, the existing recent/strong fallback supplies L instead. Only the opt-in path caps this initial fallback admission at 100 and dense reranking at min(configured limit, 64). Legacy fallback limits remain unchanged.

## Use

The query embedder must be the same object as `engine.index_embedder`. The caller is responsible for an index built from that model and dimension, kept current through writes. Object identity does not verify persisted model provenance or detect outdated content vectors. `rebuild_missing_vectors()` repairs missing IDs, not stale vectors or a model change.

The following dependency-free example demonstrates the API, not real semantic retrieval quality. An application may supply its own semantic embedder in the same positions.

```python
from mnemosis import MemoryEngine
from mnemosis.embedding import NGramEmbedder
from mnemosis.vector_index import VectorIndex

embedder = NGramEmbedder(dimension=256)
index = VectorIndex(dim=256)
engine = MemoryEngine(
    embedder=embedder, vector_index=index, index_embedder=embedder,
    auto_warmup=False,
)
try:
    engine.remember(
        "Oren stores the spare key in the jade cupboard.",
        cues=[], auto_cues=False, auto_context=False,
    )
    results = engine.recall(
        "Where is Oren's spare key?",
        candidate_policy="quota", read_only=True,
    )
finally:
    engine.close()
```

Wrong or missing index/embedder configurations raise ValueError. Malformed or non-finite index hits and index failures are surfaced, not silently downgraded to an empty channel. Unknown, inactive, wrong-kind, suppressed and explicitly excluded IDs are filtered before taking D. This is the first 36 eligible hits within the bounded lookup, not a promise to find the globally best 36 active hits when more than 100 stale/excluded entries lead the index results.

No unindexed dense scan or query-time backfill is added. The existing index itself may use an exact full matrix scan for small/medium stores; requesting 100 hits does not mean only 100 vector comparisons. The additional independent lookup adds work beyond the 64 existing dense reranking slots.

## Scope and validation

The original lexical/biomimetic score formulas, weights, association, temporal reasoning, premise packing, completion and result anchors are preserved. The quota mode bypasses the legacy fallback result cache because that key does not capture index revisions. Concept-coverage subqueries and later expansions retain their existing paths; the 100/64 guarantees apply to the initial main store pass, not every later stage in a query.

The optional English inflection policy is independent and can be combined explicitly; this feature does not change the lexical default or CJK tokenization. The later evidence selectors remain independent and are not connected by quota admission.

A regression exposed an existing SQLite list_strongest bug: its kind condition followed ORDER BY and produced invalid SQL. The condition now precedes ORDER BY; both backends have a permanent read-only kind/status/limit regression.

Validation on the frozen 2026-10-06 protocol:
- 58 new regression configurations; full suite 1038 tests and 374 subtests; CI 18/18.
- 148 public questions, paired legacy/quota with real frozen nomic768 vectors; 592 plain/observed queries and 296 persisted-ID replays.
- New public 80: initial pool contains all required evidence on 49 -> 60 questions (12 gains, 1 loss); final Top5 all evidence remains 33 -> 33; multi-evidence 6/39 -> 6/39.
- Historical 68: initial coverage 47 -> 52 (7 gains, 2 losses); final all evidence 34 -> 34; any-evidence Top5 45 -> 44.
- Of 17 newly admitted necessary-evidence occurrences in the new 80 questions, none received the current dense reranking or reached Top5.

This is an opt-in admission improvement, with no demonstrated final retrieval accuracy gain. These are retrieval-only subsets of public data, not blind evaluation or the official full LoCoMo QA score. The next separately designed stage should examine allocation of the 64 reranking slots before testing evidence composition; admitting a candidate does not automatically grant it semantic reranking.

