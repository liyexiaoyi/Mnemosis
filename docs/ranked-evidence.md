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
## 可选串联接口：排名融合后进行一次最佳替换

`mnemosis.ranked_evidence_refinement.refine_ranked_evidence` 是新增独立纯函数。
它复用原排名融合和一次最佳替换；原 `select_ranked_evidence` 接口、报告结构、
仿生评分与补全、默认 recall/CLI/MCP 均不改变。需要明确调用这个新入口。

```python
from mnemosis.evidence_selection import QueryAspect
from mnemosis.ranked_evidence import RankedChannel
from mnemosis.ranked_evidence_refinement import refine_ranked_evidence

report = refine_ranked_evidence(
    [RankedChannel("L", ["A", "B", "C"]),
     RankedChannel("D", ["A", "C", "B"])],
    [QueryAspect(str(i)) for i in range(1, 7)],
    support={
        "A": {str(i): 1 for i in (1, 2, 3, 4)},
        "B": {str(i): 1 for i in (1, 2, 5)},
        "C": {str(i): 1 for i in (3, 4, 6)},
    },
    limit=2, relevance_weight=0,
)
assert report.ranked_report.selection.selected_ids == ("A", "B")
assert report.refinement.selected_ids == ("C", "B")
assert report.refinement.coverage_component == 1
```

此例特意用纯覆盖权重展示贪心反例；排名相关性仍在报告中保留，但不参与该例
目标。通常由调用方明确选择相关性权重，默认仍是 .5；新入口没有新增或调整权重。

返回 `RankedEvidenceRefinementReport`：`ranked_report` 保留通道状态、融合排名与
原贪心报告；`refinement` 给出最终 ID、覆盖、缺口、替换记录及检查数量。
最终组合应读取 `report.refinement.selected_ids`。`ranked_report.selection.steps`
只描述原组合，不能视为最终选择步骤。两份原选择报告数值一致，容器独立。

候选顺序完全来自原融合排名，不改融合常数、通道/要点归一化、K、lambda 或支持。
以原始要点权重重新调用已有选择器，避免对已归一化权重二次舍入。调用前快照
要点和支持映射；通道由原接口复制。报告字典可修改，不是并发输入修改的沙箱。
复制支持前拒绝超过100候选/单候选32要点的映射；合法输入本就受这些边界限制。
失败、禁用、正常空通道、下溢正权重候选、明确0支持和未提供支持沿用原规则。
没有支持时仍必须显式指定 relevance_weight=1，包括容量0。

一次替换的候选配对上限2500，容量5最多475；所有替换从原组合出发。
只接受严格提高计算目标值的最佳替换，同分保留既有候选顺序。
为保持原两个公共模型不变，串联接口会再执行一次贪心基线，增加计算代价。
这不代表再次检索或进行第二轮替换；也不保证最终局部/全局最优。

### 串联验证（2026-10-07）

新增49项永久配置，含150组独立Fraction排名/替换邻域核算、数值精度、预算、
资料缺失/失败/禁用通道、输入隔离与两后端只读检查。先确认RED49失败；定向
GREEN172项/180子场景，完整1174项/374子场景、CI18/18通过。
49个原有产品源文件逐字不变；新增一个产品模块，没有依赖或数据库迁移。

额外固定300组数学输入：18组代理目标严格提高、0组退步，全部匹配原集合的一次
最佳邻域。旧六条构造轨迹中5条可评价，必要证据找齐3/5->5/5；另一个明确标为
假设的粗支持/摘要高排名变体仍失败。两后端14组完整记忆、链接、日志和SQLite
逻辑状态均不变。必要ID只在选择返回后用于评价，未传入算法。
这些是已使用构造轨迹及数学检查，不是实际QA准确率、新盲测或同类项目领先。

同一机器七次、8通道/100候选/32要点/K5的纯接口耗时中位：原融合贪心 7.17ms，串联一次替换 22.01ms。不含模型推理、实际检索、DB与序列化，不宣称端到端提速。

粗支持资料可给泛泛摘要满覆盖分，仍遗漏实际必要事件；优化目标不能替代资料质量。
新接口没有自动支持标注、事实核验、时间版本裁决或必须共同出现的证据约束。
验证日志、固定输入与恢复证明：`E:/Mnemosis/evaluation/ranked-evidence-refinement/2026-10-07/implementation-01/`。


## 可选原文引用核验（2026-10-07）

串联入口新增两个可选关键字 `source_texts`、`support_spans`，必须同时提供。
两者均为 `None` 时沿用原行为和报告结构。核验通过不会增加支持分或改变排序；
不匹配时在排名与证据选择前显式报错，不把问题静默改成0分。

```python
from mnemosis.evidence_selection import QueryAspect
from mnemosis.ranked_evidence import RankedChannel
from mnemosis.ranked_evidence_refinement import SupportSpan, refine_ranked_evidence

report = refine_ranked_evidence(
    [RankedChannel("L", ["A"])],
    [QueryAspect("arrival")],
    support={"A": {"arrival": 1}}, limit=1,
    source_texts={"A": "李明😀到了北京。"},
    support_spans={"A": {"arrival": SupportSpan(3, 8, "到了北京。")}},
)
assert report.refinement.selected_ids == ("A",)
assert report.refinement.objective == 1
```

`SupportSpan(start, end, quote)` 为 frozen/slots 数据对象。偏移使用 Python 字符串
的 Unicode 码点，采用左闭右开区间；不是字节或 UTF-16 单元。中文例中的表情计1个
码点，组合字符可占多个码点。`0 <= start < end <= len(text)` 且
`text[start:end] == quote`；偏移须为非 bool 整数，引用须非空。大小写、空格、
换行（包括 CRLF）和 Unicode 均不自动规范化。

每个原始严格正的显式支持值均须提供对应引用，包括数值转换后下溢为0的极小正值。
明确0无需引用；如果提供，仍须核验。未提供的支持对不能附加引用。即使容量为0，
所有给出的资料仍完整核验。正文与引用的记忆ID必须属于原始正权重通道的候选并集；
正文可以包含尚未提供支持的候选。原通道失败、禁用、资料缺失等规则仍然有效。

资料上限：100条正文、每候选32个引用、每正文65536码点、正文总计1048576码点。
原100候选/32要点边界不变；输入不能在调用中并发修改。调用方负责提供正文，接口
不会读取存储、生成引用、调整支持或核实正文的来源。返回仍只有 `ranked_report`
和 `refinement`，两份报告的原含义不变。

这是引用一致性检查：只能证明引用与调用方提供的正文逐字一致。它不能证明引用
蕴含要点、来源真实或事实正确。保留的粗支持反例中，泛泛摘要引用合法，仍获得满
覆盖却遗漏必要事件；不能以该检查替代语义支持评价，也未接入默认检索链路。

### 引用核验验证

新增48项永久测试配置，包括错绑、越界、缺失、0支持、极小正值、Unicode、容量0、
资源边界与两实际后端完整只读检查。有效输入保持原结果；非法引用在评分前被拒绝。
真实RED48失败后实施，定向180项通过，完整1222项/374子场景和CI18/18通过。
初期测试准备错误的日志保留，不能归因产品故障。

300组历史数学输入与14组后端报告精确复现；新增100组冻结Unicode输入的有效结果
与关闭核验时相同，300次非法调用均拒绝。14组实际后端另拒绝36次非法调用，全部
记忆、链接、召回日志、SQLite逻辑状态保持一致。原有其余49个产品源文件逐字不变。
文档示例已执行；由作者自行审查，没有独立审查者。

这些是正确性与历史回归检查，不是实际问答成绩或新的横向排名。代码和评测在
`E:/Mnemosis/evaluation/support-grounding/2026-10-07/implementation-01/`；
备份恢复完成与否以 `E:/Mnemosis/backups/2026-10-07-support-grounding/manifest.json`
为准，恢复使用外部已安装的本机运行时。
