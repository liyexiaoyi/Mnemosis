# 归一化排名融合与显式证据选择

此接口把多通道排名转成有界相关性，再依据调用方明确提供的要点支持选择互补记忆。它是独立纯函数，不读取数据库、调用模型或强化记忆，也没有自动接入 MemoryEngine.recall、recall_fused、CLI/MCP 或默认策略。

## 实际用法

```python
from mnemosis.evidence_selection import QueryAspect
from mnemosis.ranked_evidence import RankedChannel, select_ranked_evidence

report = select_ranked_evidence(
    [RankedChannel("L", ["A", "B", "C"]),
     RankedChannel("D", ["A", "C", "B"])],
    [QueryAspect("X", .6), QueryAspect("Y", .4)],
    support={"A": {"X": 1}, "B": {"X": 1}, "C": {"Y": 1}},
    limit=2,
    relevance_weight=.5,
)
assert report.selection.selected_ids == ("A", "C")
print(report.relevance_by_id)
print(report.selection.objective)
```

该例已通过实际 API 和独立 Fraction 核算。A 的相关性为 1，B/C 都是 7625/7812 ≈ 0.97606；选择 A/C 的目标值为 31061/31248 ≈ 0.99401。仅取融合排名前两项会得到 A/B，二者都支持 X，缺少 Y。这里的支持矩阵是调用方输入，接口没有从文字或答案自动推断支持。

## 数学职责

排名融合负责相关性，固定 c=60：

```
p_j = a_j / sum(a_j)
r_i = sum_j p_j * 61 / (60 + rank_ji)
```

rank 从 1 开始；未出现在某通道的候选贡献为 0。分母包含所有启用的正常通道，包括空通道。相关性处于 [0,1]，同 ID 跨通道只合并贡献，不增加独立事实来源或 verified 计数。

上例通道各占 1/2：

| ID | L 贡献 | D 贡献 | 总相关性 |
|---|---|---|---|
| A | 1/2 | 1/2 | 1 |
| B | 61/124 | 61/126 | 7625/7812 |
| C | 61/126 | 61/124 | 7625/7812 |

证据选择复用已有 select_evidence。K 为请求容量，w_t 是归一化要点权重，g_ti 是显式支持，lambda 是 relevance_weight：

```
F_K(S) = lambda * sum(r_i for i in S) / K
         + (1-lambda) * sum_t w_t * max(g_ti for i in S)
```

K 固定，不随实际选中条数变化。选择器每次取最大正边际增益；同一要点的覆盖饱和，重复支持不反复加分。K=0 时返回空选择及零分，但全部输入仍校验。仅正增益候选被选，因此结果可以少于 K。贪心不保证全局最优。

排名相关性不是事实可信度；要点覆盖分不是回答正确概率；完整必要证据是否找全须另行评价。此分工保留仿生记忆中的关联召回和有限工作记忆职责，不将共识排名当成事实核验。

## 支持资料和通道状态

没有支持资料时，调用方必须显式选择纯相关性：

```python
report = select_ranked_evidence(
    [RankedChannel("L", ["A", "B"])], [],
    support=None, relevance_weight=1, limit=2,
)
assert report.support_state == "not_supplied"
```

None、空外层映射、所有内层均为空都是未提供资料，默认 relevance_weight=.5 会拒绝，包括 limit=0。明确提供 `{"A": {"X": 0}}` 属于已提供资料，报告保留该对，但 X 的覆盖仍为 0；缺失对表示未提供，不等于已验证不存在证据。纯相关性模式也校验支持中的未知 ID、未知要点及非法值。

正常空通道仍占分母：同权 L=[A]、D=[] 得到 r_A=.5。失败不能伪装成空检索；正权重的 status="failed" 抛 ValueError。调用方确定禁用后可显式传：

```python
channels = [RankedChannel("L", ["A"]),
            RankedChannel("D", [], weight=0, status="failed")]
report = select_ranked_evidence(channels, [], relevance_weight=1)
assert report.relevance_by_id["A"] == 1
assert report.channels[1].enabled is False
```

failed 必须为空；权重 0 的通道仍完整校验。禁用改变了配置模型，函数不会自动丢弃失败通道。

## 输入、数值和报告

- channels 为 Sequence，1–8 个 RankedChannel；单通道最多 100 个 ID，原始正权重通道的候选并集最多 100 个；超限拒绝，不能隐式截断。生成器、字符串不作为序列接受。
- ID 必须是非空且无首尾空格的字符串；通道 ID 唯一，单通道 ID 不重复。跨通道仅完全相同 ID 合并，大小写和 Unicode 不自动规范化；相同文字或支持形状不会合并不同 ID。
- aspects 最多 32 个 QueryAspect，ID 唯一，非负有限权重，非空时至少一个正权重；limit 为非 bool 整数 0–100；relevance_weight 和支持为非 bool 有限 Real，范围 [0,1]。Decimal 不属于支持的 Real 类型。
- 通道权重为非 bool 非负有限 Real，至少一个原始正权重。以最大权重缩放后求和，混合巨型整数/有理数必要时使用精确比值，避免先转换浮点造成溢出。
- 原始正权重决定启用和候选并集。浮点归一化后为 0 的正权重通道列入 underflow_channel_ids，其候选仍保留，可凭显式覆盖被选中。例如权重 1e308/1e-308 时后者会报告下溢；没有人为权重下限。仅消除 1e-12 内的分数边界舍入。
- candidate_ids 按相关性降序，精确同分按通道输入及排名的首次出现顺序。选择边际增益精确同分时沿用该候选顺序，不按 ID 文本排序。

报告字段：channels 保留状态、启用标志、归一化权重和条目数；relevance_by_id 与 contributions_by_id 给出相关性及每通道排名/贡献；support_state、supplied_support_pairs 区分资料状态并保留明确的 0；underflow_channel_ids 报告归一化权重下溢；selection 为原选择器报告，包括每步增益、覆盖、缺口和最终分量。

输入容器在调用时复制。dataclass 为 frozen/slots，但报告内的字典可修改；它们不共享输入或另一调用的容器。接口不是并发修改输入的安全沙箱。

## 验证与适用边界

六条提前冻结的构造轨迹，在 Dict/SQLite 上对照，共 48 重复配置；其中 5 条有必要 ID。共享候选并集、相关性和 K 的两个主方法，完整必要证据从融合 TopK 的 2/5 到覆盖选择的 3/5，有 2 条收益、1 条退步。逐通道 TopK 的候选池不同，另报消融，不能混为同预算主对照。

退步轨迹的粗支持资料把泛泛的“讨论行程”标为覆盖两个事件要点，导致漏掉必要离开事件。另有贪心反例覆盖为 5/6，独立枚举最优为 1。这些负例保留在原始结果中，不通过修改资料凑分。

该接口不提供自动支持标注、事实冲突处理、时间版本裁决、必须共同出现的证据约束、token 预算或真实问答充分性判断。构造代理收益不能视为真实检索提升或同类项目领先。实际接入前仍需独立支持质量评价和新的真实任务留出测试。

验证入口：tests/test_ranked_evidence.py、tests/test_ranked_evidence_integration.py；固定构造评测 benchmarks/ranked_evidence_eval.py（--out 必须为新目录）。原始日志、精确审计和交付报告位于 E:/Mnemosis/evaluation/math-integration/2026-10-06/implementation-01 及 E:/Mnemosis/ranked-evidence-report-2026-10-06.md。