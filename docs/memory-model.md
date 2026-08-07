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

