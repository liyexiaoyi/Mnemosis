# 模块语言分工｜2026-10-06

审查范围：43 个 Python 模块及现有 Rust BM25 源文件，依据源码职责、调用边界、既有测量与本轮向量对照。这里只证明已测路径的收益，不能称每个模块都已跑完所有语言的最优比较。

仿生主线继续由 Python 表达：情景/语义记忆、联想预算、强化、遗忘、睡眠、工作记忆、时间适用性与不确定性。原生计算只接收可丢弃的索引或数组，不持有证据可信度与学习状态。SQL 是数据库内部执行层，不是另写一套存储服务。

| 文件 | 职责 | 当前分工 |
| --- | --- | --- |
| `src/mnemosis/__init__.py` | 公共导出与版本 | Python |
| `src/mnemosis/__main__.py` | 启动入口 | Python |
| `src/mnemosis/affective_mixin.py` | 情绪、难度与整合建议 | Python |
| `src/mnemosis/association.py` | 线索索引、批量联想边与图召回 | Python + SQLite SQL |
| `src/mnemosis/backend.py` | Dict/SQLite、事务、变化令牌与批量写入 | Python + SQLite SQL |
| `src/mnemosis/bm25.py` | 倒排、词频、BM25 评分与 Top-k | Python API + 可选 Rust |
| `src/mnemosis/cli.py` | 命令解析与嵌入器配置 | Python |
| `src/mnemosis/cognitive_mixin.py` | 注意、类比、反刍与目标进展 | Python |
| `src/mnemosis/consolidation.py` | 睡眠回放、合并、冲突与语义晋升 | Python |
| `src/mnemosis/consolidation_insights_mixin.py` | 睡眠、遗忘与元认知报告 | Python |
| `src/mnemosis/dual_track.py` | 情景/语义记忆、导入、扩散激活与缓存 | Python |
| `src/mnemosis/embedding.py` | n-gram 特征、外部模型请求与批量包装 | Python + 模型运行时 |
| `src/mnemosis/embedding_cache.py` | 持久嵌入缓存、内存 LRU 与 SQLite | Python + SQLite SQL |
| `src/mnemosis/engine.py` | 公共引擎、配置、后台预热与模块组合 | Python |
| `src/mnemosis/event_time.py` | 来源/正文事件时间的保守解析 | Python + SQLite SQL（涉及存储时） |
| `src/mnemosis/explanation_mixin.py` | 解释、比较、摘要与多跳证据组织 | Python |
| `src/mnemosis/forgetting.py` | 遗忘曲线与间隔复习调度 | Python |
| `src/mnemosis/forgetting_quality_mixin.py` | 覆盖、漂移、风险与来源校准 | Python |
| `src/mnemosis/hybrid.py` | 词法/向量融合、时间重排与最终强化 | Python |
| `src/mnemosis/importance.py` | 重要性评分与边界限制 | Python |
| `src/mnemosis/learning_mixin.py` | 学习会话与闭环分析 | Python |
| `src/mnemosis/mcp_handlers.py` | 工具参数转换与引擎调用 | Python |
| `src/mnemosis/mcp_registry.py` | 装饰器工具注册 | Python |
| `src/mnemosis/mcp_server.py` | stdio/HTTP、JSON 消息与服务启动 | Python |
| `src/mnemosis/mcp_tools.py` | 工具模式数据 | Python |
| `src/mnemosis/metacognition.py` | 置信、冲突与知识缺口 | Python |
| `src/mnemosis/narrative_mixin.py` | 时间线、识别与叙事报告 | Python |
| `src/mnemosis/overview_mixin.py` | 健康、图导出、画像与上下文包 | Python |
| `src/mnemosis/planning_mixin.py` | 意图、目标、计划与数值推理 | Python |
| `src/mnemosis/practice_mixin.py` | 掌握程度与检索练习 | Python |
| `src/mnemosis/reasoning.py` | 工作记忆与推理前提包 | Python |
| `src/mnemosis/recall_insights_mixin.py` | 过程步骤、相似性与联想报告 | Python |
| `src/mnemosis/recycle.py` | 主动遗忘、回收与恢复 | Python |
| `src/mnemosis/render.py` | SVG 图形输出 | Python |
| `src/mnemosis/retrieval_diagnostics_mixin.py` | 检索追踪、质量与模式诊断 | Python |
| `src/mnemosis/retrieval_mixin.py` | 召回入口、实体/数值/来源时间约束 | Python |
| `src/mnemosis/review_mixin.py` | 复习、预算、睡眠与预热编排 | Python |
| `src/mnemosis/schema.py` | 来源事件链、分组与增量失效 | Python + SQLite SQL（涉及存储时） |
| `src/mnemosis/snapshot_mixin.py` | 状态快照与检索辅助 | Python |
| `src/mnemosis/temporal_reason.py` | 时间锚点与时间细胞推理 | Python + SQLite SQL（涉及存储时） |
| `src/mnemosis/types.py` | 数据模型、Unicode 分词与线索抽取 | Python + 原生正则 |
| `src/mnemosis/vector_index.py` | 持久向量、LSH、安全预算、精确余弦与 Top-k | Python API + 可选 NumPy + SQLite SQL |
| `src/mnemosis/zh_nlp.py` | 中文同义词扩展与 CJK 判断 | Python + 原生正则 |
| `native/bm25/src/lib.rs` | 驻留词频倒排与 BM25/Top-k | Rust（可选） |

## 选择依据

- BM25：第九批已验证可选 Rust 的倒排评分与 Top-k 收益；默认仍 Python。分词、过滤、索引失效与最新记忆读取留在 Python。参见 [Rust 使用与限制](rust-bm25.md)。
- 分词：第十批先减少无效扫描，保留 Unicode 和中文规则；十万条首次查询实测约两倍收益。没有证据支持再写一套 Rust 分词器。
- 存储与联想导入：第十一批减少反向重复边暂存与 SQL 写入；十万条有联想分批导入耗时减少约 12.2%。提交/锁/磁盘开销不会因包装语言改变而消失。
- 向量：本轮复用可选 NumPy 的原生矩阵计算，优化少量结果排序。该路径以前就存在；启用 NumPy 的收益与本轮排序变化分开报告。参见 [向量加速说明](vector-acceleration.md)。
- 来源时间：第八批通过版本令牌和受影响分组更新解决重复建链；保持 Python 的保守日期和时区判断，不把熟悉度当作发生时间。

## 下一轮候选与触发条件

1. 第十三批已在真实向量导入中剖析 `NGramEmbedder` 并实现 Python 批次内有界哈希复用，保持向量逐项相同，见 [批量嵌入说明](embedding-batch.md)。`features` 的重复 n-gram 构建与 `vector_index._signature` 仍需根据剩余瓶颈评估；如尝试 NumPy/Rust，必须验证 Unicode、浮点边界、桶签名与持久格式。
2. `association` 扩散激活及 `consolidation` 冲突候选：先量候选数、SQL 读取及策略开销；可将纯候选计算抽出，不能把证据合并/强化规则一并迁移。
3. 外部嵌入：先测网络等待、批量命中和缓存；只有本地模型运行时支持并且实测有益才考虑 GPU/新进程。换包装语言没有已知收益。
4. 实体/事实版本：这是原优化方案仍待处理的质量问题，先补独立质量任务与保守语义，继续 Python；性能提升不表示回答更正确。

不引入尚未测量的 Go、C++、Java 或前端框架。这里的选择可以被后续真实负载推翻；对未测模块不作绝对最快承诺。
