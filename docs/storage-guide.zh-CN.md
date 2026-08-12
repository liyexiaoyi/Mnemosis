# Mnemosis 存储功能介绍（技术人员版）

> 面向想深入了解 Mnemosis 存储层的开发者。
> 默认假设你懂 SQL/数据库基本概念，但每个结论都会用大白话解释一句“为什么”。

---

## 1. 一句话总结

Mnemosis 的存储层 = **一个 SQLite 单文件数据库 + 三层内存缓存 + 一批为了“快”而做的 SQL/索引优化**。

默认零外部依赖：不需要 PostgreSQL、不需要 Redis、不需要向量数据库。
整个记忆库就是一个 `.db` 文件，拷走它，记忆就带走了。

---

## 2. 为什么选 SQLite

- **单文件、零运维**：一个 Agent/一台 NAS 就是典型场景，SQLite 是“够用且最省心”的选择。
- **事务与 ACID**：写入要么全部成功要么全部回滚，记忆不会写到一半坏掉。
- **性能足够**：10 万条级记忆库，预热后真实命中检索约 5~8ms；有缓存的高频查询 1~2ms。
- **可移植**：文件即备份；也可以传 `":memory:"` 跑纯内存模式（测试/临时用）。

> 大白话：单机场景下，为记忆单独装一个数据库服务属于“杀鸡用牛刀”，SQLite 正好卡在“够快、够稳、不用装”的点上。

---

## 3. 数据库结构（Schema）

核心 5 张表，全部是普通 SQLite 表：

### `memories` —— 记忆主表

| 字段 | 作用 |
|---|---|
| `id` (TEXT PRIMARY KEY) | 记忆唯一 ID（UUID） |
| `kind` | `episodic`（情景）/ `semantic`（语义） |
| `content` / `content_hash` | 内容原文 + 哈希（语义去重用） |
| `source_json` / `cues_json` | 来源信息与线索的 JSON 快照 |
| `created_at` / `updated_at` / `last_access_at` | 时间戳 |
| `importance` / `strength` / `confidence` | 重要度 / 强度 / 置信度 |
| `storage_strength` | 长期存储强度（涨得慢、掉得慢） |
| `retrieval_successes` / `retrieval_failures` | 回忆成功/失败次数 |
| `review_streak` / `last_review_at` | 复习状态 |
| `revision_count` | 被修改过几次（再巩固） |
| `status` | `active` / `recycled`（回收站） |
| `seq` | 全局自增序号（按时间排序用） |
| `context` / `affect` / `evidence_count` | 情境 / 情绪 / 证据数 |

### `links` —— 关联图

`(src, dst, weight)`，主键 `(src, dst)`。
记录“记忆 A 和记忆 B 有关联，权重多少”，用于关联激活、模式补全等。

### `cues` —— 线索索引

`(cue, memory_id)`，主键 `(cue, memory_id)`。
线索就是“想起这条记忆的钥匙”，一张记忆可以有多把钥匙。

### `terms` —— 分词索引

`(term, memory_id, kind)`，主键 `(term, memory_id)`。
记忆内容分词后的词条，检索时用来快速找候选。

### `settings` —— 键值设置

存 `decay_rate`（遗忘曲线参数）等运行期配置，重启后自动恢复。

> 大白话：`memories` 是“卡片本身”，`links` 是“卡片之间的线”，`cues/terms` 是“查卡片的目录”，`settings` 是“设置页”。

---

## 4. 索引设计（为什么快）

| 索引 | 服务谁 | 说明 |
|---|---|---|
| `sqlite_autoindex_memories_1`（id 主键） | 按 ID 批量取记忆 | TEXT 主键自动索引 |
| `idx_semantic_hash`（部分索引，仅 semantic） | 语义去重 | `(kind, content_hash)` 唯一 |
| `idx_memories_status_seq` | 最近记忆 | `(status, seq)` |
| `idx_memories_status_importance` | 最强记忆 | `(status, importance)` |
| `idx_memories_status_kind` | 按类型过滤 | `(status, kind)` |
| `cues/terms` 主键 | 线索/词条反查 | 覆盖索引，查词条不用回表 |
| `idx_links_dst` | 反向关联 | 图遍历用 |

**重点**：CI 里有专门的 **SQL 执行计划巡检**（`audit_query_plans`），
每次提交都检查这些核心查询是否仍走预期索引。
历史上修过一个真实事故：`get_many` 因带 `status` 过滤被 SQLite 优化器
改成状态索引全扫，50 次查询从 1ms 变成 1434ms——现在这类退化会被 CI 直接拦下。

---

## 5. 写路径：一条记忆是怎么落库的

`remember(...)` 大致做四件事：

1. **打分与建模**：算重要度、贴时间戳、建 MemoryItem。
2. **写入主表**：
   - 情景记忆：直接 INSERT；
   - 语义记忆：按 `(kind, content_hash)` 去重，存在就合并证据数。
3. **写目录**：`cues`、`terms` 批量写入。
4. **建关联**：和“共享线索/同现”的记忆建 `links`（带权重）。

批量写入（`remember_many`）则把上面这些**全部批量化**：

- 一个事务内 `executemany` 插入；
- `seq` 用 `INSERT ... SELECT MAX(seq)+1` 原子分配（多进程也不会重号）；
- 关联边数按规模自动收缩（64 条/记忆起步，10 万条时降到至少 8 条），
  避免 10 万条 × 64 = 640 万条边把库写爆。

> 实测：10 万条批量构建，走新增的 `remember_many_chunked`（分块写入 +
> 增量建链 + 批量导入模式）**约 53~63 秒**；
> 旧路径约 6~7 分钟，最初版本要 2 小时以上。
>
> 构建期的 Python 峰值内存约 120MB（10 万条，tracemalloc 口径）——
> 批量路径不会把分词缓存和记录副本堆在内存里。

---

## 6. 读路径：一次检索发生了什么

`recall(query)` 的链路：

```text
分词/同义词扩展
  → 查词频（df，决定哪些词值得当候选）
  → 取候选 ID（走 terms/cues 索引）
  → 打分（关键词重叠 + 重要度 + 遗忘曲线 + 情境/情绪/置信度…）
  → 可选：向量重排（只对 top-64 候选）
  → 图后处理（关联激活 / 模式补全 / 模式分离 / 竞争抑制）
  → 强化命中项、记录失败、安排复习
```

几个“为了快”的关键实现：

- **高频词跳过**：df > 5000 的词不再物化候选 ID，直接进兜底池，避免 5 万条候选。
- **零命中兜底**：无词法信号时用“最近 150 + 最强 50”双池，走 `(status, seq)` /
  `(status, importance)` 索引，查询只要几毫秒。
- **批量取 ID**：`get_many` 小列表用 `VALUES CTE`，大列表（≥64）用
  `CROSS JOIN json_each`，状态过滤下推到 SQL——保证任何规模都走主键索引。
- **后处理限流**：泛查询跳过竞争抑制/激活扩展，单次召回最多抑制 12 条。

---

## 7. 三层缓存（内存里的“加速器”）

| 缓存 | 存什么 | 上限/策略 | 失效 |
|---|---|---|---|
| 词频/倒排缓存 | 词条→ID、词频 | 写操作清空 | remember/update 等 |
| 嵌入向量缓存 | 文本→向量 | 默认约 512MB（按真实内存估算）+ 10 万条兜底，FIFO | 写操作清空 + 字节淘汰 |
| 兜底结果缓存 | 泛查询结果（id+分数+原因） | 默认 32 条、TTL 15 秒、驱逐率高时自动扩容到 256 | remember/update/sleep/review 等写路径清空 |

缓存命中后仍会**重新取最新记忆内容**再返回，不会把旧文本喂给 Agent；
写入即失效，缓存不会让你读到“刚删掉”的记忆。

---

## 8. 并发与可靠性

- **线程安全**：后端所有方法用 `RLock` 包裹，4 线程并发写读冒烟 0 错误。
- **WAL 模式**：读写不互相阻塞，读能看到已提交的写。
- **`busy_timeout=5000`**：写锁竞争时最多等 5 秒而不是立刻报错。
- **`synchronous=NORMAL`**：WAL 下兼顾性能与崩溃安全。
- **`temp_store=MEMORY`**：排序等临时数据放内存。
- **原子 seq**：并发/多进程写不会分配重复序号。

> 说明：SQLite 是单写者数据库。多个 Agent **同时写**同一文件时建议串行化
> 或由 MCP 服务统一转发；读并发没有问题。

---

## 9. 数据生命周期：删除不是真的删

- `forget(id)` → `status` 改为 `recycled`，进回收站（还在库里，可恢复）。
- `restore(id)` → 恢复为 `active`。
- `purge()` → 真正 DELETE，不可恢复。
- `suppress_memories` → 检索时屏蔽，但不改状态。

查询都带 `status='active'` 过滤（下推到 SQL），回收站里的记忆不会出现在检索结果里。

---

## 10. 备份、迁移与远程部署

**备份**：直接拷贝数据库文件即可。如果正在运行，最好连 `-wal` / `-shm`
一起拷，或先跑一次 `PRAGMA wal_checkpoint` 把 WAL 合并回主文件。
更稳的方式是用内置的 `export_memories` / `import_memories`。

**远程部署**：Mnemosis 本质是“本地库 + 标准 MCP 服务”。
把 `memory.db` 和 `mnemosis-mcp` 放在 VPS / NAS 上，其他设备通过网络调用；
不需要把数据库暴露成公网服务。

---

## 11. 性能数字一览（100k 级实测）

| 场景 | 数字 |
|---|---|
| 10 万条批量构建（`remember_many_chunked`） | 约 53~63 秒（旧路径 6~7 分钟） |
| 构建期 Python 峰值内存（10 万条） | 约 120MB |
| 真实命中检索（预热后） | 约 5~8 ms |
| 零命中检索 | 约 6 ms |
| 高频泛查询（兜底缓存命中） | 约 1.5~2 ms |
| `get_many` 100 / 500 / 2000 条 | 约 1 / 5 / 30 ms（本机，随机器波动） |
| 4 线程并发写读冒烟 | 0 错误 |

> 数字来自本地 100k 实库（`%TEMP%` 基准库）与 CI 性能门禁，机器不同会有波动；
> CI 每次跑 `ci_perf.py` 做“只拦灾难性退化”的宽松门禁，并积累趋势基线。

---

## 12. 常见技术问题（FAQ）

**Q：能换 PostgreSQL 吗？**
存储层有 `Backend` 抽象，但目前只内置 `SQLiteBackend` 和 `DictBackend`（内存）。
接 PostgreSQL 需要实现同一组接口；如果你有真实需求，可以按这个抽象去扩展。

**Q：`get_many` 为什么用 `CROSS JOIN json_each` 而不是 `WHERE id IN (...)`？**
因为长 `IN` 列表会被 SQLite 优化器选成全表扫描（实测 50 个 id 就退化）。
`CROSS JOIN` 强制 json_each 当驱动表，memories 稳定走主键索引，且不依赖
自动索引名（之前 `INDEXED BY` 的脆弱方案已替换）。

**Q：状态过滤为什么下推到 SQL？**
少传“已删除”的行；同时用 CI 计划巡检保证不会因此改走状态索引全扫。

**Q：缓存会不会返回旧数据？**
不会。兜底缓存命中后按 ID 重新查库取最新内容；所有写路径都会清缓存；
嵌入向量缓存按内容哈希缓存，内容变了哈希就变。

**Q：100 万条还能用吗？**
存储本身是普通 SQLite，能存，但检索的“候选评分”阶段会变慢。
当前优化目标是 10 万级；百万级需要进一步做候选剪枝或向量索引，
这在路线图里是后续方向。

**Q：数据库文件很大怎么办？**
可以 `purge()` 清回收站，跑 `sleep()` 让系统把低价值记忆自动回收，
也可以用 `VACUUM` 压缩文件空洞（Mnemosis 不自动执行，避免阻塞）。

---

## 13. 相关文档

- [奶龙级入门教程——基本功能介绍版](../奶龙级入门教程——基本功能介绍版.md)：零基础功能总览
- [架构与模块](architecture.md)：模块职责与数据流
- [记忆模型](memory-model.md)：人脑机制 ↔ 代码实现对照
- [MCP 接入](mcp-quickstart.md)：各客户端配置
