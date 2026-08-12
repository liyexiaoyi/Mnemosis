# Mnemosis 1.0 发布说明（草稿）

> 状态：草稿。正式发布前由维护者核对版本号、PyPI 信息与 Release 标题。

## 一句话

Mnemosis 1.0 是面向 AI Agent 的**长期记忆层**：不是“存下一切再搜索”，
而是照着人脑记忆机制做完整的生命周期——记住、加固、遗忘、睡眠整理、自我怀疑。
纯 Python 标准库 + SQLite，零运行时第三方依赖。

## 核心能力

- **双轨记忆**：情景（发生过的事）与语义（事实/偏好）分开存储与召回；
- **遗忘曲线**：指数衰减 + 间隔复习，重要记忆越用越牢、噪音自然淡出；
- **睡眠整合**：离线去重、提升、修剪、REM 关联加链、冲突消解（含知识更新）；
- **元认知**：`check()` 知道自己不知道，拒绝乱编；置信度标签、矛盾报告；
- **切句记忆**：`remember_turn` 按句切分存储，长对话检索与端到端准确率
  明显优于整段存储；
- **MCP 即插即用**：Claude / Cursor / Codex / Cherry Studio 一行配置；
  工具三档分级（core / advanced / experimental）；
- **远程部署**：Streamable HTTP + Docker，VPS / NAS 可用；
- **向量可选**：Ollama 或任意 OpenAI 兼容接口，主库旁两个副文件可重建。

## 性能（本机实测）

| 规模 | 批量构建 | 库大小 | 峰值内存 | 热查询 p99 |
|---|---|---|---|---|
| 10 万 | ~27s | ~543MB | ~620MB | ~1.8ms |
| 100 万 | ~367s | ~5.1GB | ~2GB | ~1.7ms |

## 独立基准（LongMemEval-S，20 题，seed 42）

| 系统 | 检索 @1/@5/@10 | 端到端答案准确率 |
|---|---|---|
| Mnemosis（`remember_turn` 切句） | 0.60 / 0.85 / 0.90 | 0.65 |
| mem0 | 0.50 / 0.80 / 0.80 | 0.45 |
| Mnemosis dense | 0.50 / 0.80 / 0.80 | 0.45（检索与 mem0 完全一致，dense 导入快约 5.8 倍） |

## 稳定边界（1.0 承诺）

- 公开导出固定为 8 个符号（`mnemosis.__all__`，契约测试锁定）；
- `MemoryEngine` 核心方法（remember/recall/check/sleep/update/forget/restore/
  purge/export/import/review/stats 等 17 个）签名冻结；
- SQLite 主存储 + WAL + 回收站语义不变；`purge` 才是真删；
- `memory_file` 构造参数名与 CLI `--db` 对齐，稳定；
- 实验工具（`--expose experimental` 共 130 个，其中实验专属 32 个）不承诺稳定性，
  可调整/移除；
- 详情见 [roadmap.md](roadmap.md) 与 [test_api_surface.py](../tests/test_api_surface.py)。

## 从 v0.3.x 迁移

- 数据库文件直接沿用（schema 自愈迁移，旧库首次打开自动补列/索引）；
- `update()` 撞语义重复现在抛 `MnemosisError`（不再是无差别 `ValueError`），
  建议捕获 `MnemosisError` 或继续捕获 `ValueError` 的调用方改为捕获
  `MnemosisError`；
- `Backend.list` 内部改名为 `list_items`（只影响直接使用 Backend 的二次开发）；
- MCP 默认 `--expose advanced`（98 个工具），需要全量用
  `--expose experimental`（130 个，含实验专属 32 个）。

## 质量门禁（发布基线）

- 507 单元测试、ruff 全过、mypy 严格模式 0 错误、CI 回归 18/18；
- 性能门禁（get_many 100/500/2000）、并发冒烟、睡眠稳态基准；
- LongMemEval 检索与端到端评测脚本可复现（seed 42）。

## 已知限制

- SQLite 单写者：多进程高频并发写需串行或经 MCP 服务统一转发；
- 100 万级可用但推荐线为 10 万级；百万级冷启动建议先 `engine.warmup()`；
- 纯关键词/ngram 模式对“完全不同说法的转述”召回弱于向量模式（dense 持平 mem0）。

## 致谢

长期迭代过程中的评测、重构与审阅由云端千问模型协同完成；LongMemEval 数据集
来自 Wu et al., ICLR 2025。
