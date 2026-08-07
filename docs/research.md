# Research grounding

Mnemosis's mechanisms are mapped to published work in cognitive psychology,
neuroscience, and AI. Each mechanism below has a concrete implementation in
the codebase and a test.

| Mechanism | Source | What we borrowed | Where |
|---|---|---|---|
| Complementary learning systems | McClelland, McNaughton & O'Reilly (1995), *Psychological Review* 102(3):419–457, [link](https://psycnet.apa.org/doiLanding?doi=10.1037%2F0033-295X.102.3.419) | Fast episodic store + slow semantic integration; semantic facts accumulate evidence during sleep consolidation | `consolidation.py`, `evidence_count` |
| Forgetting curve | Ebbinghaus (1885); operationalized in MemoryBank — Zhong et al. (2023), *arXiv:2305.10250*, [link](https://arxiv.org/abs/2305.10250) | Exponential decay; access reinforces; spaced review | `forgetting.py` |
| Context-dependent memory | Godden & Baddeley (1975), *British Journal of Psychology*, [link](https://bpspsychub.onlinelibrary.wiley.com/doi/abs/10.1111/j.2044-8295.1975.tb01468.x) | Encode context with memory; boost recall when context matches | `types.py`, `dual_track.py` |
| Emotional modulation of consolidation | Cahill & McGaugh (1998), *Trends in Neurosciences*, [link](https://pubmed.ncbi.nlm.nih.gov/9683321/) | Emotionally salient memories decay slower; affect feeds importance | `forgetting.py`, `importance.py` |
| Retrieval-induced forgetting | Anderson, Bjork & Bjork (1994), *JEP: Learning, Memory, and Cognition* 20(5):1063, [link](https://psycnet.apa.org/doiLanding?doi=10.1037%2F0278-7393.20.5.1063) | Recalling a memory slightly suppresses linked rivals (configurable) | `dual_track.py` |
| Source monitoring framework | Johnson, Hashtroudi & Lindsay (1993), *Psychological Bulletin* 114(1):3–28 | Provenance + trust + confidence on every memory; inference flagged | `types.py`, `metacognition.py` |
| Seven sins of memory | Schacter (1999), *American Psychologist*, [link](https://pubmed.ncbi.nlm.nih.gov/10199218/) | Transience (decay), blocking (failed retrieval with cues), misattribution (source), persistence (importance/affect) | across modules |
| Hippocampal indexing theory / HippoRAG | Gutiérrez et al. (2024), NeurIPS, [link](https://proceedings.neurips.cc/paper_files/paper/2024/hash/6ddc001d07ca4f319af96a3024f6dbd1-Abstract.html) | Memories act as indexes/hubs; association graph for multi-hop recall | `association.py` |
| Episodic vs semantic distinction | Tulving (1972), *Organization of Memory* | Dual-track stores as a first-class property | `types.py`, `dual_track.py` |
| Levels of processing + encoding specificity | Craik & Lockhart (1972), *JVLVB*; Tulving & Thomson (1973), *Psychological Review* | Automatic cue extraction at encoding, so content gets multiple retrieval routes | `types.py`, `engine.py` |
| New theory of disuse | Bjork & Bjork (1992), *From Learning Processes to Cognitive Processes* | `storage_strength` (slow, durable) vs `strength` (retrieval, fast decay); storage retards loss of access | `forgetting.py` |
| Testing effect | Roediger & Karpicke (2006), *Psychological Science*, [link](https://pubmed.ncbi.nlm.nih.gov/16507066/) | Reinforcement scales with how well the memory matched the retrieval | `dual_track.py` |
| Reconsolidation | Nader, Schafe & LeDoux (2000), *Nature* | `update()` makes a trace labile, records the revision, and re-stabilizes on future access | `engine.py` |
| Sleep prioritizes salient memories | Rasch & Born (2013), *Physiological Reviews*, [link](https://pubmed.ncbi.nlm.nih.gov/23589831/) | Emotionally tagged episodes promote with lower access/age thresholds | `consolidation.py` |
| Multi-store / working memory | Atkinson & Shiffrin (1968), *The Psychology of Learning and Motivation*; Baddeley (2000) episodic buffer | `working_set()` exposes recently used memories for prompt injection | `engine.py` |
| Memory stream + reflection | Park et al. (2023), Generative Agents | Importance/recency/relevance scoring; `sleep(summarizer=...)` reflects over evidence-backed facts | `metacognition.py`, `consolidation.py` |
| OS-inspired memory hierarchy | Packer et al. (2023), MemGPT | Working set + long-term tiers; interrupts for control flow (roadmap) | `engine.py`, roadmap |
| Distributional similarity | Harris (1954), *Word* | Character n-gram hashing embeddings for synonym-tolerant recall | `embedding.py` |
| Long-conversation evaluation | Maharana et al. (2024), LoCoMo, ACL | Evaluation methodology for episodic memory over time (roadmap) | roadmap |

## Why these papers

We prioritized mechanisms that (a) are strongly replicated in the literature,
(b) have a deterministic, testable implementation, and (c) fix a concrete
deficiency of current AI memory systems (no decay, no source/confidence, no
consolidation, no forgetting).

## Future candidates

- Bartlett (1932) reconstructive memory — reconstruct partial memories from
  linked fragments (roadmap v0.4).
- Roediger & Karpicke (2006) testing effect — recall difficulty as a
  scheduling signal.
- Koriat (2007) metacognition — finer-grained feeling-of-knowing calibration.

## Additional AI memory papers surveyed

- MemoryBank (Zhong et al., 2023) — Ebbinghaus-inspired memory updating,
  [arXiv:2305.10250](https://arxiv.org/abs/2305.10250).
- MemGPT (Packer et al., 2023) — LLMs as operating systems,
  [arXiv:2310.08560](https://arxiv.org/abs/2310.08560).
- Generative Agents (Park et al., 2023) — memory stream + reflection,
  [arXiv:2304.03442](https://arxiv.org/abs/2304.03442).
- CoALA (Sumers et al., 2023) — cognitive architectures for language agents,
  [arXiv:2309.02427](https://arxiv.org/abs/2309.02427).
- LoCoMo (Maharana et al., 2024) — very-long-term conversational memory
  benchmark, [ACL 2024](https://aclanthology.org/2024.acl-long.747/).
- HippoRAG (Gutiérrez et al., 2024) — hippocampal indexing theory for RAG,
  [NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/6ddc001d07ca4f319af96a3024f6dbd1-Abstract.html).
- HeLa-Mem (2026, ACL) — Hebbian learning + associative dual-path memory.
- sleeping-llm (2026) — weight-editing consolidation during "sleep".
