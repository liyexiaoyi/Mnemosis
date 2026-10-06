# 评测验证与归档

开发评测不再对每个中间轮次反复扫描全部数据库。两个导入脚本共享 `benchmarks/verification_utils.py`，不影响运行时的嵌入哈希、持久数据或仿生策略。

## 验证模式

`embedding_ingest_eval.py` 与 `ingest_pair_eval.py` 都接受 `--verification boundary|full`。

- `boundary`（默认）：每组第一轮和最后一轮，两种实现都进行完整表摘要对照。中间轮次逐表比较准确行数、schema 和首轮确定的最多 32 个分散键对应的全部行/列；空表也核对行数。抽样不计算内容摘要。
- `full`：每轮、两种实现都进行完整表摘要对照。
- 两种模式每轮都直接比较返回 ID 顺序及查询结果，避免把相同列表反复序列化后哈希。源码和基线档案的来源摘要每次启动计算一次。

键样本按主键排序等距选择并固定；没有唯一主键的桶表按 `(bucket,memory_id)` 比较对应行组，保留重复行。行数与固定样本无法证明其他行完全一致，也可能漏过仅在中间某轮出现的未抽中改动。重要的兼容性审计请选择 `full`，日常性能迭代使用默认模式。

输出不再设置会误导的 `exact_state_result_parity` / `exact_database_graph_order_recall`。`verification` 分别报告 `full_runs`、`sample_runs`、`all_runs_exhaustive`、边界/抽样通过与返回顺序/结果一致。每个样本也标记验证模式。下游读取旧字段的脚本需要更新；历史报告保持原样。

查询前后用 SQLite 的 `total_changes`、`data_version`、主/临时 schema 版本与事务状态检查变化，避免查询后重复扫描表。这能发现同连接 DML（包括随后回滚）、已提交的外部写入及可见 schema/事务变化，但不是安全沙箱，无法证明所有瞬时 DDL、PRAGMA 或非数据库副作用都没有发生。两种模式中的查询只读检查都使用此诊断。

## 使用

从仓库环境运行，输出目录必须是新目录，基线 ZIP 必须来自可信本地源码（脚本执行其中的方法）。常规规模仍为原来的 1000/10000 条、七轮。

```powershell
python benchmarks/embedding_ingest_eval.py --baseline E:/Mnemosis/backups/2026-10-06-embedding-before/repository.zip --output E:/Mnemosis/evaluation/new-run --verification boundary
python benchmarks/embedding_ingest_eval.py --baseline E:/Mnemosis/backups/2026-10-06-embedding-before/repository.zip --output E:/Mnemosis/evaluation/new-audit --verification full
```

小规模流程检查可传 `--counts 200 --rounds 3`；它不替代正式性能或质量评测。

## 归档复制

`copy_verified(source,target)` 用于静止的普通文件：复制流同时计算源 SHA-256，复制结束只读取目标一次核验；比较源前后元数据与复制字节数，拒绝覆盖。失败只删除本次创建的目标文件。返回 `bytes` 和 `sha256`，直接写入归档清单，无需再次读取源/目标做同一核验。

源必须暂停写入。元数据检查不是原子快照，也不抵御刻意恢复元数据的并发篡改；正在使用的 SQLite 数据库应先通过数据库备份接口生成静止文件，再归档。历史阶段脚本保留，后续存档使用此工具。
