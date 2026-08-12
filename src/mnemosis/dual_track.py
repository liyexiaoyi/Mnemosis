"""Dual-track memory: episodic ("what happened") vs semantic ("what is true").

Human principle #4. Events keep their narrative and time; facts are
deduplicated and kept stable. Recall paths are separate per track.
"""

from __future__ import annotations

import logging
import math
import numbers
import queue
import re
import threading
import time
from collections import OrderedDict, deque
from datetime import datetime

from .backend import Backend
from .embedding import Embedder
from .forgetting import ForgettingCurve
from .importance import ImportanceScorer
from .reasoning import apply_premise_pack
from .schema import EventChainIndex
from .temporal_reason import apply_time_cell_reasoning
from .types import (
    STOPWORDS,
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

_LOG = logging.getLogger(__name__)

_FALLBACK_RECENT = 150
"""Most recent memories loaded for a zero-hit query."""

_FALLBACK_STRONG = 50
"""Most important memories additionally loaded for a zero-hit query.

Zero-hit queries return both the recent traces and the highest-importance
core facts, so an old but critical memory (e.g. an allergy) still surfaces
instead of being drowned by recency.
"""

_TERM_CACHE_LIMIT = 50_000
"""Upper bound for the per-item term cache (FIFO eviction)."""

_DF_CACHE_LIMIT = 50_000
"""Upper bound for the term document-frequency cache (FIFO eviction)."""

_REINFORCE_QUEUE_MAX = 10_000
"""Backpressure cap for the background reinforcement queue; when full,
reinforcement falls back to a synchronous write instead of dropping."""

_FALLBACK_IMPORTANCE_BOOST = 0.20
"""Extra score per unit of importance in zero-hit fallback ranking.

Zero-hit scores are dominated by the recency term; this boost lets a
high-importance core fact (importance ~1.0) overtake recent low-importance
traces without letting mid-importance facts (<0.5) dominate.
"""

_DENSE_RERANK_CANDIDATES = 64
"""Max candidates embedded per query.

The dense term of the score used to embed every candidate (up to the 1000
memory fallback) on every query. Candidates are now lexically pre-ranked
and only this many are embedded for the semantic re-rank; with 10k memories
this takes ngram recall from ~200ms to tens of ms.
"""

_MAX_ZERO_HIT_RERANK_POOL = 200
"""Hard cap for the zero-hit semantic re-rank pool.

Local embedders (NGram, Ollama) can re-rank the whole fallback pool cheaply;
network-backed embedders fall back to ``_DENSE_RERANK_CANDIDATES`` so a
remote API is never called for hundreds of texts per query.
"""

_RERANK_SCORE_GAP = 0.10
"""Dense re-rank stops after the first adjacent score gap above this."""

_RERANK_SCORE_GAP_RATIO = 0.30
"""The gap must also exceed 30% of the previous score to count as a cliff.

An absolute gap of 0.10 means very different things at score 0.9 vs 0.25;
requiring the relative drop too stops low-score regions from being
over-cut.
"""

_RERANK_MIN_POOL = 4
"""Minimum lexical candidates embedded despite the score cliff.

A hard gap threshold can over-cut when the top score is extreme (e.g. a
very strong match next to paraphrase synonyms); keeping at least this many
candidates bounds the recall loss.
"""

_EN_SYNONYMS: dict[str, tuple[str, ...]] = {
    "spent": ("cost", "paid", "bought", "spending"),
    "money": ("cost", "amount", "price", "payment"),
    "expenses": ("cost", "costs", "spending", "bills"),
    "total": ("sum", "overall"),
    "bought": ("purchased", "got", "ordered"),
    "purchased": ("bought", "ordered", "got"),
    "price": ("cost", "amount", "fee"),
    "cost": ("price", "amount", "paid"),
    "paid": ("cost", "spent", "charged"),
    "bike": ("bicycle", "cycling"),
    "bicycle": ("bike", "cycling"),
}


def _expand_en_synonyms(query_terms: set[str]) -> set[str]:
    """English synonym expansion for lexical recall.

    Mirrors the Chinese ``expand_synonyms`` path: a query about "money spent
    on bike expenses" must also match turns written as "cost / paid / bought
    a bicycle" (semantic memory; Collins & Quillian, 1969).
    """
    expanded = set(query_terms)
    for term in query_terms:
        for synonym in _EN_SYNONYMS.get(term, ()):
            expanded.add(synonym)
        if "-" in term or "_" in term:
            expanded.update(
                part
                for part in re.split(r"[-_]", term)
                if (
                    len(part) > 1
                    and not part.isdigit()
                    and part not in STOPWORDS
                )
            )
    return expanded


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
        *,
        dense_rerank_candidates: int = _DENSE_RERANK_CANDIDATES,
        zero_hit_rerank_pool: int = _MAX_ZERO_HIT_RERANK_POOL,
        embed_cache_limit: int = 100_000,
        embed_cache_memory_limit_mb: float | None = None,
        fallback_cache_ttl: float = 15.0,
        fallback_cache_size: int = 32,
        fallback_cache_max_size: int = 256,
        fallback_cache_auto_grow: bool = True,
        fallback_cache_grow_cooldown_seconds: float = 300.0,
    ) -> None:
        self.backend = backend
        self.curve = curve
        self.scorer = scorer
        self.dense_rerank_candidates = max(1, int(dense_rerank_candidates))
        self.zero_hit_rerank_pool = max(1, int(zero_hit_rerank_pool))
        self._term_cache: OrderedDict[tuple, frozenset[str]] = OrderedDict()
        self._embed_cache: OrderedDict[tuple, list[float]] = OrderedDict()
        self.embed_cache_limit = max(1, int(embed_cache_limit))
        if embed_cache_memory_limit_mb is not None and embed_cache_memory_limit_mb > 0:
            self.embed_cache_memory_limit = int(embed_cache_memory_limit_mb * 1024 * 1024)
        else:
            self.embed_cache_memory_limit = 0  # disabled; count limit still applies
        self._embed_cache_bytes = 0
        self.fallback_cache_ttl = max(0.0, float(fallback_cache_ttl))
        self.fallback_cache_size = max(1, int(fallback_cache_size))
        self.fallback_cache_max_size = max(
            self.fallback_cache_size, int(fallback_cache_max_size)
        )
        self.fallback_cache_auto_grow = bool(fallback_cache_auto_grow)
        self.fallback_cache_grow_cooldown = max(
            0.0, float(fallback_cache_grow_cooldown_seconds)
        )
        self._last_grow_time = float("-inf")
        self._fallback_cache: OrderedDict[
            tuple, tuple[float, dict]
        ] = OrderedDict()
        self.fallback_cache_hits = 0
        self.fallback_cache_misses = 0
        self.fallback_cache_evictions = 0
        self.fallback_cache_growths = 0
        self._fallback_cache_eviction_times: deque[float] = deque(
            maxlen=32768
        )
        self._inverted: dict[str, dict[str, set[str]]] = {}
        self._df_cache: OrderedDict[
            tuple[str, MemoryKind | None], int
        ] = OrderedDict()
        self._reinforce_queue: queue.Queue = queue.Queue(
            maxsize=_REINFORCE_QUEUE_MAX
        )
        self._reinforce_thread: threading.Thread | None = None
        self._worker_lock = threading.Lock()
        self._is_shutdown = False
        self.reinforce_received = 0
        self.reinforce_written = 0
        self.reinforce_dropped = 0
        self.reinforce_sync_fallback = 0
        self._lock = threading.RLock()
        self.pattern_completions = 0

    def _cached_term_dfs(
        self, terms: set[str], kind: MemoryKind | None
    ) -> dict[str, int]:
        """Term document frequencies with an invalidated-on-write cache."""
        with self._lock:
            missing = [
                term for term in terms if (term, kind) not in self._df_cache
            ]
            cached: dict[str, int] = {}
            for term in terms:
                key = (term, kind)
                if key in self._df_cache:
                    # LRU: a hit refreshes the entry so hot terms survive
                    # the FIFO bound.
                    self._df_cache.move_to_end(key)
                    cached[term] = self._df_cache[key]
                else:
                    cached[term] = 0
        if missing:
            # Query outside the store lock so one recall's DB I/O does not
            # serialize every concurrent recall.
            found = self.backend.term_dfs(missing, kind)
            with self._lock:
                for term, df in found.items():
                    self._df_cache[(term, kind)] = df
                for term in missing:
                    self._df_cache.setdefault((term, kind), 0)
                while len(self._df_cache) > _DF_CACHE_LIMIT:
                    self._df_cache.popitem(last=False)
                cached = {
                    term: self._df_cache.get((term, kind), 0)
                    for term in terms
                }
        return cached

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

    def remember_many(self, records: list[dict]) -> list[MemoryItem]:
        """Bulk remember with the same per-item semantics as ``remember``.

        Episodic inserts share one atomic transaction and all term rows are
        rebuilt in one bulk statement, so ingesting 10k memories takes
        seconds instead of a minute. Each record mirrors ``remember``'s
        arguments: content/kind/source required; cues/importance/confidence/
        strength/created_at/context/affect/evidence_count/storage_strength
        optional.
        """
        prepared: list[MemoryItem] = []
        for record in records:
            content = record["content"]
            kind = record["kind"]
            source = record["source"]
            importance = record.get("importance")
            if importance is None:
                importance = self.scorer.score(content, source=source)
            prepared.append(
                MemoryItem(
                    content=content,
                    kind=kind,
                    source=source,
                    cues=normalize_cues(record.get("cues") or []),
                    created_at=record.get("created_at") or utcnow(),
                    importance=importance,
                    confidence=record.get("confidence", 1.0),
                    strength=record.get("strength", 1.0),
                    context=record.get("context"),
                    affect=record.get("affect"),
                    evidence_count=record.get("evidence_count", 1),
                    storage_strength=record.get("storage_strength", 1.0),
                )
            )
        episodic = [
            item
            for item in prepared
            if item.kind is not MemoryKind.SEMANTIC
        ]
        semantic = [
            item
            for item in prepared
            if item.kind is MemoryKind.SEMANTIC
        ]
        semantic_stored = (
            self.backend.upsert_many(semantic) if semantic else []
        )
        if episodic:
            self.backend.add_many(episodic)
        stored: list[MemoryItem] = []
        semantic_index = 0
        for item in prepared:
            if item.kind is MemoryKind.SEMANTIC:
                stored.append(semantic_stored[semantic_index])
                semantic_index += 1
            else:
                stored.append(item)
        self.backend.index_terms_many(
            (
                (item.id, self._terms(item, cache=False), item.kind)
                for item in stored
            ),
            replace=bool(semantic),
        )
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
        fallback_mode = False
        query_terms = set(tokenize(query))
        base_terms = set(query_terms)
        if zh_synonyms and any("\u4e00" <= ch <= "\u9fff" for ch in query):
            # Chinese synonym expansion: questions often use different words
            # than the stored memory ("筹备/旅游" vs "准备/旅行").

            query_terms = expand_synonyms(query_terms)
        elif zh_synonyms:
            query_terms = _expand_en_synonyms(query_terms)
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
        idf_weights: dict[str, float] = {}
        idf_sum = 0.0
        fallback_cache_key: tuple | None = None
        if self.fallback_cache_ttl > 0:
            embedder_key = (
                "none"
                if embedder is None
                else (
                    f"{type(embedder).__module__}."
                    f"{type(embedder).__name__}:"
                    # Without a stable cache_key, isolate by instance id so
                    # two embedders of the same class never share results.
                    f"{getattr(embedder, 'cache_key', None) or id(embedder)}"
                )
            )
            fallback_cache_key = (
                query,
                top_k,
                kind,
                context,
                frozenset(exclude_ids or ()),
                embedder_key,
            )
            cached = self._fallback_cache_get(fallback_cache_key)
            if cached is not None:
                # Cache check happens before any SQL: a hit means the query
                # was a fallback when stored, so count/df lookups (which cost
                # ~1ms at 100k) are skipped entirely.
                rebuilt = self._rebuild_cached_fallback(
                    cached,
                    query_terms=query_terms,
                    top_k=top_k,
                    now=now,
                    reinforce=reinforce,
                    suppression_factor=suppression_factor,
                    suppression_min_cues=suppression_min_cues,
                    suppression_floor=suppression_floor,
                )
                if rebuilt is not None:
                    return rebuilt
                # Entries whose items were deleted are dropped so the
                # next recall recomputes fresh results.
                self.invalidate_fallback_cache()
        if query_terms:
            total_active = self.backend.count(kind=kind)
            term_df = self._cached_term_dfs(query_terms, kind)
        else:
            total_active = 0
            term_df = {}
        if query_terms:
            hit_counts: dict[str, int] = {}
            term_ids: dict[str, set[str]] = {}
            for term in query_terms:
                df = term_df.get(term, 0)
                if (
                    df > 0
                    and total_active >= 1000
                    and df > 5000
                ):
                    # A term present in most memories carries no
                    # discriminative signal; skip materialising its ids so a
                    # generic word cannot balloon the candidate set.
                    term_ids[term] = set()
                    continue
                ids_for_term = (
                    set(self.backend.find_by_terms([term], kind))
                    if df > 0
                    else set()
                )
                term_ids[term] = ids_for_term
                for memory_id in ids_for_term:
                    hit_counts[memory_id] = hit_counts.get(memory_id, 0) + 1
            # Term-specificity weighting (idf, Robertson & Zaragoza 2009):
            # a rare term like "Admon" is a much stronger retrieval cue than
            # a generic one, so hits on rare terms should dominate the score.
            # Robertson-Sparck Jones idf: terms present in most memories get
            # ~0 weight, rare terms dominate; clipped at 4.0 so a typo-like
            # token cannot crush everything. df is clamped to the active
            # count because the term table also holds recycled rows.
            idf_weights = {}
            for term, df in term_df.items():
                if df <= 0 or total_active <= 0:
                    continue
                safe_df = min(df, total_active)
                idf_weights[term] = min(
                    max(
                        0.0,
                        math.log(
                            (total_active - safe_df + 0.5)
                            / (safe_df + 0.5)
                        ),
                    ),
                    4.0,
                )
            idf_sum = sum(idf_weights.values())
            ids = set(hit_counts) - set(exclude_ids or set())
            if ids:
                if len(ids) > 100:
                    # Pre-rank by idf-weighted hits so a candidate matching
                    # one rare term is not cut in favor of generic hits.
                    def _pre_score(memory_id: str) -> float:
                        return sum(
                            idf_weights[term]
                            for term, ids_for_term in term_ids.items()
                            if memory_id in ids_for_term
                        )

                    ids = {
                        memory_id
                        for memory_id, _ in sorted(
                            ((memory_id, _pre_score(memory_id)) for memory_id in ids),
                            key=lambda row: -row[1],
                        )[:100]
                    }
                ids = sorted(ids)
                candidates = self.backend.get_many(ids)
        if not candidates:
            # Zero-hit queries fall back to a dual pool: recent traces plus
            # the highest-importance core facts (importance -> recency), so
            # old but critical memories can still surface. Both queries use
            # (status, seq) / (status, importance) indexes, keeping the
            # fallback cheap at 100k+ scale.
            fallback_mode = True
            recent = self.backend.list(kind=kind, limit=_FALLBACK_RECENT)
            strong = self.backend.list_strongest(
                kind=kind, limit=_FALLBACK_STRONG
            )
            by_id = {item.id: item for item in recent}
            for item in strong:
                by_id.setdefault(item.id, item)
            candidates = list(by_id.values())
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
            item_terms = self._terms(item)
            if any("\u4e00" <= ch <= "\u9fff" for ch in query):
                # Chinese keeps the long-standing expanded denominator.
                hits = len(query_terms & item_terms)
                denominator_terms = query_terms
            else:
                # English: expansion contributes to hits but the denominator
                # stays on the original words, so adding "cost" for "spent"
                # never dilutes the query's geometry.
                hits = len(query_terms & item_terms)
                denominator_terms = base_terms
            if hits:
                capped = min(
                    len(item_terms), max(len(denominator_terms) * 2, 8)
                )
                overlap = hits / max(
                    1.0, math.sqrt(max(1, len(denominator_terms)) * capped)
                )
            else:
                overlap = 0.0
            if idf_sum and query_terms:
                idf_hits = sum(
                    idf_weights[term]
                    for term in query_terms
                    if term in item_terms
                )
                if idf_hits:
                    # Rare-term boost: keep the original overlap geometry and
                    # scale it up to 2x when the candidate matches terms that
                    # are rare across the store. Uniform idf -> scale 1.0,
                    # so common-topic queries behave exactly as before.
                    idf_avg = max(idf_sum / len(query_terms), 1e-6)
                    scale = min(
                        1.0 + 0.5 * (idf_hits / idf_avg - 1.0),
                        2.0,
                    )
                    weighted_overlap = overlap * scale
                else:
                    weighted_overlap = overlap
            else:
                weighted_overlap = overlap
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
            # Semantic similarity is added in a second pass over only the
            # lexically top candidates (see rerank below); until then it is
            # zero so the provisional score stays cheap.
            semantic = 0.0
            score = (
                (0.30 if query_vector is not None else 0.40)
                * weighted_overlap
                + (0.20 if query_vector is not None else 0.25)
                * retrievability
                + (0.15 if query_vector is not None else 0.20)
                * item.importance
                + 0.15 * context_overlap
                + self_bonus
                + trust_bonus
                + mood_bonus
                + confidence_bonus
                + gist_bonus
                + salience_bonus
                + corroboration_bonus
            )
            if fallback_mode:
                # Zero-hit queries have no lexical signal: let core facts
                # (high importance) compete with recent traces instead of
                # being buried by the recency term.
                score += _FALLBACK_IMPORTANCE_BOOST * item.importance
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
            if retrievability < 0.5:
                reasons.append("partially forgotten")
            if item.importance >= 0.7:
                reasons.append("high importance")
            if context_match:
                reasons.append("context match")
            elif context_overlap > 0.0:
                reasons.append(f"context overlap {context_overlap:.2f}")
            matched = overlap > 0.0
            scored.append((score, overlap, item, reasons, matched))
        if query_vector is not None and scored:
            # Dense re-rank: embed only a bounded candidate pool and add the
            # semantic term to their scores. When the query has lexical hits
            # only those are embedded (plus a small zero-overlap budget so a
            # paraphrase can still be rescued); a zero-hit fallback embeds
            # the top of the recency window. Candidates outside the pool keep
            # their lexical-only score (matched=False is accepted as the
            # documented trade-off for bounded queries).
            scored.sort(key=lambda entry: entry[0], reverse=True)
            lexical_hits = [entry for entry in scored if entry[1] > 0.0]
            if lexical_hits:
                zero_budget = min(
                    16, len(scored) - len(lexical_hits)
                )
                # Early termination: stop embedding once the lexical score
                # shows a real cliff (adjacent gap above _RERANK_SCORE_GAP).
                # A flat/slowly-decaying distribution is left intact so a
                # relative threshold cannot mis-cut paraphrase synonyms.
                top_score = lexical_hits[0][0]
                cutoff = 1
                previous = top_score
                for entry in lexical_hits[1:]:
                    gap = previous - entry[0]
                    if (
                        gap > _RERANK_SCORE_GAP
                        and gap > previous * _RERANK_SCORE_GAP_RATIO
                    ):
                        break
                    previous = entry[0]
                    cutoff += 1
                pool = lexical_hits[
                    : min(
                        max(_RERANK_MIN_POOL, cutoff),
                        self.dense_rerank_candidates - zero_budget,
                    )
                ]
                if zero_budget > 0:
                    pool = pool + [
                        entry
                        for entry in scored
                        if entry[1] == 0.0
                    ][:zero_budget]
            else:
                # Zero-hit: re-rank the WHOLE fallback pool semantically so
                # a relevant memory is not skipped just because its lexical
                # score ranked it beyond the first 64.
                pool = scored[
                    : (
                        self.zero_hit_rerank_pool
                        if not getattr(embedder, "remote", False)
                        else self.dense_rerank_candidates
                    )
                ]
            rerank_ids = {entry[2].id for entry in pool}
            rerank_items = [
                entry[2] for entry in scored if entry[2].id in rerank_ids
            ]
            if rerank_items:
                # Batch embed: network-backed embedders turn N per-item calls
                # into one HTTP request via embed_many.
                vectors = embedder.embed_many(
                    [self._embed_text(item) for item in rerank_items]
                )
                if len(vectors) != len(rerank_items):
                    raise RuntimeError(
                        f"embed_many returned {len(vectors)} vectors for "
                        f"{len(rerank_items)} items"
                    )
                cache_updates = {
                    self._embed_cache_key(item, embedder): vector
                    for item, vector in zip(rerank_items, vectors)
                }
                with self._lock:
                    for key, vector in cache_updates.items():
                        old = self._embed_cache.get(key)
                        if old is not None:
                            self._embed_cache_bytes -= self._vector_cache_bytes(old)
                        self._embed_cache[key] = vector
                        self._embed_cache_bytes += self._vector_cache_bytes(vector)
                    self._trim_embed_cache_locked()
                vector_by_id = {
                    item.id: vector
                    for item, vector in zip(rerank_items, vectors)
                }
                for index, (score, overlap, item, reasons, matched) in enumerate(
                    scored
                ):
                    if item.id not in rerank_ids:
                        continue
                    item_vector = vector_by_id[item.id]
                    semantic = embedder.cosine(query_vector, item_vector)
                    score = score + 0.20 * semantic
                    if semantic > 0.5:
                        reasons.append(
                            f"semantic similarity {semantic:.2f}"
                        )
                    scored[index] = (
                        score,
                        overlap,
                        item,
                        reasons,
                        matched or semantic >= 0.2,
                    )
            scored.sort(key=lambda entry: entry[0], reverse=True)
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
            fallback_mode=fallback_mode,
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
            updated_items: list[MemoryItem] = []
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
                updated_items.append(item)
            if updated_items:
                try:
                    self.backend.update_many(updated_items)
                except Exception as exc:  # noqa: BLE001
                    # Best-effort reinforcement: a write failure must not
                    # skip miss accounting or the recall itself.
                    _LOG.debug(
                        "reinforcement batch update failed: %s", exc
                    )
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
                    fallback_mode=fallback_mode,
                )
        if fallback_mode and fallback_cache_key is not None:
            # Generic/zero-hit queries repeat constantly in agent loops; the
            # cached payload stores only ids+scores+reasons, so a later hit
            # re-fetches live MemoryItems before returning them.
            self._fallback_cache_store(
                fallback_cache_key,
                {
                    "scored": [
                        (score, overlap, item.id, list(reasons), matched)
                        for score, overlap, item, reasons, matched in (
                            scored[:top_k]
                        )
                    ],
                    "confident": [result.confident for result in results],
                },
            )
        return results

    def _ensure_reinforce_worker(self) -> None:
        """Lazily start the single background reinforcement worker."""
        if self._is_shutdown:
            return
        with self._worker_lock:
            if (
                self._reinforce_thread is not None
                and self._reinforce_thread.is_alive()
            ):
                return
            self._reinforce_thread = threading.Thread(
                target=self._reinforce_worker_loop,
                name="mnemosis-reinforce",
                daemon=True,
            )
            self._reinforce_thread.start()

    def _reinforce_worker_loop(self) -> None:
        while True:
            first = self._reinforce_queue.get()
            if first is None:
                self._reinforce_queue.task_done()
                return
            batches = [first]
            sentinel = False
            while True:
                try:
                    extra = self._reinforce_queue.get_nowait()
                except queue.Empty:
                    break
                if extra is None:
                    sentinel = True
                    break
                batches.append(extra)
            merged: list[MemoryItem] = []
            seen: set[str] = set()
            for batch in batches:
                for item in batch:
                    if item.id not in seen:
                        seen.add(item.id)
                        merged.append(item)
            try:
                self.backend.update_many(merged)
                with self._worker_lock:
                    self.reinforce_written += len(merged)
            except Exception as exc:  # noqa: BLE001
                _LOG.debug("background reinforcement failed: %s", exc)
                with self._worker_lock:
                    self.reinforce_dropped += len(merged)
            for _ in batches:
                self._reinforce_queue.task_done()
            if sentinel:
                self._reinforce_queue.task_done()
                return

    def enqueue_reinforce(self, items: list[MemoryItem]) -> None:
        """Queue a best-effort reinforcement batch for the worker."""
        if not items:
            return
        if self._is_shutdown:
            _LOG.debug("reinforcement dropped: worker already shut down")
            with self._worker_lock:
                self.reinforce_dropped += len(items)
            return
        self._ensure_reinforce_worker()
        try:
            self._reinforce_queue.put_nowait(items)
        except queue.Full:
            # Backpressure: never let the queue grow without bound; a full
            # queue degrades to a synchronous best-effort write.
            with self._worker_lock:
                self.reinforce_received += len(items)
                self.reinforce_sync_fallback += 1
            try:
                self.backend.update_many(items)
                with self._worker_lock:
                    self.reinforce_written += len(items)
            except Exception as exc:  # noqa: BLE001
                _LOG.warning(
                    "reinforcement queue full; sync fallback failed: %s",
                    exc,
                )
                with self._worker_lock:
                    self.reinforce_dropped += len(items)
            return
        with self._worker_lock:
            self.reinforce_received += len(items)

    def reinforce_stats(self) -> dict:
        """Observability counters for the background worker."""
        with self._worker_lock:
            return {
                "received": self.reinforce_received,
                "written": self.reinforce_written,
                "dropped": self.reinforce_dropped,
                "sync_fallback": self.reinforce_sync_fallback,
                "queue_size": self._reinforce_queue.qsize(),
                "queue_max": self._reinforce_queue.maxsize,
            }

    def shutdown_reinforce_worker(self) -> None:
        """Drain pending reinforcement writes and stop the worker."""
        with self._worker_lock:
            self._is_shutdown = True
            thread = self._reinforce_thread
        if thread is None or not thread.is_alive():
            return
        self._reinforce_queue.put(None)
        thread.join(timeout=10)
        if thread.is_alive():
            _LOG.warning(
                "reinforce worker did not stop within 10s; "
                "leaving daemon thread"
            )
            return
        with self._worker_lock:
            if self._reinforce_thread is thread:
                self._reinforce_thread = None

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
                        ("\u8bc1\u636e\u52a0\u6743\u4fdd\u62a4"
                        "(\u540c\u6a21\u5f0f\u4e2d\u8bc1\u636e\u6700\u591a)")
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
                            ("\u5f31\u8bc1\u636e\u538b\u964d"
                            "(\u88ab\u66f4\u5f3a\u8bc1\u636e\u53d6\u4ee3)")
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
                # Loading 1000 neighbours to use 8 is wasted JSON decoding;
                # both orders are by seq/content, so the first 8 are identical.
                item.id,
                depth=1,
                max_nodes=max(64, max_neighbors * 4),
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
            self._df_cache = OrderedDict()
            # Term frequency changes can flip the fallback heuristic, so a
            # term-index rebuild must also drop cached fallback results.
            self._fallback_cache.clear()

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

    def _terms(
        self, item: MemoryItem, *, cache: bool = True
    ) -> frozenset[str]:
        """Token terms for an item.

        Cached per (id, content_hash, revision, cues) and auto-invalidated on
        change. Bulk ingestion sets ``cache=False``: each item is touched
        once, so an unbounded cache would retain millions of frozensets.
        """
        key = (item.id, item.content_hash, item.revision_count, tuple(item.cues))
        if cache:
            with self._lock:
                cached = self._term_cache.get(key)
                if cached is not None:
                    return cached
        terms = frozenset(tokenize(item.content)) | frozenset(item.cues)
        if cache:
            with self._lock:
                self._term_cache[key] = terms
                while len(self._term_cache) > _TERM_CACHE_LIMIT:
                    self._term_cache.popitem(last=False)
        return terms

    def _embedding(self, item: MemoryItem, embedder: Embedder) -> list[float]:
        """Cached embedding for an item.

        Keyed by content hash plus the embedder's type and optional stable
        ``cache_key`` (e.g. a model name or cache path) so different
        embedders never share vectors. ``id()`` is intentionally avoided:
        object addresses can be reused after garbage collection.
        """
        key = self._embed_cache_key(item, embedder)
        with self._lock:
            cached = self._embed_cache.get(key)
        if cached is not None:
            return cached
        # Embed outside the store lock: remote embedders can take hundreds of
        # milliseconds, and serializing every concurrent recall behind that
        # would defeat the cache's purpose.
        vector = embedder.embed(self._embed_text(item))
        with self._lock:
            existing = self._embed_cache.get(key)
            if existing is not None:
                return existing
            self._embed_cache[key] = vector
            self._embed_cache_bytes += self._vector_cache_bytes(vector)
            self._trim_embed_cache_locked()
            return vector

    def _trim_embed_cache_locked(self) -> None:
        """Evict oldest-inserted vectors beyond the limits.

        Read hits intentionally do not touch the order (a move on every hit
        would need a write lock per read); this is a capacity-bounding FIFO
        cache, which keeps concurrent reads cheap and memory bounded. The
        primary bound is an estimated byte budget (see
        ``_vector_cache_bytes``); the entry-count limit is kept as a floor so
        extremely high-dimensional vectors cannot blow past the byte estimate
        in one insert.
        """
        while len(self._embed_cache) > self.embed_cache_limit or (
            self.embed_cache_memory_limit > 0
            and self._embed_cache_bytes > self.embed_cache_memory_limit
        ):
            _, vector = self._embed_cache.popitem(last=False)
            self._embed_cache_bytes -= self._vector_cache_bytes(vector)

    @staticmethod
    def _vector_cache_bytes(vector: list[float]) -> int:
        """Estimated resident memory for one cached vector.

        Embedders normally return Python ``list[float]`` objects: each float
        is a separate ~24-byte object behind an 8-byte pointer, so the honest
        estimate is ~32 bytes per element plus list overhead. Compact arrays
        (``numpy.ndarray``, ``array.array``) expose their real ``nbytes`` and
        are measured directly. The estimate is still approximate, but it keeps
        the default 512 MB budget from silently allowing 6-8x more real memory
        than intended.
        """
        nbytes = getattr(vector, "nbytes", None)
        if isinstance(nbytes, numbers.Integral) and nbytes > 0:
            return int(nbytes)
        return len(vector) * 32 + 64

    @staticmethod
    def _embed_text(item: MemoryItem) -> str:
        """Text sent to the embedder — single source for single/batch paths."""
        return item.content

    def _embed_cache_key(
        self, item: MemoryItem, embedder: Embedder
    ) -> tuple[str, str, str]:
        return (
            item.content_hash,
            f"{type(embedder).__module__}.{type(embedder).__name__}",
            getattr(embedder, "cache_key", ""),
        )

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
        fallback_mode: bool = False,
    ) -> None:
        """Spreading activation over the association graph (HippoRAG-style).

        Memories linked to the strongest matches get a discounted score boost,
        so "what did Alice do after X?" can surface the chronologically next
        event even when it shares no words with the query.
        """
        if fallback_mode:
            # Zero-hit queries have no lexical anchor: spreading activation
            # over recent/strongest fallback items only adds noise and costs
            # 5-6 graph traversals per recall.
            return
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
        *,
        fallback_mode: bool = False,
        max_suppressed: int = 12,
    ) -> None:
        """Retrieval-induced forgetting (Anderson, Bjork & Bjork, 1994).

        Only *close competitors* — linked memories sharing at least
        `min_shared_cues` cues with what was recalled — lose a little
        strength. This mirrors RIF's category-competitor effect instead of
        punishing everything loosely related.
        """
        if fallback_mode:
            # A generic/zero-hit query carries no discriminative signal, so
            # it must not trigger retrieval-induced forgetting across a wide
            # set of loosely related traces (and the 100+ SQLite updates it
            # would otherwise cause).
            return
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
                if len(suppressed) >= max_suppressed:
                    return

    def _fallback_cache_get(self, key: tuple) -> dict | None:
        """Return a live fallback payload, or None on miss/expiry."""
        with self._lock:
            entry = self._fallback_cache.get(key)
            if entry is None:
                self.fallback_cache_misses += 1
                return None
            expires_at, payload = entry
            if expires_at <= time.monotonic():
                del self._fallback_cache[key]
                self.fallback_cache_misses += 1
                return None
            self.fallback_cache_hits += 1
            return payload

    def _fallback_cache_store(self, key: tuple, payload: dict) -> None:
        with self._lock:
            self._fallback_cache[key] = (
                time.monotonic() + self.fallback_cache_ttl,
                payload,
            )
            while len(self._fallback_cache) > self.fallback_cache_size:
                self._fallback_cache.popitem(last=False)
                self.fallback_cache_evictions += 1
                self._fallback_cache_eviction_times.append(time.monotonic())
            if (
                self.fallback_cache_auto_grow
                and self.fallback_cache_size < self.fallback_cache_max_size
                and (
                    time.monotonic() - self._last_grow_time
                    >= self.fallback_cache_grow_cooldown
                )
            ):
                cutoff = time.monotonic() - 60.0
                while (
                    self._fallback_cache_eviction_times
                    and self._fallback_cache_eviction_times[0] < cutoff
                ):
                    self._fallback_cache_eviction_times.popleft()
                if len(self._fallback_cache_eviction_times) >= max(
                    2, self.fallback_cache_size
                ):
                    self.fallback_cache_size = min(
                        self.fallback_cache_size * 2,
                        self.fallback_cache_max_size,
                    )
                    self.fallback_cache_growths += 1
                    self._last_grow_time = time.monotonic()

    def invalidate_fallback_cache(self) -> None:
        """Drop cached fallback results after any memory mutation."""
        with self._lock:
            self._fallback_cache.clear()

    def fallback_cache_stats(self) -> dict:
        """Hit/miss counters and capacity for observability."""
        with self._lock:
            total = self.fallback_cache_hits + self.fallback_cache_misses
            hit_rate = (
                self.fallback_cache_hits / total if total > 0 else 0.0
            )
            cutoff = time.monotonic() - 60.0
            while (
                self._fallback_cache_eviction_times
                and self._fallback_cache_eviction_times[0] < cutoff
            ):
                self._fallback_cache_eviction_times.popleft()
            evictions_last_60s = len(self._fallback_cache_eviction_times)
            return {
                "hits": self.fallback_cache_hits,
                "misses": self.fallback_cache_misses,
                "hit_rate": round(hit_rate, 4),
                "evictions": self.fallback_cache_evictions,
                "evictions_last_60s": evictions_last_60s,
                "growths": self.fallback_cache_growths,
                "entries": len(self._fallback_cache),
                "size_limit": self.fallback_cache_size,
                "max_size": self.fallback_cache_max_size,
                "auto_grow": self.fallback_cache_auto_grow,
                "grow_cooldown_seconds": self.fallback_cache_grow_cooldown,
                "ttl_seconds": self.fallback_cache_ttl,
            }

    def _rebuild_cached_fallback(
        self,
        payload: dict,
        *,
        query_terms: set[str],
        top_k: int,
        now: datetime,
        reinforce: bool,
        suppression_factor: float,
        suppression_min_cues: int,
        suppression_floor: float,
    ) -> list[RecallResult] | None:
        """Turn a cached fallback payload into fresh, live results.

        Item objects are re-fetched so content/strength are current even
        though the ranking was computed up to ``fallback_cache_ttl`` ago.
        The retrieval side effects (reinforcement, miss accounting, rival
        suppression) still run so repeated generic queries keep the same
        learning behaviour as an uncached recall.
        """
        scored_payload = payload["scored"]
        item_ids = [entry[2] for entry in scored_payload]
        items = {
            item.id: item for item in self.backend.get_many(item_ids)
        }
        if any(item_id not in items for item_id in item_ids):
            return None
        scored = [
            (
                score,
                overlap,
                items[item_id],
                list(reasons),
                matched,
            )
            for score, overlap, item_id, reasons, matched in scored_payload
        ]
        results = [
            RecallResult(item=entry[2], score=entry[0], reasons=entry[3])
            for entry in scored
        ]
        for result, flag in zip(results, payload["confident"]):
            result.confident = flag
        if reinforce:
            updated_items: list[MemoryItem] = []
            for score, overlap, item, _, matched in scored:
                if not matched:
                    continue
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
                updated_items.append(item)
            if updated_items:
                # Best-effort reinforcement: the write happens on a
                # background worker so a cached hit can return without
                # waiting on SQLite I/O; engine.close() drains the queue.
                self.enqueue_reinforce(updated_items)
            self._record_misses(scored, top_k, now)
            # Note: _record_misses only inspects scored[:top_k], and the
            # cached payload is exactly the top-k slice, so the side effect
            # is identical to the uncached path.
            if suppression_factor > 0:
                matched_items = [
                    item
                    for _, _, item, _, matched in scored
                    if matched
                ]
                # Cached fallback results come only from zero-hit queries,
                # which must not trigger wide retrieval-induced forgetting.
                self._suppress_linked_rivals(
                    matched_items,
                    suppression_factor,
                    suppression_min_cues,
                    suppression_floor,
                    query_terms,
                    fallback_mode=True,
                )
        return results

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
