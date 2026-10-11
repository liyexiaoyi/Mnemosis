# Mnemosis

> 仿生设计的 AI Agent 长期记忆层：记住、检索、强化、遗忘、整合，并保留不确定性。

Mnemosis is a **human-inspired memory layer for AI agents**. It manages the
life of a memory: episodic experiences and semantic facts, retrieval and
reinforcement, forgetting and review, consolidation and explicit feedback.
The agent chooses what to store and how to use the returned evidence.

The core runs locally with **Python 3.10+ and SQLite, with no third-party
runtime dependencies**. Dense embeddings, NumPy acceleration, a Rust BM25
kernel and local-model evidence annotation are optional.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/liyexiaoyi/Mnemosis/actions/workflows/ci.yml/badge.svg)](https://github.com/liyexiaoyi/Mnemosis/actions/workflows/ci.yml)
[![Open in GitHub Codespaces](https://img.shields.io/badge/Codespaces-Open-181717?logo=github)](https://codespaces.new/liyexiaoyi/Mnemosis)

**[中文介绍](README.zh-CN.md)** · [Beginner guide / 零基础教程](奶龙级入门教程——基本功能介绍版.md) · [Storage design / 存储设计](存储功能介绍（技术人员版）.md)

## What makes it biomimetic?

| Mechanism | What it does | Boundary |
| --- | --- | --- |
| Episodic + semantic memory | Keeps experiences and reusable facts in separate tracks. | Stored claims still depend on their sources. |
| Association + reinforcement | Uses cues and links to recall related memories and strengthen accessibility. | Familiarity is not factual correctness. |
| Forgetting + spaced review | Models changing accessibility and schedules review. | Decay is not a fact's expiry date. |
| Sleep consolidation | Replays, deduplicates, links and consolidates memories; tracks source contributions. | Distinct source records need not be independent or verified. |
| Explicit feedback + metacognition | Records caller judgments and reports gaps, uncertainty and conflicts. | A confidence value does not guarantee a true answer. |

These are engineering mechanisms inspired by memory, not a biological brain
simulation. Read-only recall and diagnostics let applications inspect memory
without reinforcing it. See [feedback and source boundaries](docs/biomimetic-feedback.md).

## Install

Install the default GitHub branch:

```bash
python -m pip install git+https://github.com/liyexiaoyi/Mnemosis.git
```

To run examples or work on the source:

```bash
git clone https://github.com/liyexiaoyi/Mnemosis.git
cd Mnemosis
python -m pip install -e .
python examples/demo.py
```

## Quick start

```python
from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

engine = MemoryEngine("memory.db", auto_warmup=False)
try:
    engine.remember(
        "Alice prefers green tea.",
        kind=MemoryKind.SEMANTIC,
        source=SourceRecord(origin=SourceType.USER),
        cues=["Alice", "tea", "preference"],
        importance=0.9,
    )

    # Inspect without changing persistent learning state.
    for result in engine.recall("Alice tea preference", top_k=3, read_only=True):
        print(result.item.content, result.score)

    print("knowledge gaps:", engine.check("Alice's favorite movie").gaps)
    engine.sleep()  # offline consolidation
finally:
    engine.close()
```

`remember_turn` splits and stores a conversation turn; `remember_many`
imports batches. The caller decides what is worth retaining.
Normal recall may reinforce memories; use `read_only=True` for evaluation or
candidate inspection. A retrieval score measures ranking, not truth probability.

## Connect an agent with MCP

After installation, add this configuration to an MCP-compatible client:

```json
{
  "mcpServers": {
    "mnemosis": {
      "command": "mnemosis-mcp",
      "args": ["--db", "/absolute/path/to/memory.db"]
    }
  }
}
```

On Windows, put Python's `Scripts` directory on `PATH` or use the absolute
path to `mnemosis-mcp.exe`. Use `--expose core` for everyday tools,
`--expose advanced` for the default set, or `--expose experimental` to include
experimental tools. See [MCP setup](docs/mcp-quickstart.md).

```bash
mnemosis --db memory.db remember "Alice prefers green tea." --kind semantic
mnemosis --db memory.db recall "Alice tea"
mnemosis --db memory.db check "Alice's favorite movie"
mnemosis --db memory.db sleep
mnemosis-mcp --db memory.db --expose core
```

Streamable HTTP is also available with `--transport http --host 127.0.0.1 --port 8000`.
For remote access, configure authentication and TLS at the
deployment boundary. SQLite suits local, single-process use; serialize
high-level calls when sharing an engine across concurrent agent loops.

## Retrieval and mathematical models

The existing biomimetic recall remains the default. Additional strategies
are **opt-in**, with separate mathematical responsibilities:

| Component | Approach | Documentation |
| --- | --- | --- |
| Lexical retrieval | BM25 uses term frequency, rarity and record length; optional bounded RRF fusion. | [BM25](docs/bm25-cues.md) |
| English word forms | Grouped inflection cues with bounded overlap and mean-rarity normalization. | [Inflection cues](docs/inflection-cues.md) |
| Candidate admission | Protects 64 lexical candidates and up to 36 eligible vector candidates, with lexical refill to 100. | [Quota admission](docs/candidate-admission.md) |
| Semantic reranking | Allocates the existing rerank budget to admitted vector candidates while retaining primary candidates where possible. | [Mathematical responsibilities](docs/mathematical-models.md) |
| Evidence composition | Combines relevance with weighted, saturated aspect coverage; optional refinement and required-role constraints. | [Evidence selection](docs/evidence-selection.md), [ranked evidence](docs/ranked-evidence.md) |
| Feedback calibration | Smoothed outcome estimates and population-weighted calibration statistics. | [Calibration](docs/calibration-statistics.md) |

Candidate coverage, rank scores, evidence utility and feedback estimates
are different quantities. Improving one does not prove better final answers.
Quota admission requires a matching vector index and embedder. Supplied
evidence labels remain a caller responsibility.

For dense embeddings, run a local embedding service and configure it explicitly:

```bash
mnemosis-mcp --db memory.db --embedder ollama
```

Embedding caches and vector indexes are stored beside the database and can
be rebuilt. Python orchestrates the memory lifecycle; SQL handles storage,
NumPy can accelerate vector operations and Rust can accelerate BM25 scoring.
See [language boundaries](docs/module-languages.md), [Rust setup](docs/rust-bm25.md)
and [vector acceleration](docs/vector-acceleration.md).

## Experimental grounded evidence recall

`MemoryEngine.recall_evidence` connects read-only retrieval to local-model
role annotations, unique exact source quotations and bounded mathematical
evidence selection. It requires an explicitly configured annotator; the
MCP tool also requires experimental exposure.

Reports distinguish `feasible`, `infeasible`, `undetermined`,
`annotation_failed` and `not_applicable`. Missing support remains unknown.
An exact quotation checks the source text, **not semantic entailment or
factual truth**. Incorrect roles, reversed actions, incomplete quotes and
timeouts remain known limitations. This path is not the default.

See the [API, budgets and status semantics](docs/evidence-recall.md).

## Validation and benchmarks

The 2026-10-11 local checkpoint passed **1,399 tests and 374 subtests** with
the available NumPy/Rust backends, plus 18 capability checks. A frozen
704-query replay previously preserved original recall rankings and storage
state across 20 configurations. These are regression checks, not a market ranking.

Public-data retrieval subsets and authored mathematical cases exercise
different stages. Candidate admission gains have not established a final
Top-k accuracy gain. Recent support-prompt experiments regressed and were
reverted. See [validation status and limitations](docs/evaluation-status.md).

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python benchmarks/ci_regression.py
```

Optional native checks require the relevant backend to be installed and
enabled; see [Rust verification](docs/rust-bm25.md). Local timings depend on
hardware, data, models and cache state.

The repository includes a LongMemEval comparison runner:

```bash
python benchmarks/fetch_longmemeval.py
python benchmarks/longmemeval_bench.py --data work/longmemeval_s_cleaned.json --questions 20
```

Comparison dependencies and model services must be configured separately.
Sampled historical comparisons are not a claim of general superiority over
other agent-memory projects.

## Contributing and license

[Contributions](CONTRIBUTING.md), reproducible benchmarks and failure cases
are welcome. See the [roadmap](docs/roadmap.md). Licensed under [MIT](LICENSE).
