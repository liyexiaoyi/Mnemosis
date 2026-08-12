# Mnemosis

> 像人脑一样记事的 AI 记忆层：会记住、会遗忘、会整理、会自我怀疑。

Mnemosis 是一个为 AI 助手设计的**长期记忆组件**。它不是简单地“存下所有内容再搜索”，
而是把记忆当成一个完整的生命周期来管理：写入、加固、整合、遗忘、更新，每一步都有
对应的机制，让 AI 在需要时想得起、说得准，没把握时敢说“不知道”。

> 🍼 完全没接触过？先看 [**奶龙级入门教程——基本功能介绍版**](奶龙级入门教程——基本功能介绍版.md)，
> 像老师给零基础学生讲课一样，把每个功能都讲明白。

## 安装

```bash
pip install git+https://github.com/liyexiaoyi/Mnemosis.git
```

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

## 语义嵌入（可选）

默认检索是纯关键词 + n-gram，零依赖；接入向量模型后可获得语义召回：

```bash
# 本地 Ollama
mnemosis-mcp --db memory.db --embedder ollama

# 任意 OpenAI 兼容接口（DashScope、OpenAI 等）
export MNEMOSIS_EMBEDDING_API_KEY=sk-...
mnemosis-mcp --db memory.db --embedder openai --embedding-model text-embedding-v3
```

向量会做内存缓存，默认按约 512MB 的估算内存上限淘汰
（`embed_cache_memory_limit_mb` 可调）：Python 列表按每元素约 32 字节估算，
紧凑数组（`numpy.ndarray`/`array.array`）按真实 `nbytes` 计算，避免高维向量
悄悄把内存吃满；10 万条的条数上限保留，作为极端高维时的兜底。

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

**Windows 用户**：如果客户端提示找不到 `mnemosis-mcp`，把 Python 的
`Scripts` 目录加入 `PATH`，或改用绝对路径，例如
`"command": "C:\\Users\\you\\AppData\\Local\\Programs\\Python\\Python312\\Scripts\\mnemosis-mcp.exe"`。

详细配置（含 Cursor、Codex 写法）见 [`docs/mcp-quickstart.md`](docs/mcp-quickstart.md)。

## 测试

```bash
python -m unittest discover -s tests -q   # 320 项单元测试
python benchmarks/locomo_bench.py --mode keyword   # LoCoMo 式长对话评测
```

## 许可

MIT，见 [LICENSE](LICENSE)。

## 参与贡献

欢迎提 Issue、提交 PR。每项改动请附带测试或实测结果，详见
[CONTRIBUTING.md](CONTRIBUTING.md)。
