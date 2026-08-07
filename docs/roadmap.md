# Roadmap

## v0.2 — integrate with real agents

- [x] MCP server wrapper (memory tools: `remember`, `recall`, `sleep`, `check`)
- [x] CLI (`mnemosis remember "..."`, `mnemosis recall "..."`)
- [ ] Optional embedder backends: local (hash/char n-gram, tf-idf) and
      OpenAI-compatible API
- [x] LLM-assisted consolidation summarizer (episodic -> semantic summaries)

## v0.3 — evaluation

- [ ] Benchmarks: recall precision/recall, forgetting curve behavior,
      contradiction detection accuracy
- [ ] Deterministic test corpus + human-labeled golden set
- [ ] Comparison scripts against Mem0 / Letta / cognitive-memory

## v0.4 — richer cognition

- [ ] Memory reconstruction from fragments (fill partial recall from linked
      memories, with confidence adjustment)
- [ ] Cross-domain transfer (cue overlap between previously unrelated topics)
- [ ] Multi-user / multi-agent namespacing
- [ ] Encrypted-at-rest backend

## Later ideas

- Agent-managed memory hierarchy  with Mnemosis as the
  consolidation/metacognition layer
- Distributed backends (PostgreSQL adapter)
