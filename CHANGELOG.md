# Changelog

## v0.3.0 - 性能与检索质量专项（12 轮迭代）

- 检索提速：关键词零命中不再全表扫描（10k 规模 149ms → 34ms）；融合检索
  13ms；ngram 检索 5.5ms（稠密重排限流 64 候选 + 16 零命中救援名额）
- 检索质量：IDF 词项特异性加权（稀有词命中权重高）、英文同义扩展与连字符
  拆分、英文停用词扩充；LongMemEval 10 题 dense 模式与 mem0 逐题一致，
  20 题最终对比检索四项打平、答案正确率 0.45 vs 0.40、写入快 1.4 倍；
  50 题大样本检索复验四项指标与 mem0 完全一致（0.42/0.78/0.86/0.38），
  写入快 1.37 倍
- 睡眠整合：情景/语义快照共享（10k 本地、无 LLM：优化前基线 6s → 0.41s，
  14 倍）；情感与 REM 关联建链改为线索倒排索引，冲突检测分词缓存
- 大库扩展性（50k 真实中文输入 / 25k 活跃）：词频批量统计 + 缓存，REM/
  情感建链批量写入与高频线索跳过，检索 300-400ms → 26-85ms，睡眠
  27s → 2.3s
- 写入：`remember_many` 批量 API（10k 从 70s → 13s）、批量词索引/关联图/
  向量写入、嵌入前置失败不脏库、`rebuild_vectors` 补齐缺失向量
- 部署与工具：MCP Streamable HTTP transport + Dockerfile（VPS/NAS）、
  `calibrate_decay` 持久化、MCP 参数上限防御、CLI 支持 Ollama/OpenAI 向量
- 工程：src 100% ruff 通过、395 单元测试、13 项 CI 回归、
  LongMemEval 夜间基准工作流、评测断点续传按系统+题目判断

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
