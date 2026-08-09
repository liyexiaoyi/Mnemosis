# Mnemosis MCP 接入指南（让 AI 客户端直接用上记忆层）

Mnemosis 自带一个**零依赖的 MCP 服务器**（JSON-RPC 2.0，走标准输入输出），
任何支持 MCP 的客户端（Claude Desktop、Cursor、Codex、Cherry Studio 等）
都可以用一行配置接入，让 AI 获得“会记住、会遗忘、会整理、会自我怀疑”的长期记忆。

## 第一步：安装

```bash
pip install git+https://github.com/liyexiaoyi/Mnemosis.git
```

安装后会提供两个命令：

- `mnemosis` —— 命令行：`mnemosis remember ...`、`mnemosis recall ...`
- `mnemosis-mcp` —— MCP 服务器：`mnemosis-mcp --db memory.db`

`--db` 指定 SQLite 路径用于持久化；不传则每次启动是全新内存。

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
| `update` | 更新事实（旧版本进修订记录） |
| `forget` / `restore` | 主动遗忘（先进回收站，可恢复） |
| `review_due` / `review` | 间隔复习（越复习越牢） |
| `plan` / `reason` / `record_outcome` | 规划与推理记忆（复用成功经验） |

## 提示

- 首次使用建议给 AI 一句话说明：*“用 mnemosis 的 remember 记住关键信息，recall 回忆，check 不确定时先查缺口。”*
- 数据库文件可以放在任何位置，记得备份；删除走 `forget`，不会静默丢失。
- 完整工具与参数见 MCP 服务器源码 `src/mnemosis/mcp_server.py`。
