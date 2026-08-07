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

