"""Dual-track memory: episodic ("what happened") vs semantic ("what is true").

Human principle #4. Events keep their narrative and time; facts are
deduplicated and kept stable. Recall paths are separate per track.
"""

from __future__ import annotations

import math
import re
from datetime import datetime

from .backend import Backend
from .forgetting import ForgettingCurve
from .importance import ImportanceScorer
from .embedding import Embedder
from .schema import EventChainIndex
from .types import (
    MemoryItem,
    MemoryKind,
    RecallResult,
    SourceRecord,
    normalize_cues,
    tokenize,
    utcnow,
)


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
        self.invalidate_term_index()
        return stored

    def recall(
        self,
        query: str,
        *,
        kind: MemoryKind | None = None,
        top_k: int = 5,
        now: datetime | None = None,
        reinforce: bool = True,
        context: str | None = None,
        suppression_factor: float = 0.01,
        suppression_min_cues: int = 2,
        suppression_floor: float = 0.7,
        embedder: Embedder | None = None,
        expansion_discount: float = 0.95,
        max_expansion_roots: int = 5,
        max_expansion_neighbors: int = 50,
        event_chain: EventChainIndex | None = None,
        temporal_boost: float = 1.0,
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
        kind_preference: bool = False,
        kind_pref: float = 0.03,
    ) -> list[RecallResult]:
        now = now or utcnow()
        candidates = self.backend.list(kind=kind)
        query_terms = set(tokenize(query))
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
            term_index = self._term_index(kind)
            hit_ids: set[str] = set()
            for term in query_terms:
                hit_ids |= term_index.get(term, set())
            if hit_ids:
                candidates = [
                    item for item in candidates if item.id in hit_ids
                ]
        query_vector = embedder.embed(query) if embedder is not None else None
        scored: list[tuple[float, float, MemoryItem, list[str], bool]] = []
        for item in candidates:
            overlap = _overlap(query_terms, self._terms(item))
            retrievability = min(
                1.0, self.curve.retrievability(item, now)
            )
            context_match = (
                context is not None
                and item.context is not None
                and item.context.lower() == context.strip().lower()
            )
            reasons: list[str] = []
            semantic = 0.0
            if query_vector is not None:
                item_vector = self._embedding(item, embedder)
                semantic = embedder.cosine(query_vector, item_vector)
                score = (
                    0.30 * overlap
                    + 0.20 * retrievability
                    + 0.15 * item.importance
                    + (0.15 if context_match else 0.0)
                    + 0.20 * semantic
                )
            else:
                score = (
                    0.40 * overlap
                    + 0.25 * retrievability
                    + 0.20 * item.importance
                    + (0.15 if context_match else 0.0)
                )
            if overlap > 0:
                reasons.append(f"cue/keyword overlap {overlap:.2f}")
            if action_cued and item.kind is MemoryKind.EPISODIC:
                score += 0.05
                reasons.append("action-cued episodic preference")
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
        results = [
            RecallResult(item=item, score=score, reasons=reasons)
            for score, _, item, reasons, _ in scored[:top_k]
        ]
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
        """
        if len(scored) < 2:
            return
        _, _, top_item, _, _ = scored[0]
        top_cues = set(top_item.cues)
        top_terms = self._terms(top_item)
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
            scored[index] = (
                max(0.0, score - penalty),
                overlap,
                item,
                reasons + ["\u6a21\u5f0f\u5206\u79bb(\u76f8\u4f3c\u4f46\u4e0d\u540c)"],
                matched,
            )

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
        cached = self._inverted.get(key)
        if cached is not None:
            return cached
        index: dict[str, set[str]] = {}
        for item in self.backend.list(kind=kind):
            for term in self._terms(item):
                index.setdefault(term, set()).add(item.id)
        self._inverted[key] = index
        return index

    def invalidate_term_index(self) -> None:
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
        cached = self._term_cache.get(key)
        if cached is None:
            cached = frozenset(tokenize(item.content)) | frozenset(item.cues)
            self._term_cache[key] = cached
        return cached

    def _embedding(self, item: MemoryItem, embedder: Embedder) -> list[float]:
        """Cached embedding for an item (keyed by content hash)."""
        cached = self._embed_cache.get(item.content_hash)
        if cached is None:
            cached = embedder.embed(item.content)
            self._embed_cache[item.content_hash] = cached
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
        for index, (score, overlap, item, reasons, matched) in enumerate(scored):
            if item.id not in activated_ids:
                continue
            boost, root = activated[item.id]
            if boost > score:
                reason = f"linked to '{root.content[:40]}'"
                scored[index] = (boost, overlap, item, reasons + [reason], matched)
        for linked_id, (boost, root) in activated.items():
            if any(entry[2].id == linked_id for entry in scored):
                continue
            linked = self.backend.get(linked_id)
            if linked is None:
                continue
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
    return hits / max(
        1.0, math.sqrt(len(query_terms) * max(len(item_terms), 1))
    )


__all__ = ["DualTrackStore"]
