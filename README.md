# Mnemosis

> 把 AI 的记忆，从“无限存储 + 搜索”改造成“会记住、会遗忘、会整理、会自我怀疑”的系统。

Mnemosis is a **human-inspired memory layer for AI agents**. Most "AI memory"
systems are just storage with semantic search bolted on: they save everything
and recall by similarity. Mnemosis instead treats memory as a **lifecycle** —
remembering, reinforcing, consolidating, forgetting, and reconciling — the way
human memory actually works.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/liyexiaoyi/Mnemosis/actions/workflows/ci.yml/badge.svg)](https://github.com/liyexiaoyi/Mnemosis/actions/workflows/ci.yml)

## Install

```bash
pip install git+https://github.com/liyexiaoyi/Mnemosis.git
```

Zero runtime dependencies (pure Python stdlib + SQLite). No server, no cloud
embeddings required — optional embedder hooks only.

> PyPI 版（`pip install mnemosis`）发布后会在这里同步更新。

## Quick start

```python
from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

engine = MemoryEngine("memory.db")  # pass a path for persistence

engine.remember(
    "The user prefers Chinese for technical discussions.",
    kind=MemoryKind.SEMANTIC,
    source=SourceRecord(origin=SourceType.USER),
    cues=["user", "language", "preference"],
    importance=0.9,
)

for r in engine.recall("what language does the user prefer?", top_k=3):
    print(f"[{r.item.kind.value}] {r.score:.2f}  {r.item.content}")

check = engine.check("what is the user's favorite movie?")
print("knowledge gaps:", check.gaps or "none")

engine.sleep()  # offline consolidation: dedupe, promote, detect contradictions
```

## 中文快速开始

```bash
pip install git+https://github.com/liyexiaoyi/Mnemosis.git
```

```python
from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

engine = MemoryEngine("memory.db")
user = SourceRecord(origin=SourceType.USER)

engine.remember(
    "用户喜欢用中文讨论技术问题。",
    kind=MemoryKind.SEMANTIC,
    source=user,
    cues=["语言", "偏好"],
    importance=0.9,
)
engine.remember(
    "昨天一起修了 SQLite 锁死的问题。",
    kind=MemoryKind.EPISODIC,
    source=user,
    cues=["SQLite", "锁死"],
)

for r in engine.recall("用户用什么语言聊天？", top_k=3):
    print(f"[{r.item.kind.value}] 相关度 {r.score:.2f}  {r.item.content}")
```

一分钟完整演示（记住 → 检索 → 新旧矛盾 → 睡眠整合 → 元认知 → 遗忘回收）：

```bash
pip install git+https://github.com/liyexiaoyi/Mnemosis.git
python examples/demo.py          # 仓库内
```

不想安装？直接在 [Google Colab 打开演示笔记本](examples/Mnemosis_demo.ipynb)。

## Use with your AI client (MCP)

One-line MCP integration for Claude Desktop, Cursor, Codex and any MCP client:

```json
{
  "mcpServers": {
    "mnemosis": {
      "command": "mnemosis-mcp",
      "args": ["--db", "/path/to/memory.db"]
    }
  }
}
```

Full guide (including Cursor and Codex configs): [`docs/mcp-quickstart.md`](docs/mcp-quickstart.md).

## Command line

```bash
mnemosis --db memory.db remember "用户喜欢用中文讨论技术问题。" --kind semantic
mnemosis --db memory.db recall "用户喜欢什么语言？"
mnemosis --db memory.db sleep
mnemosis --db memory.db check "用户最喜欢的电影是什么？"
mnemosis mcp --db memory.db   # or: mnemosis-mcp --db memory.db
```

## Features

- **Dual-track memory** — episodic ("what happened") and semantic ("what is
  true") stored and recalled separately (complementary learning systems).
- **Forgetting curve** — memories decay with time; access and review strengthen
  them (Ebbinghaus + spaced repetition).
- **Sleep consolidation** — offline pass promotes repeated experiences into
  stable knowledge, prunes noise, dedupes, and detects contradictions.
- **Source monitoring** — every memory keeps origin, timestamp, trust, and
  confidence, so the system can say "I'm not sure" instead of confabulating.
- **Active forgetting** — unimportant memories fade; deletions go to a
  recyclable trash, never silently.
- **Metacognition** — confidence labels, contradiction reports, and knowledge
  gaps before the agent answers.
- **Associative recall** — memories are indexed by multiple cues (time, topic,
  people, keywords) and linked, so any angle can reach them.
- **Pattern completion** — a partial cue re-activates a whole integrated
  pattern (Rolls, 2013; Theves et al., 2024).
- **Memory updating** — `update()` revises facts, tracks revisions, and
  destabilizes before re-stabilizing (Nader et al., 2000).
- **Chinese-optimized retrieval** — CJK stopword filtering, zh date
  normalization, pinyin/English-mixed records, verified at 10k-memory scale
  (total hit@5 50.3% → 98.8%).
- **Temporal reasoning** — time-cell anchored ordering for "after/before/next"
  questions (Eichenbaum, 2014; Gilboa & Marlatte, 2017).
- **Planning & reasoning memory** — successful plans, steps, and outcomes are
  remembered and reused; failed steps are avoided on replan.
- **Local-first, zero runtime dependencies** — pure Python stdlib + SQLite.

## Docs & research basis

- [`docs/memory-model.md`](docs/memory-model.md) — the memory model
- [`docs/research.md`](docs/research.md) — human-memory papers behind each feature
- [`docs/architecture.md`](docs/architecture.md) — architecture
- [`docs/mcp-quickstart.md`](docs/mcp-quickstart.md) — MCP integration
- [`docs/roadmap.md`](docs/roadmap.md) — roadmap
- [`CHANGELOG.md`](CHANGELOG.md) — every round of iteration, with measured results

## Testing

```bash
python -m unittest discover -s tests -q   # 319 unit tests
python benchmarks/locomo_bench.py --mode keyword   # LoCoMo-style long dialogue
```

## License

MIT. See [LICENSE](LICENSE).

## Contributing

PRs, issues and new benchmark scenarios are welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md). Every change should come with a test or a
measured benchmark result.
