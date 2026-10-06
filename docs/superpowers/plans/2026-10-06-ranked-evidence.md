# Ranked Evidence Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. 用户已确定主助手单人实施与审查，禁止子智能体，不再询问执行方式。

**Goal:** 实现独立的归一化排名融合到显式证据选择接口，验证分数边界、互补覆盖及失败行为。

**Architecture:** 新增一个纯函数模块，将显式通道排名转为固定权重分母的相关性，再复用现有select_evidence。调用方负责候选获取、过滤与支持资料；实际后端只用于验证读取和状态不变，首批不接入MemoryEngine默认流程。

**Tech Stack:** Python >=3.10与标准库；现有Dict/SQLite、pytest、可选Rust/NumPy仅用于既有验证环境，不新增依赖。

**Spec:** [已确认的书面规格](E:/Mnemosis/repo/docs/superpowers/specs/2026-10-06-ranked-evidence-design.md)，设计提交5273a3962efc92cbd3e157bb0b8e69a0dcaf3859。用户于2026-10-06回复“ok”批准书面规格。用户于2026-10-06回复“实施”批准本计划。三项任务已完成；948测试/374子场景、CI18/18通过，两个恢复ZIP核验通过，最终关闭记录见交付目录manifest。

## Global Constraints

- 代码、评测、报告和备份均在 E:/Mnemosis；主助手单人实施与审查；不使用子智能体、不推送远端。
- 固定c=60，不新增可调平滑常数。
- channels是标准collections.abc.Sequence，排除str/bytes/bytearray；数量1–8。每项必须是RankedChannel。
- 正权重ok通道的ID并集最多100个，超过则拒绝，不能静默截断。上限按去重并集计算，而非排名条目总数。
- 每通道最多100个；ID字符串非空、无首尾空格，各通道ID唯一，单通道记忆ID不重复。
- weight为非bool有限非负Real，至少一个原始正权重；禁用通道仍校验。正常空通道保留权重；启用failed通道抛ValueError，failed只能是空列表。
- aspects最多32个；limit为非bool整数0–100；relevance_weight为非bool有限实数0–1；相关性与支持值0–1。全部输入校验，包括limit=0。
- support=None、空映射或全空内层须显式lambda=1；明确的0支持算已提供。未知候选/要点不能在纯相关性模式绕过。
- dataclass使用frozen和slots，复制输入可变容器；报告字典不与输入或其他调用共享。
- 不改顶层__init__、MemoryEngine、recall、recall_fused、working_set_budget、CLI/MCP、数据库结构、依赖或默认策略。不新增哈希、模型调用、全库扫描、持久缓存或访问强化。
- 原始正权重决定启用和候选并集，浮点下溢另报underflow_channel_ids；只允许消除1e-12范围的0–1边界舍入。
- 代理目标不表示事实正确性、回答充分性、相同token预算或市场领先；不在查询时用金标构造支持。
- 使用既定E盘分支；正式产品编辑前保存新的恢复备份，不覆盖旧档。静态包复用copy_verified一次源流与一次目标读取，避免反复摘要记忆。

## Review Focus

1. 外层支持映射有候选键、内层全空仍是无资料；默认lambda=.5须拒绝，不能误报supplied。任务1测试test_empty_inner_maps_require_explicit_relevance。
2. 禁用通道不能隐藏无效ID、重复ID或错误状态；只禁用候选贡献，不禁用校验。任务1测试test_disabled_channel_still_validates。
3. 原权重正但归一化为0的通道仍引入候选，候选可凭显式覆盖被选。任务1测试test_underflow_keeps_enabled_candidates。
4. ID仅按完全相等合并；大小写、Unicode字符不自动规范化，同分不用字典序。任务1测试test_identifiers_are_exact_and_ties_follow_input。
5. 修改一次报告的内层映射不得污染输入、下一次报告或真实后端；多通道出现同ID不能增加独立来源/verified计数。任务1容器隔离测试、任务2真实状态检查。

## 文件职责

- Create E:/Mnemosis/repo/src/mnemosis/ranked_evidence.py：公开值对象、完整校验/快照、稳定归一化、贡献与支持状态报告，复用选择器。
- Create E:/Mnemosis/repo/tests/test_ranked_evidence.py：真实API失败测试、精确Fraction预期、输入/数值/顺序/隔离边界。
- Create E:/Mnemosis/repo/tests/test_ranked_evidence_integration.py：实际Dict/SQLite记录、只读读取和全状态对照。
- Create E:/Mnemosis/repo/benchmarks/data/ranked_evidence_cases.json：提前冻结6条构造轨迹，不做自动事实标注。
- Create E:/Mnemosis/repo/benchmarks/ranked_evidence_eval.py：相同并集的融合TopK与融合覆盖选择；逐通道消融另报候选池。
- Create E:/Mnemosis/repo/docs/ranked-evidence.md：实际用法、字段、数学职责与验证限制。
- Update 本实施计划/已批准规格的实际状态；E:/Mnemosis/WORKLOG.md与新交付报告记录事实，不改既有产品文件。

## 执行目录与验证命令

计划审查通过后新建E:/Mnemosis/evaluation/math-integration/2026-10-06/implementation-01；若已存在，不覆盖，读取其状态后选择新后缀。下面命令使用该首次目录：

~~~powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH='E:\Mnemosis\repo\src;E:\Mnemosis\repo\benchmarks;E:\Mnemosis\tools\python;E:\Mnemosis\tools\numpy'
$env:MNEMOSIS_TEST_RUST='1'
$env:MNEMOSIS_TEST_NUMPY='1'
$env:TEMP='E:\Mnemosis\evaluation\math-integration\2026-10-06\implementation-01'
$env:TMP=$env:TEMP
~~~

工作目录E:/Mnemosis/repo，写E盘及Git操作沿用现有require_escalated授权流程。保存原始日志、实际退出码和源码提交；退出0且零失败才算通过。基线926测试/279子场景及18/18属于上一轮，不作为新验证结果。

### Task 1: 数学接口与独立精确测试

**Files:** Create ranked_evidence.py、test_ranked_evidence.py及提前冻结的ranked_evidence_cases.json，路径见文件职责。

**Interfaces:**
- Consumes：evidence_selection.QueryAspect、EvidenceCandidate、EvidenceSelectionReport与select_evidence(candidates, aspects, *, limit=5, relevance_weight=.5)。仅用公开接口，不导入私有校验/评分助手。
- Produces：RankedChannel(channel_id: str, memory_ids: Sequence[str], weight: Real=1.0, status: str="ok")。
- Produces：ChannelSummary(channel_id: str, status: str, enabled: bool, normalized_weight: float, input_count: int)；RankContribution(channel_id: str, rank: int, contribution: float)。
- Produces：RankedEvidenceReport字段channels:tuple[ChannelSummary,...]、candidate_ids:tuple[str,...]、relevance_by_id:dict[str,float]、contributions_by_id:dict[str,tuple[RankContribution,...]]、support_state:str、supplied_support_pairs:tuple[tuple[str,str],...]、underflow_channel_ids:tuple[str,...]、selection:EvidenceSelectionReport。
- Produces：select_ranked_evidence(channels: Sequence[RankedChannel], aspects: Sequence[QueryAspect], *, support: Mapping[str,Mapping[str,Real]]|None=None, limit:int=5, relevance_weight:Real=.5) -> RankedEvidenceReport。dataclass构造器承载值，函数做完整校验。

- [x] **Step 1: 保存基线和冻结构造输入。** 核对工作区与批准规格/计划，保存源码提交和恢复说明；git archive当前已提交源码到新的E:/Mnemosis/backups/2026-10-06-ranked-evidence-before，核验后才编辑产品。按下方6条定义写fixture并复制到implementation-01/frozen-cases.json；参数、必要ID和支持均提前固定。
- [x] **Step 2: 写真实API失败测试。** 延迟导入mnemosis.ranked_evidence，只将该模块缺失转为明确失败，其他ImportError照常抛出。test_complementary_selection_matches_fraction断言：

~~~python
channels = [RankedChannel("L", ["A", "B", "C"]),
            RankedChannel("D", ["A", "C", "B"])]
aspects = [QueryAspect("X", .6), QueryAspect("Y", .4)]
report = select_ranked_evidence(
    channels, aspects, support={"A": {"X": 1}, "B": {"X": 1}, "C": {"Y": 1}}, limit=2)
assert report.candidate_ids == ("A", "B", "C")
assert report.selection.selected_ids == ("A", "C")
assert abs(report.relevance_by_id["B"] - float(Fraction(7625, 7812))) <= 1e-12
assert abs(report.selection.objective - float(Fraction(31061, 31248))) <= 1e-12
assert report.support_state == "supplied"
assert report.supplied_support_pairs == (("A", "X"), ("B", "X"), ("C", "Y"))
~~~

- [x] **Step 3: 补齐校验和Review Focus失败测试。** 名称与预期如下；用subTest表覆盖输入类，预期错误类型固定，错误文本不固定：

~~~python
# test_empty_inner_maps_require_explicit_relevance
with self.assertRaises(ValueError):
    select_ranked_evidence([RankedChannel("L", ["A"])], [QueryAspect("X")],
                           support={"A": {}}, limit=0)
# test_failed_channel_is_not_empty
with self.assertRaises(ValueError):
    select_ranked_evidence([RankedChannel("L", []), RankedChannel("D", [], status="failed")],
                           [], relevance_weight=1)
# test_disabled_channel_still_validates
with self.assertRaises(ValueError):
    select_ranked_evidence([RankedChannel("L", ["A"]),
                           RankedChannel("D", ["B", "B"], weight=0)], [], relevance_weight=1)
# test_explicit_zero_is_supplied
r = select_ranked_evidence([RankedChannel("L", ["A"])], [QueryAspect("X")],
                          support={"A": {"X": 0}})
assert r.support_state == "supplied" and r.supplied_support_pairs == (("A", "X"),)
assert r.selection.uncovered_aspect_ids == ("X",)
~~~

同时固定测试：1/8/0/9通道；单通道100/101ID；8通道相同100ID并集100合法、两通道合计101唯一ID拒绝；空或未trim ID、重复channel_id、错误status和failed非空；非Sequence/generator/字符串、非RankedChannel；负数/NaN/Inf/bool/string/Decimal权重；全零权重；支持外/内层错误类型、未知ID或要点及0–1错误支持；lambda和limit错误，包括limit0仍校验；空aspects规则；None/空外层/全空内层分别要求lambda1。

- [x] **Step 4: 写数值/排序/隔离失败测试并实际运行RED。** 运行test_ranked_evidence.py，保存缺少真实模块的失败日志，不造测试替代算法。独立断言覆盖：
  - test_empty_channel_keeps_denominator：L=["A"]/D=[]同权，r_A=.5；将D显式weight0/statusfailed后r_A=1、D仍在报告enabledFalse。
  - test_weight_scaling_and_mixed_reals：权重2/3，共同乘1e-200或1e200，相关性在1e-12内一致；两个1e308或两个10**400同权各.5；float与巨型Fraction混合不溢出；MNEMOSIS_TEST_NUMPY启用时实际np.int64/np.float64路径通过。
  - test_underflow_keeps_enabled_candidates：L=["A"],weight=1e308；D=["B"],weight=1e-308；支持A:X=0/B:X=1，lambda0/K1应选B，r_B=0但D.enabledTrue、underflow=("D",)。
  - test_identifiers_are_exact_and_ties_follow_input：两个同权单项通道["z"]与["A"]，同分候选顺序z,A；改ID文本/大小写但保持位置与支持关系，选择位置不变；"A"/"a"不合并。
  - test_tail_append_and_shared_id：末尾追加新ID不改旧排名分；同ID跨通道归一化贡献相加但仅一候选；同支持不同ID不合并。
  - test_fraction_contributions_and_fixed_capacity：用独立Fraction从固定排名核算全部r和每通道贡献；支持公式与最终三分量独立核算，K=0/1/100、候选不足、lambda0/1及零贡献停止遵守原选择器。
  - test_input_and_report_isolation：deepcopy输入，多次调用相同；改report.relevance_by_id和selection.aspect_coverage不改输入/下一次输出；supplied_support_pairs按融合候选及要点顺序，含0且不含缺项。
- [x] **Step 5: 最小实现函数并GREEN。** 完整快照和校验；按原始正权重建立并集；最大权重缩放+fsum，必要时精确比值解决混合Real比较/除法溢出，保存下溢ID。每项贡献p_j*61/(60+rank)，累计r、按r降序/首次出现位置排序；完整支持校验与资料状态后构造EvidenceCandidate并调用公开select_evidence。错误类型和所有输出字段按规格，不修改旧模块。
- [x] **Step 6: 验证和单人审查。** 运行 `C:/Python314/python.exe -m pytest tests/test_ranked_evidence.py tests/test_evidence_selection.py tests/test_api_surface.py -q -p no:cacheprovider`；预期零失败/退出0。核对公式/数值范围/输入不变/没有新存储或模型依赖，独立oracle不调用产品评分助手。
- [x] **Step 7: 本地提交任务1。** diff --check，只暂存新模块、测试和已冻结fixture；提交“Add normalized ranked evidence selection”，不推送。

### Task 2: 两后端只读与固定构造对照

**Files:** Create test_ranked_evidence_integration.py、ranked_evidence_eval.py；使用任务1冻结fixture。不得看结果后改fixture。

**Interfaces:** Consumes任务1的全部公开接口；评测入口 `C:/Python314/python.exe benchmarks/ranked_evidence_eval.py --out E:/Mnemosis/evaluation/math-integration/2026-10-06/implementation-01/benchmark`。out须新建，记录实际模块路径、源码提交和冻结数据；不覆盖旧结果。

**冻结fixture定义：** 所有通道正常、同权；各条2通道，c60；每条保存唯一记忆ID及不同正文、USER来源ref、实体Mina、scope、aware occurred_at、episodic类型。支持是构造资料，不自动从正文/金标生成。除另注明，要点X/Y权重.6/.4，K2/lambda.5。

| name | L/D排名 | 支持、lambda差异 | necessary_ids |
|---|---|---|---|
| complementary | ABC / ACB | A:X1,B:X1,C:Y1 | A,C |
| same_support_distinct_ids | ABC / ABC | 单要点X，A:X1,B:X1,C:X0；lambda1 | A,B |
| partial_support | ABC / ACB | X/Y各.5；A:X.6,B:X.9,C:Y.8；lambda0 | B,C |
| support_not_supplied | ABC / ACB | support=null；lambda1 | null |
| necessary_time_chain_negative | BCA / BCA | A:X1Y1,B:X1,C:Y1；粗粒度A支持有误 | B,C |
| greedy_nonoptimal | ABC / BCA | 六同权要点；A:1234,B:125,C:346；lambda0 | B,C |

负例time_chain的B正文“Mina arrived on October 1.”、C“Mina departed on October 4.”，A“Mina discussed an October trip.”；A的粗粒度支持故意不能代表必要事件。必要ID在描述中声明，不能修正矩阵使例子变成收益。
complementary正文A“Mina visited Osaka.”、B“Osaka was the destination.”、C“The trip occurred in October.”。其他条正文按明确ID区分；same_support的A/B是不同记录，不能以同支持形状去重。

- [x] **Step 1: 写真实两后端集成测试。** 固定UTC2026-10-06T12:00:00，显式MemoryItem/来源/关系，带非零access、retrieval及verified计数和已有日志。get_many读取实际ID，构造两通道ABC/ACB与支持；断言选AC和精确目标。选择前后比较所有to_dict、all_links、_recall_log；SQLite完整iterdump与ReadOnlyGuard；多通道共享ID不能增加证据来源或计数。
- [x] **Step 2: 运行集成验证。** `C:/Python314/python.exe -m pytest tests/test_ranked_evidence_integration.py tests/test_evidence_selection_integration.py -q -p no:cacheprovider`，预期两个后端无状态变更/零失败。若需改旧召回或后端，报告范围变化，不把改动混入本任务。
- [x] **Step 3: 实现评测脚本。** 6轨迹×2后端×2主方法=24重复配置：normalized_rrf_topk与ranked_coverage共享同一候选并集/相关性/K。另6×2×2通道=24逐通道TopK消融，候选池不同，另报池覆盖；共48配置，不算48独立题。无必要ID的轨迹不计完整证据成功，5条可评价构造轨迹分别报，不做统计领先。
- [x] **Step 4: 独立审计评测输出。** 脚本内独立Fraction计算相关性和目标，不用产品私有函数做预期；所有方法记录原始ID/必要ID找全/缺口/分量/通道贡献。complementary应coverage选AC；time_chain应coverage选AB、漏C而融合TopK选BC，保留退步；greedy_nonoptimal应覆盖5/6、独立枚举最优BC为1。重算全部配置、主方法收益/退步和只读标志，保留null金标排除。
- [x] **Step 5: 记录有界耗时。** 固定8通道每条100同ID集合的排名、并集100、32要点、K5，7次真实函数调用；保存每次ns/中位数和输入/输出大小。包含归一化与选择、不含模型/数据库，不称端到端提速，不新增全量SDK性能测试。
- [x] **Step 6: 单人审查与本地提交。** 核对候选池差别、构造支持标签、负例保留与真实状态验证；提交新集成测试/评测脚本，不改fixture凑分，不推送。

### Task 3: 用法、完整回归与E盘交付

**Files:** Create docs/ranked-evidence.md；Update本计划/规格实际状态与E:/Mnemosis/WORKLOG.md；Create E:/Mnemosis/ranked-evidence-report-2026-10-06.md及新的E:/Mnemosis/backups/2026-10-06-ranked-evidence交付目录。

**Interfaces:** 使用任务1API和任务2结果；文档示例为实际执行输出，不更改调用方。

- [x] **Step 1: 写用法与限制。** 展示实际AC例子、通道贡献、固定分母、no-support显式lambda1、failed显式禁用、极小权重下溢、输入顺序平局、支持0/缺失区别。说明不是自动事实核验、没有接入recall及token预算，不把构造代理收益写成检索提升。
- [x] **Step 2: 完整回归。** 上述Rust/NumPy环境执行 `C:/Python314/python.exe -m pytest -q -p no:cacheprovider` 和 `C:/Python314/python.exe benchmarks/ci_regression.py`。预期零失败/退出0与18/18门槛；保存实际测试/子场景数、耗时和原日志。只在新问题/新改动时重跑相关验证。
- [x] **Step 3: 最终单人审查与提交。** diff --check；检查只新增独立接口，旧默认/存储无变化，数学界不等于任务成功；实际通过后更新完成复选框、规格状态和文档，本地提交。
- [x] **Step 4: 报告与恢复存档。** 报告实际源码、定向/完整测试、6轨迹/48重复配置、5可评价轨迹、收益与退步、纯函数耗时和限制。归档提交源码ZIP、冻结fixture、原始结果/日志/脚本、规格/计划、WORKLOG及恢复说明；静态copy_verified核验包，包外manifest保存实际完成情况。
- [x] **Step 5: 关闭交付。** 检查Git干净、产物与恢复说明可读，交付E盘链接；不宣称未来MemoryEngine自动融合已经完成，保留单人/无推送约束。

## 计划自审与执行交接

规格§1–2目标/范围对应全部任务；§3–6输入、数学、输出与数值契约对应Task1及Task2状态测试；§7精确例子对应Task1/Task2独立oracle；§8验收对应三项任务；§9负例和边界对应Task2/Task3；§10审查存档对应Task3。
五项Review Focus均有明确测试；后续接口名与字段均在Task1定义，没有未定义的产品函数、默认切换或子智能体任务。计划只包含测试断言和必要实现决策，不预写产品函数体。

执行方式已确定为主助手使用executing-plans单人完成。用户已批准实施；实施前恢复档与失败测试已实际执行。功能、回归、作者自审及恢复包核验已完成；源码检查点e791101a7b8d00925cf21be2c12409bc9eb2f1c5，后续仅本规格/计划状态关闭提交保存在包外manifest，产品树不变。
