# Mathematical responsibilities in Mnemosis

These models have different outputs. Do not treat a capacity, rank agreement,
coverage proxy, familiarity or archive checksum as factual confidence.

| Responsibility | Existing or new model | Output and boundary |
| --- | --- | --- |
| Candidate admission | Bounded set union: lexical64 union semantic36, lexical refill to100 | Candidate membership; existing opt-in quota |
| Dense rerank opportunity | Constrained maximum primary retention with protected semantic prefix | Which candidates receive the original cosine term; new opt-in |
| Evidence composition | Fixed-capacity relevance plus weighted saturated max support | Utility of explicitly supplied aspects; independent greedy selector and opt-in one-swap refinement |
| Confidence calibration | Beta(1,1) empirical smoothing and memory-weighted bucket discrepancy | Legacy outcome estimate; no-trial sentinel is not perfect calibration |
| Forgetting/access | Exponential retrieval-strength decay, storage strength and access reinforcement | Accessibility over time; not fact expiration |
| Backup/recovery | Dependency closure, exact content verification and actual replay from restored files | Recoverability for the tested runtime/data; not retrieval scoring |

## Semantic reserve

Let B=min(configured dense rerank limit,64), P the existing quota-mode rerank
pool, and D the eligible admitted/scorable semantic ranking (at most36).
Define D_B=D[:B], then

```text
R = D_B union earliest (B-|D_B|) IDs in P not already in D_B
```

No extra padding is invented. This solves maximum |R intersection P| subject
to D_B subset R subset (P union D_B) and |R|<=B. Ties retain earlier primary
IDs. The number of original IDs displaced is exactly

```text
max(0, |P union D_B| - B)
```

For the default64 budget, even disjoint36 semantics retain the primary first28.
Cross-channel overlaps free more primary slots. For B<36 only the semantic
prefix B is protected. Keeping the most previous candidates does not prove
better final retrieval: previously scored items that leave R keep their
existing lexical/biomimetic score; the score formula is unchanged.

Use `candidate_policy="quota", rerank_policy="semantic_reserve"`. Default
`rerank_policy="legacy"` preserves both prior default and prior quota paths.
The new option requires quota admission and its matching index/embedder.
Only the initial main pass is changed: there is one existing index lookup,
no query-time reindex, and no changes to subsequent completion/anchor paths.

The index scores decide admission priority; admitted IDs receive their
original cosine calculation and 0.20 coefficient. No float32 index score is
substituted for the original score, and no new ranking weights are added.

```python
from mnemosis import MemoryEngine
from mnemosis.embedding import NGramEmbedder
from mnemosis.vector_index import VectorIndex

embedder = NGramEmbedder(dimension=256)
engine = MemoryEngine(
    embedder=embedder, vector_index=VectorIndex(dim=256),
    index_embedder=embedder, auto_warmup=False,
)
try:
    engine.remember(
        "The spare key is in the jade cupboard.",
        cues=[], auto_cues=False, auto_context=False,
    )
    results = engine.recall(
        "Where is the spare key?", read_only=True,
        candidate_policy="quota", rerank_policy="semantic_reserve",
    )
finally:
    engine.close()
```

This dependency-free example demonstrates the API only; it does not measure
semantic quality. Applications may supply their existing semantic model.

## Other models remain separate

Evidence composition uses
F(S)=lambda*sum(relevance_i/K)+(1-lambda)*sum_a(w_a*max_i support_ia).
The maximum saturates each aspect: repeated support for the same aspect
does not multiply coverage. The existing greedy selector is not always
globally optimal; aspects and support must be explicitly supplied, and the
selector is still independent of default recall.

Calibration uses (hits+1)/(hits+fails+2), with insufficient evidence reported
as unknown by the existing interface. Current counts include legacy outcomes;
this is not a verified factual-truth posterior.

Forgetting uses strength*storage_strength*exp(-effective_rate*elapsed_hours),
with the existing affect/review rules. Recency and accessibility must not
stand in for correctness.

Backup readiness is the conjunction of verified dependencies reachable from
the replay target: code, protocol, raw cases, frozen vectors, memory DBs,
vector DBs and the tested runtime. Cycles or missing dependencies invalidate
closure. CRC/archive hashes check bytes; extracting and replaying all frozen
queries checks functional recovery. This validates the tested snapshot and
external runtime, not a probabilistic promise about all future failures.

## Frozen validation

36 new regression configurations include200 independent exhaustive small-set
comparisons. Full suite1074 tests/374 subtests and CI18/18 pass.

225 public retrieval questions compare legacy, quota, and quota plus semantic
reserve. Prior148 use the original saved IDs; new77 use source indices5/6
frozen before results. Required evidence is never a selection input.

Prior148 final Top5 all-evidence stays67 across all three modes; new77 stays23.
Newly admitted necessary evidence gains reranking opportunities: prior31
occurrences1->31; new19 occurrences2->19. Their median internal ranks improve
94->41 and91->34, but none reaches Top5. There is no demonstrated final
retrieval accuracy gain, and defaults remain unchanged. These are public
retrieval-only subsets, not blind tests or the full LoCoMo QA benchmark.


## Optional one-swap evidence refinement

`mnemosis.evidence_refinement.refine_evidence` keeps the original fixed-capacity
objective and normalization. Starting from the existing greedy set S, examine
S minus u plus v for each selected position u and originally unselected v.
Accept only the greatest strictly positive computed objective gain; ties keep
selected-position order, then candidate input order. Replace in place once.
There is no second round, insertion, deletion or new score weight.

The result holds `original_report` (including its unchanged greedy steps),
final `selected_ids`, an optional `swap` with before/after objective and gain,
final coverage/components/gaps, and `examined_swaps`. The original steps describe
the original subset, not the final one. Each score is fully recomputed with the
same `math.fsum` objective and validated, snapshotted supplied supports.
Floating-point comparisons determine strict improvements and exact computed
ties; this is not an arbitrary-precision optimization guarantee.

At most k*(n-k)<=2500 pairs are examined for n<=100 and k<=limit; capacity5
examines at most475. Each full subset evaluation costs O(k*aspects); aspects
remain bounded at32. This is a candidate-count capacity, not a token budget.
One round finds the best neighbor of the original set, but need not reach a
local optimum of the final set or the global optimum. It cannot retrieve
missing candidates or infer missing support. Explicit aspect support is a
proxy supplied by the caller; never generate it from benchmark answers.

```python
from mnemosis.evidence_selection import EvidenceCandidate, QueryAspect
from mnemosis.evidence_refinement import refine_evidence

candidates = [
    EvidenceCandidate("A", .6, {str(a): 1 for a in (1, 2, 3, 4)}),
    EvidenceCandidate("B", .6, {str(a): 1 for a in (1, 2, 5)}),
    EvidenceCandidate("C", .6, {str(a): 1 for a in (3, 4, 6)}),
]
report = refine_evidence(candidates, [QueryAspect(str(a)) for a in range(1, 7)],
                         limit=2)
assert report.original_report.selected_ids == ("A", "B")
assert report.selected_ids == ("C", "B")
assert report.swap.removed_id == "A" and report.swap.added_id == "C"
assert report.coverage_component == 1
```

In this constructed example the objective rises from43/60 to4/5 and coverage
from5/6 to6/6. This is mathematical proxy validation, not a real QA accuracy
result. `select_evidence`, ranked fusion, default recall, biomimetic scoring,
completion, calibration and forgetting retain their existing behavior.
Backup validation remains dependency/content/recovery verification.

### One-swap validation checkpoint (2026-10-07)

51 new permanent configurations cover the original trap, one-round stopping,
no-gain/ties, numeric types and weight scaling, validation at zero capacity,
100/32/2500 budgets, 250 independently enumerated rational neighborhoods and
real dict/SQLite full state preservation. Initial missing-interface RED was
51 failures; combined GREEN was125 tests/184 subtests. Complete suite1125
 tests/374 subtests and CI18/18 passed (forced E NumPy/Rust runtime paths).
All48 pre-existing source files remain byte-identical.

An additional400 frozen rational inputs independently enumerate the original
one-swap neighborhood:2 strictly better proxy objectives,0 regressions; all
match the best original neighbor, with no zero-exact-gain swaps observed.
These are constructed mathematical cases, not independent real QA samples.

Seven local pure-selector timing samples for100 candidates/32 aspects gave
median17.19ms at capacity5 (475 pairs), and337.77ms at capacity50 (2500 pairs).
These include greedy selection plus refinement and exclude model inference,
retrieval, DB and serialization. Larger capacities cost more; there is no
end-to-end speedup claim. The documentation example executed successfully.
Author self-review only, with no independent reviewer or remote push.
Detailed logs, inputs and recovery proof live under
`E:/Mnemosis/evaluation/evidence-refinement/2026-10-07/implementation-01/`.
