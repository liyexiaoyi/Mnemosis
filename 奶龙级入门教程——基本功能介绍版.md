# Mnemosis 完全入门指南（零基础版）

> 这份文档写给**完全没接触过本项目**的人。
> 读完你会明白：它是什么、为什么叫这个名字、能做什么、怎么用，
> 以及每一个功能在讲什么。全程用大白话，遇到术语都会先解释。

---

## 1. 一句话介绍

Mnemosis 是一个**给 AI 助手用的长期记忆组件**。

普通程序存数据，用数据库；AI 助手“记住”东西，一般也是把对话塞进一个库里再搜索。
Mnemosis 不一样：它把记忆当成一个**有生命的对象**来管理——会记住、会遗忘、会整理、
会自我怀疑、会在“睡觉”时把白天的事消化成长期知识。

简单说：**别的方案是“仓库”，Mnemosis 是“大脑”**。

---

## 2. 名字的由来

名字拆成两半：

- **Mnem-**：来自希腊神话里的记忆女神 **Mnemosyne（谟涅摩叙涅）**。
  她是九位缪斯女神（掌管艺术与科学的神）的母亲，在希腊文化里
  “记忆”是一切知识、艺术和思想的源头。
- **-osis**：希腊语后缀，表示“过程 / 状态 / 变化”，
  比如 metamorphosis（变形）、hypnosis（催眠）。

合起来 **Mnemosis ≈ “记忆化的过程”**，意思是：
把零散经历变成可长期使用记忆的那个过程——正好就是这个项目做的事。

---

## 3. 它是给谁用的

- 你在用 **Claude / Cursor / Codex / 自己写的 Agent**，希望它“记得住你”。
- 你发现 AI 每次对话都像失忆，想要一个能**跨对话、跨天**记住事情的层。
- 你想让 AI 不只是“搜到旧文本”，而是像人一样：记得牢的优先、
  快忘的补一补、矛盾的信息会自我怀疑、没把握时敢说“我不知道”。

安装方式：

```bash
pip install git+https://github.com/liyexiaoyi/Mnemosis.git
```

装好后有两个命令：

- `mnemosis` —— 命令行工具
- `mnemosis-mcp` —— MCP 服务器（给 AI 客户端接入用）

---

## 4. 30 秒上手体验

```python
from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

engine = MemoryEngine("memory.db")   # 传一个路径就持久化到 SQLite
user = SourceRecord(origin=SourceType.USER)

# 记住一句话
engine.remember(
    "用户喜欢用中文讨论技术问题。",
    kind=MemoryKind.SEMANTIC,          # 这是“事实”
    source=user,
    cues=["语言", "偏好"],              # 给记忆贴“线索”，方便以后想起来
    importance=0.9,                    # 重要度：0~1
)

# 换个说法也能找到
for r in engine.recall("用户用什么语言聊天？", top_k=3):
    print(r.score, r.item.content)

# 自我检查：没把握就直接告诉你
check = engine.check("用户最喜欢的电影是什么？")
print("知识缺口:", check.gaps or "无")

# 睡觉：把白天的事整理成长期知识、去重、查矛盾
print(engine.sleep().summary())
```

不用写代码也可以先跑演示：

```bash
python examples/demo.py
```

---

## 5. 扫盲词典：先懂这 12 个词

| 词 | 大白话解释 |
|---|---|
| **记忆条目（MemoryItem）** | 一条记忆，就像一张卡片：内容 + 时间 + 线索 + 重要度等 |
| **情景记忆（Episodic）** | “发生了什么”：昨天下午修了 SQLite 死锁——像**日记** |
| **语义记忆（Semantic）** | “什么是真的”：用户喜欢中文——像**常识卡** |
| **线索（Cue）** | 想起这条记忆的“钥匙”，比如“语言”“偏好” |
| **来源（Source）** | 谁告诉你的：用户、文档、Agent 自己推导……可信度不同 |
| **重要度（Importance）** | 这条记忆对你多重要，0~1，重要的事不容易忘 |
| **置信度（Confidence）** | 这条记忆“有多确定”，高置信=敢拍胸脯 |
| **强度（Strength）** | 记忆的“电量”，被回忆会充电，长时间不用会掉电 |
| **可提取性（Retrievability）** | 现在能不能想起来的概率，按遗忘曲线计算 |
| **遗忘曲线（Forgetting Curve）** | 就是背单词书里说的艾宾浩斯曲线：不复习就慢慢忘 |
| **复习（Review）** | 到时间了把记忆再提一遍，像背单词的“今日复习” |
| **睡眠整合（Sleep）** | 离线批处理：白天的事在“睡一觉”后被整理、去重、提炼成长期知识 |

---

## 6. 记忆的一生（核心生命周期）

```text
记住(remember) → 回忆(recall) → 复习(review) → 检查(check)
      ↓                                        ↓
  变旧、变弱                            没把握就提醒你
      ↓                                        ↓
  睡眠(sleep)：提升/去重/查矛盾 ←────── 更新(update)改错
      ↓
  没用的 → 遗忘(forget) → 回收站(restore 可恢复)
```

每天的使用节奏通常是：

1. **白天**：Agent 和人聊天时，把重要的事情 `remember` 下来；
   需要时 `recall` 想起来；拿不准时 `check` 一下。
2. **随时**：Agent 想起一条记忆后，这条记忆会自动“充电”（强化）；
   该复习的会被 `review_due` 列出来。
3. **晚上（或空闲时）**：跑一次 `sleep()`，系统把重复的合并、
   重要的提炼、矛盾的标记出来、没用的送进回收站。

---

## 7. 功能详解（按类别）

> 每个功能都会告诉你：**是什么 / 什么时候用 / 怎么用**。

### 7.1 记住（写入记忆）

#### remember —— 记住一条

```python
engine.remember(
    "用户说下周要去北京出差。",
    kind=MemoryKind.EPISODIC,       # 这是“事”
    source=user,
    cues=["北京", "出差"],           # 自动提取之外，再手动加两个线索
    context="工作计划",              # 情境，以后同样情境下更容易想起
    affect="neutral",               # 情绪标签（正面/负面/兴奋等）
)
```

- 会自动分词、抽线索、算重要度、和已有记忆建关联。
- 语义记忆会自动去重：内容完全一样的只保留一条，并累加证据数。
- 支持 `remember_turn`（把一整轮对话/上下文存下来）和
  `remember_many`（批量写入，几万条也很快）。

#### tag_memories —— 打标签

给记忆追加标签（线索），相当于在旧日记上补写几个关键词。

#### 导入导出

`export_memories` / `import_memories` 可以把记忆导出成文件，
换机器或备份用。

---

### 7.2 回忆（检索记忆）

#### recall —— 核心检索

```python
results = engine.recall("下周的行程安排？", top_k=5)
```

一条查询进来后，系统会做很多“人脑式”的处理：

| 机制 | 大白话 |
|---|---|
| 关键词 / 线索匹配 | 先按字面找候选 |
| 同义词扩展 | 中文“旅游/出行”、英文 cost/spent 这种近义也能命中 |
| 重要度加权 | 重要的事排前面 |
| 遗忘曲线加权 | 刚记的、经常回忆的更容易想起来 |
| 情境匹配 | 你在“工作计划”情境问，工作计划相关记忆加分 |
| 情绪一致 | 高兴时更容易想起高兴的事 |
| 置信度加权 | 确定的事优先 |
| 关联激活 | 想起 A，顺带把和 A 有关联的 B、C 也提上来 |
| 模式补全 | 只给半个线索也能激活整条相关记忆（像闻到一个味道想起整件事） |
| 模式分离 | 太像的两条记忆会被刻意区分开，防止混淆 |
| 检索诱导遗忘 | 想起 A 会轻微压一压和 A 竞争的 B（像人一样） |

回忆本身也是学习：**成功想起来 = 充电**（测试效应）；
想不起来 = 记一次失败，复习调度器会更快安排它再见一次。

#### search_batch —— 批量检索

一次传多个问题，一次返回多组结果，适合 Agent 一次要查很多事。

#### 语义检索（可选）

默认是零依赖的关键词匹配。想要“真·语义”可以接向量模型：

```bash
# 本地 Ollama
mnemosis-mcp --db memory.db --embedder ollama

# 任意 OpenAI 兼容接口（DashScope、OpenAI 等）
export MNEMOSIS_EMBEDDING_API_KEY=sk-...
mnemosis-mcp --db memory.db --embedder openai --embedding-model text-embedding-v3
```

向量只用来给候选**重排**（不改变关键词筛选），所以既快又准。

#### 兜底缓存（性能）

太泛的查询（比如只问“用户”）没有词法信号，会走“最近 + 最重要”的兜底池，
结果会缓存一段时间；命中时查询只要 1~2 毫秒。

---

### 7.3 自我怀疑（元认知）

#### check —— 检查“知不知道”

```python
check = engine.check("用户最喜欢的电影？")
check.gaps      # 知识缺口：哪些问题根本答不上来
check.blocked   # 阻塞：线索很像但想不起来（像话到嘴边说不出）
```

AI 最怕“一本正经地胡说八道”。Mnemosis 会诚实告诉你：
**这条答案靠不靠谱、有没有更强的反方证据、要不要先跟用户确认**。

相关工具：`confidence`（置信度评估）、`calibrated_confidence`
（用真实命中率校准置信度）、`list_conflicts` / `conflict_advice`
（发现矛盾并给建议）、`recognition_check`（认不认识）。

---

### 7.4 复习与遗忘（让记忆“保鲜”）

#### review_due —— 今天该复习什么

```python
due = engine.review_due(limit=10)
```

和背单词软件一样，快到遗忘点的记忆会被列出来。

#### review —— 记录一次复习结果

```python
engine.review(memory_id, success=True)   # 记得牢 → 下次间隔更长
engine.review(memory_id, success=False)  # 忘了 → 下次更快再见
```

还有 `review_batch`（批量提交结果）、`review_load`（今天复习量多少）、
`review_consistency`（复习结果前后一致吗）。

#### calibrate_decay —— 校准你的遗忘速度

每个人忘得快慢不一样。跑一次 `calibrate_decay`（MCP 工具；
Python 里是 `calibrate_decay_rate()`），
系统会根据你真实的回忆历史，把“遗忘曲线”调到更适合你。

#### forgetting_export / forgetting_risk / forgetting_balance

- 导出某条记忆的遗忘曲线；
- 看哪些记忆快忘了；
- 看整个系统的“遗忘平衡”（有没有该忘没忘、该留却快没的）。

---

### 7.5 睡觉（离线整合）

`sleep()` 是整个项目最有“人味”的功能。它一次做六件事：

| 阶段 | 干什么 | 大白话 |
|---|---|---|
| 提升（Promote） | 反复出现、重要的情景记忆变成语义事实 | 把“昨天她说了三遍喜欢中文”变成“她喜欢中文” |
| 修剪（Prune） | 没价值的旧情景记忆送回收站 | 把“3 点整发了个表情包”这种垃圾忘掉 |
| 去重（Dedupe） | 相同/几乎相同的事实合并 | 三张一样的卡片合成一张，证据数=3 |
| 查矛盾（Conflict） | 找出互斥的事实 | “预算 100 万”和“预算 200 万”同时存在 → 标记 |
| 反思（Reflect） | 用 LLM 把支持性经历总结成抽象知识 | 从 20 次“项目延期”里总结出规律 |
| REM 联想（REM phase） | 给相关记忆加强关联、调和矛盾 | 白天零碎的点，夜里连成网 |

`sleep_and_plan` 可以在睡觉之后顺便生成新的复习计划；
`sleep_replay` 会优先强化“出乎意料”的重要经历；
`sleep_inference` 会从记忆里推断隐含信息。

---

### 7.6 更新与改写（改记忆）

#### update —— 修订一条记忆

人脑有个特性叫**再巩固**：想起一条记忆时，它会被“解锁”，可以修改。

```python
engine.update(memory_id, content="用户现在更喜欢用英文讨论技术了。")
```

修改后系统会：降低一点置信度、记录“这是第几版”、
以后检索时会提醒“这条记忆被改过”——防止 AI 把旧版本当真相。

相关工具：`explain_memory`（解释为什么一条记忆排在最前）、
`reconsolidation_plan`（建议如何巩固一条被改过的记忆）。

---

### 7.7 主动遗忘与回收站

- `forget(id)`：把记忆丢进**回收站**（不是直接删除）。
- `restore(id)`：后悔了？一键恢复。
- `purge()`：彻底清空回收站（不可恢复）。
- `suppress_memories(ids)`：暂时“屏蔽”某些记忆，不让它出现在检索里
  （比如你不想让 AI 再提起某件事，但又不舍得删）。
- `unsuppress_memories(ids)`：解除屏蔽。
- `suppressed_report()`：看看现在屏蔽了哪些。

这和操作系统回收站一个道理：**删除永远可撤销，除非你主动 purge**。

---

### 7.8 关联与记忆图谱

记忆之间不是孤立的。系统会自动给“同时出现、共享线索”的记忆建关联
（带权重的关系网）。

| 工具 | 干什么 |
|---|---|
| `related(id)` | 找和某条记忆直接关联的其他记忆 |
| `similarity_report` | 找出内容相似的记忆（可能重复或冲突） |
| `association_report` | 查看整张关联网的统计 |
| `memory_map` | 把记忆按主题/时间/强度可视化（“记忆地图”） |
| `kg_export` | 把记忆图谱导出成知识图谱格式 |
| `multi_hop_report` | 多跳推理：A→B→C 这种“绕两步”的答案 |
| `analogy_bridge` / `analogy_prompt` | 类比：用旧记忆帮助理解新问题 |

---

### 7.9 规划与意图（给 Agent 的“记事本 + 计划本”）

| 工具 | 干什么 |
|---|---|
| `plan_for_goal(goal)`（Python）/ `plan`（MCP） | 为一个目标生成多步计划 |
| `replan` | 某一步失败后重新规划 |
| `predict_step` | 预测下一步最可能是什么 |
| `remember_intent` | 记住一个“待办意图”（比如：下周提醒我订酒店） |
| `intent_due` / `intent_complete` / `intent_cancel` / `intent_report` | 到期、完成、取消、汇总待办 |
| `plan_tracker` / `plan_quality` / `plan_effort` / `plan_rehearsal` | 跟踪进度、评估计划质量/难度、演练计划 |
| `goal_progress` / `goal_replay` | 目标进展、回放目标相关记忆 |
| `action_queue` | 行动队列：下一步该干什么 |
| `project_brief` / `project_risk` / `dependency_map` | 项目简报、风险评估、依赖关系 |

这些功能让 Agent 不只是“记得住”，还能**记得自己打算干什么、干到哪一步了**。

---

### 7.10 推理与过程（让记忆参与思考）

| 工具 | 干什么 |
|---|---|
| `reason` | 基于记忆回答问题，并给出推理过程 |
| `reasoning_trace` | 展示推理链条（先想到什么、再想到什么） |
| `recall_steps` / `recall_reasoning` | 回忆“做某事的步骤”或“当时的推理” |
| `numeric_reasoning` / `math_ladder` / `physics_simulate` | 数字推理、数学阶梯题、物理情境模拟 |
| `temporal_anchor` | 时序锚点：A 之后发生了什么 |
| `recall_trace` | 回溯：这条记忆是怎么被想起来的 |

记忆不是“死资料”，而是参与思考的素材：**想起过去的经验，才能推理新问题**。

---

### 7.11 练习与学习科学（教育类功能）

这一组把认知科学里的学习法搬进了记忆系统：

| 工具 | 对应的学习法 |
|---|---|
| `practice_plan` / `practice_session` / `practice_report` / `practice_answer` / `practice_due` / `practice_forecast` | 制定练习计划、执行、报告、答题、到期、预测 |
| `spacing_plan` | 间隔练习（分散复习比突击好） |
| 交叉练习（interleave） | 混合题型比单一题型好（内置机制，由评测脚本验证） |
| 测试效应（testing effect） | 做题比重读记得牢（回忆自动强化，内置机制） |
| 适度困难（desirable difficulty） | 难一点的练习效果更好（复习时自动调节间隔，内置机制） |
| `learner_profile` | 学习画像（你的强弱项） |
| `mastery_map` | 掌握度地图（哪些知识已经熟练） |
| `learning_loop` | 完整学习循环 |
| `cramming_plan` | 考前突击计划（确实需要时） |

---

### 7.12 分析与健康检查（给记忆系统“体检”）

| 工具 | 干什么 |
|---|---|
| `stats()` | 总览：多少条记忆、多少链接、多少线索 |
| `memory_status` | 单条记忆的完整状态 |
| `memory_audit` | 全库审计：有没有该合并/该删/该修的 |
| `memory_health` | 健康评分 |
| `cleanup_preview` | 预览“清理一次会删掉什么”（不真删） |
| `dedupe_memories` / `resolve_conflicts` | 直接执行去重 / 解决冲突 |
| `timeline_report` / `life_story` | 按时间线 / 人生故事线回顾 |
| `topic_drift_report` | 话题漂移：最近关注点和以前还一样吗 |
| `session_summary` | 一段对话的总结 |
| `community_report` | 记忆社区画像（谁、什么主题、何时） |
| `coverage_report` / `concept_cover` | 知识覆盖度：哪些主题记得全，哪些有空洞 |
| `interference_report` | 干扰：哪些记忆互相干扰 |
| `working_set` / `working_set_budget` | 工作记忆：最近常用的几条（适合塞进 prompt） |
| `recall_log` | 最近都查过什么、结果如何 |

---

### 7.13 情绪与情境

- 记忆可以带**情绪标签**（正面/负面/兴奋/中性）。
- 情绪会参与记忆强度：强烈情绪的事更难忘（杏仁核强化）。
- `mood_congruent`：检索时自动偏好与当前情绪一致的内容。
- 情境（context）匹配会加分：在“开会”情境下更容易想起开会相关的事。
- 相关工具：`emotion_advice`、`affect_decay`、`context_pack`；
  情绪一致检索、情绪显著强化、自我参照（和自己有关的事记得更牢）
  都是 `recall` 里的内置加权机制。

---

### 7.14 导入导出与向量修复

- `export_memories` / `import_memories`：备份 / 迁移。
- `rebuild_vectors`：如果批量向量化中途失败，可以只补缺失的向量，不重算全部。
- `source_calibration`：校准不同来源的可信度。

---

### 7.15 工程与性能（进阶用户看）

- **存储**：SQLite（WAL 模式），单文件，零外部依赖；也支持纯内存模式。
- **扩展性**：10 万条级批量写入约 6~7 分钟；高频词检索缓存命中 1~2ms。
- **并发**：线程安全，4 线程读写冒烟 0 错误。
- **质量防线**：13 项能力回归 + SQL 执行计划巡检（防止索引退化）
  + get_many 性能门禁（CI 里跑，慢了会报警）。
- **可观测性**：`stats()` 会返回兜底缓存命中率、驱逐率等指标；
  性能趋势会跨 CI 运行积累，并在 PR 上自动贴摘要评论。

---

## 8. 命令行（CLI）速查表

```bash
# 记住一条
mnemosis --db memory.db remember "用户喜欢用中文讨论技术问题。" --kind semantic

# 检索
mnemosis --db memory.db recall "用户喜欢什么语言？"

# 睡觉整合
mnemosis --db memory.db sleep

# 自我检查
mnemosis --db memory.db check "用户最喜欢的电影是什么？"

# 看统计
mnemosis --db memory.db stats

# 修改 / 删除 / 恢复
mnemosis --db memory.db update <id> --content "新内容"
mnemosis --db memory.db forget <id>
mnemosis --db memory.db restore <id>
mnemosis --db memory.db purge

# 该复习什么 / 记录复习
mnemosis --db memory.db review-due --limit 10
mnemosis --db memory.db review <id>
mnemosis --db memory.db review <id> --fail

# 最近用过的记忆
mnemosis --db memory.db working-set --limit 8

# 启动 MCP 服务器
mnemosis mcp --db memory.db
```

> 提示：不传 `--db` 时每次运行都是全新的临时记忆，传了 `--db` 才会持久化。

---

## 9. 接入 AI 客户端（MCP）

Claude Desktop、Cursor、Codex 等支持 MCP 的客户端，加一行配置即可：

```json
{
  "mcpServers": {
    "mnemosis": {
      "command": "mnemosis-mcp",
      "args": ["--db", "/path/to/memory.db"]
    }
  }
}
```

Windows 用户如果提示找不到 `mnemosis-mcp`，把 Python 的 `Scripts` 目录
加入 `PATH`，或把 `command` 改成可执行文件的绝对路径。

接入后，AI 客户端会看到一组“记忆工具”（共 131 个，默认隐藏实验性工具；
加 `--expose experimental` 可全部显示）。它就能自己决定：
什么时候该记住、什么时候该回忆、什么时候该睡觉整理。

详细配置见 [`docs/mcp-quickstart.md`](mcp-quickstart.md)。

---

## 10. 常见问题（FAQ）

**Q：它是向量数据库吗？**
不是。核心是“关键词 + 线索 + 关联图 + 遗忘曲线”，零依赖；
向量 embedding 是可选增强，只用于候选重排。

**Q：它会把所有对话都存下来吗？**
不会。它鼓励“只记重要的事”：你（或 Agent）决定 `remember` 什么；
系统还会在睡觉时修剪没价值的记忆。它不是录音机，是笔记本 + 大脑。

**Q：会不会限制 AI 的创造性？**
记忆是素材不是规则。它让 AI 有据可依、有例可循，
同时“没把握就直说”的机制反而能减少胡说八道。

**Q：Agent 自己不是有记忆吗？为什么还要这个？**
聊天窗口的记忆是“短时记忆”，会随上下文长度被挤掉；
Mnemosis 是**跨会话的长期记忆**，而且带遗忘、复习、整合、元认知
这些管理机制，不只是“把旧文本堆在一起”。

**Q：删除安全吗？**
安全。`forget` 进回收站，随时 `restore`；只有 `purge` 才彻底删除。

**Q：能远程部署吗？**
可以。它本质是本地库 + 标准 MCP 服务，可以跑在 VPS / NAS 上，
其他设备通过网络调用（见 `llm-integration.md` 与 MCP 文档）。

**Q：它和 mem0 这类项目比怎么样？**
各有侧重。Mnemosis 更强调“人脑生命周期”：遗忘曲线、睡眠整合、
复习调度、元认知、规划意图；在长对话时序回忆等独立基准上有自己的优势。
（本仓库的历史迭代报告里有大量对比数据。）

---

## 11. 下一步去哪里看

- [`README.zh-CN.md`](../README.zh-CN.md)：项目主页（中文）
- [`docs/memory-model.md`](memory-model.md)：人脑记忆原理 ↔ 项目机制对照表
- [`docs/architecture.md`](architecture.md)：模块与数据流
- [`docs/research.md`](research.md)：每一篇论文/文献依据
- [`docs/mcp-quickstart.md`](mcp-quickstart.md)：各客户端接入配置
- [`examples/demo.py`](../examples/demo.py)：一分钟演示

---

## 附：131 个 MCP 工具全名单

```text
action_queue affect_decay agent_learning_session analogy_bridge analogy_prompt
association_report attention_filter bridge_suggestions calibrate_decay check
cleanup_preview community_report compare_memories concept_cover conflict_advice
consolidation_forecast context_pack coverage_report cramming_plan cue_diversity
curve_fit decision_review dedupe_memories dependency_map difficulty_estimator
effort_estimate emotion_advice encoding_quality explain_memory export_memories
forget forgetting_balance forgetting_export forgetting_risk goal_progress
goal_replay import_memories intent_cancel intent_complete intent_conflicts
intent_due intent_remember intent_report interference_report kg_export
learner_profile learning_loop lesson_learned life_story list_conflicts
mastery_map math_ladder memory_audit memory_health memory_integration
memory_map memory_status metacog_report mnemosis multi_hop_report next_interval
nightly_routine numeric_reasoning physics_simulate plan plan_quality
plan_rehearsal plan_rewrite plan_support plan_tracker practice_answer
practice_due practice_forecast practice_plan practice_report practice_session
predict_step project_brief project_risk reason reasoning_trace rebuild_vectors
recall recall_log recall_trace recognition_check reconsolidation_plan
record_outcome remember remember_turn replan resolve_conflicts restore
retrieval_assist retrieval_quality retrieval_snapshot review review_batch
review_consistency review_due review_load rumination_check schema_fit
schema_report search search_batch session_summary similarity_report sleep
sleep_advice sleep_and_plan sleep_inference sleep_replay source_calibration
spacing_plan stats summarize_cluster suppress_memories suppressed_report
tag_memories temporal_anchor test_generator timeline_report topic_drift_report
transfer_prompt transfer_report unsuppress_memories update weekly_review
working_set working_set_budget
```
