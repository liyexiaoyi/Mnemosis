# Mnemosis

> 像人脑一样记事的 AI 记忆层：会记住、会遗忘、会整理、会自我怀疑。

Mnemosis 是一个为 AI 助手设计的**长期记忆组件**。它不是简单地“存下所有内容再搜索”，
而是把记忆当成一个完整的生命周期来管理：写入、加固、整合、遗忘、更新，每一步都有
对应的机制，让 AI 在需要时想得起、说得准，没把握时敢说“不知道”。

## 特性

- **双通道记忆**：事件（发生了什么）和事实（什么是真的）分开存储、分开检索。
- **遗忘曲线**：记忆会随时间衰减，访问和复习会增强它（符合间隔复习原理）。
- **睡眠整合**：离线整理——去重、提炼事实、检查矛盾，像人睡觉时巩固记忆。
- **来源监控**：每条记忆都带来源、时间、可信度，不把道听途说当事实。
- **主动遗忘**：不重要的记忆会淡出；删除先进回收站，可恢复，不静默丢失。
- **元认知**：回答前先检查知识缺口和矛盾，没把握时如实说不知道。
- **联想检索**：时间、主题、人物、关键词多路索引，换个说法也能找到。
- **模式补全**：给一个部分线索，能激活完整相关记忆。
- **记忆更新**：事实改变时更新旧记录，并保留修订痕迹。
- **中文优化**：中文日期、拼音、英文混排都能正确检索，1 万条记忆规模下实测有效。
- **时序推理**：能回答“上次/下次/之后/之前”这类带时间顺序的问题。
- **规划与推理记忆**：记住成功的计划和步骤，失败步骤下次会避开。
- **本地优先、零依赖**：纯 Python 标准库 + SQLite，无服务器、无强制云端依赖。

## 安装

```bash
pip install git+https://github.com/liyexiaoyi/Mnemosis.git
```

安装后有两个命令：

- `mnemosis` —— 命令行工具
- `mnemosis-mcp` —— MCP 服务器（给 AI 客户端接入用）

## 快速开始

```python
from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

engine = MemoryEngine("memory.db")  # 传一个路径即可持久化
user = SourceRecord(origin=SourceType.USER)

# 记住
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

# 检索（换个说法也能找到）
for r in engine.recall("用户用什么语言聊天？", top_k=3):
    print(f"[{r.item.kind.value}] 相关度 {r.score:.2f}  {r.item.content}")

# 元认知：没把握就直说
check = engine.check("用户最喜欢的电影是什么？")
print("知识缺口:", check.gaps or "无")

# 睡眠整合：离线去重、提炼、查矛盾
print(engine.sleep().summary())
```

不想写代码？先跑一分钟演示：

```bash
pip install git+https://github.com/liyexiaoyi/Mnemosis.git
python examples/demo.py
```

或在 [Google Colab](examples/Mnemosis_demo.ipynb) 在线体验。

## 命令行

```bash
# 记住一条事实
mnemosis --db memory.db remember "用户喜欢用中文讨论技术问题。" --kind semantic

# 检索
mnemosis --db memory.db recall "用户喜欢什么语言？"

# 睡眠整合
mnemosis --db memory.db sleep

# 元认知检查
mnemosis --db memory.db check "用户最喜欢的电影是什么？"

# 启动 MCP 服务器
mnemosis mcp --db memory.db
```

## 接入 AI 客户端（MCP）

Claude Desktop、Cursor、Codex 等支持 MCP 的客户端，加一行配置即可：

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

详细配置（含 Cursor、Codex 写法）见 [`docs/mcp-quickstart.md`](docs/mcp-quickstart.md)。

## 测试

```bash
python -m unittest discover -s tests -q   # 320 项单元测试
python benchmarks/locomo_bench.py --mode keyword   # LoCoMo 式长对话评测
```

## 文档

- [`docs/memory-model.md`](docs/memory-model.md) —— 记忆模型设计
- [`docs/research.md`](docs/research.md) —— 背后的认知科学研究
- [`docs/architecture.md`](docs/architecture.md) —— 架构说明
- [`docs/mcp-quickstart.md`](docs/mcp-quickstart.md) —— MCP 接入指南
- [`docs/roadmap.md`](docs/roadmap.md) —— 路线图
- [`CHANGELOG.md`](CHANGELOG.md) —— 版本记录

## 许可

MIT，见 [LICENSE](LICENSE)。

## 参与贡献

欢迎提 Issue、提交 PR。每项改动请附带测试或实测结果，详见
[CONTRIBUTING.md](CONTRIBUTING.md)。
