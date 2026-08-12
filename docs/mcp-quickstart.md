# Mnemosis MCP 接入指南（让 AI 客户端直接用上记忆层）

Mnemosis 自带一个**零依赖的 MCP 服务器**（JSON-RPC 2.0，走标准输入输出），
任何支持 MCP 的客户端（Claude Desktop、Cursor、Codex、Cherry Studio 等）
都可以用一行配置接入，让 AI 获得“会记住、会遗忘、会整理、会自我怀疑”的长期记忆。

## 第一步：安装

```bash
pip install git+https://github.com/liyexiaoyi/Mnemosis.git
```

安装后会提供两个命令：

- `mnemosis` —— 命令行：`mnemosis remember ...`、`mnemosis recall ...`、
  `mnemosis memory-map --out map.svg`（看一眼记忆地图，会生成中文 SVG 图表）
- `mnemosis-mcp` —— MCP 服务器：`mnemosis-mcp --db memory.db`

`--db` 指定 SQLite 路径用于持久化；不传则每次启动是全新内存。

如果 MCP 服务器脚本不在 PATH（比如某些 Windows/虚拟环境），用模块方式启动
MCP 服务：

```bash
python -m mnemosis.mcp_server --db memory.db
```

> 启动预热：MCP 服务器启动后会在后台线程扫描主表/索引页（`engine.warmup()`），
> 在真实冷启动场景（容器重启 / VPS 冷启）下可显著减少第一次查询的磁盘页
> 加载等待；本地热缓存环境感知不明显。

## 快速看一眼记忆

```bash
# 记两条
mnemosis --db memory.db remember "用户喜欢红色。" --cues "偏好"
mnemosis --db memory.db remember "用户喜欢蓝色。" --cues "偏好"

# 人类可读表格
mnemosis --db memory.db memory-map

# 生成 SVG 图表（主题条形图 + 强度分布）
mnemosis --db memory.db memory-map --out memory_map.svg
```

## 第二步：配置客户端

### Claude Desktop

编辑 `claude_desktop_config.json`，加入：

```json
{
  "mcpServers": {
    "mnemosis": {
      "command": "mnemosis-mcp",
      "args": ["--db", "C:\\Users\\你的名字\\mnemosis.db"]
    }
  }
}
```

### Cursor

Settings → MCP → Add new MCP server：

```text
type: command
name: mnemosis
command: mnemosis-mcp --db C:\Users\你的名字\mnemosis.db
```

### Codex

在 `~/.codex/config.toml` 中加入：

```toml
[mcp_servers.mnemosis]
command = "mnemosis-mcp"
args = ["--db", "C:/Users/你的名字/mnemosis.db"]
```

## MCP 服务器参数

| 参数 | 作用 |
|---|---|
| `--db PATH` | SQLite 路径（默认内存） |
| `--expose advanced\|experimental` | 默认 advanced 只暴露核心+高级工具；experimental 暴露全部 100+ 工具 |
| `--transport stdio\|http` | 本地进程用 stdio；VPS/NAS 远程部署可用 http（配 `--host/--port`） |
| `--host HOST` / `--port PORT` | HTTP 模式监听地址/端口（默认 127.0.0.1:8000，远程部署改 `0.0.0.0`） |
| `--embedder none\|ollama\|openai` | 开启稠密语义检索（可选；openai 需要 API Key，ollama 需要本地服务） |

*注：`--embedder openai` 需要配置 `MNEMOSIS_EMBEDDING_API_KEY`（或
`--embedding-api-key`）；`--embedder ollama` 需要本机 Ollama 服务。*

远程部署示例（配合反向代理或内网访问）：

```bash
mnemosis-mcp --db /data/mnemosis.db --transport http --host 0.0.0.0 --port 8000
```

> **客户端兼容性**：`--transport http` 适用于支持远程 HTTP 的 MCP 客户端
> （Cherry Studio、Cline、Cursor 等）；**Claude Desktop 目前只支持 stdio**，
> 要在 Claude Desktop 里用请保持默认 stdio，或通过本地代理把远程服务挂成本地进程。

## 第三步：验证

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | mnemosis-mcp --db demo.db
```

能返回一长串工具列表就说明接好了。核心工具：

| 工具 | 作用 |
|---|---|
| `remember` | 写入记忆（区分事件/事实，可带线索、情绪、重要度） |
| `recall` | 联想检索（时间、主题、人物、关键词多路命中） |
| `check` | 元认知核查（知识缺口、矛盾、没把握先说不知道） |
| `sleep` | 睡眠整合（去重、提炼事实、查矛盾） |
| `rebuild_vectors` | 补齐缺失向量（批量嵌入失败后的修复） |
| `update` | 更新事实（旧版本进修订记录） |
| `forget` / `restore` | 主动遗忘（先进回收站，可恢复） |
| `review_due` / `review` | 间隔复习（越复习越牢） |
| `plan` / `reason` / `record_outcome` | 规划与推理记忆（复用成功经验） |

## 提示

- 首次使用建议给 AI 一句话说明：*“用 mnemosis 的 remember 记住关键信息，recall 回忆，check 不确定时先查缺口。”*
- 数据库文件可以放在任何位置，记得备份；删除走 `forget`，不会静默丢失。
- 完整工具与参数见 MCP 服务器源码 `src/mnemosis/mcp_server.py`。
- 想知道数据怎么存、批量导入怎么加速，看 [架构文档](architecture.md)；
  想复现 10 万~200 万规模性能，看 [扩展性基准](scalability.md)。

## 独立公开基准验证（LongMemEval）

为了确认记忆能力不是只在自建数据上有效，项目用 ICLR 2025 的
LongMemEval（约 11.5 万 token 长对话、高干扰）与官方 `mem0` 包做对比。
先下载官方数据（已存在则直接复用，也支持断网时用本地目录导入）：

```bash
python benchmarks/fetch_longmemeval.py
```

再运行对比（需要装 mem0 的 Python 环境，以及 Ollama 或云端
embedding/LLM 用于稠密模式）：

```bash
python benchmarks/longmemeval_bench.py --data work/longmemeval_s_cleaned.json --questions 20
```

结果会输出双方在长对话中的检索命中率、回答正确率和耗时对比。
