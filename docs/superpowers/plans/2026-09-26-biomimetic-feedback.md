# 仿生反馈闭环第一批实施计划

Spec: E:/Mnemosis/plans/biomimetic-improvement-plan-2026-09-26.md
Goal: 完成方案第一批的只读检索、反馈分离、整合证据去重和生命周期回归。
Architecture: 在既有 SQLite/DictBackend 和双轨记忆上增加兼容的只读入口与独立验证反馈字段；强化仍保留为熟悉度信号。来源账本随 MemoryItem 序列化。
Constraints: 默认旧接口兼容；新数据库字段增量迁移；无新必需依赖；工作和备份在 E 盘。

- [ ] Task 1: recall/read_only 与融合只结算最终结果；check 和 recall_trace 只读，固定 now 传到底层。测试真实 SQLite 与内存库，比较全部条目、链接、成功失败计数。
- [ ] Task 2: feedback 独立计数，record_feedback(memory_id, *, useful: bool, now=None)；verified_confidence(item) 只使用显式反馈，不把未知视为正确。SQLite 增量迁移和 JSON 导入导出，旧校准入口继续兼容。
- [ ] Task 3: consolidation_sources 保存情景来源和已计入贡献；重复 sleep 幂等，来源修订与重复记录不虚增证据；持久化重启、不同来源、合并和旧库回归。
- [ ] Task 4: 固定 0/7/30/90 天只读探针评测，正确/错误反馈和重复 sleep 对照；全套 unit/ci_regression，记录剩余后续阶段。

Review focus: 内存对象引用带来的隐式写入；缓存命中副作用；旧库字段默认；重复导入和来源账本；多次内部调用导致统计污染。
Verification: 每项先运行失败用例，再改代码，运行相关测试；结束运行 python -m unittest discover -s tests -q 和 python benchmarks/ci_regression.py，并独立审查。
Ruling: 本批执行原方案明确的首批闭环；语义模型、BM25/新融合排序、完整回答模型评测属于后续阶段，不以本批测试宣称全部完成。
