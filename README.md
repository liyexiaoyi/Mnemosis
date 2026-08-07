# Mnemosis

> 把 AI 的记忆，从“无限存储 + 搜索”改造成“会记住、会遗忘、会整理、会自我怀疑”的系统。

Mnemosis is a **human-inspired memory layer for AI agents**. Most "AI memory"
systems today are just storage with semantic search bolted on: they save
everything and recall by similarity. Mnemosis instead treats memory as a
**lifecycle** — remembering, reinforcing, consolidating, forgetting, and
reconciling — the way human memory actually works.

- **Dual-track memory** — episodic ("what happened") and semantic ("what is
  true") are stored and recalled separately.
- **Forgetting curve** — memories decay with time; access and review
  strengthen them (Ebbinghaus + spaced repetition).
- **Sleep consolidation** — an offline pass promotes repeated experiences into
  stable knowledge, prunes noise, and detects contradictions.
- **Source monitoring** — every memory keeps its origin, timestamp, trust, and
  confidence, so the system can say "I'm not sure" instead of confabulating.
- **Active forgetting** — unimportant memories fade; deletions go to a
  recyclable trash, never silently.
- **Metacognition** — confidence labels, contradiction reports, and knowledge
  gaps before the agent answers.
- **Associative recall** — memories are indexed by multiple cues (time, topic,
  people, keywords) and linked, so any angle can reach them.
- **Context-dependent recall** — memories keep the context they were formed
  in, and recall boosts context matches (Godden & Baddeley, 1975).
- **Emotional persistence** — affect-tagged memories decay more slowly
  (Cahill & McGaugh, 1998).
- **Evidence accumulation** — repeated episodes consolidate into semantic
  facts whose confidence grows with supporting evidence (complementary
  learning systems; McClelland et al., 1995).
- **Blocking detection** — when cues match but recall fails, Mnemosis reports
  the "blocked" memories so the agent can try another route (Schacter, 1999).
- **Local-first, zero runtime dependencies** — pure Python `stdlib`, SQLite
  persistence, no server, no mandatory cloud embeddings (optional embedder
  hooks).

## Why another memory project?

The space is crowded (Mem0, Letta/MemGPT, Zep, Cognee, `cognitive-memory`,
`hippo-memory`, ...). We reviewed those projects and built Mnemosis around the
gaps they leave open:

| Capability | Mem0 | Letta | Zep | cognitive-memory | hippo-memory | **Mnemosis** |
|---|---|---|---|---|---|---|
| Episodic vs semantic dual track | partial | no | temporal graph | **missing (self-reported)** | partial | **first-class** |
| Forgetting curve / decay | expiry only | no | no | yes | yes | yes |
| Sleep consolidation + conflict detection | no | no | no | basic promotion | consolidation | **explicit + contradictions** |
| Active forgetting with recycle | no | no | no | removal | decay | **recycle bin** |
| Source monitoring + confidence | source list | no | no | basic | provenance | **trust + confidence labels** |
| Metacognition (gaps, contradictions) | no | agent-driven | no | basic | no | **explicit API** |
| Associative multi-cue recall | dynamic links | no | graph | no | no | **cue index + links** |
| Local-first, zero deps | no | no | no | needs Bedrock/Chroma | yes | **yes** |

## Quick start

```python
from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

engine = MemoryEngine()  # in-memory; pass a path for persistence

engine.remember(
    "The user prefers Chinese for technical discussions.",
    kind=MemoryKind.SEMANTIC,
    source=SourceRecord(origin=SourceType.USER),
    cues=["user", "language", "preference"],
    importance=0.9,
)

engine.remember(
    "Yesterday we debugged the SQLite locking issue together.",
    kind=MemoryKind.EPISODIC,
    source=SourceRecord(origin=SourceType.AGENT),
    cues=["sqlite", "debug", "yesterday"],
)

results = engine.recall("what language does the user prefer?", top_k=3)
for r in results:
    print(f"{r.item.kind.value:8s} {r.score:.2f}  {r.item.content}")

report = engine.sleep()          # consolidate: promote, prune, find conflicts
check = engine.check("sqlite")   # metacognition: confidence + gaps
```

## Architecture

```mermaid
flowchart LR
    A[Agent / LLM] -->|remember| E[MemoryEngine]
    A -->|recall| E
    E --> F[ForgettingCurve]
    E --> S[DualTrackStore]
    S -->|episodic| ES[(Episodic memories)]
    S -->|semantic| SS[(Semantic memories)]
    E --> AI[AssociationIndex]
    E --> C[Consolidator - sleep]
    E --> M[Metacognition]
    E --> R[RecycleBin]
    C -->|promote / prune / conflict| S
    M -->|confidence / gaps / contradictions| A
```

See [docs/architecture.md](docs/architecture.md) and
[docs/memory-model.md](docs/memory-model.md) for details, and
[docs/research.md](docs/research.md) for the paper-by-paper grounding.

## Roadmap

See [docs/roadmap.md](docs/roadmap.md). Near-term: MCP/CLI wrappers, optional
embedder backends (local + OpenAI-compatible), LLM-assisted consolidation,
and an evaluation harness.

## License

MIT. See [LICENSE](LICENSE).
