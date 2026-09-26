# 仿生记忆：检索、反馈与证据边界

本批保留双轨记忆、遗忘、强化、联想和睡眠整合，修正学习信号的边界。

## 使用方法

```python
# 候选搜索、评测与诊断：不增加访问次数，不写关联，不累计成功/失败。
candidates = engine.recall_fused("用户喜欢什么饮料？", read_only=True)

# 实际调用：融合完成后，仅对最终返回且词项匹配的记忆强化一次熟悉度。
results = engine.recall_fused("用户喜欢什么饮料？")

# 只有外部确实判断该记忆有用/无用时才调用；每个判断事件提交一次。
engine.record_feedback(results[0].item.id, useful=True)
item = engine.backend.get(results[0].item.id)
usefulness = engine.verified_retrieval_confidence(item)
```

`recall(..., read_only=True)` 同样可用。`check`、`recall_trace` 和检索诊断默认只读。
“只读”指不修改持久化学习状态；允许填充查询缓存。

`verified_successes` / `verified_failures` 只接受显式反馈；没有反馈并不等于正确。
至少两次反馈后，`verified_retrieval_confidence` 返回带 Beta(1,1) 平滑的有用性估计；
不足样本返回 `None`。这不是事实真实性概率，也没有经过实际任务的校准验证。
正反馈提供复习强化，负反馈降低可检索强度；两者都不增加事实证据或来源信任。
调用者负责去重反馈事件；当前接口不支持事件 ID 或网络重试幂等。

旧 `retrieval_successes` / `retrieval_failures` 和 `calibrated_confidence` 保留兼容，
仍代表旧式内部匹配统计。新应用应使用显式反馈接口；本批没有全局切换旧校准策略。
新接口目前在 Python API 提供，未增加 MCP 工具。

## 睡眠整合

`evidence_sources` 保存原始来源与已计入贡献。来源标识包含来源类别、
`SourceRecord.ref`（缺省使用原始记忆 ID）、发生时间（若提供）和内容哈希。
请将 `ref` 指向具体事件/对话轮次，而非整份可变文档。

同一来源的重复存入、合并和回放不会反复增加证据；新增来源才增加贡献。
这表示“不同来源记录”，不意味着这些来源在统计上独立或已经核实。
没有 ref 的两次独立写入会产生两个身份，系统无法凭空判断是否来自同一事件。
来源账本随 SQLite 与 JSON 导出保存。内容修订会重置该条记忆的证据和显式反馈；
旧语义记忆保留原来的历史账本。

旧数据库自动增加新字段，不将旧内部匹配计数冒充外部反馈。
已有整合链接可用于保守接纳旧证据；不追溯编造历史来源，也不自动纠正历史膨胀数值。

## 验证与适用范围

```text
python -m unittest discover -s tests -q
python benchmarks/ci_regression.py
python benchmarks/biomimetic_feedback_eval.py --output feedback-report.json
```

新增生命周期评测使用固定时钟和 0/7/30/90 天只读探针，在同一进程重复运行核对一致性。
它验证机制边界，不代表真实对话准确率，也不证明优于竞品。
BM25 候选排序、受预算约束的联想、事实时效/版本策略和实际问答校准属于后续阶段。
