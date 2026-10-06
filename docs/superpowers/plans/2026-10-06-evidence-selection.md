# Evidence Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 用户要求由主助手独自实施与审查，禁止子智能体；此执行方式已经确定，不再询问。

**Goal:** 实现独立只读的固定容量归一化证据选择接口，验证互补覆盖目标和数学边界，不改变现有检索默认。

**Architecture:** 新模块只接收显式候选ID/相关性/要点支持，按固定K的边际覆盖增益贪心选择，返回逐步解释。与存储、召回、访问强化和模型调用完全解耦；离线构造对照另放benchmarks，后续召回集成不在本计划。

**Tech Stack:** Python >=3.10，标准库dataclasses、numbers、collections.abc、math；现有Dict/SQLite后端仅用于只读集成验证。沿用已有Rust/NumPy可选测试环境，无新依赖。

**Spec:** [已获用户确认的设计](E:/Mnemosis/repo/docs/superpowers/specs/2026-10-06-evidence-selection-design.md)。2026-10-06用户选择“认可设计，写实施计划”。本计划仍待用户审查。

## Global Constraints

- 开发根E:/Mnemosis/repo；评测E:/Mnemosis/evaluation/evidence-selection/2026-10-06/implementation，执行时新建，保留design目录和旧恢复档不变。
- 主助手单人实施/审查，无子智能体、远端推送、全局缓存、功能哈希、格式迁移或新依赖。
- 首版不改顶层__init__、MemoryEngine、working_set、working_set_budget、recall签名、MCP/CLI入口或任何默认策略。
- candidates最多100条、aspects最多32个；limit为0–100整数，bool不作为数值/整数参数。
- r_i/g_ci/relevance_weight有限且0–1，原始权重有限非负；非空要点至少一项原始权重>0，稳定归一化。
- 请求K固定，不除|S|或min(K,N)；支持矩阵固定，缺失支持为未提供的0，不使用答案/金标自动构造支持。
- lambda默认.5；K=0空返回且全部输入校验；空要点仅lambda=1合法。只选正增益，不填零贡献项；完全相等增益按输入顺序平局。
- 分数表示代理目标与给定支持，不是真实性或任务充分性；纯条数预算不称token预算，理论界不称答对率。
- 产品实现前做新里程碑恢复备份；每阶段只用copy_verified一次源流和一次目标读取核验静态恢复包，不重复摘要所有记录。

## Review Focus

1. 无贡献候选和候选不足：不得改变固定K的已有集合目标。任务1加实际_score_subset与select_evidence用例。
2. 正权重直接加和溢出、极端不均匀权重下溢：稳定归一化；小权重下溢影响数值，但原始正权重要点不能误报为不关心。任务1加1e308同权、1e-308/1e308及大整数权重用例。
3. limit=0或空候选不能绕过错误输入校验；字符串、bool、NaN/Inf不能静默变分数。任务1覆盖早返回边界。
4. 同支持向量不代表同事实：不同ID都保留为候选，不自动合并。任务1加lambda=1两条相同支持不同ID；任务2相似时间链反例。
5. 复用可变support/报告映射：不能修改调用方输入或污染下一次调用。任务1快照与重复调用；任务2持久状态只读验证。

## 文件职责

- 新增src/mnemosis/evidence_selection.py：值接口、输入快照校验、稳定归一化、固定K评分与选择报告。
- 新增tests/test_evidence_selection.py：实际API/数学边界/独立Fraction预期/无副作用测试。
- 新增tests/test_evidence_selection_integration.py：两后端实际记忆与SQLite诊断；不测试框架自身。
- 新增benchmarks/data/evidence_selection_cases.json：执行前冻结6条构造轨迹，显式分数及独立声明的必要ID。
- 新增benchmarks/evidence_selection_eval.py：原排序TopK、精确重复记录去重和选择器的只读对照；输出代理目标/已声明必要ID找全/退步与有界耗时。
- 新增docs/evidence-selection.md：用法、分数含义与已验证限制。
- 既有产品文件不需要编辑。实现中新发现需要改调用方/存储/版本/候选池，立即说明升级范围，不在本计划偷偷追加。

## 执行环境和基础验证命令

所有会写E盘的操作经现有授权的require_escalated执行，不另外向用户要路径权限。运行目录E:/Mnemosis/repo：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH='E:\Mnemosis\repo\src;E:\Mnemosis\repo\benchmarks;E:\Mnemosis\tools\python;E:\Mnemosis\tools\numpy'
$env:MNEMOSIS_TEST_RUST='1'
$env:MNEMOSIS_TEST_NUMPY='1'
$env:TEMP='E:\Mnemosis\evaluation\evidence-selection\2026-10-06\implementation'
$env:TMP=$env:TEMP
& 'C:\Python314\python.exe' -m pytest -q -p no:cacheprovider
```

全套命令不加文件过滤；再运行benchmarks/ci_regression.py，期望18/18含生命周期。确认现有Rust/NumPy实际可加载；退出码与日志同时保存。产品修复引起新失败，先定位并修复，不能漏报。

### Task 1: 选择器与独立数学验收

**Files:** Create E:/Mnemosis/repo/src/mnemosis/evidence_selection.py；Test E:/Mnemosis/repo/tests/test_evidence_selection.py。

**Interfaces:**

- QueryAspect(aspect_id: str, weight: float=1.0)和EvidenceCandidate(memory_id: str, relevance: float, support: Mapping[str,float])，frozen dataclass。构造器仅承载值；完整校验在select_evidence内。
- select_evidence(candidates: Sequence[EvidenceCandidate], aspects: Sequence[QueryAspect], *, limit: int=5, relevance_weight: float=.5) -> EvidenceSelectionReport。
- SelectionStep字段memory_id:str，relevance_gain/coverage_gain/total_gain/objective_after:float。
- EvidenceSelectionReport字段selected_ids:tuple[str,...]、steps:tuple[SelectionStep,...]、aspect_coverage/normalized_aspect_weights:dict[str,float]、uncovered_aspect_ids/partial_aspect_ids:tuple[str,...]、relevance_component/coverage_component/objective:float、requested_limit/candidate_count:int。
- 私有_score_subset(candidates: Sequence[EvidenceCandidate], normalized_weights: Mapping[str,float], selected_indices: Sequence[int], *, limit: int, relevance_weight: float) -> tuple[float,float,float]，返回(R_K,C,F_K)。仅用于已校验快照和最终报告；产品中实际调用，用它对独立Fraction子集预期做数学回归，不把产品辅助函数用于生成预期。

- [ ] **Step 1: 保存实施前源码与冻结构造输入。** 新建implementation目录，将当前已提交源码归档；copy_verified保存到新的backups/2026-10-06-evidence-before。生成任务2的6条JSON轨迹，所有分数/要点/必要ID先固定，不在结果出来后改lambda或金标；保存协议和源码提交。
- [ ] **Step 2: 写真实接口失败测试。** 使用测试内延迟导入：只有缺失mnemosis.evidence_selection模块转为明确assert失败，其他依赖导入错误继续抛出。不要造模拟选择器，不在产品放测试工具。核心测试独立手算：

```python
# test_fixed_capacity_prefers_complementary_support
aspects = [QueryAspect("X", .6), QueryAspect("Y", .4)]
candidates = [EvidenceCandidate("A", 1, {"X": 1}),
              EvidenceCandidate("B", .95, {"X": 1}),
              EvidenceCandidate("C", .4, {"Y": 1})]
report = select_evidence(candidates, aspects, limit=2)
assert report.selected_ids == ("A", "C")
assert abs(report.steps[1].relevance_gain - .1) < 1e-12
assert abs(report.steps[1].coverage_gain - .2) < 1e-12
assert abs(report.objective - .85) < 1e-12
```

- [ ] **Step 3: 补齐任务1失败/边界用例后运行RED。** 名称/独立断言如下，先全部保存，再运行本文件并记录是缺失API的失败而非集合错误：

```python
# test_diminishing_same_aspect_support: A(X=1), B(X=1) with lambda=0
assert select_evidence([A, B], [X], limit=2, relevance_weight=0).selected_ids == ("A",)
# test_same_support_does_not_merge_ids: lambda=1, positive relevance 1/.9
assert select_evidence([A, B], [X], limit=2, relevance_weight=1).selected_ids == ("A", "B")
# test_zero_capacity_validates_before_empty_return
with self.assertRaises(ValueError): select_evidence([bad_nan], [X], limit=0)
with self.assertRaises(TypeError): select_evidence([], [X], limit=True)
# test_fixed_budget_ignores_null_candidate
assert abs(_score_subset([A, B], weights, [0], limit=5, relevance_weight=.5)[2]
           - _score_subset([A, B, null], weights, [0], limit=5, relevance_weight=.5)[2]) < 1e-12
```

完整用例同时覆盖：limit0/1/5/100/101/-1、101候选/33要点、空候选、lambda0/1/越界/NaN/Inf/bool、零/全部零权重、空要点lambda1/其他值、缺失支持0、未知要点、重复ID、空白ID、support非映射、score非实数/bool/越界/非有限、输入平局顺序。断言错误类型，不固定错误文案。

权重测试：两项1e308同权归一化各.5；共同缩放1e-200/1e200不改变正常样本选择；两个10**400整数权重保持同权（先按最大权重缩放，不能先float转换溢出）。1e-308/1e308可能下溢为0，给定小权重支持为0时仍列未覆盖原始正权重要点，不能隐瞒数值局限。所有非法输入即使早返回仍拒绝。

只读测试：对原始support映射和输入列表保存deepcopy，多次选择前后相等；修改上次报告dict不会污染下一次报告；不同ID相同支持不得合并。所有0贡献时选空，lambda>0且r>0时可无覆盖仍选项，必须报告全部给定正权重要点未覆盖。

- [ ] **Step 4: 用独立Fraction oracle写数学测试。** 固定N<=8的3组非负矩阵；枚举所有可行子集，并对_score_subset断言三个量与独立精确预期误差<=1e-12、F(empty)=0和0–1。枚举合法相邻扩展验证实际评分单调、实际边际收益递减。对select_evidence与oracle最优值检查小样本近似下界；这不代替理论证明。保留6同权要点A=1234/B=125/C=346、K2/lambda0的实际greedy=5/6、optimal=1反例，不能把每例都断言等于最优。
- [ ] **Step 5: 实现最小模块并GREEN。** 用numbers.Real/Integral排除bool及错误类型，比较检查NaN/±Inf与范围，避免在最大值缩放前强制把大整数权重变float。完整校验、复制标量/映射，记录原始正权重mask用于缺口诊断。归一化用最大权重缩放+math.fsum。局部维护m_c，每轮扫描未选候选最大正Delta，精确相等按输入顺序；达到K或无正增益停止。_score_subset重算最终分量，报告误差越界只修<=1e-12舍入。不得新增接口外功能。
- [ ] **Step 6: 验证真实GREEN并单人审查。** 运行tests/test_evidence_selection.py与tests/test_api_surface.py；检查oracle独立、字段/顺序/系数吻合、没有模型/存储引用、没有无根据的truth字段。若失败先修真正原因，不改手算期望凑通过。
- [ ] **Step 7: 本地提交任务1。** diff --check；只暂存模块/测试/预先冻结fixture，提交“Add capacity-normalized explicit evidence selector”。保持本地分支，无推送。

### Task 2: 实际记忆只读与构造对照

**Files:** Create E:/Mnemosis/repo/tests/test_evidence_selection_integration.py；Create E:/Mnemosis/repo/benchmarks/evidence_selection_eval.py；使用任务1提前冻结的benchmarks/data/evidence_selection_cases.json。

**Interfaces:** 使用任务1的候选/要点/select_evidence/report；脚本参数--out为新的E评测输出目录，记录源码提交与fixture出处，不自动修改fixture。

- [ ] **Step 1: 写实际两后端只读集成测试。** 固定UTC时钟2026-10-06T12:00:00Z、显式MemoryItem/来源/链接；候选仅映射实际ID及固定分数，不调用模型从答案生成支持。选择前后比较所有记忆to_dict、links、_recall_log；SQLite用完整dump和已有ReadOnlyGuard检查所有列/状态。断言互补选中ID，同时验证不同调用预算不触发访问/verified计数，样本尚无充分事实版本时不增加兼容性保证。
- [ ] **Step 2: 运行测试，调查任何失败。** 本步骤是已有接口的集成验证；没有新产品行为。若发现实际代码问题，先保留失败，再做最小修复并回归任务1；若需要改召回/后端则停止并报告范围升级。
- [ ] **Step 3: 实现构造对照脚本。** 6条提前冻结轨迹分别是：A/B重复要点+C互补；相同文本与相同来源/实体/范围/时间的精确重复记录；lambda0覆盖贪心非最优；多要点部分覆盖；完全未提供支持；必要时间链与错误/过粗支持矩阵导致漏证据的负例。最后两例保留限制与退步，不修矩阵使其变正例。

每条构造轨迹的必要ID由给定事件说明预先声明，支持值由fixture显式给定；这些都是构造样本，不称公开盲测。用同一候选对照：输入原排序TopK、精确重复记录去重后TopK、选择器。去重键必须含正文/来源/实体/范围/发生时间/类型，不能只按support同形；保留第一个相同记录，其余原始候选保留在报告。不实现MMR产品策略。

输出selection/results JSON含6独立轨迹×2后端×3方法=36重复配置（不是36独立题），全部所选ID、逐步增益、代理目标、给定支持覆盖、声明必要ID是否找全、相对原排序改善/退步、预算和状态检查。没有计算回答正确率或事实概率。

- [ ] **Step 4: 运行对照并独立核验结果。** 保存原始日志/JSON；用独立Fraction预期检查第一条选A/C及.85、非最优案例greedy5/6/opt1；核验未提供支持的缺口、负例的实际必要ID损失、报告配置计数和所有后端状态标志。不得删除退步。
- [ ] **Step 5: 记录有界耗时。** 仅独立函数100候选/32要点/K5，同一固定矩阵7次调用，保存每次perf_counter_ns、median和候选/要点/预算。无模型/数据库阶段，不称端到端加速；不重复2400历史性能查询。
- [ ] **Step 6: 单人审查与本地提交。** 核对benchmark标签/独立轨迹数/对照公平、必要ID不回灌产品支持生成、只读；提交tests和benchmark，不推送。

### Task 3: 完整回归、用法与E盘恢复档

**Files:** Create E:/Mnemosis/repo/docs/evidence-selection.md；Modify 本实施计划的完成复选框（仅实际完成步骤）；E:/Mnemosis/WORKLOG.md与新一批报告；新backups里程碑目录。

**Interfaces:** 模块/API/报告沿用任务1，数据/原始结果沿用任务2。只新增文档/交付记录，不改默认调用路径。

- [ ] **Step 1: 文档展示实际示例与限制。** 用A/B/C实际API结果，区分归一化相关性、覆盖、代理目标和真实任务；说明缺失/部分支持、lambda1/空要点/零预算、固定K、正权重下溢、参数上限、纯条数、负例、没有接入recall。任何结果值取已核验输出，不提前写成功结论。
- [ ] **Step 2: 完整回归与门槛。** 在上述强制Rust/NumPy环境，先无过滤运行完整pytest，再运行benchmarks/ci_regression.py。期望全套零失败/退出0与18/18能力/生命周期；保存日志及实际测试数。已有906/190只是基线，报告不能复用为新验证。
- [ ] **Step 3: 最终单人审查并提交。** diff --check；检查新模块职责、API兼容、所有数值/只读失败名、冻结协议与损失记录；只在真实通过后提交docs和计划步骤更新。产品范围仍是独立接口。
- [ ] **Step 4: 保存实际报告与恢复包。** 报告源码/新增测试/完整测试/6构造轨迹与36重复配置/负例/耗时/无真实检索收益主张。打包提交源码ZIP、冻结fixture、原始结果/脚本/日志、设计/计划、WORKLOG和恢复说明至新的E盘目录；copy_verified一次源流/目标读取核验，包外清单记录实际结果。
- [ ] **Step 5: 最终确认。** Git工作树干净；无推送/子智能体；报告和核验恢复档链接可用。未来接入召回、生成支持或默认切换不属于本次完成声明。

## 计划自审

已逐项核对书面设计：字段/类型/数学式/K固定/空与零/数值域/预算/不可变输入/只读/旧接口/证明条件/非最优与负例/独立oracle均对应上述任务。五项Review Focus各有明确测试。所有产品评分/接口名在任务1定义，后续无隐含类型。没有TODO占位、额外模型或子智能体工作。

## 执行交接

本计划待用户审查。用户已选择由主助手单人执行；无需重新选择执行方式。用户确认计划捕捉其需求后，使用executing-plans从Task1开始；不要把设计批准当作尚未审查计划的批准。
