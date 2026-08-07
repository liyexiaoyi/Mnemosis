# Memory model: how Mnemosis maps to human memory

Every mechanism in Mnemosis traces back to a property of human memory. If a
feature cannot be mapped to a principle below, it probably does not belong in
the core.

| # | Human principle | What it means | Mnemosis mechanism | Module |
|---|---|---|---|---|
| 1 | Consolidation during sleep | Experiences are replayed and moved from short-term (hippocampus) to long-term (cortex) storage while offline | `engine.sleep()` promotes repeated/important episodic memories into semantic knowledge, prunes noise, detects contradictions | `consolidation.py` |
| 2 | Forgetting curve (Ebbinghaus) | Memories decay exponentially; spaced review keeps them alive | `ForgettingCurve.retrievability()` + `ReviewScheduler` with growing review intervals | `forgetting.py` |
| 3 | Emotional salience / value | Humans prioritize what matters to them | `ImportanceScorer` weights explicit signals, affect words, frequency and source trust | `importance.py` |
| 4 | Episodic vs semantic memory | "What happened" (narrative, time, context) differs from "what is true" (facts, stable) | Separate storage tracks, separate recall paths | `dual_track.py` |
| 5 | Associative (cue-based) recall | A smell, name, or feeling can trigger a whole memory | Multi-dimensional cue index + link graph between related memories | `association.py` |
| 6 | Source monitoring | Humans track who told them what, and whether they were there | `SourceRecord` (origin, ref, timestamp, trust) + confidence on every item | `types.py` |
| 7 | Active forgetting | Forgetting reduces noise; the brain does not store everything forever | Low-value memories fade; `RecycleBin` keeps deletions recoverable, never silent | `recycle.py` |
| 8 | Metacognition | Humans doubt themselves, ask for confirmation, notice gaps | Confidence labels, contradiction reports, knowledge-gap detection, "should confirm" signals | `metacognition.py` |
| 9 | Context-dependent memory | Godden & Baddeley (1975): recall is better when the environment matches encoding | Memories carry an optional `context`; recall boosts context matches | `types.py`, `dual_track.py` |
| 10 | Emotional modulation of consolidation | Cahill & McGaugh (1998): arousal strengthens lasting memory | Affect tags slow decay and feed importance scoring | `forgetting.py`, `importance.py` |
| 11 | Complementary learning systems | McClelland et al. (1995): hippocampus stores fast, neocortex integrates slowly | Episodic store is fast; semantic facts accumulate `evidence_count` and confidence during sleep | `consolidation.py` |
| 12 | Retrieval-induced forgetting | Anderson, Bjork & Bjork (1994): retrieval itself causes forgetting of related items | Recalling a memory slightly suppresses linked, unrecalled rivals | `dual_track.py` |
| 13 | Blocking / feeling-of-knowing | Schacter (1999): cues present but recall fails | `check()` reports `blocked` memories — cues matched, not recalled — as an alternative-route signal | `metacognition.py` |
| 14 | Encoding specificity / levels of processing | Craik & Lockhart (1972); Tulving & Thomson (1973): richer encoding means more retrieval routes | Automatic cue extraction from content at encoding time | `types.py`, `engine.py` |
| 15 | Storage vs retrieval strength | Bjork & Bjork (1992): durable storage strength vs volatile retrieval strength | `storage_strength` accrues slowly, `strength` decays fast; both drive retrievability | `forgetting.py` |
| 16 | Testing effect | Roediger & Karpicke (2006): retrieval practice beats re-exposure | Reinforcement delta scales with retrieval match quality | `dual_track.py` |
| 17 | Reconsolidation | Nader et al. (2000): retrieved memories become labile and can be revised | `update()` destabilizes, records `revision_count`/`updated_at`, re-stabilizes on access | `engine.py` |
| 18 | Sleep prioritizes salient memories | Rasch & Born (2013): sleep optimizes consolidation of what matters | Emotionally tagged episodes promote with lower access/age thresholds | `consolidation.py` |
| 19 | Working memory | Atkinson & Shiffrin (1968); Baddeley (2000); CoALA working memory | `working_set()` returns recently used memories for prompt injection | `engine.py` |
| 20 | Reflection | Park et al. (2023), Generative Agents: agents periodically abstract over their memories | `sleep(summarizer=...)` rewrites evidence-backed semantic facts as abstractions of supporting episodes | `consolidation.py` |

## Wake / sleep lifecycle

- **Wake**: `remember()` encodes an experience (episodic) or a fact
  (semantic), attaches cues and source, scores importance, links associations.
  `recall()` applies the forgetting curve, reinforces accessed memories, and
  schedules future reviews.
- **Sleep**: `engine.sleep()` runs the offline consolidation pass: promote,
  prune, dedupe, and reconcile contradictions. Nothing in sleep happens in
  real-time; it is a batch maintenance cycle.

## What Mnemosis deliberately does *not* do (yet)

- Vector embeddings in core (optional embedder hook only) — semantic recall in
  v0.1 is keyword/cue based and fully deterministic.
- Model-weight editing (see `sleeping-llm` / MEMIT for that line of work).
- Human-like emotion — we store an affect signal as one input to importance,
  not a simulation of feelings.

Full paper-by-paper mapping: [research.md](research.md).
