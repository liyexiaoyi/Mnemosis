# Mnemosis

> 把 AI 的记忆，从“无限存储 + 搜索”改造成“会记住、会遗忘、会整理、会自我怀疑”的系统。

Mnemosis is a **human-inspired memory layer for AI agents**. Most "AI memory"
systems are just storage with semantic search bolted on: they save everything
and recall by similarity. Mnemosis instead treats memory as a **lifecycle** —
remembering, reinforcing, consolidating, forgetting, and reconciling — the way
human memory actually works.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/liyexiaoyi/Mnemosis/actions/workflows/ci.yml/badge.svg)](https://github.com/liyexiaoyi/Mnemosis/actions/workflows/ci.yml)
[![Open in GitHub Codespaces](https://img.shields.io/badge/Codespaces-一键打开-181717?logo=github)](https://codespaces.new/liyexiaoyi/Mnemosis)

中文说明：[README.zh-CN.md](README.zh-CN.md) · English: README.md

## Install

```bash
pip install git+https://github.com/liyexiaoyi/Mnemosis.git
```

Zero runtime dependencies (pure Python stdlib + SQLite). No server, no cloud
embeddings required — optional embedder hooks only.

> PyPI 版（`pip install mnemosis`）发布后会在这里同步更新。

SQLite 存储适合单进程/低并发场景；多个 Agent 并发写入时建议串行访问或接入
外部数据库适配层。

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

不想安装？可以在线体验：

- [Google Colab 打开演示笔记本](https://colab.research.google.com/github/liyexiaoyi/Mnemosis/blob/main/examples/Mnemosis_demo.ipynb)
  （部分地区访问不了 Colab，可改用下面的方式）
- [GitHub Codespaces 一键打开](https://codespaces.new/liyexiaoyi/Mnemosis)：云端环境，
  打开终端执行 `python examples/demo.py` 即可
- 下载 `examples/Mnemosis_demo.ipynb` 后，用本地 Jupyter 或百度 AI Studio 打开

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

**Windows users**: if the client reports that `mnemosis-mcp` is not found,
add Python's `Scripts` directory to `PATH`, or use an absolute path, e.g.
`"command": "C:\\Users\\you\\AppData\\Local\\Programs\\Python\\Python312\\Scripts\\mnemosis-mcp.exe"`.

Full guide (including Cursor and Codex configs): [`docs/mcp-quickstart.md`](docs/mcp-quickstart.md).

## Command line

```bash
mnemosis --db memory.db remember "用户喜欢用中文讨论技术问题。" --kind semantic
mnemosis --db memory.db recall "用户喜欢什么语言？"
mnemosis --db memory.db sleep
mnemosis --db memory.db check "用户最喜欢的电影是什么？"
mnemosis mcp --db memory.db   # or: mnemosis-mcp --db memory.db
```

## Threading

`MemoryEngine` is designed for one agent loop per instance: SQLite access and
the shared intent / suppression state are internally locked, so light
concurrent read/write calls are safe. If you fan one engine out across many
threads, serialize the high-level calls yourself.

## Testing

```bash
python -m unittest discover -s tests -q   # 320 unit tests
python benchmarks/locomo_bench.py --mode keyword   # LoCoMo-style long dialogue
```

## License

MIT. See [LICENSE](LICENSE).

## Contributing

PRs, issues and new benchmark scenarios are welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md). Every change should come with a test or a
measured benchmark result.
