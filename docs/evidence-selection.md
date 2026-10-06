# 独立证据选择：有限容量下挑选互补线索

本接口为仿生工作记忆增加独立的证据选择机制。候选已经由调用方准备，问题要点和支持值也由调用方显式提供。它只计算选择和解释，不访问存储、不调用模型、不触发访问或验证强化。现有 `recall`、`working_set`、`working_set_budget`、默认检索与顶层导出保持原样；须从子模块导入。

## 使用示例

```python
from mnemosis.evidence_selection import EvidenceCandidate, QueryAspect, select_evidence

candidates = [
    EvidenceCandidate("A", 1.0, {"X": 1.0}),
    EvidenceCandidate("B", 0.95, {"X": 1.0}),
    EvidenceCandidate("C", 0.4, {"Y": 1.0}),
]
aspects = [QueryAspect("X", 0.6), QueryAspect("Y", 0.4)]
report = select_evidence(candidates, aspects, limit=2, relevance_weight=0.5)
print(report.selected_ids)   # ('A', 'C')
print(report.objective)      # 0.85
```

A与B重复支持X，C支持Y。A选中后，B的增益为0.2375，C的增益为0.3，所以选C。最终归一化相关性为0.7、给定要点覆盖为1、综合代理目标为0.85。原排序Top2选A/B，其目标为0.7875。这些值是显式输入下的数学结果，不是答案正确率。

## 公式与各部分职责

令K为调用时固定的请求容量，r为给定相关性，g为给定要点支持，w为归一化要点权重，lambda为`relevance_weight`。K>0时：

```text
R(S) = sum(r_i for i in S) / K
m_c(S) = max(g_ci for i in S), max(empty)=0
C(S) = sum(w_c * m_c(S))
F(S) = lambda * R(S) + (1-lambda) * C(S)
Delta(i | S) = lambda*r_i/K
               + (1-lambda)*sum(w_c*max(0, g_ci-m_c(S)))
```

在合法集合大小不超过K时，R、C、F均为0–1。分母始终是K，不能改成当前选中数量或候选数量：前者可能使加入弱项后目标下降，后者会使增加无贡献候选改变已有集合目标。候选不足时也不缩小K。

覆盖采用最大支持，所以相同要点逐渐饱和，新的要点获得额外价值。BM25、余弦、RRF继续负责候选检索和融合；指数遗忘负责保留强度；verified Beta负责反馈有用性估计；本模块只负责有限容量下的显式证据组合。仿生类比是功能分工，不是生理模拟。

理想实数条件下，固定支持矩阵的非负模块化相关性加最大覆盖构成单调次模目标。纯条数约束的精确边际贪心有经典1−1/e代理目标近似界；这不保证全局最优、答案正确或必要证据完整，也不适用于直接替换成token/冲突/时间链硬约束。[Krause与Golovin的综述](https://www.cs.cmu.edu/~dgolovin/papers/submodular_survey12.pdf)。实现用浮点数，极端权重可能下溢，理论说明不能作为任意浮点边界的精确保证。

## 输入和报告

- `EvidenceCandidate(memory_id, relevance, support)`：不同候选的ID须唯一且为非空、无首尾空白字符串；相关性和所有支持值是有限0–1实数。`support`是要点ID到支持值的映射。
- `QueryAspect(aspect_id, weight=1.0)`：要点ID须唯一；原始权重有限非负，非空要点至少一项正权重。权重先按最大值缩放再归一化；极大整数、Fraction和混合浮点权重不会先转换成溢出浮点。
- 最多100候选、32要点，`limit`为0–100整数（默认5），`relevance_weight`为有限0–1实数（默认0.5）。拒绝bool作为数值、错误类型、未知要点、NaN/Inf、越界和超限；不静默截断。
- K=0仍验证全部输入，然后返回空选择和零目标。空候选也返回空；空要点仅lambda=1合法，此时只按正相关性选择。
- 只选严格正增益，达到K或无正增益时停止；精确平局保持候选输入顺序。不同ID即使支持相同也不自动合并。
- `selected_ids`及`steps`按贪心选择顺序返回。步骤中的`relevance_gain`、`coverage_gain`已包含lambda系数，`total_gain`为两者之和，`objective_after`为该步后的目标。
- `relevance_component`、`coverage_component`为未乘lambda的最终分量；`objective`为综合目标。`requested_limit`和`candidate_count`保留原请求及输入数量，便于解释不足额选择。
- `aspect_coverage`报告给定支持矩阵上的最大支持；`normalized_aspect_weights`报告归一化权重；`uncovered_aspect_ids`列原始正权重且支持为0的要点，`partial_aspect_ids`列支持在0与1之间的要点。

未提供支持默认0，只表示调用方未提供，不表示记忆中不存在事实。原始正权重极小时归一化可能下溢成0，但该要点仍参与缺口诊断；原始零权重要点不列为缺口。缺口不是自动拒答依据，覆盖1也不是事实确认或证据独立性。

输入的列表/支持映射不会被修改。DTO字段冻结；返回报告里的字典可由调用方修改，但不会污染后续调用。调用方负责ID存在、活跃状态、排除规则、来源可信度、实体/范围/版本和时间链相容性。本函数不知道任何存储内容。

## 已核验的构造对照及限制

提前冻结6条构造轨迹，两个存储后端、三种方法重复得到36配置。只有5条有声明的必要ID；未提供支持的第六条不计“找全”。原排序TopK找全2/5，精确记录去重TopK为3/5，本选择器为3/5。相对原排序有2条改善、1条退步；相对精确去重有1条改善、1条退步。两后端选中结果一致，完整记忆/关联/召回日志及SQLite完整dump与写入诊断均保持。

负例必须保留：必要时间链B/C在过粗支持矩阵下被A/B替代，漏掉C。另有六要点覆盖反例，贪心选A/B仅5/6，最优B/C为1。代理覆盖不能表达所有“必须一起出现”的任务互补性。

这些是显式输入的构造诊断，未运行实际召回、模型回答或新公开盲测；不能推断真实检索准确率提高或同类产品排名。独立函数100候选、32要点、K=5的七次耗时只描述函数成本，不能视为端到端加速。

运行对照：`python benchmarks/evidence_selection_eval.py --out <新输出目录>`。脚本固定使用本仓库src与冻结fixture，拒绝覆盖已有结果；必要ID仅用于评测，不回灌支持生成。实际输出含完整输入、选中ID、逐步增益、独立Fraction目标、必要ID完整性、后端状态与七次原始耗时。

## 可选必需要点约束（2026-10-07）

`select_required_evidence` 在同一模块中提供受限组合选择。原 `select_evidence`、
排名融合、一次替换和默认 recall 的行为与报告不变。调用方显式提供候选、归一化
相关性、要点和支持资料；本接口不自动召回或标注支持。

```python
from mnemosis.evidence_selection import (
    EvidenceCandidate, QueryAspect, select_required_evidence,
)

report = select_required_evidence(
    [EvidenceCandidate("A", 1, {"place": 1}),
     EvidenceCandidate("B", 1, {"place": 1}),
     EvidenceCandidate("C", .6, {"time": 1})],
    [QueryAspect("place"), QueryAspect("time")],
    required_aspects=("place", "time"), limit=2, relevance_weight=.8,
)
assert report.status == "feasible"
assert report.selection.selected_ids == ("A", "C")
assert report.completeness == 1
```

`required_aspects` 为要点ID序列时阈值默认1，也可使用映射，如
`{"place": 1, "time": Fraction(3, 4)}`。阈值须有限且属于(0,1]；要点必须
已声明，无重复、未知或非法ID。原100候选、32要点、容量和数值验证仍适用，
容量0也不绕过验证。必需要点权重为0时仍须满足约束。

算法保留原固定容量效用U，要求每项必需支持的最大值达到其阈值，然后提高U。
原始支持与阈值先转换为精确Fraction再比较，不先转换成float。没有容差补全：
`1 - Fraction(1, 10**30)` 不能满足阈值1。目标U仍用既有浮点计算；不声称
浮点最优等于任意精度实数最优。

先检查容量0和全池支持不足，保留原贪心的可行组合，再进行确定性的深度优先
子集搜索。按达到阈值的要点数、相关性、原输入顺序访问候选；用剩余候选覆盖
并集和所需条数的安全下界剪枝。默认 `search_budget=10000`，可设0–100000整数。
预算计算访问节点（包括剪枝节点），不是子集数量、毫秒或总CPU成本。前置验证、
原贪心与标注不计入节点预算。预算限制避免100候选时无条件遍历全部组合。

报告同时提供原贪心 `baseline` 与可行结果 `selection`：

| 字段/状态 | 含义 |
| --- | --- |
| `status="feasible"` | 已找到容量内满足给定约束的组合 |
| `status="infeasible"` | 已证明给定候选及支持资料下不可行 |
| `status="undetermined"` | 预算结束且未找到组合，不能宣布不存在 |
| `status="not_applicable"` | 必需集合为空，原选择结果精确沿用 |
| `optimality="optimal"` | 搜索完成，得到既有浮点U的最大可行值 |
| `optimality="not_proven"` | 已有可行组合但未证明最大效用 |
| `optimality="not_applicable"` | 没有可行组合，或未启用约束 |
| `search_complete`、`visited_nodes` | 是否搜索/证明完成以及实际访问节点数 |

找不到可行组合时 `selection=None`，不把原不完整组合冒充成功。预算耗尽但已有
可行组合时保留该组合。空必需集合不进行搜索，也不宣称原贪心最优。
约束结果的ID按原输入顺序返回；相同浮点U优先较少条数，再按输入索引平局排序。
`steps` 为该顺序下的边际分量回放，不是搜索路径。必需支持可能带来0增益步骤。

`required_thresholds`、`pool_coverage`、`required_coverage` 和 `completeness` 使用
精确Fraction。对返回的可行集合，完整度为
`min_a min(1, required_coverage[a]/required_thresholds[a])`，必为1；空必需集合
或无可行结果时为None。序列化时需显式保存分数为字符串或分子/分母，不要用
舍入展示值重新判断可行性。报告字典可被调用方修改，不影响后续调用。

`missing_support_pairs` 列出所有候选与必需要点之间未提供的支持对；
`support_state` 为 `complete`、`partial`、`absent` 或空约束的 `not_applicable`。
明确0计为已提供，缺失则内部用0占位。给定输入不可行不证明原文无证据。
全池每个要点都有支持，也不保证容量内可行。

该约束不校验语义蕴含、实体/时间相容、来源真实性或事实正确。错误地给泛泛摘要
标注满支持仍会通过，永久负例保留。原引用核验入口没有自动串联到本函数。
必需要点及支持不得由测试答案或gold证据ID生成。

本轮200组固定数学输入、4547子集与精确枚举一致。其中21组原选择漏要点但存在
可行组合得到修复，16组旧效用下降以满足约束；这不是实际QA收益。两个实际
后端的完整记忆、关联、召回日志及SQLite状态保持不变。验证、局部耗时和恢复
记录在 `E:/Mnemosis/evaluation/required-evidence/2026-10-07/implementation-01/`。
