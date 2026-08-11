"""Dual-track memory: episodic ("what happened") vs semantic ("what is true").

Human principle #4. Events keep their narrative and time; facts are
deduplicated and kept stable. Recall paths are separate per track.
"""

from __future__ import annotations

import math
import re
import threading
from datetime import datetime

from .backend import Backend
from .embedding import Embedder
from .forgetting import ForgettingCurve
from .importance import ImportanceScorer
from .reasoning import apply_premise_pack
from .schema import EventChainIndex
from .temporal_reason import apply_time_cell_reasoning
from .types import (
    MemoryItem,
    MemoryKind,
    MemoryStatus,
    RecallResult,
    SourceRecord,
    normalize_cues,
    tokenize,
    utcnow,
)
from .zh_nlp import expand_synonyms

_FALLBACK_SCAN_LIMIT = 1000
"""Max memories loaded for a zero-hit query (recency fallback)."""

MOOD_WORDS: dict[str, tuple[str, ...]] = {
    "positive": (
        "开心", "高兴", "快乐", "兴奋", "满意", "喜欢", "愉快",
        "happy", "glad", "excited", "pleased",
    ),
    "negative": (
        "难过", "悲伤", "焦虑", "紧张", "害怕", "生气", "愤怒", "担心",
        "sad", "anxious", "angry", "afraid", "worried",
    ),
    "arousing": (
        "刺激", "惊吓", "惊喜", "惊险", "arousing", "surprising",
    ),
}


def _query_mood(query: str) -> str | None:
    """Detect a single dominant emotion in the query (Bower, 1981)."""
    lowered = query.lower()
    found: set[str] = set()
    for tag, words in MOOD_WORDS.items():
        if any(w in lowered for w in words):
            found.add(tag)
    return found.pop() if len(found) == 1 else None


class DualTrackStore:
    def __init__(
        self,
        backend: Backend,
        curve: ForgettingCurve,
        scorer: ImportanceScorer,
    ) -> None:
        self.backend = backend
        self.curve = curve
        self.scorer = scorer
        self._term_cache: dict[tuple, frozenset[str]] = {}
        self._embed_cache: dict[str, list[float]] = {}
        self._inverted: dict[str, dict[str, set[str]]] = {}
        self._lock = threading.RLock()
        self.pattern_completions = 0

    def remember(
        self,
        content: str,
        kind: MemoryKind,
        source: SourceRecord,
        *,
        cues: list[str] | None = None,
        importance: float | None = None,
        confidence: float = 1.0,
        strength: float = 1.0,
        created_at: datetime | None = None,
        context: str | None = None,
        affect: str | None = None,
        evidence_count: int = 1,
        storage_strength: float = 1.0,
    ) -> MemoryItem:
        if importance is None:
            importance = self.scorer.score(content, source=source)
        item = MemoryItem(
            content=content,
            kind=kind,
            source=source,
            cues=normalize_cues(cues or []),
            created_at=created_at or utcnow(),
            importance=importance,
            confidence=confidence,
            strength=strength,
            context=context,
            affect=affect,
            evidence_count=evidence_count,
            storage_strength=storage_strength,
        )
        if kind is MemoryKind.SEMANTIC:
            stored = self.backend.upsert(item)
        else:
            self.backend.add(item)
            stored = item
        self.backend.add_cues(stored.id, stored.cues)
        self.backend.index_terms(stored.id, self._terms(stored), stored.kind)
        self.invalidate_term_index()
        return stored

    def reindex_terms(self, item: MemoryItem) -> None:
        """Rebuild the persisted term index for a changed item."""
        self.backend.remove_terms(item.id)
        self.backend.index_terms(item.id, self._terms(item), item.kind)
        self.invalidate_term_index()

    def recall(
        self,
        query: str,
        *,
        kind: MemoryKind | None = None,
        top_k: int = 5,
        now: datetime | None = None,
        reinforce: bool = True,
        context: str | None = None,
        context_boost: bool = True,
        elaborate_links: bool = True,
        self_reference_boost: bool = True,
        source_trust_boost: bool = True,
        source_trust_weight: float = 0.06,
        mood_congruent_boost: bool = True,
        mood_boost_weight: float = 0.05,
        confidence_boost: bool = True,
        confidence_weight: float = 0.05,
        gist_preference: bool = True,
        gist_boost: float = 0.20,
        emotional_salience_boost: bool = True,
        emotional_salience_weight: float = 0.05,
        second_look: bool = False,
        conflict_flag: bool = True,
        corroboration_boost: bool = True,
        corroboration_weight: float = 0.03,
        revision_flag: bool = True,
        decay_flag: bool = True,
        suppression_factor: float = 0.01,
        suppression_min_cues: int = 2,
        suppression_floor: float = 0.7,
        embedder: Embedder | None = None,
        expansion_discount: float = 0.95,
        max_expansion_roots: int = 5,
        max_expansion_neighbors: int = 50,
        event_chain: EventChainIndex | None = None,
        temporal_boost: float = 1.0,
        temporal_reason: bool = True,
        reasoning_pack: bool = True,
        zh_synonyms: bool = True,
        pattern_completion: bool = True,
        pc_min_overlap: float = 0.25,
        pc_max_overlap: float = 0.95,
        pc_link_weight_min: float = 0.8,
        pc_min_shared_cues: int = 2,
        pc_boost_scale: float = 0.9,
        pc_max_roots: int = 4,
        pc_max_neighbors: int = 8,
        pc_max_appended: int = 16,
        separation: bool = True,
        sep_shared_cues_min: int = 2,
        sep_overlap_min: float = 0.35,
        sep_penalty: float = 0.08,
        kind_preference: bool = True,
        kind_pref: float = 0.03,
        exclude_ids: set[str] | None = None,
    ) -> list[RecallResult]:
        now = now or utcnow()
        candidates: list[MemoryItem] = []
        query_terms = set(tokenize(query))
        if zh_synonyms and any("\u4e00" <= ch <= "\u9fff" for ch in query):
            # Chinese synonym expansion: questions often use different words
            # than the stored memory ("筹备/旅游" vs "准备/旅行").

            query_terms = expand_synonyms(query_terms)
        # Temporal questions ("after X, what did Y do next?") cue the event
        # *sequence*, so episodic memories get a small preference; ordinary
        # event queries ("what did Y buy on date?") are left untouched so the
        # lexical match stays authoritative.
        lowered_query = query.lower()
        action_cued = any(
            word in lowered_query
            for word in ("after", "next", "then")
        )
        semantic_cued = any(
            word in lowered_query
            for word in (
                "what is", "what's", "favorite", "prefers", "which is",
                "who is", "when is",
            )
        )
        event_cued = any(
            word in lowered_query
            for word in ("did ", "bought", "buy ", "visited", "had ",
                         "went", "where did", "when did", "what did")
        )
        if query_terms:
            hit_counts: dict[str, int] = {}
            for term in query_terms:
                for memory_id in self.backend.find_by_terms([term], kind):
                    hit_counts[memory_id] = hit_counts.get(memory_id, 0) + 1
            ids = set(hit_counts) - set(exclude_ids or set())
            if ids:
                if len(ids) > 100:
                    # Cheap pre-ranking with hit counts (tf-free BM25-style
                    # signal, Robertson & Zaragoza, 2009): keep the top-300
                    # candidates before loading full items for scoring.
                    ids = {
                        memory_id
                        for memory_id, _ in sorted(
                            hit_counts.items(), key=lambda row: -row[1]
                        )[:100]
                    }
                ids = sorted(ids)
                candidates = self.backend.get_many(ids)
        if not candidates:
            # Zero-hit queries fall back to recency instead of scanning the
            # whole store: with 10k+ memories a full load + score costs
            # hundreds of ms, while the most recent slice is what the
            # retrievability ranking would surface anyway (Ebbinghaus
            # recency). Large stores stay fast; small stores are unaffected.
            candidates = self.backend.list(
                kind=kind, limit=_FALLBACK_SCAN_LIMIT
            )
            if exclude_ids:
                candidates = [
                    item for item in candidates if item.id not in exclude_ids
                ]
        query_vector = embedder.embed(query) if embedder is not None else None
        query_mood = _query_mood(query) if mood_congruent_boost else None
        lowered_query = query.lower()
        summary_cued = (
            "总结" in query
            or "要点" in query
            or "主旨" in query
            or "概括" in query
            or "大意" in query
            or "summary" in lowered_query
            or "main point" in lowered_query
        )
        scored: list[tuple[float, float, MemoryItem, list[str], bool]] = []
        for item in candidates:
            overlap = _overlap(query_terms, self._terms(item))
            retrievability = min(
                1.0, self.curve.retrievability(item, now)
            )
            context_overlap = 0.0
            if (
                context_boost
                and context is not None
                and item.context is not None
            ):
                ctx_terms = set(tokenize(item.context))
                cur_terms = set(tokenize(context))
                if ctx_terms and cur_terms:
                    context_overlap = _overlap(
                        cur_terms, frozenset(ctx_terms)
                    )
            context_match = context_overlap >= 1.0
            reasons: list[str] = []
            semantic = 0.0
            self_bonus = 0.0
            self_marked = (
                "我" in item.content
                or "自己" in item.content
                or any("我" in cue or "自己" in cue for cue in item.cues)
            )
            if (
                self_reference_boost
                and ("我" in query or "自己" in query)
                and self_marked
            ):
                # Self-reference effect (Rogers, Kuiper & Kirker, 1977):
                # self-relevant traces are encoded deeper and retrieved more
                # easily, so "我/自己" questions prefer self-related facts.
                self_bonus = 0.05
                reasons.append("自我参照(自传体记忆)")
            trust_bonus = (
                source_trust_weight * item.source.trust
                if source_trust_boost
                else 0.0
            )
            mood_bonus = 0.0
            if query_mood and item.affect in (query_mood, "mixed"):
                # Mood-congruent memory (Bower, 1981): a question full of
                # joy/anxiety preferentially retrieves traces stored under
                # the same emotion, as mood acts as a retrieval cue.
                mood_bonus = mood_boost_weight
            confidence_bonus = (
                confidence_weight * item.confidence
                if confidence_boost
                else 0.0
            )
            gist_bonus = 0.0
            if (
                gist_preference
                and summary_cued
                and item.kind is MemoryKind.SEMANTIC
                and (now - item.created_at).total_seconds() > 30 * 86400
            ):
                # Fuzzy-trace theory (Brainerd & Reyna, 1990): for summary
                # questions the consolidated gist is the right answer, and
                # it survives better than verbatim details over time.
                gist_bonus = gist_boost
                reasons.append("图式要点(旧)")
            salience_bonus = 0.0
            if (
                emotional_salience_boost
                and item.affect in ("positive", "negative", "arousing")
            ):
                # Emotionally enhanced memory (Kensinger, 2009): emotional
                # content is prioritized in memory; among equal matches the
                # emotional trace ranks first.
                salience_bonus = emotional_salience_weight
                reasons.append("情绪显著")
            corroboration_bonus = 0.0
            if corroboration_boost and item.evidence_count >= 3:
                # Source corroboration (Johnson et al., 1993): facts
                # confirmed multiple times are more trustworthy; among
                # otherwise-equal matches the corroborated trace ranks
                # first.
                corroboration_bonus = corroboration_weight
                reasons.append("多来源印证")
            if query_vector is not None:
                item_vector = self._embedding(item, embedder)
                semantic = embedder.cosine(query_vector, item_vector)
                score = (
                    0.30 * overlap
                    + 0.20 * retrievability
                    + 0.15 * item.importance
                    + 0.15 * context_overlap
                    + 0.20 * semantic
                    + self_bonus
                    + trust_bonus
                    + mood_bonus
                    + confidence_bonus
                    + gist_bonus
                    + salience_bonus
                    + corroboration_bonus
                )
            else:
                score = (
                    0.40 * overlap
                    + 0.25 * retrievability
                    + 0.20 * item.importance
                    + 0.15 * context_overlap
                    + self_bonus
                    + trust_bonus
                    + mood_bonus
                    + confidence_bonus
                    + gist_bonus
                    + salience_bonus
                    + corroboration_bonus
                )
            if overlap > 0:
                reasons.append(f"cue/keyword overlap {overlap:.2f}")
            if source_trust_boost and item.source.trust >= 0.95:
                # Source monitoring (Johnson, Hashtroudi & Lindsay, 1993):
                # when several traces compete, prefer the one from a more
                # trustworthy origin instead of letting recency win.
                reasons.append("来源可信(高)")
            if query_mood and item.affect in (query_mood, "mixed"):
                reasons.append(f"情绪一致({query_mood})")
            if confidence_boost and item.confidence >= 0.85:
                # Metacognitive calibration (Koriat & Goldsmith, 1996):
                # when two traces match equally, prefer the one the system
                # itself is more confident about, so agents avoid asserting
                # shaky memories.
                reasons.append("置信度高")
            if action_cued and item.kind is MemoryKind.EPISODIC:
                score += 0.05
                reasons.append("action-cued episodic preference")
            if item.evidence_count > 1:
                # Memory strength grows with confirmations (Anderson 1974):
                # a small, bounded evidence bonus lets well-confirmed facts
                # rank above weakly-supported same-pattern rivals even when
                # the rival appears earlier in the store.
                evidence_bonus = min(0.08, 0.02 * (item.evidence_count - 1))
                score += evidence_bonus
                reasons.append(
                    f"\u8bc1\u636e\u52a0\u6743(+{evidence_bonus:.2f})"
                )
            if kind_preference:
                if semantic_cued and item.kind is MemoryKind.SEMANTIC:
                    score += kind_pref
                    reasons.append("\u8981\u70b9\uff08gist\uff09\u504f\u597d")
                if (
                    event_cued
                    and item.kind is MemoryKind.EPISODIC
                    and self._precise_event_match(query, item)
                ):
                    score += kind_pref
                    reasons.append("\u7cbe\u51c6\u4e8b\u4ef6\u504f\u597d(\u4eba\u7269+\u65e5\u671f)")
            if semantic > 0.5:
                reasons.append(f"semantic similarity {semantic:.2f}")
            if retrievability < 0.5:
                reasons.append("partially forgotten")
            if item.importance >= 0.7:
                reasons.append("high importance")
            if context_match:
                reasons.append("context match")
            elif context_overlap > 0.0:
                reasons.append(f"context overlap {context_overlap:.2f}")
            matched = overlap > 0.0 or semantic >= 0.2
            scored.append((score, overlap, item, reasons, matched))
        scored.sort(key=lambda entry: entry[0], reverse=True)
        self._spread_activation(
            scored,
            query_terms,
            now,
            context,
            query_vector,
            embedder,
            expansion_discount,
            max_expansion_roots,
            max_expansion_neighbors,
        )
        if event_chain is not None:
            self._follow_event_chain(
                scored, event_chain, temporal_boost
            )
        if temporal_reason:
            apply_time_cell_reasoning(
                scored,
                candidates,
                query,
                query_terms,
            )
        if reasoning_pack:
            apply_premise_pack(
                scored,
                candidates,
                query,
                query_terms,
            )
        if pattern_completion:
            self._pattern_completion(
                scored,
                min_overlap=pc_min_overlap,
                max_overlap=pc_max_overlap,
                link_weight_min=pc_link_weight_min,
                min_shared_cues=pc_min_shared_cues,
                boost_scale=pc_boost_scale,
                max_roots=pc_max_roots,
                max_neighbors=pc_max_neighbors,
                max_appended=pc_max_appended,
            )
        if separation:
            self._separate_near_duplicates(
                scored,
                min_shared_cues=sep_shared_cues_min,
                overlap_min=sep_overlap_min,
                penalty=sep_penalty,
            )
        matched_ids = [
            item.id
            for _, _, item, _, matched in scored[:top_k]
            if matched
        ][:5]
        if elaborate_links and len(matched_ids) >= 2:
            # Elaborative encoding (Craik & Tulving, 1975): memories that
            # co-occur in one retrieval act become associated, so recalling
            # one later primes the other (Collins & Loftus, 1975 spreading
            # activation). Links are small and saturate to avoid dense graphs.
            for i in range(len(matched_ids)):
                for j in range(i + 1, len(matched_ids)):
                    w = min(
                        1.0,
                        self.backend.link_weight(matched_ids[i], matched_ids[j])
                        + 0.05,
                    )
                    self.backend.add_link(matched_ids[i], matched_ids[j], w)
                    self.backend.add_link(matched_ids[j], matched_ids[i], w)
        results = [
            RecallResult(item=item, score=score, reasons=reasons)
            for score, _, item, reasons, _ in scored[:top_k]
        ]
        if second_look and results:
            # Second look (metacognitive monitoring, Koriat & Goldsmith
            # 1996; recollection, Yonelinas 2002): when the first answer is
            # shaky, re-rank the candidates by evidence strength and source
            # reliability before answering - "think again, what am I most
            # sure of?".
            top_score = results[0].score
            second_score = results[1].score if len(results) > 1 else -1.0
            shaky = not (
                top_score >= 0.45 and top_score - second_score >= 0.03
            )
            if shaky:
                def _recollect(entry) -> float:
                    _, _, item, _, _ = entry
                    evidence_boost = 0.08 * min(
                        2, item.evidence_count - 1
                    )
                    trust_boost = max(
                        0.0, 0.03 * (item.source.trust - 0.8)
                    )
                    return entry[0] + evidence_boost + trust_boost

                reordered = sorted(
                    scored[:top_k], key=_recollect, reverse=True
                )
                if reordered[0][2].id != results[0].item.id:
                    new_top = reordered[0]
                    new_top[3].append("复核(证据/来源重排)")
                    scored[:top_k] = reordered
                    results = [
                        RecallResult(
                            item=item, score=score, reasons=reasons
                        )
                        for score, _, item, reasons, _ in scored[:top_k]
                    ]
        if results:
            # Metacognitive flag (Koriat & Goldsmith, 1996): tell the agent
            # when the top answer is shaky - low absolute score or a tiny
            # gap to the runner-up means it should hedge ("我不太确定").
            top_score = results[0].score
            second_score = results[1].score if len(results) > 1 else -1.0
            results[0].confident = bool(
                top_score >= 0.45 and top_score - second_score >= 0.03
            )
            if not results[0].confident:
                results[0].reasons.append("低置信(与次选差距小)")
        if conflict_flag and results:
            # Conflict awareness (reconsolidation, Nader et al., 2000):
            # when a clearly stronger-evidenced rival exists for the top
            # answer's primary cue, tell the agent to hedge instead of
            # asserting a stale fact.
            top_item = results[0].item
            primary = top_item.cues[0] if top_item.cues else None
            if primary:
                for rival in self.backend.find_by_cue(primary):
                    if (
                        rival.id == top_item.id
                        or rival.status is not MemoryStatus.ACTIVE
                    ):
                        continue
                    if (
                        rival.evidence_count
                        >= 3 * max(1, top_item.evidence_count)
                        and rival.source.trust >= top_item.source.trust
                    ):
                        results[0].confident = False
                        if not any(
                            "更强证据冲突" in reason
                            for reason in results[0].reasons
                        ):
                            results[0].reasons.append("存在更强证据冲突")
                        break
        if revision_flag:
            for result in results:
                if result.item.revision_count > 0 and not any(
                    "已修订" in reason for reason in result.reasons
                ):
                    # Reconsolidation transparency (Nader et al., 2000):
                    # a revised trace should tell the agent it changed, so
                    # the newest version is not mistaken for the original.
                    result.reasons.append(
                        f"已修订(版本{result.item.revision_count})"
                    )
        if decay_flag:
            for result in results:
                if (
                    self.curve.retrievability(result.item, now) < 0.3
                    and not any(
                        "快遗忘" in reason for reason in result.reasons
                    )
                ):
                    # Decay warning (Ebbinghaus forgetting curve): the
                    # trace is close to the forgetting threshold; the agent
                    # should review it soon or answer with caution.
                    result.reasons.append("低可提取(快遗忘)")
        if reinforce:
            for score, overlap, item, _, matched in scored[:top_k]:
                if not matched:
                    continue  # failed retrieval does not strengthen (testing effect)
                # Testing effect (Roediger & Karpicke, 2006): reinforcement
                # scales with how well the memory matched the retrieval.
                # Desirable difficulty (Bjork & Kroll, 2015): a successful
                # retrieval that required more effort (low retrievability)
                # yields a larger gain than an effortless one.
                retrievability = min(
                    1.0, self.curve.retrievability(item, now)
                )
                effort = 1.0 - retrievability
                delta = 0.05 + 0.15 * overlap
                self.curve.reinforce_review(
                    item,
                    delta=delta,
                    now=now,
                    effort=effort,
                )
                item.retrieval_successes += 1
                self.backend.update(item)
            self._record_misses(scored, top_k, now)
            if suppression_factor > 0:
                matched_items = [
                    item
                    for _, _, item, _, matched in scored[:top_k]
                    if matched
                ]
                self._suppress_linked_rivals(
                    matched_items,
                    suppression_factor,
                    suppression_min_cues,
                    suppression_floor,
                    query_terms,
                )
        return results

    @staticmethod
    def _precise_event_match(query: str, item: MemoryItem) -> bool:
        """Precise event preference: query must carry a date AND the item must
        be the one for that date sharing at least one other cue with the
        query (e.g. the person's name). Uniform episodic boosting regressed
        at scale (round-8 negative result), so only fully anchored events
        get the bump."""
        date_tokens = set(re.findall(r"\d{4}-\d{2}-\d{2}", query))
        if not date_tokens:
            return False
        cue_set = set(item.cues)
        if not any(dt in cue_set or dt in item.content for dt in date_tokens):
            return False
        query_terms = set(tokenize(query))
        non_date_cues = {
            c for c in cue_set if not re.match(r"\d{4}-\d{2}-\d{2}$", c)
        }
        return bool(query_terms & non_date_cues)

    def _separate_near_duplicates(
        self,
        scored: list[tuple[float, float, MemoryItem, list[str], bool]],
        *,
        min_shared_cues: int,
        overlap_min: float,
        penalty: float,
    ) -> None:
        """Hippocampal pattern separation (Bakker et al., 2008, Science).

        The dentate gyrus / CA3 decorrelates similar-but-distinct memories so
        overlapping experiences do not overwrite or crowd each other. We
        emulate this with a small, bounded penalty: candidates that share at
        least `min_shared_cues` cues AND high lexical overlap with the top
        match, but are a different memory, lose a little score. Only the
        top-10 window is considered, so large stores stay cheap.

        Evidence-weighted protection (learning science: strength/evidence
        accumulation; Anderson 1974; complementary learning systems,
        McClelland et al. 1995): among a near-duplicate group, the memory
        with the most confirmations (`evidence_count`) is *protected* from
        the separation penalty and gets a small boost, so a well-confirmed
        fact can win over weak same-pattern rivals. When all memories have
        evidence_count == 1 (the default), behavior is unchanged.
        """
        if len(scored) < 2:
            return
        _, _, top_item, _, _ = scored[0]
        top_cues = set(top_item.cues)
        top_terms = self._terms(top_item)
        # Pass 1: find the near-duplicate group (relative to the top match)
        # and the group's strongest evidence. Protection must be scoped to
        # the group, not the whole window (another person's high-evidence
        # memory in the window must not block this group's protection).
        group: list[int] = []
        group_max_evidence = top_item.evidence_count
        for index in range(1, min(len(scored), 10)):
            score, overlap, item, reasons, matched = scored[index]
            if item.content_hash == top_item.content_hash:
                continue
            if len(top_cues & set(item.cues)) < min_shared_cues:
                continue
            intersection = top_terms & self._terms(item)
            union = top_terms | self._terms(item)
            if not union:
                continue
            jaccard = len(intersection) / len(union)
            if jaccard < overlap_min:
                continue
            group.append(index)
            group_max_evidence = max(group_max_evidence, item.evidence_count)
        # Pass 2: penalize weaker-evidence rivals; protect the strongest one.
        changed = False
        for index in group:
            score, overlap, item, reasons, matched = scored[index]
            if (
                group_max_evidence > 1
                and item.evidence_count >= group_max_evidence
            ):
                # strongest-evidenced rival: protect and nudge upward
                scored[index] = (
                    score + penalty * 0.5,
                    overlap,
                    item,
                    reasons + [
                        "\u8bc1\u636e\u52a0\u6743\u4fdd\u62a4"
                        "(\u540c\u6a21\u5f0f\u4e2d\u8bc1\u636e\u6700\u591a)"
                    ],
                    matched,
                )
                changed = True
            else:
                if (
                    group_max_evidence > 1
                    and group_max_evidence >= 2 * max(1, item.evidence_count)
                ):
                    # A clearly stronger-evidenced fact exists: push the
                    # weak rival out of the default context so the LLM does
                    # not see a stale contradiction (belief updating /
                    # reconsolidation; Nader et al. 2000, Smolen et al. 2016).
                    scored[index] = (
                        max(0.05, score * 0.3),
                        overlap,
                        item,
                        reasons + [
                            "\u5f31\u8bc1\u636e\u538b\u964d"
                            "(\u88ab\u66f4\u5f3a\u8bc1\u636e\u53d6\u4ee3)"
                        ],
                        matched,
                    )
                    changed = True
                    continue
                else:
                    effective_penalty = penalty
                scored[index] = (
                    max(0.0, score - effective_penalty),
                    overlap,
                    item,
                    reasons + ["\u6a21\u5f0f\u5206\u79bb(\u76f8\u4f3c\u4f46\u4e0d\u540c)"],
                    matched,
                )
        if changed:
            # a protected rival may now outrank the previous top item
            scored.sort(key=lambda entry: entry[0], reverse=True)

    def _pattern_completion(
        self,
        scored: list[tuple[float, float, MemoryItem, list[str], bool]],
        *,
        min_overlap: float,
        max_overlap: float,
        link_weight_min: float,
        min_shared_cues: int,
        boost_scale: float,
        max_roots: int,
        max_neighbors: int,
        max_appended: int,
    ) -> None:
        """Hippocampal pattern completion (Rolls, 2013; Theves et al., 2024).

        A partial cue -- the query overlaps with only some of a memory's
        pattern -- is enough to re-activate the whole integrated cluster in
        the MTL memory system. We emulate this with a *bounded* completion
        pass: for partially matched roots, strongly linked neighbours (strong
        link weight AND at least `min_shared_cues` shared cues) receive a
        discounted boost, so the rest of the pattern can surface even when it
        shares no words with the query.

        The pass is deliberately bounded (few roots, few neighbours, small
        boost) so large stores do not flood the top-k with loosely related
        items; it never changes the base ranking logic for fully matched
        memories.
        """
        roots = [
            entry
            for entry in scored
            if min_overlap <= entry[1] < max_overlap
        ][:max_roots]
        if not roots:
            return
        boosts: dict[str, float] = {}
        for score, _, item, _, _ in roots:
            root_cues = set(item.cues)
            for linked in self.backend.related(
                item.id, depth=1, max_nodes=1000
            )[:max_neighbors]:
                if self.backend.link_weight(item.id, linked.id) < link_weight_min:
                    continue
                if len(root_cues & set(linked.cues)) < min_shared_cues:
                    continue
                boost = score * boost_scale * min(1.0, linked.confidence)
                if boost > boosts.get(linked.id, 0.0):
                    boosts[linked.id] = boost
        if not boosts:
            return
        existing_ids = {entry[2].id for entry in scored}
        reason = "\u6a21\u5f0f\u8865\u5168(\u90e8\u5206\u7ebf\u7d22)"
        applied = 0
        for index, (score, overlap, item, reasons, matched) in enumerate(scored):
            boost = boosts.get(item.id)
            if boost is None or boost <= score:
                continue
            scored[index] = (boost, overlap, item, reasons + [reason], matched)
            applied += 1
        appended = 0
        for linked_id, boost in boosts.items():
            if linked_id in existing_ids or appended >= max_appended:
                continue
            linked = self.backend.get(linked_id)
            if linked is None:
                continue
            scored.append((boost, 0.0, linked, [reason], False))
            existing_ids.add(linked_id)
            appended += 1
        if applied or appended:
            self.pattern_completions += applied + appended
            scored.sort(key=lambda entry: entry[0], reverse=True)

    def _term_index(self, kind: MemoryKind | None) -> dict[str, set[str]]:
        """Lazily built inverted index: term -> memory ids.

        Built once per (kind) and cached; remember() invalidates it via
        `invalidate_term_index()`. This is the same lexical matching used for
        overlap scoring, so pruning by it never changes the ranking — it only
        avoids scanning memories that share no terms with the query (the
        dominant cost at 10k+ memories).
        """
        key = kind.value if kind is not None else "all"
        with self._lock:
            cached = self._inverted.get(key)
            if cached is not None:
                return cached
            index = self.backend.all_terms(kind=kind)
            self._inverted[key] = index
            return index

    def invalidate_term_index(self) -> None:
        with self._lock:
            self._inverted = {}

    def _follow_event_chain(
        self,
        scored: list[tuple[float, float, MemoryItem, list[str], bool]],
        chain: EventChainIndex,
        boost_scale: float,
    ) -> None:
        """Boost the chronological successor of a matched episode.

        Event schemas (Gilboa & Marlatte, 2017): once the anchor of a
        sequence is recognized ("after visiting X..."), the *next* event is
        cued by the script itself, not by shared words. The successor gets a
        discounted boost so it can surface for temporal questions even when
        it shares no tokens with the query.
        """
        by_id: dict[str, int] = {
            item.id: index for index, (_, _, item, _, _) in enumerate(scored)
        }
        boosts: dict[str, float] = {}
        for score, _, item, _, matched in scored[:5]:
            if not matched or item.kind is not MemoryKind.EPISODIC:
                continue
            successor_id = chain.next_event_id(item.id)
            if successor_id is None:
                continue
            boost = score * boost_scale
            if boost > boosts.get(successor_id, 0.0):
                boosts[successor_id] = boost
        for successor_id, boost in boosts.items():
            index = by_id.get(successor_id)
            if index is not None:
                old_score, overlap, item, reasons, matched = scored[index]
                if boost > old_score:
                    scored[index] = (
                        boost,
                        overlap,
                        item,
                        reasons + ["\u65f6\u5e8f\u540e\u7ee7(\u4e8b\u4ef6\u94fe)"],
                        matched,
                    )
                elif not any(
                    "\u65f6\u5e8f\u540e\u7ee7" in reason for reason in reasons
                ):
                    scored[index] = (
                        old_score,
                        overlap,
                        item,
                        reasons + ["\u65f6\u5e8f\u540e\u7ee7(\u4e8b\u4ef6\u94fe)"],
                        matched,
                    )
            else:
                successor = self.backend.get(successor_id)
                if successor is not None:
                    scored.append(
                        (
                            boost,
                            0.0,
                            successor,
                            ["\u65f6\u5e8f\u540e\u7ee7(\u4e8b\u4ef6\u94fe)"],
                            False,
                        )
                    )
        scored.sort(key=lambda entry: entry[0], reverse=True)

    def _record_misses(
        self,
        scored: list[tuple[float, float, MemoryItem, list[str], bool]],
        top_k: int,
        now: datetime,
    ) -> None:
        """Track retrieval failures for adaptive scheduling (Smolen et al. 2016).

        Memories that appeared among the top candidates but did not actually
        match the query are counted as failed retrievals; the review scheduler
        can then re-present them sooner instead of letting the interval grow.
        """
        for _, _, item, _, matched in scored[:top_k]:
            if matched:
                continue
            item.retrieval_failures += 1
            self.backend.update(item)

    def _terms(self, item: MemoryItem) -> frozenset[str]:
        """Cached token terms for an item (auto-invalidated on change)."""
        key = (item.id, item.content_hash, item.revision_count, tuple(item.cues))
        with self._lock:
            cached = self._term_cache.get(key)
            if cached is None:
                cached = frozenset(tokenize(item.content)) | frozenset(item.cues)
                self._term_cache[key] = cached
            return cached

    def _embedding(self, item: MemoryItem, embedder: Embedder) -> list[float]:
        """Cached embedding for an item.

        Keyed by content hash plus the embedder's type and optional stable
        ``cache_key`` (e.g. a model name or cache path) so different
        embedders never share vectors. ``id()`` is intentionally avoided:
        object addresses can be reused after garbage collection.
        """
        key = (
            item.content_hash,
            f"{type(embedder).__module__}.{type(embedder).__name__}",
            getattr(embedder, "cache_key", ""),
        )
        with self._lock:
            cached = self._embed_cache.get(key)
            if cached is None:
                cached = embedder.embed(item.content)
                self._embed_cache[key] = cached
            return cached

    def _spread_activation(
        self,
        scored: list[tuple[float, float, MemoryItem, list[str], bool]],
        query_terms: set[str],
        now: datetime,
        context: str | None,
        query_vector: list[float] | None,
        embedder: Embedder | None,
        discount: float,
        max_roots: int,
        max_neighbors: int,
    ) -> None:
        """Spreading activation over the association graph (HippoRAG-style).

        Memories linked to the strongest matches get a discounted score boost,
        so "what did Alice do after X?" can surface the chronologically next
        event even when it shares no words with the query.
        """
        roots = [entry for entry in scored[:max_roots] if entry[4]]
        if not roots:
            return
        activated: dict[str, tuple[float, MemoryItem]] = {}
        for root_score, _, root, _, _ in roots:
            neighbors = self.backend.related(
                root.id, depth=1, max_nodes=1000
            )
            # Temporal contiguity: temporally adjacent memories associate more
            # strongly, so their activation decays with distance from the root.
            neighbors.sort(
                key=lambda item: abs(item.seq - root.seq)
            )
            for rank, linked in enumerate(neighbors[:max_neighbors]):
                boost = root_score * discount * (0.985**rank)
                current = activated.get(linked.id)
                if current is None or boost > current[0]:
                    activated[linked.id] = (boost, root)
        if not activated:
            return

        activated_ids = set(activated)
        existing_ids = {entry[2].id for entry in scored}
        for index, (score, overlap, item, reasons, matched) in enumerate(scored):
            if item.id not in activated_ids:
                continue
            boost, root = activated[item.id]
            if boost > score:
                reason = f"linked to '{root.content[:40]}'"
                scored[index] = (boost, overlap, item, reasons + [reason], matched)
        for linked_id, (boost, root) in activated.items():
            if linked_id in existing_ids:
                continue
            linked = self.backend.get(linked_id)
            if linked is None:
                continue
            existing_ids.add(linked_id)
            scored.append(
                (
                    boost,
                    0.0,
                    linked,
                    [f"linked to '{root.content[:40]}'"],
                    False,
                )
            )
        scored.sort(key=lambda entry: entry[0], reverse=True)

    def _suppress_linked_rivals(
        self,
        items: list[MemoryItem],
        suppression_factor: float,
        min_shared_cues: int,
        floor: float,
        query_terms: set[str],
    ) -> None:
        """Retrieval-induced forgetting (Anderson, Bjork & Bjork, 1994).

        Only *close competitors* — linked memories sharing at least
        `min_shared_cues` cues with what was recalled — lose a little
        strength. This mirrors RIF's category-competitor effect instead of
        punishing everything loosely related.
        """
        selected = {item.id for item in items}
        suppressed: set[str] = set()
        for item in items:
            item_cues = set(item.cues)
            for linked in self.backend.related(item.id, depth=1, max_nodes=50):
                if linked.id in selected or linked.id in suppressed:
                    continue
                if len(item_cues & set(linked.cues)) < min_shared_cues:
                    continue
                if not _overlap(query_terms, self._terms(linked)) > 0.0:
                    continue  # only true retrieval competitors are suppressed
                linked.strength = max(
                    floor, linked.strength - suppression_factor
                )
                self.backend.update(linked)
                suppressed.add(linked.id)

    def recent(
        self, kind: MemoryKind | None = None, limit: int = 10
    ) -> list[MemoryItem]:
        return self.backend.list(kind=kind, limit=limit)

    def all_active(self, kind: MemoryKind | None = None) -> list[MemoryItem]:
        return self.backend.list(kind=kind)


def _overlap(query_terms: set[str], item_terms: frozenset[str]) -> float:
    """Keyword/cue overlap in [0, 1] between query and an item's terms."""
    if not query_terms or not item_terms:
        return 0.0
    hits = len(query_terms & item_terms)
    # Cap the item-length factor: dividing by sqrt(|query| * |item|) lets
    # long records dilute the discriminating terms, which broke retrieval
    # when facts were buried in long noisy text (large-volume benchmark).
    capped = min(len(item_terms), max(len(query_terms) * 2, 8))
    return hits / max(1.0, math.sqrt(len(query_terms) * capped))


__all__ = ["DualTrackStore"]
