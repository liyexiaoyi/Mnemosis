# 新数学模型接入真实召回 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 用户已指定主助手单人实施和审查；不得使用子智能体。

**Goal:** 将已有必需要点约束选择器接入实际只读召回和实验性MCP，通过真实原文标注产生支持输入并测量收益与代价。

**Architecture:** 新入口冻结原仿生召回结果，以本机模型分两步生成问题要点和原文支持，再复用引用核验、单通道排名相关性及原约束选择器。原recall和旧MCP工具行为不变；标注失败、不适用、数学不可行和预算未确定分开报告。标注协议、HTTP适配器、召回编排三个模块各自测试，最后接入MCP及对照评测。

**Tech Stack:** Python >=3.10、标准库HTTP/JSON/dataclasses/typing、现有Dict/SQLite/向量后端和pytest；本机现有Ollama/qwen2.5:3b，无新增必需依赖。

**Spec:** [2026-10-07-evidence-recall-design.md](../specs/2026-10-07-evidence-recall-design.md)，本地设计提交8f09a0c5b7deadc74758cd61aea37c94dc6fd3ac。用户“介入吧”确认进入计划阶段；本文件待用户书面计划审查，尚未实施。

## Global Constraints

- 主助手单人实施与审查，不使用子智能体。代码、评测、备份均在E:/Mnemosis，无远程推送。
- 原recall及其MCP工具保持原签名、返回类型和默认行为。首版新入口只读，不强化候选、不写记忆、反馈、召回日志或工作记忆。
- 不新增依赖，不下载新模型，不修改原检索评分和候选准入预算。
- query非空，最多4096码点；top_k非bool整数1–100且不超过candidate_limit；candidate_limit非bool整数1–100，默认100；top_k默认5。
- 自动要点最多8项，每描述512码点；等权、全部必需、阈值1；数学接口原32项边界不改。
- 单条可标注正文最多2048码点；超长记录不截断，整条保留unknown并报告跳过。
- 支持1–8条原文/批、最多13批；完整messages序列化UTF-8最多12288字节；响应最多1MiB，每支持批最多64决策。
- 非流式，temperature=0，num_ctx=16384，单次num_predict=2048；1次要点＋最多13次支持；每次socket timeout最多10秒，全流程模型预算60秒，不重试。
- 数学搜索0–100000节点，默认10000；relevance_weight默认0.5、有限0–1；沿用原固定容量U和精确阈值语义。
- supported转为1，明确not_supported转为0，unknown或未返回保留缺失；精确引用不证明语义蕴含。
- 原RecallResult.score/confident保留原义；相关性仅向选择器提供r_i=61/(60+rank_i)，不覆盖原分数。
- 首版只显式启用；MCP工具加入EXPERIMENTAL_TOOLS，core/advanced列表不新增该工具；标注器默认none。
- 测试答案/gold只供结果后的评价，禁止加入要点或支持请求；全部112历史公开题保留，不适用与失败不能剔除。

## Review Focus

1. 标注期间候选被调用方/并发写入更改：返回内容和引用必须来自同一冻结快照，网络调用不持有引擎锁（Task 3）。
2. 重复JSON键、重复支持行或候选/要点ID错绑：拒绝非法批次，不让最后一行覆盖前一行冒充有效支持（Tasks 1–2）。
3. 中文、emoji、Unicode组合符与重复引用：以Python码点精确绑定；重复出现不自行挑选位置（Task 1）。
4. 大问题/要点导致动态缩批、13批预算耗尽或正文过长：保留全部候选的原排名与固定容量，未评估资料保持缺失（Tasks 2–3）。
5. 实验工具被隐藏但通过tools/call直接调用：新入口必须检查experimental与显式标注器，旧工具行为不改（Task 4）。

## 文件布局与验证环境

新建src/mnemosis/evidence_annotation.py（协议、DTO、解析、引用绑定）、ollama_evidence.py（提示/结构与有界HTTP）、evidence_recall.py（验证、快照、组合和序列化）。修改retrieval_mixin.py只增加委托方法；修改mcp_tools.py、mcp_handlers.py、mcp_server.py接入实验工具。旧evidence_selection/ranked_evidence及原recall正文保持，复用ranked_evidence_refinement._validate_grounding，不作无关提取或重构。

新建tests/test_evidence_annotation.py、test_ollama_evidence.py、test_evidence_recall.py、test_evidence_recall_integration.py、test_evidence_recall_mcp.py、test_evidence_recall_eval.py。新建benchmarks/evidence_recall_eval.py及evidence_recall_audit.py；文档docs/evidence-recall.md。完整回归发现的旧manifest计数断言如受新增实验工具影响，只修精确预期，不弱化校验。

所有Run从E:/Mnemosis/repo执行：Python=C:/Python314/python.exe，设置PYTHONUTF8=1、PYTHONDONTWRITEBYTECODE=1、PYTHONHASHSEED=0、PYTHONPATH=E:/Mnemosis/repo/src;E:/Mnemosis/repo/benchmarks;E:/Mnemosis/tools/numpy;E:/Mnemosis/tools/python、MNEMOSIS_TEST_NUMPY=1、MNEMOSIS_TEST_RUST=1。TEMP/TMP及pytest --basetemp指向本轮新建E盘目录。计划中的python指上述解释器；pytest通过python -m pytest运行。JSON/文本读写明确UTF-8。

### Task 1: 支持标注协议、解析与引用绑定

**Files:** Create src/mnemosis/evidence_annotation.py; Test tests/test_evidence_annotation.py。

**Interfaces:**
- 产生冻结dataclass：EvidenceAspect(aspect_id:str, description:str)；QuestionPlan(scope:str, aspects:tuple[EvidenceAspect,...])。
- ModelReply(payload:object|None, request:Mapping[str,object]|None, response:Mapping[str,object]|None, elapsed_seconds:float, error:str|None)，保存实际完整请求/响应及已知失败原因，不含答案/gold。
- SupportBatchReply(memory_ids:tuple[str,...], reply:ModelReply)；SkippedEvidence(memory_id:str, reason:str)；SupportReplies(batches:tuple[SupportBatchReply,...], skipped:tuple[SkippedEvidence,...])。
- EvidenceAnnotator Protocol：budget_seconds:float；plan(query:str, *, deadline:float)->ModelReply；support(query:str, aspects:Sequence[EvidenceAspect], source_texts:Mapping[str,str], *, deadline:float)->SupportReplies。deadline是同一time.monotonic时基的绝对截止值；support按输入顺序分批。提供者不访问记忆库。
- parse_question_plan(payload:object)->QuestionPlan；parse_support_batch(payload:object, *, aspects:Sequence[EvidenceAspect], source_texts:Mapping[str,str])->ParsedSupportBatch。
- ParsedSupportBatch包含support:dict[str,dict[str,int]]、spans:dict[str,dict[str,SupportSpan]]、unknown_pairs:tuple[tuple[str,str],...]。合法supported/not_supported决策数量由support实际键数计算。

- [ ] **Step 1: 写失败测试。** 要点payload严格为{"scope":"finite|open_set|unsupported","aspects":["描述",...]}，有限空列表合法且后续不适用；描述非空、去首尾空白后不超过512码点，不接受9项、非字符串、额外键。程序生成a0...，模型不得指定权重/阈值。支持payload严格为{"decisions":[{"memory_id":...,"aspect_id":...,"verdict":...,"quote":...}]}；三种verdict，只有supported可有非空quote，其余quote必须null。覆盖64/65、未知ID、重复pair、错误类型、缺行与明确0。

```python
def test_quote_uses_codepoints_and_unknown_is_absent():
    aspects = (EvidenceAspect("a0", "目的地"),)
    texts = {"m0": "🙂去大阪", "m1": "目的地未说明"}
    payload = {"decisions": [
        {"memory_id":"m0", "aspect_id":"a0", "verdict":"supported", "quote":"大阪"},
        {"memory_id":"m1", "aspect_id":"a0", "verdict":"unknown", "quote":None}]}
    result = parse_support_batch(payload, aspects=aspects, source_texts=texts)
    assert result.support == {"m0": {"a0": 1}}
    assert result.spans["m0"]["a0"] == SupportSpan(2, 4, "大阪")
    assert result.unknown_pairs == (("m1", "a0"),)
```

增加重复出现、重叠出现、正文不存在、组合符不规范化和跨候选错绑测试；一个非法决策拒绝整个批次，不部分接受。精确引用匹配但语义错误的负例明确只通过字面校验，不声称真支持。

- [ ] **Step 2:** Run `python -m pytest tests/test_evidence_annotation.py -q`；确认失败来自未实现接口，保存RED。
- [ ] **Step 3:** 实现以上协议与解析；不从unknown产生0，不修补引用；用find及从start+1的第二次find检测唯一性，再复用_validate_grounding。这里只传可标注正文/有效支持，跳过的超长全文不送该校验器，以免触发旧65536/1MiB边界。DTO内集合主动复制，禁止外部可变字典别名泄漏。
- [ ] **Step 4:** 同一命令GREEN，并运行旧test_support_grounding.py及test_required_evidence.py，原规则不变。
- [ ] **Step 5:** 自审并本地提交本任务代码与测试，记录RED/GREEN和提交。

### Task 2: 有预算的Ollama标注提供者

**Files:** Create src/mnemosis/ollama_evidence.py; Test tests/test_ollama_evidence.py。

**Interfaces:** 消费Task 1 Protocol/DTO。产生OllamaEvidenceAnnotator(*, model:str="qwen2.5:3b", base_url:str="http://127.0.0.1:11434", request_timeout:float=10.0, budget_seconds:float=60.0)，实现plan/support。暴露PLAN_SCHEMA、SUPPORT_SCHEMA及PROMPT_VERSION，方便归档与冻结响应回放。内部clock/urlopen可通过monkeypatch替换，生产使用标准库time.monotonic/urllib.request。

- [ ] **Step 1:** 写mock HTTP失败测试，断言plan请求只含问题/固定协议、format=PLAN_SCHEMA，支持请求仅含问题/固定要点/本批ID和完整原文；stream为False、temperature为0、num_ctx为16384、num_predict为2048。assert每次messages序列化ensure_ascii=False的UTF-8长度<=12288；从8条动态缩小且不截断字符串；单条超长/无法放入提示时skipped有明确reason。
- [ ] **Step 2:** 测试1MiB读取上限使用read(limit+1)，重复JSON键、NaN/Infinity、空content、非法JSON、done=False、done_reason=length、提示/输出统计异常和未知结构；失败返回ModelReply.error，不能产生有效支持。每支持批最多64决策；总支持请求<=13，没有重试；同一deadline传给plan/support，timeout<=min(10,剩余时间)，截止后不新发请求。timeout/budget_seconds必须非bool有限正数且分别<=10/60；超预算、错误URL/model在HTTP前拒绝。只允许运行者配置http/https URL，拒绝含认证信息、查询/片段；MCP调用方不能更换它。
- [ ] **Step 3:** Run `python -m pytest tests/test_ollama_evidence.py -q`并保存RED。
- [ ] **Step 4:** 实现固定system协议和单独序列化数据消息，声明记忆内指令是数据，无tools字段；schema+严格程序解析，不相信JSON模式保证语义。raw response受上限约束后归档；UTF-8严格解码。support返回所有成功/失败batch和每个未处理ID的原因；动态缩批不计为发出请求。socket超时和HTTP错误转明确失败，配置异常仍抛出。记录prompt_eval_count/eval_count及实际elapsed；只拒绝能观察到的截断，不声称完整检测静默截断。
- [ ] **Step 5:** 同一命令GREEN并运行Task 1测试；自审所有I/O有界、没有工具/存储访问后本地提交。

### Task 3: 新只读召回入口与数学组合

**Files:** Create src/mnemosis/evidence_recall.py; Modify src/mnemosis/retrieval_mixin.py（只增加recall_evidence委托）；Test tests/test_evidence_recall.py和test_evidence_recall_integration.py。

**Interfaces:** 消费Tasks 1–2及现有RecallResult、RankedChannel、select_ranked_evidence、select_required_evidence。产生EvidenceRecallReport、recall_evidence(engine:MemoryEngine, query:str, *, annotator:EvidenceAnnotator, top_k:int=5, candidate_limit:int=100, relevance_weight:float=.5, search_budget:int=10000, kind:MemoryKind|None=None, now:datetime|None=None, context:str|None=None, exclude_ids:set[str]|None=None, temporal_policy:str="content", lexical_policy:str="literal", candidate_policy:str="legacy", rerank_policy:str="legacy")->EvidenceRecallReport；RetrievalMixin同签名去掉engine并委托。

EvidenceRecallReport字段：status:str、reason:str|None、baseline:tuple[RecallResult,...]、results:tuple[RecallResult,...]、candidate_ids:tuple[str,...]、aspects:tuple[EvidenceAspect,...]、annotation_status:str（not_run/complete/partial/failed）、annotation_errors:tuple[str,...]、skipped:tuple[SkippedEvidence,...]、support:dict[str,dict[str,int]]、support_spans:dict[str,dict[str,SupportSpan]]、relevance_by_id:dict[str,float]、selector:RequiredEvidenceReport|None、model_replies:tuple[ModelReply,...]、timings:dict[str,float]（recall/plan/support/math/total）。to_dict()->dict[str,object]用于MCP/归档，精确Fraction转"numerator/denominator"，时间ISO字符串、枚举value；不由浮点复判状态。MCP序列化不默认包含model_replies中的全量请求/原始响应，显式评测归档读取该字段。

- [ ] **Step 1:** 写永久失败测试，fake engine仅允许一次recall(query, top_k=100, read_only=True, now=同一aware时间及固定控制)。参数错误、未配置标注器、错误kind/policy、非有限λ、bool数值、无效exclude_ids/context和naive now在recall/模型前拒绝；quota必须已有匹配索引/embedder，semantic_reserve必须quota。保留原默认控件，不引入新关联/学习策略。
- [ ] **Step 2:** 固定提供者测试：原排序前两条同义重复地点、第三条日期，K2时选地点＋日期；原score/confident/reasons保持原值，r分别1、61/62、61/63。测试feasible/infeasible/undetermined与完整/部分支持；没有有效0或1时annotation_failed，全部0可报告给定标注infeasible。预算0未获可行证据时不能回填baseline冒充feasible。
- [ ] **Step 3:** 测试无候选不调用模型；finite空要点、open_set/unsupported、英文独立词all/every及中文所有/全部/哪些不适用并返回baseline，英文词边界避免把small误判为all。问题开放范围守卫可在plan前执行，但在实际召回后返回baseline。非法plan报告annotation_failed且无selected；有效有限plan必须与query-only请求绑定。所有missing、失败批、超长、未处理ID保持原候选顺序和固定K。
- [ ] **Step 4:** 两后端实际MemoryEngine+固定提供者测试：快照全部MemoryItem.to_dict、all_links、recall_log、SQLite iterdump；提供者执行时另线程能获取engine._lock且不阻塞，返回后修改results.item不影响库。额外变更候选文本的测试仅用隔离库/伪引擎验证冻结返回，不混入只读不变用例。向量后端在写入守卫内调用并比较完整索引状态。
- [ ] **Step 5:** Run `python -m pytest tests/test_evidence_recall.py tests/test_evidence_recall_integration.py -q`并保存RED。
- [ ] **Step 6:** 实现严格前置验证；在现有RLock内执行原recall及deepcopy结果，然后释放锁再调用标注器。模型deadline在召回后创建并在plan/support共享；复制参数集合。单通道select_ranked_evidence(aspects=(), relevance_weight=1)取得r，不重复实现公式；把有效support交给原required selector，required IDs全为1。解析非法批次整体缺失，记录错误继续处理合法批次；未经解析的原始模型数据不进入评分。
- [ ] **Step 7:** GREEN Tasks 1–3及旧required/ranked/grounding集；核验原recall AST正文、原选择器文件字节不变。作者自审并本地提交。

### Task 4: 实验MCP入口、配置与使用文档

**Files:** Modify src/mnemosis/mcp_tools.py、mcp_handlers.py、mcp_server.py；Create docs/evidence-recall.md；Test tests/test_evidence_recall_mcp.py，必要时Modify tests/test_mcp.py精确manifest预期。

**Interfaces:** MCPServer(engine=None, expose="advanced", *, evidence_annotator:EvidenceAnnotator|None=None)保持旧位置参数；build_http_server增加同名keyword-only可选注入。run_stdio/run_http各在旧参数后增加evidence_annotator:str="none"、evidence_model:str|None=None、evidence_base_url:str|None=None。_build_evidence_annotator(kind:str,model:str|None,base_url:str|None)->EvidenceAnnotator|None仅读取运行者配置。新handler @_tool("recall_evidence")，返回Task 3 to_dict。

- [ ] **Step 1:** 写失败测试：core/advanced列表和旧recall响应不变；experimental含新工具且registry/manifest完全匹配。tools/call在非experimental或None标注器时明确失败、不请求模型，旧工具照常。新工具允许query/kind/now/context/exclude_ids/top_k/candidate_limit/λ/budget/四policy，严格拒绝其他参数、model/base_url/annotator/read_only/learning_policy，不沿用旧_bounded静默夹紧。exclude_ids JSON列表严格解析成set并拒绝重复/非字符串/空ID，now要求aware ISO，不修改旧_dt。
- [ ] **Step 2:** stdin/stdout framing与HTTP POST真实传输测试注入固定提供者，结果精确Fraction字符串可JSON往返；CLI main分别传递显式配置到两种传输。默认none不构造Ollama；新endpoint/model无caller覆写。并发HTTP请求不共享deadline、候选、支持或错误状态。
- [ ] **Step 3:** Run `python -m pytest tests/test_evidence_recall_mcp.py tests/test_mcp.py -q`并记录RED。
- [ ] **Step 4:** 添加实验schema/注册方法/配置参数；MCPServer仅为新工具记录expose标志，不改旧工具路由检查。stdio/HTTP共享构造函数；默认值兼容旧main mocks。文档给Python调用和--expose experimental --evidence-annotator ollama例子，解释全部状态、引用≠语义证明、原分数与r、只读、预算/成本、无默认切换。
- [ ] **Step 5:** GREEN全部MCP及Tasks 1–3；文档例子用固定提供者执行，真实模型调用留至Task 5。作者审查新入口可访问及禁用路径后本地提交。

### Task 5: 固定输入、真实本机推理与A/B/C归因

**Files:** Create benchmarks/evidence_recall_eval.py、evidence_recall_audit.py、tests/test_evidence_recall_eval.py；输出E:/Mnemosis/evaluation/evidence-recall/2026-10-07/implementation-01（若已存在，使用新的序号，禁止覆盖）；报告E:/Mnemosis/evidence-recall-report-2026-10-07.md。

**Interfaces:** eval main(argv:Sequence[str]|None=None)->int支持--protocol、--cases、--output、--mode constructed|public|replay；audit main(argv)->int消费协议、冻结输入、原始逐题结果，重新计算汇总与收益/退步，不调用模型或原评测聚合函数。Protocol JSON固定source commit、model digest、now、seed、候选/K/λ/budget/policies、提示schema版本、input hash、轨迹split。公开输入复用horizontal-02/frozen-cases.json及embeddings.json；原数据库只读复制，ID持久保持。

- [ ] **Step 1:** 写测试断言A调用K5；B一次K100并冻结，C消费同一冻结RecallResult列表，不另跑候选检索。通过内部编排函数select_from_snapshot(query, candidates, *, annotator, top_k, relevance_weight, search_budget)->EvidenceRecallReport复用Task 3的标注/数学路径；Task 3公开入口只做验证/召回/快照，再调用该函数。报告明确C/B条件，C total耗时=同一B召回耗时＋C各阶段耗时，不伪造第二次召回测量。audit独立复算逐题hit1/找齐/不适用/失败/候选覆盖/每对gain-loss，未知题非空不称幻觉。
- [ ] **Step 2:** Run `python -m pytest tests/test_evidence_recall_eval.py -q`，RED后实现最小评测/审计，再GREEN。先冻结30条新构造轨迹及原文，按轨迹dev20/accept10；包括实体同名/时间顺序/否定/版本/改写/粗摘要/指令数据/缺证据/开放集，每题预存期望证据。冻结后不根据验收结果改题或调λ；存档作者逐项支持判断和依据，声明作者审查非独立语义标注。
- [ ] **Step 3:** 实际本机查询model digest与元数据，必须与协议明确记录；不自动下载/改模型。对30条构造及公开112题实际运行，不适用/错误/超时全部保存，未完成必须显示已运行数量和原因，不能填成0或说全跑。保留请求/响应/候选/引用/精确状态/五阶段耗时。公开三组固定：A既有词形K5，B词形K100前5，C相同B候选、实际自动标注和约束K5；不把gold放入provider，测试捕获每条请求确认无额外答案字段。
- [ ] **Step 4:** 正常/异常完整只读state和guard核验；固定真实响应重放每题支持/引用/数学/选中ID一致。至少对10条构造验收查询再真实调用一次，报告标注和选中变化，temp0不当成确定性保证。所有推理费用计入，报告每组median/p95、支持错误、适用率、候选池完整但组合漏证据及单/多证据收益退步。
- [ ] **Step 5:** Run audit并与评测逐题/汇总精确一致；记录A能否复现历史49/112，多证据7/48；不一致先定位时钟/状态/政策，不能悄悄换基线。写诚实报告，收益为零或负仍披露，不切默认、不据此市场领先。作者审查评测脚本和结果后本地提交可复用脚本/测试；大评测文件保存在E盘仓库外。

### Task 6: 完整兼容回归、恢复与交付

**Files:** 使用上述源码/测试；输出本轮日志、source hash、self-review.json、E:/Mnemosis/WORKLOG.md；新backup里程碑目录。

**Interfaces:** 消费前五任务代码、冻结请求/响应及报告；产生可恢复源码ZIP、固定响应重放ZIP和manifest，外部运行时/旧测试DB不包含时明确声明。

- [ ] **Step 1:** 计划获批后、Task 1代码改动前先保存新repo备份和全部产品源码/跟踪文件hash，CRC与恢复字节一致；不修改既有backup目录。后续本地提交保留原分支，若execution技能要求隔离，用E盘路径并维持既有单人工作约定。
- [ ] **Step 2:** Run `python -m pytest tests -q`、`python benchmarks/ci_regression.py`；期望全部通过及18能力检查通过，无新增外部服务依赖的默认测试。1262旧测试加新增数准确统计，不承诺新总数。类型/编译检查对新增模块运行python -m compileall -q src/mnemosis，缓存路径设E盘；仅本机Python3.14验证，不称所有版本CI已过。
- [ ] **Step 3:** 复制既有verification-01/replay-recall.py到本轮并修改输出目录，不修改历史脚本或DB；实际旧库/真实nomic向量20配置704次原recall只读重放，列表及完整memory/vector SQLite/log不变。检查原recall和旧MCP recall正文AST不变，旧数学文件hash不变。新增入口异常/标注失败两后端也维持完整只读状态。
- [ ] **Step 4:** 自行逐项对照spec与Review Focus审查，修发现的实际问题并补失败测试后GREEN；禁止调用子智能体或声称独立审查。报告未解语义质量、服务耗时与开放范围限制。
- [ ] **Step 5:** 保存最终本地提交及Git状态；归档repo跟踪源/新测试/文档、协议和固定响应。CRC及每文件原件/解包字节一致；实际从恢复源码运行所有新增永久测试及固定响应组合重放，结果精确一致。恢复脚本使用恢复源码路径，防误导入开发repo。不把不含DB/模型运行时的包称全系统灾难恢复。
- [ ] **Step 6:** WORKLOG记录代码变化、实际测试数/结果、A/B/C收益退步与总耗时、模型digest、档案范围和恢复证据；向用户交付新API/MCP启用示例、报告与备份链接，声明是否已接入及仍未切默认。

## 执行次序与审查结论

用户审查本计划后，先执行Task 6 Step 1的实施前备份，再顺序Tasks 1–5，最后Task 6其余步骤。各任务RED/GREEN、审查和本地提交不可由文档自检冒充。

作者自检：设计目标/适用范围映射Tasks 1/3，资源预算映射Task 2，状态/快照/原评分映射Task 3，MCP映射Task 4，真实语义与A/B/C映射Task 5，回归/恢复映射Task 6。Review Focus五项有指定永久测试。类型与名字在本计划内一致；select_from_snapshot单独作为Task 3内部接口以支持同候选对照，不创建第二套选择逻辑。无产品实现或真实推理结果。

执行方法已确定：当前主助手单人、同会话执行，使用executing-plans；不再询问子智能体选项。等待本书面计划审查后实施。
