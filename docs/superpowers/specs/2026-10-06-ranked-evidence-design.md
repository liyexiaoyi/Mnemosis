# Mnemosis：归一化排名融合与显式证据选择接口设计

日期：2026-10-06。
状态：用户已于2026-10-06回复“ok”批准本书面规格；实施计划已写待审查，尚未实现产品功能。
产品基线：31846c89d8d63ce2eeaab4293f0f4718e472ab4e。
代码、评测、报告和备份均在 E:/Mnemosis；主助手单人实施与审查；不使用子智能体、不推送远端。

## 1. 目标、背景和成功定义

用户希望优先提高检索准确性及必要证据完整性，保留仿生设计，让不同数学机制承担明确职责。此次已确认路线是“归一化排名融合 → 显式证据选择”，先建立无存储依赖的数学接口。

2026-10-06诊断对419条历史LoCoMo conv-26记忆及40道题回放：默认literal的完整证据Top5为14/40，已有可选inflection为16/40，已有BM25为12/40。inflection补回research/books两题，完整证据覆盖2收益0退步。该数据已使用，不是新盲测，也不是新增算法的效果。
诊断目录：E:/Mnemosis/evaluation/math-integration/2026-10-06/diagnosis-01。
上次默认回放40题指标全部复现，返回集合38/40一致；两题集合差异原因尚未证明，本接口不承担修改旧候选截断排序的任务。

现有hybrid.normalize_fusion可叠加辅助增益，分数上限可能为1.25；现有evidence_selection要求relevance在0–1，support来自调用方。直接传分或截断不能解决含义不同的问题。

首批成功定义：通道权重和排名得到有上限、可解释的相关性；该相关性能合法传入已有select_evidence；只在明确支持矩阵上优化覆盖；严格区分缺少支持资料与明确提供0支持；非法或失败输入不被伪装成正常检索。数学验证通过不等于真实任务效果提高。

## 2. 选择的方法与范围

采用带权RRF的固定上界归一化，再调用已实现的固定容量证据选择器。复用现有优化器，不重新实现贪心选择，不修改现有hybrid算法。

备选只启用词形策略成本较低，但不能解决分数接口与互补覆盖。更大范围的自动事实提取、多跳图和在线学习需要支持归属、事实版本及独立反馈的数据契约，后续另行设计。

首批只新增src/mnemosis/ranked_evidence.py、相关测试、固定构造评测与用户文档。直接从子模块导入，不改顶层__init__、MemoryEngine、recall、recall_fused、working_set_budget、CLI/MCP、数据库结构、依赖或默认策略。不新增哈希、模型调用、全库扫描、持久缓存或访问强化。

调用方通过既有检索入口取得排名；它负责过滤非活跃项、排除/抑制项，以及实体、情境和时间适用性。新接口没有记忆正文或数据库，不能执行这些过滤，也不承诺产生更多候选。首批没有MemoryEngine一体化入口。

## 3. 输入接口

新增以下值对象和一个公开函数，名称与字段按本规格固定：

~~~text
RankedChannel(
    channel_id: str,
    memory_ids: Sequence[str],
    weight: Real = 1.0,
    status: str = "ok",
)

select_ranked_evidence(
    channels: Sequence[RankedChannel],
    aspects: Sequence[QueryAspect],
    *,
    support: Mapping[str, Mapping[str, Real]] | None = None,
    limit: int = 5,
    relevance_weight: Real = .5,
) -> RankedEvidenceReport
~~~

QueryAspect、EvidenceCandidate、EvidenceSelectionReport和select_evidence直接复用mnemosis.evidence_selection的公开接口。不依赖该模块的私有校验或评分函数，不为此重构旧模块。

### 通道契约

- channels是标准collections.abc.Sequence，排除str/bytes/bytearray；数量1–8。每项必须是RankedChannel。
- channel_id为非空、无首尾空格字符串，各通道唯一。memory_ids同样是Sequence，每通道最多100个；ID字符串规则相同。同一通道重复ID拒绝，跨通道同ID合为同一候选。只按明确ID合并，不按正文、支持矩阵或相似度合并。
- weight是非bool的有限非负numbers.Real。至少一个原始权重大于0。正权重通道启用，0权重通道禁用。
- status仅接受"ok"或"failed"。failed必须提供空memory_ids。正权重failed通道使调用抛ValueError；不能当作正常空通道参与选择。若调用方决定降级，须显式重调用并将该通道weight=0，报告仍保留failed状态。禁用failed且空列表合法。
- 禁用通道不引入候选；它的列表、标识、权重和状态仍校验。正权重ok通道的ID并集最多100个，超过则拒绝，不能静默截断。上限按去重并集计算，而非排名条目总数。
- 所有正权重ok通道均为空是合法查询，仍保留通道归一化权重，得到空候选。空channels或全零权重不合法。

status描述调用方的输入声明；本函数不会探测真实检索是否执行、验证声明或恢复通道。

### 支持资料与容量

- support按memory_id → aspect_id → 支持值提供。外层和内层必须是Mapping；键须满足ID规则，候选键必须存在于启用通道并集中，要点键必须存在于aspects。未知键即使在纯相关性模式也拒绝。
- 支持值是非bool有限实数，范围0–1；明确的0是一项已提供资料。漏项没有提供资料，按0参与代理计算，但不能解释为已核验的不支持。
- support=None、空外层映射或所有内层均为空都没有提供任何支持值。此时必须显式relevance_weight=1，函数不自动改lambda。否则抛ValueError，避免输出看似平衡、实际缺少支持的结果。
- 显式提供至少一项支持值，包括0，则允许任意合法relevance_weight；是否足够准确由调用方负责，不要求每候选或每要点都提供支持。
- aspects沿用原选择器：最多32个、ID唯一、权重有限非负；非空时至少一个正权重；空aspects只允许relevance_weight=1。
- limit沿用原选择器：非bool整数0–100；relevance_weight为非bool有限实数0–1。limit=0、无候选或纯相关性均不绕过任何输入合法性校验。

## 4. 归一化排名相关性

固定c=60，不新增可调平滑常数。rank_j(i)为通道中一基排名，未出现则该通道贡献0。
对启用通道原权重a_j，A为所有启用通道权重之和：

~~~text
p_j = a_j / A
v_ji = p_j * (c+1)/(c+rank_j(i))    if i appears in j
v_ji = 0                           otherwise
r_i = sum_j v_ji
~~~

正常空通道仍进入A，不重新将其权重分配给有结果的通道。因此权重1的单通道首位得1，另一个权重1的正常空通道存在时得0.5。禁用通道不进入A；显式禁用改变查询配置，与正常空通道不是同一状态。

精确算术中，每项衰减因子在0–1，p非负且和为1，故r在0–1。统一乘上正系数不改变p与r。相同配置中，给排名末尾追加一个新的候选不改变已有记录的排名或相关性；插入到前方会改变排名，不承诺不变。

基础RRF使用排名而非不同检索器的任意原分。[Cormack、Clarke与Buettcher，SIGIR 2009](https://cormack.uwaterloo.ca/cormack/cormacksigir09-rrf.pdf)。
权重归一化、固定分母、状态契约与边界是本项目推导，不是论文对Mnemosis效果的证明。多通道可能高度相关；排名一致不等于独立来源印证。调用方复制成另一个通道会改变模型，首版不自动检测内容相关或重复通道。

### 数值与确定性

先把全部启用权重除以最大正权重，再以math.fsum求和归一化，不直接累加巨大权重，不设任意小分母下限。
支持Python整数、float、Fraction及符合Real契约的NumPy标量。混合巨大整数/有理数与浮点数，必要时通过精确比值处理比较或缩放转换的溢出，不能把有限权重错判成Inf。

输出使用binary64。超过可表示动态范围的极小正权重可以归一化为0，报告underflow_channel_ids；候选是否启用仍由原始weight>0决定，不能因此悄悄丢候选。精确共同缩放不变性质在浮点中允许舍入；测试在可表示范围验证，不承诺所有极端比值保持非零。

以math.fsum累计每个候选的贡献；相关性报告仅允许消除1e-12范围内的0–1边界舍入，实质越界抛ArithmeticError。选择不先显示舍入，不引入epsilon平局规则。贡献之和与报告r在1e-12内一致。

按通道输入顺序及各排名顺序，记录候选第一次出现的位置；先按r降序，完全同分按该位置，形成candidate_ids。传给select_evidence的候选顺序就是该顺序；其完全相同边际增益遵守现有输入顺序规则。不用ID字典序、UUID、随机数或集合遍历顺序决定平局。该确定性只针对相同输入，不能修复上游检索本身的排序差异。

## 5. 固定容量证据选择

为每个候选构造EvidenceCandidate(id, r_i, copied_support)，调用select_evidence，保持用户指定K和lambda，不调参数、不更改优化器：

~~~text
m_t(S) = max_(i in S) g_ti, max(empty)=0
F_K(S) = lambda * sum_(i in S) r_i/K
         + (1-lambda) * sum_t w_t*m_t(S)

Delta(i|S) = lambda*r_i/K
             + (1-lambda)*sum_t w_t*max(0,g_ti-m_t(S))
~~~

K>0时使用固定请求K；K=0无除法，选择和分量为0。重复同一要点支持取最大值而非累计，避免重复描述虚增覆盖。已有正增益停止、部分覆盖和缺口逻辑全部保留。

相关性与覆盖使用独立量纲，不把熟悉度、来源信任和时间适用性相乘后称作概率。支持资料必须来自调用方声明的标注或核验；接口不能验证其质量，输出不证明事实为真或问题回答充分。

固定非负支持与非负相关性下，现有目标仍为非负单调次模；组合排名相关性不改变这一条件。[Nemhauser、Wolsey与Fisher的条数约束分析](https://thibaut.horel.org/submodularity/papers/nemhauser1978.pdf)约束的是代理目标，不是问答正确率。
不将其保证扩展到token预算、冲突限制、必要成对时间链或自动支持模型。保留已有贪心非最优例及“高代理分但漏必要时间链”负例。

## 6. 输出接口

~~~text
ChannelSummary(
    channel_id: str,
    status: str,
    enabled: bool,
    normalized_weight: float,
    input_count: int,
)
RankContribution(channel_id: str, rank: int, contribution: float)
RankedEvidenceReport(
    channels: tuple[ChannelSummary, ...],
    candidate_ids: tuple[str, ...],
    relevance_by_id: dict[str, float],
    contributions_by_id: dict[str, tuple[RankContribution, ...]],
    support_state: str,
    supplied_support_pairs: tuple[tuple[str, str], ...],
    underflow_channel_ids: tuple[str, ...],
    selection: EvidenceSelectionReport,
)
~~~

- channels遵守原输入顺序；禁用通道normalized_weight=0，enabled依据原权重。input_count是提供的排名列表长度，不是已扫描库大小。
- contributions_by_id只列出启用通道中实际出现的排名，遵守通道输入顺序；未出现的通道贡献为0。candidate_ids为融合排序，selection.selected_ids为贪心选择顺序，两者区别明确。
- support_state为"not_supplied"或"supplied"，按是否存在至少一项显式支持值区分；显式0也为supplied。supplied_support_pairs包含所有明确提供的合法候选/要点组合，按candidate_ids和aspects输入顺序排列，保留0。未列出的组合是未提供，不能被报告成核验不支持。
- selection复用现有全部分量、步骤、未覆盖与部分覆盖字段。缺口只描述当前资料矩阵，不是全库无事实证明。没有自动拒答阈值或事实置信度字段。
- dataclass使用frozen和slots，调用入口对序列与映射做快照；输出所有嵌套字典/序列为新对象，不与输入共享可变容器。frozen不代表内部dict不可编辑；修改一份报告不能影响输入、其他调用或之后的报告。
- 不保存正文、时钟、来源、查询日志或反馈计数，不保留全局状态。

错误类型：错误输入类型用TypeError；数量、ID、状态、数值域、未知支持、启用通道失败用ValueError；实质数学范围违反用ArithmeticError。错误文本需说明对应输入，不要求逐字兼容。没有catch-and-continue失败降级。

## 7. 精确手算例子

通道L排名(A,B,C)，通道D排名(A,C,B)，同权、正常，c=60。
融合候选顺序A,B,C：

~~~text
r_A = 1
r_B = r_C = (61/62 + 61/63)/2 = 7625/7812
~~~

K=2、lambda=.5，要点X/Y权重.6/.4。A和B只支持X=1，C只支持Y=1。
纯相关性Top2因平局顺序选A,B；覆盖选择先A再C。

~~~text
F({A,B}) = 124057/156240
F({A,C}) = 31061/31248
difference = 1/5
~~~

这是构造代理目标例子，不是实际检索收益。支持分不是从检索词命中推算。
另一个通道的正常空列表会降低相关性；failed正权重必须报错。明确提供全部0支持与完全没有提供支持资料是不同输入状态。

## 8. 实施后验收要求

书面规格批准后才写实施计划和产品失败测试。本节规定验收，不是已经完成的测试。

1. 独立Fraction核算上述分数、通道贡献与最终增益；公开API测试不把产品私有评分函数作为预期。
2. 单通道、权重比例、多个排名、跨通道去重、同通道重复、同分顺序、尾部追加不改变已有分数。
3. 正常空通道固定分母、正权重failed拒绝、禁用failed显式报告；零权重不引入候选。
4. 巨大/极小/混合整数有理数浮点权重、NumPy标量、统一缩放、下溢清单、NaN/Inf/bool、错误类型；可表示范围的舍入界独立检查。
5. 1/8通道、0/100候选、32要点、limit0/100边界及超界；limit0仍完整校验。禁用通道非法输入不能绕过；支持未知ID/要点拒绝。
6. None/空映射/空内层的纯相关性要求、显式0与缺项区别、稀疏支持、lambda0/1与空aspects，候选为空时的缺口。
7. 输入/输出容器隔离、重复执行一致；改ID文本但保持顺序和关系不改变选择位置。不要求对通道重排保持同分的既定顺序。
8. 复用选择器现有数学性质和负例；新增一条组合后依然漏必要证据的构造案例，不能只挑赢的例子。
9. Dict与SQLite实际记录的显式只读排名与支持映射；比较完整记忆字段、关系、查询日志、SQLite逻辑导出，并使用已有ReadOnlyGuard。记录它是写入诊断，不宣称安全沙箱或瞬时DDL检测证明。
10. 提前冻结构造排名与支持：纯融合TopK与融合加覆盖选择使用相同候选并集和K；分别报告代理目标、必要ID完整覆盖、收益/退步。逐通道TopK只作为消融参考，使用相同语料与通道预算，但候选池不同，单独记录其池覆盖。人工支持条件下的成绩与自动真实检索分开，不能在查询时用金标填支持。
11. 现有全套测试及18项能力/生命周期门槛通过，Rust和NumPy检查按已建立测试环境运行；只新增数学模块时无需重复全部同类SDK比较。
12. 最大8通道/并集100/32要点/K5的有界函数耗时与输入/输出大小；不声称端到端加速或相同token成本。

若后续增加公开数据诊断：先确认会话是否已参与过开发、冻结排名及协议；已有数据只称回归。首版不承诺必须取得公开检索提升，不能把人工构造支持覆盖率写成市场领先或自动QA正确率。

## 9. 风险与后续边界

- RRF按排名放弃原分差距，相关通道可重复强化偏好；通道权重仍是配置，不是已学到的最优注意力。
- 缺少候选时选择器无法修补漏检；细粒度事实归属和支持生成仍未解决。
- 固定空通道权重分母会改变覆盖/相关性的实际相对贡献，调用方须保留通道状态；不能自动改lambda遮掩。
- 源事件发生时间不是事实有效时间；未来事实版本接口需区分实体、范围、更正和有效区间。
- 需要两条同时支持的逻辑依赖不是简单max覆盖；既有负例保持。
- 新接口的相同输入确定性不等于旧检索跨新建库完全稳定。另开诊断后才能修旧截断行为。
- 分数归一化不是统计校准；legacy calibration_stats仍不是核验任务事件ECE。未来反馈学习须使用真实核验结果。

## 10. 审查与存档

本规格只记录用户已认可的路线和可审查契约；本次不实现产品功能。
主助手检查占位符、矛盾、范围和歧义后本地提交；用户审查书面规格后才调用writing-plans写实施计划。计划审查后由主助手单人执行，不再次征询已明确的子智能体或存档偏好。

本次规格与精确标量核算存 E 盘；核算文件为 E:/Mnemosis/evaluation/math-integration/2026-10-06/design-01/closed-form-checks.json，只验证设计标量，不是产品接口测试。正式实施前创建新的恢复备份；既有存档不覆盖。新增产品模块、测试、评测、报告、恢复包均沿用E:/Mnemosis，C盘原件保持历史用途。
