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

