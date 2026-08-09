# Changelog

## v0.2.1 - MCP 修复与仓库整理

- MCP 服务器同时支持换行分隔（当前 MCP stdio 规范）与 Content-Length 帧
  （旧版客户端），按请求格式回应，兼容 Claude Desktop / Cursor 等客户端
- 参数兼容性加固：`null` 参数回退默认值、缺失必填参数返回标准错误、
  CLI `review` 简化、内容哈希改用 SHA-256、cues 过滤空串
- 新增中文说明 README.zh-CN.md；不再跟踪基准结果文件；版本号对齐 0.2.1
- 长文本检索优化：关键词重叠不再被长记录长度稀释（3000 条高干扰实测：
  检索 8/12 → 12/12，本地小模型 7/12 → 9/12）

## v0.2.0 - first public release

- Install: `pip install git+https://github.com/liyexiaoyi/Mnemosis.git`
- Zero-dependency memory layer (pure Python stdlib + SQLite)
- MCP server entry point `mnemosis-mcp` for one-line integration with
  Claude Desktop / Cursor / Codex
- Bilingual README, Colab demo notebook, one-command demo
  (`examples/demo.py`)
- CI + release workflows on GitHub Actions

## v0.17.x - iteration series (365+ rounds, 内部迭代版本号）

> 说明：项目自 v0.17.x 起切换为语义化版本（0.2.x），本段为历史迭代记录摘要。

- Human-inspired memory lifecycle: dual-track storage, forgetting curves,
  sleep consolidation, active forgetting with recycle bin, source
  monitoring, metacognition, associative recall, Chinese-optimized
  retrieval, temporal reasoning, planning & reasoning memory
- Adversarial/chaos testing across many domains; 319 unit tests,
  163/163 evaluation gate
