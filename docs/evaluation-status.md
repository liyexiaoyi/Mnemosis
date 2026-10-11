# Validation status and limitations

Status date: 2026-10-11. The implementation checkpoint before this README
update is `3b6c671b0894696a4d45aa8ddd3f4f2d394b061b`.

## What the checks establish

| Check | Recorded outcome | Interpretation |
| --- | --- | --- |
| Full local regression suite | 1,399 tests and 374 subtests passed on Python 3.14, with installed NumPy/Rust backends enabled. | Covers tested mechanisms and regressions; not a cross-version/platform certification. |
| Capability regression | 18/18 checks passed. | Specific application scenarios; not a general reasoning benchmark. |
| Original recall replay | 704 queries across 20 configurations retained rankings and memory/vector/log state. | Regression preservation on frozen cases and embeddings, not improved QA accuracy. |
| Restored evidence snapshot | 113 relevant tests passed after archive extraction and import-path verification. | Tested snapshot recovery with an external runtime; not a full-system disaster-recovery claim. |

The full suite was rerun on 2026-10-11 before pushing the improvement branch.
Optional backends are not bundled with the core installation. Native tests
require explicit setup; see [Rust](rust-bm25.md) and [NumPy](vector-acceleration.md).
Run `python -m pytest -q` and `python benchmarks/ci_regression.py` from the repo.

## Retrieval, composition and answers are separate

The opt-in quota policy improved initial necessary-evidence coverage on a
frozen public-data subset of 80 questions: 49 to 60. Final Top-5 complete
evidence stayed 33 to 33. The historical 68-question subset also retained
its final complete-evidence count, while one any-evidence result regressed.
These are retrieval subsets, not blind evaluations or full LoCoMo QA scores.
See the [admission protocol and results](candidate-admission.md).

Protecting semantic rerank opportunities did not establish a final Top-5
gain on the tested subsets. See [mathematical responsibilities](mathematical-models.md).
Explicit-support evidence selectors validate mathematical objectives; labels
supplied by authors are not evidence that a real model can infer them.

## Local-model annotation remains a bottleneck

The experimental evidence path uses local model annotations. Literal quote
binding checks that text occurs exactly once in its source; it does not
check whether it entails the requested role or completely supplies the answer.

On an authored planning check, scope classification improved from 6/24 to
23/24, but strict author review found complete usable roles in only 8/16
finite questions. This is a planning-stage result. It bypasses neither the
support-classification problem nor the need for end-to-end validation.
See the [evidence API](evidence-recall.md).

Two subsequent support-prompt candidates were rejected and reverted:

| Experiment | Paired valid support on known positive records | Decision |
| --- | --- | --- |
| Protocol clarification, 60 reused variants, two rounds | 71 to 70 out of 120 positive observations | Reject: overall support loss and six persistent variant losses despite fewer duplicate decisions. |
| Role teaching, 112 authored/reused variants, two rounds | 135 to 126 out of 216 positive observations | Reject: new-role support 58 to 53 out of 96; invalid batches 13 to 54; accepted false positives 28 to 30. |

The role-teaching experiment made 457 requests including the preliminary
9-call baseline check: 456 received response bodies and one baseline request
timed out. Its 48 new-role variants derive from just four underlying events.
Correct author-written roles bypassed planning and retrieval. Repeated
variants and rounds are not independent samples or unseen public tasks.

Prompt compression and teaching examples changed together, so their effects
cannot be attributed separately. Some literal-valid short quotes also lacked
the actor/action or answer identity; valid-record support counts therefore
do not certify complete semantic grounding. Rejected candidates did not
change current product prompts, parsing rules or default recall.

## How to interpret comparisons

Public-data scripts, authored cases, mathematical checks, retrieval replay
and generated-answer evaluations measure different things. Dataset subsets,
model versions, cache state, ingestion granularity and failure handling affect
comparison results. Historical sampled comparisons do not establish general
superiority over another memory project.

The repository contains benchmark scripts and regression fixtures. Full local
experiment archives and backups remain in the maintainer's E:/Mnemosis
workspace; they are not all published as a remote reproducibility bundle.
No new public end-to-end or competitor-SDK comparison was run for this README
update. The next evaluation should test independent actor/action/patient and
quote-sufficiency checks before changing the default evidence path.
