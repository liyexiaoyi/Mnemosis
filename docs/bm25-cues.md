# 可选 BM25 线索通道

```python
# 精确词项线索，始终只读，未匹配词项时返回空列表。
candidates = engine.recall_bm25("Alice green tea", top_k=10)

# 经本批评测的受限融合配置；实际调用保留最终单次熟悉度强化。
results = engine.recall_fused(
    "Alice green tea", bm25_weight=2.0, ng_weight=1.0, kw_weight=0.0,
    normalize_fusion=True, pass_k=50, rrf_k=60,
)
# 评测、候选尝试或诊断时，再传 read_only=True。
```

BM25 复用项目分词和 cues，利用词频、词的稀有程度和文档长度找线索。
不写入独立事实证据，不替代遗忘、整合、反馈或元认知。
recall_bm25 支持 kind、exclude_ids，并尊重 active 状态和定向遗忘。
其 confident=False 表示没有经过事实置信判断，不代表内容为假。

旧调用默认不启用 BM25 或归一化。归一化把 RRF 除以各有效通道的理论最大分数之和，
再将时间/线索增益限制在相关性分数的 25% 内；结果分数也不是正确概率。
显式选用新模式时，early_stop 不会提前跳过 BM25 通道。

缓存首次构建含词频的倒排表，热查询只累计相关倒排表。
SQLite 的词法标记由触发器随内容、cues、类型、状态、顺序变化而更新；
反馈、强度和关联改变不使索引失效。标记可跨连接读取，也随事务回滚恢复。
标记使用随机令牌避免回滚后版本序号重复。SQLite 旧库自动增加元数据，不改记忆字段。
内存后端每次检查轻量内容指纹；自定义后端若未实现 revision_token 则不缓存。
只缓存最近一种 kind；首次调用、重启或切换 kind 需要建立索引。
新增有界变更记录与每文档反向词项：普通增删改、遗忘/恢复只更新变化文档，精确维护 df 和平均长度。
每次同步最多 1,024 事件；记录缺失、链断裂、回滚分叉或超预算时完整重建。
SQLite 最多保留约 4,351 条元数据事件，定期清理，旧记忆不会被日志清理删除。
十万条 65 词合成记忆：单条编辑写入约10.5毫秒，随后指定词查询约0.24毫秒；
同一数据强制完整重建约10.2秒。首次/重启成本仍在，以上不是任意查询的延迟保证。
近似保留索引对象图约123 MiB，不包含进程整体或峰值内存。
第三批实测和边界说明：E:/Mnemosis/third-batch-report-2026-09-26.md。

本批留出 95 道可回答题：BM25 Top-5 84.2%，原 n-gram 75.8%，组合 81.1%。
留出题共享部分聊天历史；不能据此声称完整回答准确率或竞品总排名提升。
详细对照、退步案例和冷/热性能见 E:/Mnemosis/second-batch-report-2026-09-26.md。

复现工具：benchmarks/bm25_cue_eval.py、analyze_bm25_cues.py、bm25_scale_eval.py。
冻结协议存放在 benchmarks/protocols/2026-09-26-bm25-cues.json，数据哈希包含其中。
本批 Python API 已提供，MCP 工具参数尚未扩展。
