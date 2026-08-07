# Benchmarks

## compare_with_models.py

Compares Mnemosis against local LLMs (via Ollama) on a small memory
benchmark: 6 synthetic memories (English + Chinese) and 6 fact-retrieval
questions. Three conditions:

1. `mnemosis_only` — does Mnemosis retrieval surface the correct memory?
2. `llm_alone` — can the LLM answer from parametric knowledge alone?
3. `llm_with_mnemosis` — LLM answers grounded in Mnemosis recall results.

```bash
python benchmarks/compare_with_models.py \
  --models gemma3:12b qwen2.5-vl:latest
```

Needs a running Ollama (`http://127.0.0.1:11434`). Any OpenAI-compatible
endpoint can be wired in the same way. Results are saved as JSON under
`benchmarks/results/`.

## Results (2026-08-07, local Ollama)

| Approach | Model | Accuracy | Avg LLM time |
|---|---|---|---|
| mnemosis_only | - | 1.000 | - |
| llm_alone | gemma3:12b | 0.000 | 3.0s |
| llm_with_mnemosis | gemma3:12b | 1.000 | 1.7s |
| llm_alone | qwen2.5-vl | 0.000 | 1.6s |
| llm_with_mnemosis | qwen2.5-vl | 1.000 | 0.5s |

The LLMs cannot recall arbitrary facts from parametric memory (0/6), while
grounding them in Mnemosis recall results lifts them to 6/6 — and Mnemosis
itself surfaces the correct memory 6/6. This is the expected pattern for
external memory systems: retrieval quality is the bottleneck, and grounding
fixes it.

## test_perf.py

Coarse regression guards: 1,000 memories must encode quickly and recall and
sleep must stay under generous bounds. Run with the rest of the suite:

```bash
python -m unittest discover -s tests
```

## locomo_bench.py

LoCoMo-style long-conversation memory evaluation: a deterministic synthetic
persona (4 people, 24 sessions, 5 dated events each) with 88 questions across
four categories — fact recall, event recall, temporal ordering, and
never-mentioned distractors.

```bash
python benchmarks/locomo_bench.py                 # retrieval only
python benchmarks/locomo_bench.py --with-llm      # + local LLM grounding
```

### Results (seed 42, deterministic)

| Mode | event hit@1 | event hit@5 | fact hit@1 | fact hit@5 | temporal anchor@5 |
|---|---|---|---|---|---|
| keyword | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| ngram embedder | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| BM25 baseline (hippo-memory-style) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 (anchor) / 0.083 (strict both) |

Distractor questions pass 16/16 (never-mentioned topics are reported as
knowledge gaps rather than confabulated).

LLM answer accuracy on a 12-question subset:

| Approach | gemma3:12b | qwen2.5-vl | qwen2.5:3b |
|---|---|---|---|
| llm_alone | 0.250 | 0.250 | 0.250 |
| llm_with_mnemosis | 0.92–1.00 | 0.83–0.92 | 0.750 |

Observed range across repeated runs: with perfect retrieval context, the
residual misses are model-side temporal reasoning (the correct event is
present in the context), not memory retrieval failures.

### Reading the temporal number

Temporal questions ("after X, what did Y do next?") are the hardest: retrieval
surfaces the anchor event 67% of the time (ngram), but the *next* event shares
no words with the query, so strict top-5 retrieval alone cannot find it. This
is expected — the full pipeline resolves it by retrieving the anchor and
letting the LLM reason over the linked neighborhood (see the LLM rows above).

Two refinements made temporal reasoning tractable:

- Temporal questions are disambiguated with the anchor event's date (like a
  real conversation would); with ngram embeddings all retrieval metrics hit
  1.000.
- For temporal questions the LLM context is sorted chronologically with dates
  attached, which lets the model reason about order instead of guessing from
  score order.

### Distractor behavior (confabulation guard)

Mnemosis reports knowledge gaps for all 16 never-mentioned topics (16/16).
BM25 — which has no metacognition — returns the most lexically similar memory
for every one of them (0/16), e.g. answering "What is Alice's favorite music
genre?" with "Alice's favorite color is amber."

### Reproducibility

Results are deterministic for a fixed seed (tie-breaking is by
`(created_at, content)`, never by random ids or set iteration order).

Scale check (10,000 events, 4,040 questions, keyword mode, ~8 min):

| Category | hit@1 | hit@5 | MRR |
|---|---|---|---|
| event | 0.971 | 0.971 | 0.971 |
| fact | 1.000 | 1.000 | 1.000 |
| temporal | 0.972 | 0.906 | 0.973 |
| total | 0.968 | 0.935 | 0.968 |

The association graph stays sparse (per-item link budget of 64), so ingestion
scales without all-pairs explosion.

## lifecycle_eval.py

Validates the forgetting/updating promises without any LLM:

```bash
python benchmarks/lifecycle_eval.py
```

Results (30 simulated days, seed-free deterministic):

- Spaced review keeps memories strong: correct-memory average recall score
  0.343 (reviewed weekly) vs 0.260 (never reviewed) — 32% higher.
- Emotional persistence: retrievability 0.421 for affect-tagged vs 0.237 for
  neutral memories after 30 days.
- `update()` replaces stale facts cleanly (old content no longer surfaces)
  and sleep detects the planted contradiction.
- At 1,000 memories, updating one fact still fully replaces it (no stale copy
  survives) and two WAL connections see each other's writes.
- Learning curve: re-answering the same 88 questions three times keeps
  hit@1 perfectly stable at 0.818 (retrieval-induced forgetting is bounded:
  only true query competitors are suppressed, strength never drops below 0.7).

`--sleep` mode on locomo_bench verifies consolidation does not hurt
retrieval: after `engine.sleep()`, fact/event hit@1 stay 1.000 and temporal
strict@5 stays 0.625 (ngram).
