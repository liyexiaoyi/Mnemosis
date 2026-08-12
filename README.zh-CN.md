# Mnemosis

> 像人脑一样记事的 AI 记忆层：会记住、会遗忘、会整理、会自我怀疑。

Mnemosis 是一个为 AI 助手设计的**长期记忆组件**。它不是简单地“存下所有内容再搜索”，
而是把记忆当成一个完整的生命周期来管理：写入、加固、整合、遗忘、更新，每一步都有
对应的机制，让 AI 在需要时想得起、说得准，没把握时敢说“不知道”。

> 🍼 完全没接触过？先看 [**奶龙级入门教程——基本功能介绍版**](奶龙级入门教程——基本功能介绍版.md)，
> 像老师给零基础学生讲课一样，把每个功能都讲明白。

> 🗄️ 想看存储层怎么设计？[**存储功能介绍（技术人员版）**](存储功能介绍（技术人员版）.md)。

> 🗺️ 1.0 收敛计划与核心承诺：[docs/roadmap.md](docs/roadmap.md)

## 安装

```bash
pip install git+https://github.com/liyexiaoyi/Mnemosis.git
```

零运行时第三方依赖（纯 Python 标准库 + SQLite），不需要服务器、不需要云向量服务
（向量接口是可选的）。

安装后有两个命令：

- `mnemosis` —— 命令行工具
- `mnemosis-mcp` —— MCP 服务器（给 AI 客户端接入用）

> SQLite 存储适合单进程/低并发场景；多个 Agent 并发写入时建议串行访问或
> 接入外部数据库适配层。

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

或在 [Google Colab](https://colab.research.google.com/github/liyexiaoyi/Mnemosis/blob/main/examples/Mnemosis_demo.ipynb) 在线体验。

> 注意：国内网络通常无法访问 Google Colab。替代方式：
>
> - [GitHub Codespaces 一键打开](https://codespaces.new/liyexiaoyi/Mnemosis)：
>   云端环境，打开终端执行 `python examples/demo.py`
> - 下载 `examples/Mnemosis_demo.ipynb`，用本地 Jupyter 或百度 AI Studio 打开
> - 最稳的方式：本地 `pip install` 后直接跑 `python examples/demo.py`

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

# 生成记忆地图 SVG
mnemosis --db memory.db memory-map --out memory_map.svg

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

工具按三档分级暴露：

```bash
mnemosis-mcp --db memory.db                 # 默认 advanced：98 个（不含实验工具）
mnemosis-mcp --db memory.db --expose core   # 只留 16 个日常工具
mnemosis-mcp --db memory.db --expose experimental  # 全部 130 个
```

**Windows 用户**：如果客户端提示找不到 `mnemosis-mcp`，把 Python 的
`Scripts` 目录加入 `PATH`，或改用绝对路径，例如
`"command": "C:\\Users\\you\\AppData\\Local\\Programs\\Python\\Python312\\Scripts\\mnemosis-mcp.exe"`。

详细配置（含 Cursor、Codex 写法）见 [`docs/mcp-quickstart.md`](docs/mcp-quickstart.md)。

## 远程部署（VPS / NAS）

MCP 服务器支持 Streamable HTTP，可以跑在 VPS / NAS 上供其他设备调用：

```bash
mnemosis-mcp --transport http --host 0.0.0.0 --port 8000 --db /data/memory.db
```

客户端指向 `http://your-server:8000/` 即可（Claude Desktop、Cursor、Cherry Studio
都支持远程 MCP URL）。暴露到公网前建议用 Caddy/nginx 反代并加 TLS 和鉴权。

或用 Docker：

```bash
docker build -t mnemosis .
docker run -d -p 8000:8000 -v mnemosis-data:/data mnemosis
```

记忆就是一个 SQLite 单文件，备份 = 拷贝一个文件。

## 语义嵌入（可选）

默认检索是纯关键词 + n-gram，零依赖；接入向量模型后可获得语义召回：

```bash
# 本地 Ollama
mnemosis-mcp --db memory.db --embedder ollama

# 任意 OpenAI 兼容接口（DashScope、OpenAI 等）
export MNEMOSIS_EMBEDDING_API_KEY=sk-...
mnemosis-mcp --db memory.db --embedder openai --embedding-model text-embedding-v3
```

向量会持久缓存在主库旁边（`memory.db.cache` / `memory.db.vec`，可重建），
默认内存缓存上限约 512MB，超出时自动淘汰（`embed_cache_memory_limit_mb` 可调）。

## 自动记忆保存（agent 推荐用法）

Mnemosis 不偷听对话——由 Agent 决定存什么。最简单的自动模式是每轮对话调用一次
`remember_turn`：它会自动按句切分、提取线索并存储，不需要手写 `remember`。

```bash
mnemosis-mcp --db memory.db
```

然后在系统提示词里告诉 Agent：

> 每轮用户/助手对话结束后调用 `remember_turn` 存入原文；当用户提到之前的话题时，
> 先调用 `recall`（或 `check`）再回答。

长对话用按句切分存储（`remember_turn`）后，检索与端到端准确率都明显更好（见下方独立基准）。

## 批量导入

```python
engine.remember_many([
    {"content": "用户喜欢喝咖啡。", "kind": MemoryKind.SEMANTIC, "cues": ["用户"]},
    {"content": "上周修了空调。", "kind": MemoryKind.EPISODIC},
])
```

小规模用 `remember_many` 即可；10 万条以上的超大导入请用分块优化的
`remember_many_chunked`（约 25~27 秒），单条循环会慢一个数量级。

## 启动预热

MCP 服务器启动后会自动在后台扫描主表/索引页（`engine.warmup()`），大幅减少
实际冷启动（容器重启 / VPS 冷启）后第一次查询的磁盘页加载等待。

## 原理

Mnemosis 模拟人脑记忆机制做长期记忆：`remember` 写入、`recall` 联想检索、
遗忘曲线自动衰减、`sleep` 睡眠式整理（去重/建联/消矛盾）、`check` 知道自己不知道
（不会乱编答案）。它不是录音机，谁调用、存什么由你和 agent 决定。

## 测试

```bash
python -m unittest discover -s tests -q   # 500 项单元测试
python benchmarks/locomo_bench.py --mode keyword   # LoCoMo 式长对话评测
```

质量门禁：ruff 全过、mypy 严格模式 0 错误、CI 回归测试 18/18、性能门禁、
并发与睡眠冒烟测试。

## 性能（本机实测）

| 规模 | 构建 | 库大小 | 峰值内存 | 热查询 p99 |
|---|---|---|---|---|
| 10 万 | ~27s | ~543MB | ~620MB | ~1.8ms |
| 100 万 | ~367s | ~5.1GB | ~2GB | ~1.7ms |

更多细节见 [docs/scalability.md](docs/scalability.md)。

## 独立基准（LongMemEval）

基于 LongMemEval-S 数据集（采样 20 个测试问题），与官方 `mem0` 包对比：

| 系统 | 检索 @1/@5/@10 | 端到端答案准确率 |
|---|---|---|
| Mnemosis（`remember_turn` 切句） | 0.60 / 0.85 / 0.90 | 0.65 |
| mem0 | 0.50 / 0.80 / 0.80 | 0.45 |
| Mnemosis（dense 模式） | 0.50 / 0.80 / 0.80 | 与 mem0 持平，导入快约 5.8 倍 |

## 许可

MIT，见 [LICENSE](LICENSE)。

## 参与贡献

欢迎提 Issue、提交 PR。每项改动请附带测试或实测结果，详见
[CONTRIBUTING.md](CONTRIBUTING.md)。
