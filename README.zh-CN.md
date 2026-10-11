# Mnemosis

> 仿生设计的 AI Agent 长期记忆层：记住、检索、强化、遗忘、整合，并保留不确定性。

Mnemosis 将记忆作为一个完整生命周期管理：用情景记忆保存经历，用语义记忆保存
可复用的事实，通过线索联想、访问强化、遗忘曲线、间隔复习和睡眠整合组织长期记忆。
Agent 决定存什么、问什么，以及如何使用返回的证据。

核心使用 **Python 3.10+ 和 SQLite，零第三方运行时依赖**，可以本地运行。
语义向量模型、NumPy 加速、Rust BM25 内核与本机模型证据标注均按需启用。

**[English](README.md)** · [零基础教程](奶龙级入门教程——基本功能介绍版.md) · [存储设计](存储功能介绍（技术人员版）.md)

## 仿生设计体现在哪里？

| 机制 | 对应能力 | 使用边界 |
| --- | --- | --- |
| 情景／语义双轨 | 分别管理具体经历与可复用事实。 | 记录内容的可靠性仍取决于来源。 |
| 联想与强化 | 利用线索和关联唤起记忆，调整可访问性。 | 熟悉度不等于事实正确。 |
| 遗忘与间隔复习 | 描述记忆随时间的可检索强度，安排复习。 | 遗忘曲线不决定事实有效期。 |
| 睡眠整合 | 回放、去重、建联、整合，记录来源贡献。 | 不同来源记录不一定独立或已核实。 |
| 显式反馈与元认知 | 接收调用方有用／无用判断，提示缺口、不确定性和冲突。 | 置信值不保证最终回答正确。 |

这是受记忆机制启发的工程设计，并不等于生物大脑仿真。
只读检索与诊断允许检查记忆而不强化它，详见[反馈与证据边界](docs/biomimetic-feedback.md)。

## 安装

从 GitHub 默认分支安装：

```bash
python -m pip install git+https://github.com/liyexiaoyi/Mnemosis.git
```

运行示例或参与开发：

```bash
git clone https://github.com/liyexiaoyi/Mnemosis.git
cd Mnemosis
python -m pip install -e .
python examples/demo.py
```

## 快速开始

```python
from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

engine = MemoryEngine("memory.db", auto_warmup=False)
try:
    engine.remember(
        "用户喜欢用中文讨论技术问题。",
        kind=MemoryKind.SEMANTIC,
        source=SourceRecord(origin=SourceType.USER),
        cues=["用户", "中文", "技术"],
        importance=0.9,
    )

    # 只读探针不改变持久化学习状态。
    for result in engine.recall("用户 中文 技术", top_k=3, read_only=True):
        print(result.item.content, result.score)

    print("知识缺口：", engine.check("用户最喜欢的电影").gaps)
    engine.sleep()  # 离线整合
finally:
    engine.close()
```

`remember_turn` 按句拆分并保存一轮对话；`remember_many` 批量导入记录。
普通检索可能强化记忆，评测、诊断或候选探索应传 `read_only=True`。
检索分数用于排序，不是事实正确概率。没有检查出缺口，也不保证问题已被完整回答。

## 接入 AI 客户端（MCP）

安装后，在支持 MCP 的客户端加入配置：

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

Windows 用户需要把 Python 的 `Scripts` 目录加入 `PATH`，或使用
`mnemosis-mcp.exe` 的绝对路径。`--expose core` 暴露日常工具，默认 `advanced`
扩展常规工具，`--expose experimental` 才包含实验工具。
详见 [MCP 配置指南](docs/mcp-quickstart.md)。

```bash
mnemosis --db memory.db remember "用户喜欢喝绿茶。" --kind semantic
mnemosis --db memory.db recall "用户 绿茶"
mnemosis --db memory.db check "用户最喜欢的电影"
mnemosis --db memory.db sleep
mnemosis-mcp --db memory.db --expose core
```

服务也支持 Streamable HTTP，可添加 `--transport http --host 127.0.0.1 --port 8000`。
跨设备部署时配置鉴权和 TLS。SQLite 适合本地、单进程场景；多个 Agent 并发共享
同一引擎时，应串行执行高层调用。

## 不同数学模型负责不同能力

原仿生检索仍是默认路径。新增策略均可选，按职责分工：

| 部分 | 模型／机制 | 说明 |
| --- | --- | --- |
| 词法检索 | BM25 词频、稀有度和长度归一化；可选受限 RRF 融合。 | [BM25 线索](docs/bm25-cues.md) |
| 英文词形 | 按原查询词分组扩展，限制重叠分，以平均稀有度校正。 | [词形策略](docs/inflection-cues.md) |
| 候选准入 | 保护 64 个词法候选与最多 36 个合格向量候选，重叠名额按词法补足至 100。 | [固定配额](docs/candidate-admission.md) |
| 语义重排 | 在原重排预算内保护语义候选机会，尽可能保留原候选。 | [数学职责](docs/mathematical-models.md) |
| 证据组合 | 相关性与加权要点覆盖分别计分，同一要点的重复支持不重复累加；可选补全约束和精修。 | [证据选择](docs/evidence-selection.md)、[排名证据](docs/ranked-evidence.md) |
| 反馈校准 | 平滑有用性估计、按记忆数量加权的校准统计。 | [校准统计](docs/calibration-statistics.md) |

候选覆盖、排名分数、证据效用和反馈估计是不同指标，某一项改善不能直接证明最终回答更准。
配额准入需要匹配的向量索引与嵌入器；证据选择仍依赖调用方提供的要点与支持标注。

可选接入本地 Ollama 嵌入服务：

```bash
mnemosis-mcp --db memory.db --embedder ollama
```

缓存和向量索引存放在记忆库旁边，可重建。Python 负责记忆生命周期，SQL 负责存储，
NumPy 可加速向量计算，Rust 可加速 BM25 评分；无需将整个项目改写为 Rust。
详见[语言分工](docs/module-languages.md)、[Rust 内核](docs/rust-bm25.md)、[向量加速](docs/vector-acceleration.md)。

## 实验功能：有原文绑定的证据检索

`MemoryEngine.recall_evidence` 将只读检索、问题职责标注、唯一原文引用和受预算约束的
数学证据选择连接起来。需要显式配置标注模型；通过 MCP 使用时还需启用实验工具。

结果区分可行、不可行、未确定、标注失败和不适用，缺失支持保留为未知。
**引用确实出现在原文，不等于原文证明了问题角色，也不等于事实真实。**
角色方向弄反、限定词遗漏、引用不充分与超时仍是已知短板，该功能没有切换为默认检索。
接口、预算和状态语义见[实验说明](docs/evidence-recall.md)。

## 测试与效果边界

2026-10-11 本地检查点在已配置 NumPy／Rust 后端的环境中通过 **1399 项测试、374 项子测试**，
以及 18 项能力检查。此前在 20 种配置下实际重放 704 次旧召回，排名与存储状态保持一致。
这些结果证明回归边界，不是同类项目实力排名。

已有公开数据检索子集与作者构造数学案例评测。候选准入覆盖有改善，但未证明最终 Top-k
准确率提高；近期支持提示实验出现退步，已撤回。详见[验证记录与限制](docs/evaluation-status.md)。

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python benchmarks/ci_regression.py
```

可选原生测试需安装并启用对应后端，参见 [Rust 测试说明](docs/rust-bm25.md)。
延迟受硬件、数据、模型与缓存状态影响，不提供任意场景的固定速度承诺。

仓库保留 LongMemEval 对比脚本：

```bash
python benchmarks/fetch_longmemeval.py
python benchmarks/longmemeval_bench.py --data work/longmemeval_s_cleaned.json --questions 20
```

对比项目依赖与模型服务需单独配置；历史抽样结果不能推导本项目普遍优于其他记忆项目。

## 文档与参与

[路线图](docs/roadmap.md) · [贡献指南](CONTRIBUTING.md) · [MIT 许可证](LICENSE)

欢迎提交可复现的失败案例、检索评测和改进建议。
