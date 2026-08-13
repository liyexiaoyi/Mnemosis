# Roadmap

当前版本：**v0.3.1**（2026-08-13）。本页是向 **1.0** 收敛的清单：
明确哪些是核心承诺、哪些是实验特性、1.0 之前还需要做什么。

## 当前验证状态（2026-08-13）

- 单元测试：**500 passed**；
- 静态检查：ruff 全过（src / tests / benchmarks）；
- CI 回归：**18/18**（含关联图快照、中文规划、端到端链路）；
- 性能门禁：`get_many` 100/500/2000 通过；100k 构建约 27s、热查询 p99 ~2ms；
- 独立基准：LongMemEval-S 20 题，seg 检索 0.60/0.85/0.90、云判分端到端
  0.65 vs mem0 0.45；100 万条构建约 6 分钟。

## 1.0 核心承诺（API 稳定，签名冻结）

以下引擎方法在 1.0 之前不会破坏性变更（可加参数，不改语义）：

| 方法 | 承诺 |
|---|---|
| `remember` / `remember_many` / `remember_turn` | 写入语义稳定：情景插入、语义按哈希去重、自动线索/上下文 |
| `recall` / `recall_fused` | 检索语义稳定：关键词 + n-gram + 可选稠密重排 |
| `check` | 元认知：知识缺口 / 矛盾 / 置信度标签 |
| `sleep` | 睡眠整合：去重、提升、修剪、REM 加链、冲突消解 |
| `update` / `forget` / `restore` / `purge` | 生命周期语义稳定（回收站可恢复；purge 才是真删） |
| `export_memories` / `import_memories` | 备份迁移格式稳定 |
| `review_due` / `review` / `working_set` / `stats` | 复习与状态查询 |

存储承诺：

- SQLite 单文件是官方主存储（WAL、回收站、批量导入临时表）；
- `memory.db.cache` / `memory.db.vec` 是可选向量副文件，可重建；
- 100k 级为推荐日常规模：构建约 27s、热查询 p99 ~2ms、睡眠稳态约 1s 级；
- 100 万级可用：构建约 6 分钟、主库文件约 5GB（不含可选向量副文件）、
  热查询 p99 ~1.7ms（冷启动预热：MCP 服务启动时自动预热索引页；大库用户可传 auto_warmup=True）。

公开导出（1.0 锁定）：`MemoryEngine`、`fused_recall`、`MemoryItem`、
`MemoryKind`、`MnemosisError`、`RecallResult`、`SourceRecord`、`SourceType`
（`mnemosis.__all__`，新增导出须先改契约测试）。

构造契约：`MemoryEngine(memory_file=None, ...)` 的 `memory_file` 参数名
与 CLI `--db`、README 示例保持一致，属稳定 API（不可改名为 db_path 等）。

## 1.0 实验特性（`--expose experimental` 才可见，可随时调整/移除）

- 情绪/睡眠建议、反刍、类比桥接、夜间例程、突击计划等认知侧工具；
- 知识图谱导出、社区检测、多跳报告、来源校准等分析报告；
- 实验期行为以 `EXPERIMENTAL_TOOLS`（mcp_tools.py，包含 32 个实验专属工具，
  使 `--expose experimental` 总暴露数达到 130 个）为准。

> 使用约定：默认 `--expose advanced`（代码默认值）只暴露核心 + 高级工具；`--expose core`
> 只留 16 个日常工具；`--expose experimental` 暴露全部 130 个
> （core≥16、advanced=其余、experimental≥32，1.x 工具只增不减；均为累计包含关系）；
> 实验工具仍可调用但不承诺稳定性。

## 1.0 发布前待办

- [ ] **PyPI 发布**：需要维护者 token；发布后同步更新 README 与所有文档的
      安装命令（`git+...` → `pip install mnemosis` / `uvx mnemosis-mcp`）。
- [ ] **包元数据收口**：确认 `pyproject.toml` 版本号更新为 1.0.0，更新
      `classifiers`（移除 Alpha 预发布标记），检查 README 徽章/简介与 1.0 一致。
- [ ] **依赖梳理与 Release**：梳理运行期依赖——若坚持纯 stdlib 则剥离第三方
      库，否则在 `pyproject.toml` 明确声明并锁定版本；准备 GitHub Release 与
      Release Notes（基于 CHANGELOG v0.3.x 收口）。
- [ ] **类型检查接入 CI**：pyright/mypy 存量清理 + 门禁（长期减少隐性 bug）。
- [ ] **评测进 CI**：把 LongMemEval / 扩展性基准固化成命令，作为夜间/定期
      CI 门禁，任何能力下滑立刻报警。
- [ ] **基准脚本归档**：一次性渲染脚本移到 `archive/` 并更新相关文档引用。
- [ ] **架构图与原理文档**：README 已链接存储/架构/入门文档；1.0 前补一张
      Mermaid 架构图与 MCP 多客户端配置示例（Claude / Cursor / Codex / Cherry）。
- [ ] **CHANGELOG 收口**：1.0 时把 v0.3.x 的实验行为写清楚，明确稳定边界。
- [x] **Release Notes 草稿**：[docs/release-notes-1.0.md](release-notes-1.0.md)
- [ ] **废弃接口清理**：对 v0.x 遗留的废弃方法强制标记
      `DeprecationWarning` 或移除，确保 1.0 的“API 冻结”没有隐藏破坏。
- [x] **干净环境安装验证**：在全新 venv / Docker 中端到端验证
      `pip install` 与 Quickstart（含 `py.typed`、entry_points、打包内容）。
      （2026-08-13 已通过：wheel 安装、CLI/MCP 入口、py.typed、quickstart 冒烟）

## 之后（1.1+ 候选）

- Agent 管理的记忆层级：Mnemosis 作为整合/元认知层；
- 分布式后端（PostgreSQL 适配器，按 `Backend` 抽象扩展）；
- 记忆安全（可选 SQLCipher / 应用层加密）；
- 多语言检索增强（英文/日文同义词与日期解析）。
