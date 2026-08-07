# Architecture

Mnemosis is a small, dependency-free Python library. The public entry point is
`mnemosis.MemoryEngine`; everything else is a swappable component.

## Modules

| Module | Responsibility |
|---|---|
| `types.py` | Core data model: `MemoryItem`, `SourceRecord`, `MemoryKind`, `RecallResult` |
| `forgetting.py` | Exponential decay, access reinforcement, spaced-review scheduler |
| `importance.py` | Rule-based importance scoring with an optional LLM scorer hook |
| `backend.py` | Storage abstraction: `DictBackend` (tests/quickstart) and `SQLiteBackend` (persistence) |
| `dual_track.py` | Episodic vs semantic stores: encode, upsert, recall |
| `association.py` | Cue index + link graph for associative recall |
| `consolidation.py` | Offline "sleep" pass: promotion, pruning, dedupe, conflict detection |
| `metacognition.py` | Confidence labels, contradiction reports, knowledge gaps |
| `recycle.py` | Soft-delete recycle bin with restore and purge |
| `engine.py` | Facade wiring everything together: `remember`, `recall`, `sleep`, `forget`, `restore`, `check` |
| `cli.py` | `argparse` command-line interface over `MemoryEngine` |
| `mcp_server.py` | Stdlib-only stdio MCP server (JSON-RPC 2.0) exposing the engine as tools |

## Data flow

```text
remember(content, kind, source, cues, importance)
  -> MemoryItem (hash, timestamps, strength=1.0)
  -> DualTrackStore.add / upsert (semantic dedupe by content hash)
  -> AssociationIndex: index cues, link to related active memories

recall(query)
  -> candidates from the requested track(s)
  -> score = keyword overlap + importance + retrievability
  -> reinforce accessed items (strength +, access_count +)
  -> schedule next review

sleep()
  -> Consolidator.sleep():
       promote episodic -> semantic (access >= 2, age >= threshold, importance)
       prune low-value stale episodic memories into RecycleBin
       detect contradictions among confident semantic memories
       reflect(): rewrite evidence-backed semantic facts as abstractions
                  of their supporting episodes (optional LLM summarizer)

check(query)
  -> Metacognition: confidence labels on recalled items,
     knowledge gaps, open contradictions
```

## Storage schema (SQLite)

```sql
memories(id, kind, content, content_hash, source_json, cues_json,
         created_at, last_access_at, access_count, importance,
         strength, confidence, status)
links(src, dst, weight)          -- associative links
cues(cue, memory_id)             -- multi-cue index
```

`memories` has a unique constraint on `(kind, content_hash)` so semantic facts
are deduplicated on write.

## Design rules

1. **Zero runtime dependencies.** Core must stay `stdlib`-only.
2. **Deterministic by default.** No randomness in scoring unless explicitly
   seeded; every decision is explainable.
3. **Pluggable, not coupled.** Embedders and LLM scorers are optional callbacks;
   the core works without them.
4. **Nothing is deleted silently.** All forgetting flows through the recycle
   bin.
