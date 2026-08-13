# Benchmarks

## archive/

一次性渲染/打分脚本（`render_*.py`、`score_*.py` 等 377 个）归档在此，
不再参与日常 CI 与基准。保留的入口脚本与文档均不依赖它们；`render_memory_map.py`
是正式工具，仍留在 `benchmarks/` 根目录。

> 规范：所有 benchmark 必须 pin 本地 `src/`（`sys.path.insert(0, ../src)`）
> 并打印被测模块路径，禁止静默依赖 site-packages 里的旧安装包——否则会把
> 旧版本误当成当前代码来测（详见下方 high_df_recall_bench 的历史说明）。

## nightly-benchmarks（定时 CI 门禁）

`.github/workflows/nightly-benchmarks.yml` 每天 20:00 UTC 自动跑重型基准
（也可手动触发）：100k 批量构建、100k 高频词检索、20k 睡眠稳态。三个
脚本都支持 `--out` 输出 JSON 汇总，`build_bench`/`sleep_bench` 支持
`--max-build-seconds`/`--max-steady-seconds` 时长门禁；最后由
`nightly_report.py` 汇总成 Markdown 报告并上传 artifact。任何崩溃或
门禁超限都会让工作流变红报警。LongMemEval 检索回归由既有的
`nightly-bench.yml` 定时执行（`--skip-mem0 --skip-answers`，默认 10 题，
`turn_recall@5 >= 0.3` 门禁——10 题小样本下保留统计余量，无需外部
服务），两者互补。

## bench_utils.py

统一工具：`pin_local_src()`（把 `benchmarks/` 和本地 `src/` 放进
`sys.path`）、`assert_local_mnemosis()`（导入 `mnemosis` 并断言来自本地
`src/`，否则抛错拒绝运行）、`percentile(values, pct)`（线性插值分位数）。
核心基准与门禁脚本（build / scalability / sleep / ci_regression / ci_perf /
high_df_recall）以及独立评测脚本（bm25 / embedding / lifecycle / locomo /
mem0 / mem0-style / hipporag / compare_with_models / unified_compare）都已
迁移到该工具，新基准脚本应直接复用。

## high_df_recall_bench.py

High-document-frequency keyword recall at scale (run manually). Every
record in the synthetic corpus contains the term 用户, so queries like
"用户" or "用户 投影仪" exercise the worst-case keyword channel (df ~=
store size).

```bash
python benchmarks/high_df_recall_bench.py --count 100000 --chunk 5000
```

The script pins the **local** `src/` on `sys.path` and prints the module
path under test, so it can never silently measure a stale installed copy.
Fails (exit 1) if warm "用户" p99 exceeds the 100ms guard (this only
catches catastrophic regressions such as importing the stale release; it
does not promise to catch medium regressions).

> 冷启动说明：`cold_start_ms` 是进程内冷启动（重新加载数据库文件），
> 并未清理操作系统 Page Cache；跨机器对比时受文件系统缓存影响。

### Results (2026-08-13, 100k local build)

The first-query numbers below are honest cold reads: the bulk build only
writes the terms/links indexes, so the first query must pull those pages
from disk (this machine's C: drive is slow HDD-class storage). Once the
pages are in the OS cache -- or after `warmup()` (MCP servers call it at
startup; library users can pass `auto_warmup=True`) -- the same query is
~1ms.

| Metric | Value |
|---|---|
| Build (`remember_many_chunked`, 100k) | 25.2 s |
| df lookup for "用户" (100k ids, median of 5) | 74.5 ms |
| First query right after build (cold index read) | 2403 ms |
| Reopen + immediate first query (no warmup yet) | 2400 ms |
| Reopen + synchronous `warmup()` then first query | 1.15 ms |
| OS-cache-hot reopen first query (no warmup needed) | 18.4 ms |
| Warm "用户" p50 / p95 / p99 | 0.33 / 0.92 / 1.15 ms |
| Warm "用户 投影仪" p50 / p95 / p99 | 0.29 / 0.71 / 1.83 ms |
| Warm zero-hit p50 / p95 / p99 | 0.54 / 1.25 / 8.27 ms |

Gate (high_df_recall_bench): warm p99 <= 100ms; preheated first query <=
min(1000ms, max(100ms, 20% of the cold-start first query)) -- an
absolute+relative double bound with a floor, so neither a slow disk nor a
very fast NVMe causes false alarms while a half-working warmup still fails.

History: the old round-13 smoke script imported `mnemosis` from
site-packages and reported ~1.8-2.3s per high-df query on a 100k store.
That number was an artifact of measuring a stale installed release; the
same queries on the local source are sub-ms to ~30ms warm.

## longmemeval_bench.py

Official LongMemEval-S comparison vs the `mem0` package (Ollama
embeddings + Chroma). See the script docstring for the exact protocol;
this section records fresh runs.

### Results (2026-08-13, 20 questions, retrieval-only, seed 42)

| System | turn_recall@1 | @5 | @10 | answer_tokens@5 | avg ingest |
|---|---|---|---|---|---|
| mnemosis seg | 0.60 | 0.85 | 0.90 | 0.30 | 12.9 s |
| mem0 | 0.50 | 0.80 | 0.80 | 0.35 | 62.4 s |
| mnemosis dense | 0.50 | 0.80 | 0.80 | 0.35 | 10.8 s |
| mnemosis hybrid | 0.30 | 0.60 | 0.70 | 0.45 | 0.46 s |
| mnemosis ngram | 0.35 | 0.60 | 0.70 | 0.40 | 0.47 s |
| mnemosis kw | 0.30 | 0.60 | 0.65 | 0.40 | 0.47 s |

Conclusion: the sentence-segmented mode (`remember_turn` pattern) leads
every retrieval metric (@1 0.60 / @5 0.85 / @10 0.90) and beats mem0 on
@1/@5/@10 while ingesting ~4.8x faster. Dense mode matches mem0 exactly;
hybrid/lexical modes trade recall for speed. This reproduces the
pre-refactor numbers (no quality regression from the module-split rounds).

> 波动说明：seg 的 turn_recall@1 本次 0.60，历史多次记录为 0.65，属 20 题
> 小样本的正常抽样波动（本次 @5 0.85 还略高于历史的 0.80）；历史端到端
> llm_accuracy 为云端 0.55、本地 0.65-0.70。

### Cloud-judged end-to-end (2026-08-13, 20 questions, seed 42)

| System | turn_recall@1 | @5 | @10 | llm_accuracy | avg ingest |
|---|---|---|---|---|---|
| mnemosis seg | 0.60 | 0.85 | 0.90 | 0.65 | 12.3 s |
| mem0 | 0.50 | 0.80 | 0.80 | 0.45 | 62.4 s |

Answers/judging by qwen3.7-plus. The seg pipeline leads every metric,
including end-to-end answer accuracy (+20 points over mem0) while
ingesting ~5x faster.

> 评测修复：答案生成原先只给 `max_tokens=300`，而 prompt 要求先列时间线
> 再输出 `ANSWER:` 行——seg 上下文条目多，300 token 常被时间线吃光，
> 导致 20 题里 15 题缺 `ANSWER:` 行、被判 0.25（假低分）。上限提到 1200
> 后同一批题升到 0.65；mem0 上下文条目少，不受影响（0.45 不变）。

## sleep_bench.py

Sleep-consolidation benchmark with steady-state timing:

```bash
python benchmarks/sleep_bench.py --count 20000 --tail-queries 0 --steady-runs 3
```

`--steady-runs N` times additional `sleep()` calls after the first and prints
median/p99. The first sleep includes whole-store consolidation work; the
steady-state number is the honest per-cycle cost.

### Results (2026-08-13, 20k store, local build)

| Metric | Value |
|---|---|
| First sleep | 0.51 s |
| Steady-state sleep (median of 3) | 0.48 s |

Profiling note (100k input / 50k active store): steady-state sleep is
~1.0-1.1s on this machine; the dominant cost is SQLite row → `MemoryItem`
materialization (JSON source/cues + object creation), which the phases
genuinely need (`source.trust` is used by accommodation). Enum-lookup
micro-tuning measured neutral and was reverted; no further safe win found
without changing consolidation semantics.

## compare_with_models.py

Compares Mnemosis against local LLMs (via Ollama) on a small memory
benchmark: 6 synthetic memories (English + Chinese) and 6 fact-retrieval
questions. Three conditions:

1. `mnemosis_only` — does Mnemosis retrieval surface the correct memory?
2. `llm_alone` — can the LLM answer from parametric knowledge alone?
3. `llm_with_mnemosis` — LLM answers grounded in Mnemosis recall results.

```bash
python benchmarks/compare_with_models.py \
  --models gemma3:12b qwen2.5-vl:latest
```

Needs a running Ollama (`http://127.0.0.1:11434`). Any OpenAI-compatible
endpoint can be wired in the same way. Results are saved as JSON under
`benchmarks/results/`.

## Results (2026-08-07, local Ollama)

| Approach | Model | Accuracy | Avg LLM time |
|---|---|---|---|
| mnemosis_only | - | 1.000 | - |
| llm_alone | gemma3:12b | 0.000 | 3.0s |
| llm_with_mnemosis | gemma3:12b | 1.000 | 1.7s |
| llm_alone | qwen2.5-vl | 0.000 | 1.6s |
| llm_with_mnemosis | qwen2.5-vl | 1.000 | 0.5s |

The LLMs cannot recall arbitrary facts from parametric memory (0/6), while
grounding them in Mnemosis recall results lifts them to 6/6 — and Mnemosis
itself surfaces the correct memory 6/6. This is the expected pattern for
external memory systems: retrieval quality is the bottleneck, and grounding
fixes it.

## test_perf.py

Coarse regression guards: 1,000 memories must encode quickly and recall and
sleep must stay under generous bounds. Run with the rest of the suite:

```bash
python -m unittest discover -s tests
```

## locomo_bench.py

LoCoMo-style long-conversation memory evaluation: a deterministic synthetic
persona (4 people, 24 sessions, 5 dated events each) with 88 questions across
four categories — fact recall, event recall, temporal ordering, and
never-mentioned distractors.

```bash
python benchmarks/locomo_bench.py                 # retrieval only
python benchmarks/locomo_bench.py --with-llm      # + local LLM grounding
```

### Results (seed 42, deterministic)

| Mode | event hit@1 | event hit@5 | fact hit@1 | fact hit@5 | temporal anchor@5 |
|---|---|---|---|---|---|
| keyword | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| ngram embedder | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| BM25 baseline (hippo-memory-style) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 (anchor) / 0.083 (strict both) |

Distractor questions pass 16/16 (never-mentioned topics are reported as
knowledge gaps rather than confabulated).

LLM answer accuracy on a 12-question subset:

| Approach | gemma3:12b | qwen2.5-vl | qwen2.5:3b |
|---|---|---|---|
| llm_alone | 0.250 | 0.250 | 0.250 |
| llm_with_mnemosis | 0.917 (3/3 轮稳定) | 0.833 (3/3 轮稳定) | 0.750 (3/3 轮稳定) |

Across three repeated rounds per model (temperature 0), accuracy is
perfectly stable (e.g. gemma3:12b 0.917 in all rounds). Residual misses are
model-side temporal reasoning (the correct event is present in the context),
not memory retrieval failures.

### Reading the temporal number

Temporal questions ("after X, what did Y do next?") are the hardest: retrieval
surfaces the anchor event 67% of the time (ngram), but the *next* event shares
no words with the query, so strict top-5 retrieval alone cannot find it. This
is expected — the full pipeline resolves it by retrieving the anchor and
letting the LLM reason over the linked neighborhood (see the LLM rows above).

Two refinements made temporal reasoning tractable:

- Temporal questions are disambiguated with the anchor event's date (like a
  real conversation would); with ngram embeddings all retrieval metrics hit
  1.000.
- For temporal questions the LLM context is sorted chronologically with dates
  attached, which lets the model reason about order instead of guessing from
  score order.

### Distractor behavior (confabulation guard)

Mnemosis reports knowledge gaps for all 16 never-mentioned topics (16/16).
BM25 — which has no metacognition — returns the most lexically similar memory
for every one of them (0/16), e.g. answering "What is Alice's favorite music
genre?" with "Alice's favorite color is amber."

### Reproducibility

Results are deterministic for a fixed seed (tie-breaking is by
`(created_at, content)`, never by random ids or set iteration order).

Scale check (10,000 events, 4,040 questions, keyword mode, ~8 min):

| Category | hit@1 | hit@5 | MRR |
|---|---|---|---|
| event | 0.971 | 0.971 | 0.971 |
| fact | 1.000 | 1.000 | 1.000 |
| temporal | 0.972 | 0.906 | 0.973 |
| total | 0.968 | 0.935 | 0.968 |

The association graph stays sparse (per-item link budget of 64), so ingestion
scales without all-pairs explosion.

## lifecycle_eval.py

Validates the forgetting/updating promises without any LLM:

```bash
python benchmarks/lifecycle_eval.py
```

Results (30 simulated days, seed-free deterministic):

- Spaced review keeps memories strong: correct-memory average recall score
  0.343 (reviewed weekly) vs 0.260 (never reviewed) — 32% higher.
- Emotional persistence: retrievability 0.421 for affect-tagged vs 0.237 for
  neutral memories after 30 days.
- `update()` replaces stale facts cleanly (old content no longer surfaces)
  and sleep detects the planted contradiction.
- At 1,000 memories, updating one fact still fully replaces it (no stale copy
  survives) and two WAL connections see each other's writes.
- Learning curve: re-answering the same 88 questions three times keeps
  hit@1 perfectly stable at 0.818 (retrieval-induced forgetting is bounded:
  only true query competitors are suppressed, strength never drops below 0.7).

`--sleep` mode on locomo_bench verifies consolidation does not hurt
retrieval: after `engine.sleep()`, fact/event hit@1 stay 1.000 and temporal
strict@5 stays 0.625 (ngram).
