# Experimental mathematical evidence recall

`MemoryEngine.recall_evidence` connects real read-only biomimetic recall to local model annotations, exact quotation binding and the existing required-evidence selector. The original `recall` API and default MCP tool are unchanged.

```python
from mnemosis import MemoryEngine
from mnemosis.ollama_evidence import OllamaEvidenceAnnotator

engine = MemoryEngine(auto_warmup=False)
try:
    engine.remember("Mina's trip destination was Osaka.")
    engine.remember("Mina's trip was in October.")
    report = engine.recall_evidence(
        "Where and when was Mina's trip?",
        annotator=OllamaEvidenceAnnotator(model="qwen2.5:3b"),
        top_k=2, candidate_limit=100,
    )
    print(report.status, report.annotation_status)
    print([r.item.content for r in report.results])
finally:
    engine.close()
```

The operator must already run Ollama with this model installed. This path installs nothing. Its question-only plan defines up to eight finite required roles; batched classification supplies 1 for supported with a unique exact original quotation, 0 for an explicit negative, and no value for unknown/missing. Quote matching checks literal consistency, not semantic entailment or factual truth. Model annotations can be wrong.

The selector keeps the existing fixed-capacity objective and uses single-channel rank relevance `61/(60+rank)` instead of raw biomimetic scores. Original returned `score`, `confident` and reasons retain their meaning. All automatic roles are equally weighted and required at threshold 1. `relevance_weight=.5` and `search_budget=10000` are defaults; the latter can be 0–100000 nodes.

| Status | Meaning / returned results |
| --- | --- |
| feasible | Selected evidence satisfies the supplied annotations; partial annotation remains separately visible. |
| infeasible | No selected results; impossibility proved for the given candidate/support inputs. Missing annotations are not factual absence. |
| undetermined | No selected results; budget ended without a feasible witness. |
| annotation_failed | No selected results; invalid plan or no valid positive/negative decisions. |
| not_applicable | Baseline results; empty pool, empty roles, open enumeration or unsupported query. |

`baseline` always refers to the expanded candidate query's first K, which may differ from a separate original `recall(top_k=K)`. With a feasible witness but exhausted search, `selector.optimality` is `not_proven`. `selector.completeness` is an exact `Fraction`; JSON reports serialize fractions as `numerator/denominator`. It is not a probability or answer-accuracy score.

The new path never reinforces or writes memory, links, feedback, recall logs or working memory. Results use detached snapshots and provider I/O runs outside the engine lock. Exclusions, context, kind and the existing temporal/lexical/candidate/rerank policies are supported. Query clocks must have a timezone. Quota admission needs the same existing index embedder as original recall.

Limits: query4096 codepoints, candidates100, K1–100 and K<=candidate_limit; roles8, description512; full record text above2048 remains unknown rather than truncated. Requests use at most8 texts/batch and13 support batches; serialized messages12288 UTF-8 bytes and response1MiB. Unknowns/skips and failures retain IDs. Nonstreaming generation uses temperature0, context16384 and output2048. There is one plan request plus up to13 support requests, socket timeout<=10s and a shared60s deadline. That deadline stops subsequent requests and bounds socket waiting; it cannot force termination of server generation. Byte limits are not exact token counting, and silent truncation may escape detection. Actual model calls may vary at temperature0.

Expose the MCP tool explicitly:

```text
python -m mnemosis.mcp_server --expose experimental --evidence-annotator ollama --evidence-model qwen2.5:3b --evidence-base-url http://127.0.0.1:11434
```

For HTTP add `--transport http`; configuration is identical. The tool is `recall_evidence`. Its parameters include `query`, `top_k`, `candidate_limit`, `relevance_weight`, `search_budget` and the filters/policies above. Callers cannot change the model/URL or disable read-only behavior. Without experimental exposure or a configured provider, direct calls fail. Core/advanced keep their original tool lists.

`report.to_dict()` omits full model requests/responses from the normal MCP response. Python `report.model_replies` retains bounded request/response provenance for explicit evaluation archives. Reports include exact quotes, missing-support diagnostics and recall/plan/support/math/total timings. Runtime model inference is part of end-to-end cost.

This experimental path is not the default. Validate usefulness on independent tasks before changing that. Historical A/B/C evaluation separates original TopK, larger-pool prefix, and annotation-plus-math on that same pool; any change includes the annotation effect and should not be attributed to mathematics alone.
