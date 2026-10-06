# Mathematical responsibilities in Mnemosis

These models have different outputs. Do not treat a capacity, rank agreement,
coverage proxy, familiarity or archive checksum as factual confidence.

| Responsibility | Existing or new model | Output and boundary |
| --- | --- | --- |
| Candidate admission | Bounded set union: lexical64 union semantic36, lexical refill to100 | Candidate membership; existing opt-in quota |
| Dense rerank opportunity | Constrained maximum primary retention with protected semantic prefix | Which candidates receive the original cosine term; new opt-in |
| Evidence composition | Fixed-capacity relevance plus weighted saturated max support | Utility of explicitly supplied aspects; existing independent selector |
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

