# Changelog

## v0.2.2 - 兼容性与长文本优化

- MCP stdio 双帧兼容：同时支持换行分隔（当前 MCP 规范 / 官方 SDK 2.0）与
  Content-Length 帧（旧版客户端），按请求格式回应；已用官方 mcp SDK 实测通过
- 参数加固：`null` 参数回退默认值、缺失必填参数返回标准错误 -32602、
  CLI `review` 简化、内容哈希改用 SHA-256、cues 过滤空串
- Colab 链接修正为官方格式；CI 测试矩阵增加 Python 3.10
- 长文本检索优化：关键词重叠不再被长记录长度稀释（3000 条高干扰实测：
  检索 8/12 → 12/12，本地小模型 7/12 → 9/12）
- 新增大文本量基准 `benchmarks/bulk_longtext_bench.py` 与高干扰基准
  `benchmarks/bulk_noise_bench.py`

## v0.2.1 - MCP UTF-8 修复与仓库整理

- MCP 服务器强制 UTF-8 标准输入输出（修复 Windows 下中文工具描述导致
  JSON-RPC 解析失败）
- 新增中文说明 README.zh-CN.md；不再跟踪基准结果文件；版本号对齐 0.2.1

## v0.2.0 - first public release

- Install: `pip install git+https://github.com/liyexiaoyi/Mnemosis.git`
- Zero-dependency memory layer (pure Python stdlib + SQLite)
- MCP server entry point `mnemosis-mcp` for one-line integration with
  Claude Desktop / Cursor / Codex
- Bilingual README, Colab demo notebook, one-command demo
  (`examples/demo.py`)
- CI + release workflows on GitHub Actions

## v0.17.x - iteration series (365+ rounds, 内部迭代版本号)

> 说明：项目自 v0.17.x 起切换为语义化版本（0.2.x），本段为历史迭代记录摘要。

- Human-inspired memory lifecycle: dual-track storage, forgetting curves,
  sleep consolidation, active forgetting with recycle bin, source
  monitoring, metacognition, associative recall, Chinese-optimized
  retrieval, temporal reasoning, planning & reasoning memory
- Adversarial/chaos testing across many domains; 320 unit tests,
  163/163 evaluation gate
