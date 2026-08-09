# Roadmap

## v0.2 — integrate with real agents

- [x] MCP server wrapper (memory tools: `remember`, `recall`, `sleep`, `check`)
- [x] CLI (`mnemosis remember "..."`, `mnemosis recall "..."`)
- [x] Optional embedder backends: local `NGramEmbedder` (hash/char n-gram)
      and OpenAI-compatible APIs via `CallableEmbedder`
- [x] LLM-assisted consolidation summarizer (episodic -> semantic summaries)

## v0.3 - evaluation

- [x] Local LLM comparison harness (`benchmarks/compare_with_models.py`)
- [x] LoCoMo-style long-conversation harness (`benchmarks/locomo_bench.py`)
- [x] Larger scale: recall precision/recall at 10k+ memories, forgetting curve
      behavior, contradiction detection accuracy
- [x] Deterministic test corpus (24/100/200/400/800 sessions, 88 questions)
- [x] Baseline scripts against BM25 / kNN / local embeddings

## v0.4 - richer cognition

- [x] Event-chain schema recall (chronological successor boost; Gilboa &
      Marlatte 2017)
- [x] Spaced-repetition feedback loop (`review_due()` / `review()`)
- [x] Sleep replay + near-duplicate dedup
- [ ] Memory reconstruction from arbitrary fragments - partial-cue track
      prototyped, reverted (noisy at scale)
- [ ] Cross-domain transfer (cue overlap between previously unrelated topics)

## Later ideas

- Agent-managed memory hierarchy with Mnemosis as the consolidation/metacognition layer
- Distributed backends (PostgreSQL adapter)
