"""Mnemosis public facade."""

from __future__ import annotations

from collections import deque
from datetime import datetime

from .association import AssociationIndex
from .backend import Backend, make_backend
from .consolidation import ConsolidationReport, Consolidator
from .dual_track import DualTrackStore
from .embedding import Embedder
from .forgetting import ForgettingCurve, ReviewScheduler
from .importance import ImportanceScorer
from .metacognition import ConfidenceLabel, Metacognition, MetacognitiveCheck
from .recycle import RecycleBin
from .schema import EventChainIndex
from .types import (
    MemoryItem,
    MemoryKind,
    MemoryStatus,
    RecallResult,
    SourceRecord,
    SourceType,
    extract_cues,
    hash_content,
    normalize_cues,
    utcnow,
)


class MemoryEngine:
    """The one thing most users touch.

    ```python
    engine = MemoryEngine("memory.db")   # persistent
    engine = MemoryEngine()              # in-memory
    engine.remember(...)
    engine.recall(...)
    engine.sleep()
    engine.check(...)
    ```
    """

    def __init__(
        self,
        memory_file: str | None = None,
        *,
        decay_rate: float = 0.002,
        base_interval_hours: float = 24.0,
        importance_scorer: ImportanceScorer | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        self.backend: Backend = make_backend(memory_file)
        self.curve = ForgettingCurve(decay_rate)
        self.scheduler = ReviewScheduler(self.curve, base_interval_hours)
        self.scorer = importance_scorer or ImportanceScorer()
        self.embedder = embedder
        self.store = DualTrackStore(self.backend, self.curve, self.scorer)
        self.associations = AssociationIndex(self.backend)
        self.event_chain = EventChainIndex(self.backend)
        self.consolidator = Consolidator(self.store, self.backend)
        self.meta = Metacognition(self.store, self.curve, self.consolidator)
        self.recycle = RecycleBin(self.backend)
        self._recall_log: deque[dict] = deque(maxlen=100)
        self._intents: dict[str, dict] = {}
        self._suppressed_ids: dict[str, str] = {}

    # -- wake cycle ---------------------------------------------------------

    @staticmethod
    def _extract_context(content: str) -> str | None:
        """Auto-tag the situational context of a memory (round 71).

        Context-dependent memory (Godden & Baddeley, 1975): where something
        happened is a powerful retrieval cue. Patterns like "在会议室里"
        / "在公司" / "去家里" are extracted so later fuzzy-context recall
        can use them without the caller tagging every memory by hand.
        """
        import re

        match = re.search(
            r"(?:在|去|到)([\u4e00-\u9fff]{2,6}?)"
            r"(?:里|中|上|内|旁边)?",
            content,
        )
        if not match:
            return None
        candidate = match.group(1)
        if len(candidate) == 2:
            following = content[match.end():match.end() + 1]
            if following in "室馆店站楼场院厅":
                candidate += following
        if candidate in (
            "这里", "那里", "这时", "当时", "今天", "昨天", "明天",
            "现在", "这", "那", "现场", "家里家外",
        ):
            return None
        return candidate

    def remember(
        self,
        content: str,
        *,
        kind: MemoryKind = MemoryKind.EPISODIC,
        source: SourceRecord | None = None,
        cues: list[str] | None = None,
        importance: float | None = None,
        confidence: float = 1.0,
        strength: float = 1.0,
        created_at: datetime | None = None,
        context: str | None = None,
        affect: str | None = None,
        evidence_count: int = 1,
        storage_strength: float = 1.0,
        auto_cues: bool = True,
        auto_context: bool = True,
    ) -> MemoryItem:
        source = source or SourceRecord(origin=SourceType.USER)
        if auto_context and context is None:
            context = self._extract_context(content)
        if auto_cues:
            cues = normalize_cues(list(cues or []) + extract_cues(content))
        item = self.store.remember(
            content,
            kind,
            source,
            cues=cues,
            importance=importance,
            confidence=confidence,
            strength=strength,
            created_at=created_at,
            context=context,
            affect=affect,
            evidence_count=evidence_count,
            storage_strength=storage_strength,
        )
        self.associations.index(item)
        self.associations.link_related(item)
        if item.kind is MemoryKind.EPISODIC:
            self.event_chain.invalidate()
        return item

    def update(
        self,
        memory_id: str,
        *,
        content: str | None = None,
        importance: float | None = None,
        confidence: float | None = None,
        cues: list[str] | None = None,
        now: datetime | None = None,
    ) -> MemoryItem | None:
        """Revise a memory (reconsolidation: Nader et al., 2000).

        The retrieved trace is made labile: content changes destabilize
        confidence/strength, the revision is recorded, and the memory
        re-stabilizes through future access.
        """
        item = self.backend.get(memory_id)
        if item is None:
            return None
        now = now or utcnow()
        if content is not None and content.strip() and content != item.content:
            new_hash = hash_content(content)
            if item.kind is MemoryKind.SEMANTIC:
                duplicate = self.backend.find_by_hash(MemoryKind.SEMANTIC, new_hash)
                if duplicate is not None and duplicate.id != item.id:
                    raise ValueError("update would create a semantic duplicate")
            item.content = content
            item.content_hash = new_hash
            item.revision_count += 1
            item.updated_at = now
            item.confidence = (item.confidence + 0.4) / 2.0
            item.strength = max(0.3, item.strength * 0.8)
        if importance is not None:
            item.importance = max(0.0, min(1.0, importance))
        if confidence is not None:
            item.confidence = max(0.0, min(1.0, confidence))
        if cues is not None:
            item.cues = normalize_cues(cues)
            self.backend.add_cues(item.id, item.cues)
        self.backend.update(item)
        return item

    def recall(
        self,
        query: str,
        *,
        kind: MemoryKind | None = None,
        top_k: int = 5,
        now: datetime | None = None,
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
        temporal_boost: float = 1.0,
        temporal_reason: bool = True,
        reasoning_pack: bool = True,
        zh_synonyms: bool = True,
        pattern_completion: bool = True,
        separation: bool = True,
        kind_preference: bool = True,
        exclude_ids: set[str] | None = None,
    ) -> list[RecallResult]:
        embedder = embedder or self.embedder
        exclude_ids = set(exclude_ids or ()) | set(self._suppressed_ids)
        results = self.store.recall(
            query,
            kind=kind,
            top_k=top_k,
            now=now,
            context=context,
            context_boost=context_boost,
            elaborate_links=elaborate_links,
            self_reference_boost=self_reference_boost,
            source_trust_boost=source_trust_boost,
            source_trust_weight=source_trust_weight,
            mood_congruent_boost=mood_congruent_boost,
            mood_boost_weight=mood_boost_weight,
            confidence_boost=confidence_boost,
            confidence_weight=confidence_weight,
            gist_preference=gist_preference,
            gist_boost=gist_boost,
            emotional_salience_boost=emotional_salience_boost,
            emotional_salience_weight=emotional_salience_weight,
            second_look=second_look,
            conflict_flag=conflict_flag,
            corroboration_boost=corroboration_boost,
            corroboration_weight=corroboration_weight,
            revision_flag=revision_flag,
            decay_flag=decay_flag,
            suppression_factor=suppression_factor,
            suppression_min_cues=suppression_min_cues,
            suppression_floor=suppression_floor,
            embedder=embedder,
            expansion_discount=expansion_discount,
            event_chain=self.event_chain,
            temporal_boost=temporal_boost,
            temporal_reason=temporal_reason,
            reasoning_pack=reasoning_pack,
            zh_synonyms=zh_synonyms,
            pattern_completion=pattern_completion,
            separation=separation,
            kind_preference=kind_preference,
            exclude_ids=exclude_ids,
        )
        self._recall_log.append(
            {
                "query": query,
                "top_id": results[0].item.id if results else None,
                "top_preview": (
                    results[0].item.content[:40] if results else None
                ),
                "confident": results[0].confident if results else None,
                "ts": utcnow().isoformat(),
            }
        )
        return results

    def get_recall_log(self, limit: int = 50) -> list[dict]:
        """Return the most recent recall entries (bounded audit log)."""
        return list(self._recall_log)[-max(1, int(limit)):]

    def search_batch(
        self,
        queries: list[str],
        *,
        top_k: int = 3,
        kind: MemoryKind | None = None,
        now: datetime | None = None,
    ) -> list[dict]:
        """Run several recall queries in one call.

        Returns one result group per query in the input order, so agents
        can fan out a whole question list through a single MCP round trip
        (working-memory chunking; Miller, 1956).
        """
        out: list[dict] = []
        for query in queries:
            results = self.recall(
                query, kind=kind, top_k=top_k, now=now
            )
            out.append(
                {
                    "query": query,
                    "count": len(results),
                    "results": [
                        {
                            "id": r.item.id,
                            "preview": r.item.content[:40],
                            "score": round(r.score, 4),
                            "confident": r.confident,
                        }
                        for r in results
                    ],
                }
            )
        return out

    def remember_intent(
        self,
        content: str,
        due_at: datetime,
        *,
        context_cue: str | None = None,
        importance: float = 0.5,
        now: datetime | None = None,
    ) -> dict:
        """Register a future intention (prospective memory).

        Prospective memory is the capacity to remember to carry out an
        intended action at the right later moment (Einstein & McDaniel,
        1990): the intent stays in a small register with its deadline and
        optional context cue, and surfaces when due instead of being
        reinforced like a past fact.
        """
        import uuid

        now = now or utcnow()
        record = {
            "id": uuid.uuid4().hex,
            "content": content.strip(),
            "due_at": due_at.isoformat(),
            "context_cue": (context_cue or "").strip() or None,
            "importance": max(0.0, min(1.0, float(importance))),
            "created_at": now.isoformat(),
            "status": "active",
            "completed_at": None,
        }
        self._intents[record["id"]] = record
        return dict(record)

    def intent_due(
        self,
        now: datetime | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Return active intents whose deadline has arrived."""
        from datetime import datetime as _dt

        now = now or utcnow()
        due = [
            r for r in self._intents.values()
            if r["status"] == "active"
            and _dt.fromisoformat(r["due_at"]) <= now
        ]
        due.sort(key=lambda r: r["due_at"])
        return [dict(r) for r in due[: max(1, int(limit))]]

    def complete_intent(
        self,
        intent_id: str,
        now: datetime | None = None,
    ) -> dict | None:
        """Mark an intent as completed."""
        now = now or utcnow()
        record = self._intents.get(intent_id)
        if record is None or record["status"] != "active":
            return None
        record["status"] = "completed"
        record["completed_at"] = now.isoformat()
        return dict(record)

    def cancel_intent(self, intent_id: str) -> dict | None:
        """Cancel an intent without completing it."""
        record = self._intents.get(intent_id)
        if record is None or record["status"] != "active":
            return None
        record["status"] = "cancelled"
        return dict(record)

    def intent_report(self, now: datetime | None = None) -> dict:
        """Summarize the intention register (due / upcoming / done)."""
        from datetime import datetime as _dt

        now = now or utcnow()
        active = [
            r for r in self._intents.values() if r["status"] == "active"
        ]
        overdue = [
            r for r in active if _dt.fromisoformat(r["due_at"]) <= now
        ]
        upcoming = [
            r for r in active if _dt.fromisoformat(r["due_at"]) > now
        ]
        upcoming.sort(key=lambda r: r["due_at"])
        return {
            "active": len(active),
            "completed": sum(
                1 for r in self._intents.values()
                if r["status"] == "completed"
            ),
            "cancelled": sum(
                1 for r in self._intents.values()
                if r["status"] == "cancelled"
            ),
            "overdue": len(overdue),
            "next_upcoming": (
                dict(upcoming[0]) if upcoming else None
            ),
        }

    def intent_conflicts(
        self,
        time_window_minutes: int = 60,
    ) -> dict:
        """Detect intention clashes (time or context collisions).

        Prospective memory must schedule actions without collisions: two
        intentions due within a short window (Einstein & McDaniel, 1990)
        or sharing the same context cue risk one being forgotten. This
        tool reports both kinds so the agent can reschedule.
        """
        from datetime import datetime as _dt

        active = [
            r for r in self._intents.values() if r["status"] == "active"
        ]
        conflicts = []
        for i in range(len(active)):
            a = active[i]
            for b in active[i + 1:]:
                ta = _dt.fromisoformat(a["due_at"])
                tb = _dt.fromisoformat(b["due_at"])
                gap = abs((ta - tb).total_seconds()) / 60.0
                if gap < max(1, int(time_window_minutes)):
                    conflicts.append(
                        {
                            "type": "time",
                            "intent_a": a["id"],
                            "intent_b": b["id"],
                            "gap_minutes": round(gap, 1),
                        }
                    )
                if (
                    a.get("context_cue")
                    and a["context_cue"] == b.get("context_cue")
                ):
                    conflicts.append(
                        {
                            "type": "context",
                            "intent_a": a["id"],
                            "intent_b": b["id"],
                            "cue": a["context_cue"],
                }
            )
        return {"total": len(conflicts), "conflicts": conflicts}

    def memory_health(self) -> dict:
        """Return one overall memory-health score with sub-metrics.

        Metacognitive monitoring (Koriat & Goldsmith, 1996): a memory
        system should know how healthy it is. This aggregates existing
        read-only signals - linked ratio, crowded cues, conflicts,
        overdue/clashing intentions and suppressed memories - into a
        0-100 score with itemized penalties.
        """
        active = self.store.all_active()
        memory_count = len(active)
        assoc = self.association_report(limit=5)
        connected = assoc["connected_count"]
        linked_ratio = (
            round(connected / memory_count, 3) if memory_count else 0.0
        )
        crowded = len(
            self.interference_report(shared_cue_min=3)["crowded_clusters"]
        )
        conflicts = len(self.consolidator.detect_conflicts())
        intents = self.intent_report()
        clashes = self.intent_conflicts()["total"]
        suppressed = self.suppressed_report()["count"]
        penalties = {
            "isolated": min(
                20, int(round((1.0 - linked_ratio) * 50))
            ),
            "crowded": min(15, crowded * 3),
            "conflicts": min(20, conflicts * 4),
            "overdue_intents": min(10, intents["overdue"] * 2),
            "intent_clashes": min(10, clashes * 3),
            "suppressed": min(5, suppressed),
        }
        score = max(0, 100 - sum(penalties.values()))
        return {
            "score": score,
            "memory_count": memory_count,
            "linked_ratio": linked_ratio,
            "crowded_clusters": crowded,
            "conflicts": conflicts,
            "overdue_intents": intents["overdue"],
            "intent_clashes": clashes,
            "suppressed_count": suppressed,
            "penalties": penalties,
        }

    def kg_export(self) -> dict:
        """Export the memory network as a knowledge-graph edge list.

        Semantic-network organization (Collins & Quillian, 1969): related
        facts form a graph. This returns nodes and deduplicated undirected
        edges so external tools can visualize or analyze the store.
        """
        items = {
            item.id: item for item in self.store.all_active()
        }
        nodes = [
            {
                "id": item.id,
                "label": item.content[:24],
                "kind": item.kind.value,
            }
            for item in items.values()
        ]
        edges = []
        seen: set[frozenset[str]] = set()
        for src, dst, weight in self.backend.all_links():
            if src not in items or dst not in items:
                continue
            pair = frozenset((src, dst))
            if pair in seen:
                continue
            seen.add(pair)
            edges.append(
                {
                    "source": src,
                    "target": dst,
                    "weight": round(float(weight), 3),
                }
            )
        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def learner_profile(self, now: datetime | None = None) -> dict:
        """Estimate the learner's rate from review history.

        Adaptive spaced repetition estimates learning rate from observed
        retrieval success (Mozer et al., 2009): fast learners get longer
        intervals, struggling ones get shorter ones. This reports the
        estimated profile and a suggested interval scale.
        """
        items = self.store.all_active()
        total_reviews = 0
        successes = 0
        retrievability_sum = 0.0
        importance_sum = 0.0
        for item in items:
            total_reviews += (
                item.retrieval_successes + item.retrieval_failures
            )
            successes += item.retrieval_successes
            retrievability_sum += self.curve.retrievability(item, now)
            importance_sum += item.importance
        n = len(items)
        success_rate = (
            successes / total_reviews if total_reviews else None
        )
        if n == 0 or success_rate is None:
            profile = "unknown"
            scale = 1.0
        elif success_rate >= 0.8:
            profile = "fast"
            scale = 1.2
        elif success_rate >= 0.6:
            profile = "steady"
            scale = 1.0
        else:
            profile = "struggling"
            scale = 0.8
        return {
            "total_memories": n,
            "total_reviews": total_reviews,
            "success_rate": (
                round(success_rate, 3) if success_rate is not None else None
            ),
            "avg_retrievability": round(
                retrievability_sum / max(1, n), 3
            ),
            "avg_importance": round(importance_sum / max(1, n), 3),
            "profile": profile,
            "suggested_interval_scale": scale,
        }

    def context_pack(
        self,
        queries: list[str],
        *,
        top_k: int = 3,
        max_chars: int = 1200,
        now: datetime | None = None,
    ) -> dict:
        """Pack the best matching memories into a bounded context.

        Working memory is limited; cognitive-load theory (Sweller, 1988)
        says only the essential information should reach the model. This
        runs recall for several queries, deduplicates by id, ranks by
        score and returns as much as fits the character budget.
        """
        best: dict[str, tuple[float, str]] = {}
        found = 0
        for query in queries:
            for result in self.recall(query, top_k=top_k, now=now):
                if not any(
                    "overlap" in r or "semantic" in r
                    for r in result.reasons
                ):
                    continue
                found += 1
                item = result.item
                current = best.get(item.id)
                if current is None or result.score > current[0]:
                    best[item.id] = (
                        result.score, item.content
                    )
        ranked = sorted(
            best.items(), key=lambda kv: kv[1][0], reverse=True
        )
        packed = []
        used = 0
        truncated = 0
        for memory_id, (score, content) in ranked:
            if used + len(content) > max(1, int(max_chars)) and packed:
                truncated += 1
                continue
            packed.append(
                {
                    "id": memory_id,
                    "content": content,
                    "score": round(score, 3),
                }
            )
            used += len(content)
        return {
            "query_count": len(queries),
            "total_found": found,
            "unique_found": len(best),
            "packed_count": len(packed),
            "packed_chars": used,
            "truncated_count": truncated,
            "packed": packed,
        }

    def encoding_quality(self, memory_id: str) -> dict | None:
        """Score how well one memory was encoded.

        Elaborative encoding (Craik & Tulving, 1975): deeper encoding
        (more cues, context, emotion, importance) makes a memory more
        retrievable. This scores 0-100 and suggests what is missing.
        """
        item = self.backend.get(memory_id)
        if item is None:
            return None
        cue_count = len(item.cues)
        has_context = bool(item.context)
        has_affect = bool(item.affect)
        content_length = len(item.content)
        score = 0.0
        suggestions = []
        if cue_count >= 2:
            score += 25
        elif cue_count == 1:
            score += 15
            suggestions.append("再补 1 个线索（日期/对象/主题）")
        else:
            suggestions.append("没有线索，先加 2 个检索线索")
        if has_context:
            score += 20
        else:
            suggestions.append("缺少情景上下文，补一句当时的环境")
        if has_affect:
            score += 10
        if item.importance >= 0.6:
            score += 15
        elif item.importance >= 0.3:
            score += 10
            suggestions.append("重要度偏低，确认是否值得长期保留")
        if item.strength >= 0.5:
            score += 15
        else:
            suggestions.append("记忆强度偏低，建议尽快复习一次")
        if 10 <= content_length <= 200:
            score += 15
        elif content_length > 200:
            score += 8
            suggestions.append("内容偏长，考虑拆成几条")
        else:
            score += 5
            suggestions.append("内容太短，补充一点细节")
        score = min(100, int(round(score)))
        if score >= 80:
            verdict = "well_encoded"
        elif score >= 60:
            verdict = "adequate"
        else:
            verdict = "weak"
        return {
            "memory_id": memory_id,
            "score": score,
            "verdict": verdict,
            "cue_count": cue_count,
            "has_context": has_context,
            "has_affect": has_affect,
            "importance": round(item.importance, 3),
            "strength": round(item.strength, 3),
            "content_length": content_length,
            "suggestions": suggestions[:4],
        }

    def explain_memory(
        self,
        memory_id: str,
        now: datetime | None = None,
    ) -> dict | None:
        """Explain one memory's full state in plain fields.

        Metacognitive monitoring (Koriat & Goldsmith, 1996): an agent
        should be able to say why a memory exists and how reachable it
        is. This returns content, cues, retrievability, importance,
        strength, confidence, evidence, links, suppression, access and
        review state.
        """
        item = self.backend.get(memory_id)
        if item is None:
            return None
        linked_count = sum(
            1
            for src, dst, _weight in self.backend.all_links()
            if src == memory_id or dst == memory_id
        )
        return {
            "memory_id": memory_id,
            "content": item.content,
            "kind": item.kind.value,
            "created_at": item.created_at.isoformat(),
            "cues": item.cues,
            "retrievability": round(
                self.curve.retrievability(item, now), 3
            ),
            "importance": round(item.importance, 3),
            "strength": round(item.strength, 3),
            "confidence": round(item.confidence, 3),
            "evidence_count": item.evidence_count,
            "linked_count": linked_count,
            "suppressed": memory_id in self._suppressed_ids,
            "access_count": item.access_count,
            "last_access_at": (
                item.last_access_at.isoformat()
                if item.last_access_at is not None
                else None
            ),
            "review_streak": item.review_streak,
            "last_review_at": (
                item.last_review_at.isoformat()
                if item.last_review_at is not None
                else None
            ),
        }

    def compare_memories(self, id_a: str, id_b: str) -> dict | None:
        """Compare two memories: overlap, differences and verdict.

        Source monitoring and schema integration (Johnson, Hashtroudi &
        Lindsay, 1993): agents holding two records of the same event must
        know whether they duplicate, conflict or are simply distinct. This
        reports token overlap, shared cues and a verdict.
        """
        from .types import tokenize

        a = self.backend.get(id_a)
        b = self.backend.get(id_b)
        if a is None or b is None:
            return None
        a_terms = set(tokenize(a.content))
        b_terms = set(tokenize(b.content))
        common_terms = sorted(a_terms & b_terms)
        overlap = (
            len(common_terms) / max(1, min(len(a_terms), len(b_terms)))
            if a_terms and b_terms
            else 0.0
        )
        shared_cues = sorted(set(a.cues) & set(b.cues))
        if overlap >= 0.6:
            verdict = "duplicate"
        elif shared_cues and a.content != b.content:
            verdict = "conflict"
        else:
            verdict = "distinct"
        return {
            "a": {
                "id": a.id,
                "preview": a.content[:40],
                "kind": a.kind.value,
                "importance": round(a.importance, 3),
                "confidence": round(a.confidence, 3),
                "evidence_count": a.evidence_count,
                "created_at": a.created_at.isoformat(),
            },
            "b": {
                "id": b.id,
                "preview": b.content[:40],
                "kind": b.kind.value,
                "importance": round(b.importance, 3),
                "confidence": round(b.confidence, 3),
                "evidence_count": b.evidence_count,
                "created_at": b.created_at.isoformat(),
            },
            "overlap": round(overlap, 3),
            "common_terms": common_terms[:5],
            "shared_cues": shared_cues[:5],
            "verdict": verdict,
        }

    def action_queue(
        self,
        now: datetime | None = None,
        limit: int = 20,
    ) -> dict:
        """Order active intentions as an action queue.

        Goal-directed behavior prioritizes urgent tasks (ACT-R, Anderson,
        1983): overdue first, then upcoming by deadline, with clashing
        intentions flagged for rescheduling.
        """
        from datetime import datetime as _dt, timedelta

        now = now or utcnow()
        conflicts = self.intent_conflicts()["conflicts"]
        clash_ids = {
            c["intent_a"] for c in conflicts
        } | {c["intent_b"] for c in conflicts}
        actions = []
        for record in self._intents.values():
            if record["status"] != "active":
                continue
            due = _dt.fromisoformat(record["due_at"])
            actions.append(
                {
                    "type": "intent",
                    "intent_id": record["id"],
                    "content": record["content"][:60],
                    "due_at": record["due_at"],
                    "overdue": due <= now,
                    "urgent": due <= now + timedelta(minutes=60),
                    "clash": record["id"] in clash_ids,
                }
            )
        actions.sort(key=lambda a: (not a["overdue"], a["due_at"]))
        return {
            "total": len(actions),
            "overdue": sum(1 for a in actions if a["overdue"]),
            "upcoming": sum(1 for a in actions if not a["overdue"]),
            "clashes": len(clash_ids),
            "actions": actions[: max(1, int(limit))],
        }

    def summarize_cluster(
        self,
        memory_ids: list[str],
    ) -> dict | None:
        """Summarize a cluster of related memories as one gist.

        Fuzzy-trace theory (Brainerd & Reyna, 1990): people keep the gist
        of repeated related experiences rather than every verbatim
        detail. This extracts shared cues, frequent terms and evidence
        counts into a compact summary an agent can use (or write back).
        """
        from collections import Counter
        from .types import tokenize

        items = []
        for memory_id in memory_ids:
            item = self.backend.get(memory_id)
            if item is not None:
                items.append(item)
        if not items:
            return None
        cue_sets = [set(item.cues) for item in items]
        common_cues = sorted(set.intersection(*cue_sets)) if cue_sets else []
        term_counter: Counter = Counter()
        for item in items:
            for term in tokenize(item.content):
                term_counter[term] += 1
        top_terms = [
            term for term, _count in term_counter.most_common(6)
        ]
        total_chars = sum(len(item.content) for item in items)
        evidence = sum(item.evidence_count for item in items)
        previews = [item.content[:24] for item in items[:4]]
        summary = (
            f"共 {len(items)} 条记忆，共享线索："
            + ("、".join(common_cues) if common_cues else "无")
            + f"；高频词：{'、'.join(top_terms) if top_terms else '无'}；"
            + f"累计证据 {evidence} 次"
        )
        return {
            "memory_ids": [item.id for item in items],
            "summary": summary,
            "common_cues": common_cues,
            "top_terms": top_terms,
            "evidence_count": evidence,
            "total_chars": total_chars,
            "previews": previews,
        }

    def multi_hop_report(
        self,
        start_id: str,
        depth: int = 2,
        limit: int = 20,
    ) -> dict | None:
        """Walk the association network hop by hop from a start memory.

        Spreading activation (Collins & Loftus, 1975): related memories
        become reachable through their links, hop by hop. This BFS report
        shows which memories appear at each distance, so agents can gather
        multi-hop evidence for reasoning.
        """
        from collections import defaultdict

        if self.backend.get(start_id) is None:
            return None
        adj: dict[str, set[str]] = defaultdict(set)
        for src, dst, _weight in self.backend.all_links():
            adj[src].add(dst)
            adj[dst].add(src)
        frontier = {start_id}
        seen = {start_id}
        hops = []
        for hop in range(1, max(1, int(depth)) + 1):
            next_frontier: set[str] = set()
            for node in frontier:
                next_frontier |= adj.get(node, set())
            next_frontier -= seen
            if not next_frontier:
                break
            seen |= next_frontier
            hops.append(
                {
                    "hop": hop,
                    "memory_ids": sorted(next_frontier)[: max(1, int(limit))],
                    "count": len(next_frontier),
                }
            )
            frontier = next_frontier
        return {
            "start_id": start_id,
            "depth": max(1, int(depth)),
            "hops": hops,
            "total_reached": len(seen) - 1,
            "reached_ids": sorted(seen - {start_id})[: max(1, int(limit))],
        }

    def cramming_plan(
        self,
        target_at: datetime,
        hours_available: float = 6.0,
        session_minutes: int = 30,
        limit: int = 20,
    ) -> dict:
        """Plan a last-minute review schedule before a deadline.

        Even with little time, spacing beats massing (Cepeda et al.,
        2006): the available hours are split into short sessions and the
        most at-risk important memories are reviewed first.
        """
        from datetime import timedelta

        scored = []
        for item in self.store.all_active():
            need = item.importance * (
                1.0 - self.curve.retrievability(item, target_at)
            )
            scored.append((need, item))
        scored.sort(key=lambda pair: -pair[0])
        picked = scored[: max(1, int(limit))]
        n_sessions = max(
            1,
            int(float(hours_available) * 60 // max(1, int(session_minutes))),
        )
        per_session = len(picked) // n_sessions
        extra = len(picked) % n_sessions
        sessions = []
        for i in range(n_sessions):
            start = i * per_session + min(i, extra)
            size = per_session + (1 if i < extra else 0)
            chunk = picked[start:start + size]
            if not chunk:
                break
            start = target_at - timedelta(
                minutes=max(1, int(session_minutes)) * (n_sessions - i)
            )
            sessions.append(
                {
                    "start_at": start.isoformat(),
                    "duration_minutes": max(1, int(session_minutes)),
                    "memory_ids": [item.id for _need, item in chunk],
                    "count": len(chunk),
                }
            )
        return {
            "target_at": target_at.isoformat(),
            "hours_available": round(float(hours_available), 2),
            "sessions": sessions,
            "total_memories": len(picked),
        }

    def session_summary(
        self,
        memory_ids: list[str],
        compare_limit: int = 20,
    ) -> dict | None:
        """Summarize one work session's memories into facts/events/issues.

        Post-session consolidation integrates new traces into knowledge:
        this splits the memories into semantic facts and episodic events,
        then flags conflict and duplicate pairs so the agent can resolve
        them before moving on.
        """
        from itertools import combinations

        items = []
        for memory_id in memory_ids:
            item = self.backend.get(memory_id)
            if item is not None:
                items.append(item)
        if not items:
            return None
        facts = [
            {"id": item.id, "preview": item.content[:40]}
            for item in items if item.kind is MemoryKind.SEMANTIC
        ]
        events = [
            {"id": item.id, "preview": item.content[:40]}
            for item in items if item.kind is MemoryKind.EPISODIC
        ]
        conflicts = []
        duplicates = []
        compare_items = items[: max(2, int(compare_limit))]
        for a, b in combinations(compare_items, 2):
            verdict = self.compare_memories(a.id, b.id)["verdict"]
            if verdict == "conflict" and len(conflicts) < 5:
                conflicts.append(
                    {"id_a": a.id, "id_b": b.id,
                     "a_preview": a.content[:24],
                     "b_preview": b.content[:24]}
                )
            elif verdict == "duplicate" and len(duplicates) < 5:
                duplicates.append(
                    {"id_a": a.id, "id_b": b.id,
                     "a_preview": a.content[:24],
                     "b_preview": b.content[:24]}
                )
        summary = (
            f"共 {len(items)} 条记忆：事实 {len(facts)} 条、"
            f"事件 {len(events)} 条、冲突 {len(conflicts)} 对、"
            f"重复 {len(duplicates)} 对"
        )
        return {
            "total": len(items),
            "facts": facts,
            "events": events,
            "conflicts": conflicts,
            "duplicates": duplicates,
            "summary": summary,
        }

    def retrieval_assist(
        self,
        query: str,
        *,
        limit: int = 8,
        now: datetime | None = None,
    ) -> dict:
        """Suggest alternative retrieval cues when a query stalls.

        Encoding specificity (Tulving & Thomson, 1973) and
        transfer-appropriate processing (Morris, Bransford & Franks,
        1977): a memory is reachable through the cues present at encoding,
        so rephrasing the question with the stored cue words recovers
        traces the original query misses. This tool mines existing cues
        and content terms that overlap the (synonym-expanded) query and
        returns them as concrete follow-up queries.
        """
        from .types import tokenize
        from .zh_nlp import expand_synonyms, has_cjk

        q_terms = set(tokenize(query))
        expanded = (
            expand_synonyms(q_terms) if has_cjk(query) else set(q_terms)
        )
        new_synonyms = sorted(expanded - q_terms)
        cue_counts: dict[str, int] = {}
        content_counts: dict[str, int] = {}
        for item in self.store.all_active():
            best_cue = 0
            for cue in item.cues:
                common = len(expanded & set(tokenize(cue)))
                if common > best_cue:
                    best_cue = common
            if best_cue and item.cues:
                cue_counts[item.cues[0]] = max(
                    cue_counts.get(item.cues[0], 0), best_cue
                )
            common = len(expanded & set(tokenize(item.content)))
            if common:
                for cue in item.cues[:3] or [item.content[:12]]:
                    content_counts[cue] = max(
                        content_counts.get(cue, 0), common
                    )
        suggestions: list[dict] = []
        for cue, count in sorted(
            cue_counts.items(), key=lambda kv: (-kv[1], kv[0])
        ):
            suggestions.append(
                {"cue": cue, "source": "cue", "matched_count": count}
            )
        for cue, count in sorted(
            content_counts.items(), key=lambda kv: (-kv[1], kv[0])
        ):
            if not any(s["cue"] == cue for s in suggestions):
                suggestions.append(
                    {"cue": cue, "source": "content", "matched_count": count}
                )
        suggestions = suggestions[: max(1, int(limit))]
        recall = self.recall(query, top_k=3, now=now)
        return {
            "query": query,
            "expanded_terms": sorted(expanded),
            "new_synonyms": new_synonyms,
            "suggestions": suggestions,
            "top_recall": [
                {
                    "id": r.item.id,
                    "preview": r.item.content[:40],
                    "score": round(r.score, 3),
                    "confident": r.confident,
                }
                for r in recall
            ],
        }

    def schema_report(self, limit: int = 20) -> dict:
        """Group memories into topic schemas by their primary cue.

        Schema theory (Bartlett, 1932; event schemas, Gilboa & Marlatte,
        2017): the mind organizes related experiences under shared
        scripts/topics. This report clusters active memories by their
        primary cue and shows each cluster's size, average importance,
        kind mix and content samples, so agents can see what topics their
        memory store actually covers.
        """
        groups: dict[str, dict] = {}
        for item in self.store.all_active():
            topic = item.cues[0] if item.cues else "（无标签）"
            group = groups.setdefault(
                topic,
                {
                    "topic": topic,
                    "memory_count": 0,
                    "avg_importance": 0.0,
                    "kinds": {"semantic": 0, "episodic": 0},
                    "samples": [],
                },
            )
            group["memory_count"] += 1
            group["avg_importance"] += item.importance
            group["kinds"][item.kind.value] += 1
            if len(group["samples"]) < 3:
                group["samples"].append(item.content[:24])
        out = []
        for group in groups.values():
            group["avg_importance"] = round(
                group["avg_importance"] / group["memory_count"], 3
            )
            out.append(group)
        out.sort(key=lambda g: (-g["memory_count"], g["topic"]))
        return {
            "total_memories": len(self.store.all_active()),
            "group_count": len(out),
            "top_groups": out[: max(1, int(limit))],
        }

    def suppress_memories(
        self,
        memory_ids: list[str],
        now: datetime | None = None,
    ) -> dict:
        """Temporarily suppress memories from retrieval (directed
        forgetting; Anderson & Green, 2001).

        Unlike deletion, suppression keeps the trace intact but blocks it
        from recall - the agent can deliberately stop being reminded of
        something, then unsuppress it later.
        """
        now = now or utcnow()
        suppressed = 0
        for memory_id in memory_ids:
            if self.backend.get(memory_id) is None:
                continue
            if memory_id not in self._suppressed_ids:
                self._suppressed_ids[memory_id] = now.isoformat()
                suppressed += 1
        return {"suppressed": suppressed}

    def unsuppress_memories(self, memory_ids: list[str]) -> dict:
        """Restore suppressed memories to normal retrieval."""
        unsuppressed = 0
        for memory_id in memory_ids:
            if memory_id in self._suppressed_ids:
                del self._suppressed_ids[memory_id]
                unsuppressed += 1
        return {"unsuppressed": unsuppressed}

    def suppressed_report(self) -> dict:
        """List currently suppressed memories with their previews."""
        out = []
        for memory_id, suppressed_at in self._suppressed_ids.items():
            item = self.backend.get(memory_id)
            if item is None:
                continue
            out.append(
                {
                    "id": memory_id,
                    "preview": item.content[:40],
                    "suppressed_at": suppressed_at,
                }
            )
        out.sort(key=lambda r: r["suppressed_at"])
        return {"count": len(out), "memories": out}

    def timeline_report(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 200,
    ) -> dict:
        """Return an autobiographical timeline of episodic memories.

        Autobiographical memory is organized hierarchically by time
        (Conway & Pleydell-Pearce, 2000): life periods contain events,
        events contain details. This report lists episodic traces in
        chronological order grouped by day, optionally bounded by a
        start/end window.
        """
        items = [
            item
            for item in self.store.all_active(MemoryKind.EPISODIC)
            if item.status is MemoryStatus.ACTIVE
        ]
        items.sort(key=lambda item: item.created_at)
        if start is not None:
            items = [item for item in items if item.created_at >= start]
        if end is not None:
            items = [item for item in items if item.created_at < end]
        items = items[: max(1, int(limit))]
        days: dict[str, list[dict]] = {}
        for item in items:
            day = item.created_at.date().isoformat()
            days.setdefault(day, []).append(
                {
                    "id": item.id,
                    "preview": item.content[:40],
                    "kind": item.kind.value,
                    "importance": round(item.importance, 3),
                    "created_at": item.created_at.isoformat(),
                }
            )
        out = [
            {"date": day, "count": len(entries), "items": entries}
            for day, entries in sorted(days.items())
        ]
        return {
            "total": len(items),
            "days": out,
            "start_date": out[0]["date"] if out else None,
            "end_date": out[-1]["date"] if out else None,
        }

    def recognition_check(
        self,
        query: str,
        memory_id: str,
    ) -> dict:
        """Classify a memory hit as recollection vs familiarity.

        Dual-process theory (Yonelinas, 2002): recognition can rest on
        recollection (specific evidence recovered) or familiarity (a
        vague "I know it" without detail). This tool checks one candidate
        memory against a query and reports which process supports it.
        """
        from .types import tokenize

        item = self.backend.get(memory_id)
        if item is None:
            return {"memory_id": memory_id, "verdict": "missing"}
        results = self.recall(query, top_k=10)
        entry = next(
            (r for r in results if r.item.id == memory_id), None
        )
        q_terms = set(tokenize(query))
        item_terms = set(tokenize(item.content)) | set(item.cues)
        common = len(q_terms & item_terms)
        overlap = (
            common / max(1, min(len(q_terms), len(item_terms)))
            if q_terms and item_terms
            else 0.0
        )
        if entry is None:
            verdict = "unmatched"
            score = 0.0
            reasons = []
        else:
            score = entry.score
            reasons = entry.reasons
            evidence = any(
                "overlap" in r or "semantic" in r for r in reasons
            )
            if overlap >= 0.6:
                verdict = "recollection"
            elif overlap > 0 and evidence:
                verdict = "familiarity"
            else:
                verdict = "unmatched"
        return {
            "memory_id": memory_id,
            "verdict": verdict,
            "score": round(score, 3),
            "overlap": round(overlap, 3),
            "confidence": item.confidence,
            "reasons": reasons[:5],
        }

    def interference_report(
        self,
        shared_cue_min: int = 3,
        limit: int = 20,
    ) -> dict:
        """Report cue-crowded clusters that cause interference.

        Proactive interference (Wickens, 1972): when too many memories
        hang on the same cue, they compete and get confused. This tool
        finds cues with >= shared_cue_min active memories and suggests
        differentiating them with extra cues.
        """
        from collections import defaultdict
        from .types import tokenize

        cue_members: dict[str, list] = defaultdict(list)
        for item in self.store.all_active():
            for cue in item.cues:
                cue_members[cue].append(item)
        clusters = []
        for cue, members in cue_members.items():
            if len(members) < max(2, int(shared_cue_min)):
                continue
            total_overlap = 0.0
            pairs = 0
            for i in range(len(members)):
                a_terms = set(tokenize(members[i].content))
                for j in range(i + 1, len(members)):
                    b_terms = set(tokenize(members[j].content))
                    common = len(a_terms & b_terms)
                    denominator = max(
                        1, min(len(a_terms), len(b_terms))
                    )
                    total_overlap += common / denominator
                    pairs += 1
            avg_overlap = (
                round(total_overlap / pairs, 3) if pairs else 0.0
            )
            members.sort(key=lambda it: it.seq, reverse=True)
            clusters.append(
                {
                    "cue": cue,
                    "memory_count": len(members),
                    "avg_content_overlap": avg_overlap,
                    "members": [
                        {
                            "id": item.id,
                            "preview": item.content[:32],
                        }
                        for item in members[:5]
                    ],
                }
            )
        clusters.sort(
            key=lambda c: (-c["memory_count"], c["cue"])
        )
        clusters = clusters[: max(1, int(limit))]
        return {
            "total_cues": len(cue_members),
            "crowded_clusters": clusters,
            "suggestion": (
                "给同一线索下的记忆补上区别性线索（日期/对象/主题词），"
                "降低互相抢答"
            ),
        }

    def life_story(
        self,
        period_days: int = 30,
        limit: int = 20,
    ) -> dict:
        """Summarize the memory store as life periods.

        Autobiographical memory is organized into lifetime periods that
        contain events (Conway & Pleydell-Pearce, 2000). This tool groups
        episodic traces into time buckets (default 30 days) and reports
        each period's event count, top themes, average importance and
        highlights.
        """
        from collections import defaultdict
        from datetime import date, timedelta

        epoch = date(1970, 1, 1)
        items = [
            item
            for item in self.store.all_active(MemoryKind.EPISODIC)
            if item.status is MemoryStatus.ACTIVE
        ]
        items.sort(key=lambda item: item.created_at)
        buckets: dict[date, list] = defaultdict(list)
        for item in items:
            day = item.created_at.date()
            bucket = epoch + timedelta(
                days=(day - epoch).days // max(1, int(period_days))
                * max(1, int(period_days))
            )
            buckets[bucket].append(item)
        periods = []
        for bucket in sorted(buckets):
            members = buckets[bucket]
            theme_counts: dict[str, int] = defaultdict(int)
            importance_sum = 0.0
            for item in members:
                topic = item.cues[0] if item.cues else "（无标签）"
                theme_counts[topic] += 1
                importance_sum += item.importance
            highlights = sorted(
                members,
                key=lambda it: (it.importance, it.seq),
                reverse=True,
            )[:3]
            periods.append(
                {
                    "period_start": bucket.isoformat(),
                    "period_end": (
                        bucket + timedelta(days=max(1, int(period_days)) - 1)
                    ).isoformat(),
                    "event_count": len(members),
                    "top_themes": [
                        {"cue": cue, "count": count}
                        for cue, count in sorted(
                            theme_counts.items(),
                            key=lambda kv: (-kv[1], kv[0]),
                        )[:5]
                    ],
                    "avg_importance": round(
                        importance_sum / len(members), 3
                    ),
                    "highlights": [
                        {
                            "id": item.id,
                            "preview": item.content[:32],
                            "importance": round(item.importance, 3),
                        }
                        for item in highlights
                    ],
                }
            )
        periods = periods[: max(1, int(limit))]
        return {
            "period_days": max(1, int(period_days)),
            "total_events": len(items),
            "periods": periods,
        }

    def recall_reasoning(
        self,
        query: str,
        *,
        top_k: int | None = None,
        now: datetime | None = None,
    ) -> list[RecallResult]:
        """System-2 recall: assemble a reasoning premise pack.

        Fast keyword retrieval (System 1) plus a bounded boost for all
        same-dimension premises (math / compare / transitive questions), so
        the full premise set reaches the LLM context (Kahneman 2011;
        Miller & Cohen 2001).
        """
        from .reasoning import suggested_pack_size

        return self.recall(
            query,
            top_k=top_k or suggested_pack_size(query),
            now=now,
            reasoning_pack=True,
        )

    def recall_steps(
        self,
        query: str,
        *,
        top_k: int = 10,
        now: datetime | None = None,
        zh_synonyms: bool = True,
        plan_reuse: bool = True,
    ) -> list[RecallResult]:
        """Chain-of-thought step retrieval for process questions.

        "怎么 / 如何 / 为什么" questions need the ordered intermediate
        steps, not a keyword soup: mental time travel (Tulving, 1985) and
        event schemas (Gilboa & Marlatte, 2017) organize episodes into a
        chronological script, and chain-of-thought reasoning (Wei et al.,
        2022) consumes those steps in order. Episodic results are sorted by
        event date; non-process questions behave exactly like
        ``recall_reasoning``.
        """
        import re

        from .types import MemoryKind

        results = self.recall(
            query,
            top_k=max(top_k * 2, 16),
            now=now,
            reasoning_pack=True,
            zh_synonyms=zh_synonyms,
        )
        if not any(marker in query for marker in (
            "怎么", "如何", "为什么", "过程", "步骤", "准备", "计划", "安排",
            "第一步", "该做什么", "怎么做", "流程", "方法", "办法", "方式",
            "想", "要", "打算", "希望",
            "how", "why", "step",
        )):
            return results[:top_k]

        def _event_date(result) -> str:
            content = result.item.content
            match = re.search(r"\d{4}-\d{2}-\d{2}", content)
            if match:
                return match.group(0)
            match = re.search(
                r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
                content,
            )
            if match:
                return (
                    f"{int(match.group(1)):04d}-"
                    f"{int(match.group(2)):02d}-"
                    f"{int(match.group(3)):02d}"
                )
            return "9999-12-31"

        episodic = [
            r for r in results
            if r.item.kind is MemoryKind.EPISODIC
            and "执行成功" not in r.item.content
            and "执行失败" not in r.item.content
        ]
        others = [
            r for r in results if r.item.kind is not MemoryKind.EPISODIC
        ]
        ref_persons: list[str] = []
        if plan_reuse:
            import re as _re

            found = _re.findall(
                r"(?:参考|参照|学|模仿|按照|像)([\u4e00-\u9fff]{2})"
                r"|和([\u4e00-\u9fff]{2})",
                query,
            )
            ref_persons = [
                (a or b) for a, b in found if (a or b)
            ]
            if ref_persons:
                from .types import tokenize as _tokenize
                from .zh_nlp import expand_synonyms as _expand

                query_terms = _expand(set(_tokenize(query)))
                _TOPIC_STOP = {
                    "怎么", "如何", "准备", "计划", "参考", "参照", "模仿",
                    "按照", "更好", "希望", "想要", "想做", "打算", "安排",
                }
                topic_terms = [
                    t for t in query_terms
                    if t not in ref_persons
                    and t not in _TOPIC_STOP
                    and len(t) > 1
                ][:4]
                topic = " ".join(topic_terms)
                existing_ids = {r.item.id for r in episodic}
                for ref_person in ref_persons:
                    extra = self.recall(
                        f"{ref_person} {topic}".strip(),
                        top_k=8,
                        now=now,
                        kind=MemoryKind.EPISODIC,
                        reasoning_pack=True,
                        zh_synonyms=zh_synonyms,
                    )
                    for r in extra:
                        if (
                            r.item.kind is not MemoryKind.EPISODIC
                            or r.item.id in existing_ids
                            or "执行成功" in r.item.content
                            or "执行失败" in r.item.content
                        ):
                            continue
                        if (
                            ref_person not in r.item.cues
                            and ref_person not in r.item.content
                        ):
                            continue
                        episodic.append(r)
                        existing_ids.add(r.item.id)
                        if not any(
                            "\u7c7b\u6bd4\u8ba1\u5212" in reason
                            for reason in r.reasons
                        ):
                            r.reasons.append(
                                "\u7c7b\u6bd4\u8ba1\u5212(\u53c2\u8003"
                                f"{ref_person})"
                            )
            ref_persons_all = ref_persons
            if ref_persons_all:
                ref_person = ref_persons_all[0]
                for r in episodic:
                    if (
                        ref_person in r.item.cues
                        or ref_person in r.item.content
                    ):
                        r.score = round(r.score + 0.08, 4)
                        if not any(
                            "类比计划" in reason for reason in r.reasons
                        ):
                            r.reasons.append(
                                "\u7c7b\u6bd4\u8ba1\u5212(\u53c2\u8003"
                                f"{ref_person})"
                            )
        def _plan_key(result) -> tuple:
            person = (
                result.item.cues[0][:2]
                if result.item.cues
                else result.item.content[:2]
            )
            ref_priority = 0 if person in ref_persons else 1
            return (ref_priority, _event_date(result))

        episodic.sort(key=_plan_key)
        ordered = episodic + others
        for result in episodic:
            if not any("步骤" in reason for reason in result.reasons):
                result.reasons.append(
                    "\u601d\u7ef4\u94fe\u6b65\u9aa4(\u6309\u65f6\u95f4\u6392\u5e8f)"
                )
        return ordered[:top_k]

    def plan_for_goal(
        self,
        goal: str,
        *,
        top_k: int | None = None,
        now: datetime | None = None,
        zh_synonyms: bool = True,
        outcome_aware: bool = True,
        effort: str | None = None,
    ) -> list[RecallResult]:
        """Agent planning: turn a goal into an ordered step plan.

        Prefrontal goal maintenance (Miller & Cohen, 2001): the agent holds
        the goal and pulls the task-relevant schema - the person's own past
        steps or, when the goal references another person ("参考阿丽"),
        that person's steps as an analogical template (Gick & Holyoak, 1980).
        Outcome-aware reranking (law of effect, Thorndike 1911; Smolen et
        al., 2016): steps whose past executions succeeded more often get a
        bounded boost, failed steps get demoted, so the plan prefers
        what actually worked.
        Falls back to the reasoning premise pack for non-step goals.
        """
        if effort is None:
            effort = self._plan_effort(goal)
        if effort == "low":
            outcome_aware = False
            top_k = top_k or 6
        elif effort == "high":
            top_k = top_k or 14
        else:
            top_k = top_k or self._suggested_plan_size(goal)
        if top_k is None:
            top_k = self._suggested_plan_size(goal)
        if any(marker in goal for marker in (
            "想", "要", "打算", "计划", "准备", "希望", "怎么", "如何",
        )):
            plan = self.recall_steps(
                goal,
                top_k=top_k,
                now=now,
                zh_synonyms=zh_synonyms,
            )
            # outcome records are evidence, not plan steps: filter them out
            plan = [
                r for r in plan
                if "执行成功" not in r.item.content
                and "执行失败" not in r.item.content
            ]
            if outcome_aware:
                self._apply_outcome_rerank(plan)
            return plan
        return self.recall_reasoning(goal, top_k=top_k, now=now)

    def _plan_effort(self, goal: str) -> str:
        """Resource-rational planning depth (Lieder & Griffiths, 2020).

        Simple goals get a shallow, fast plan; goals with many references /
        constraints get a deep plan. Constraint words: 预算/人数/时间/地点/
        要求/限制/完整/全部/按顺序; references: 参考/参照/学/模仿/按照/像.
        """
        import re as _re

        refs = len(_re.findall(
            r"(?:参考|参照|学|模仿|按照|像)([\u4e00-\u9fff]{2})"
            r"|和([\u4e00-\u9fff]{2})",
            goal,
        ))
        constraints = sum(
            1 for token in (
                "预算", "人数", "时间", "地点", "要求", "限制",
                "完整", "全部", "按顺序", "一共", "几天",
            ) if token in goal
        )
        score = refs * 2 + constraints
        if score >= 4:
            return "high"
        if score >= 2:
            return "medium"
        return "low"

    def replan(
        self,
        goal: str,
        failed_step: str,
        *,
        top_k: int | None = None,
        now: datetime | None = None,
    ) -> list[RecallResult]:
        """Replan after a failed step (error monitoring and re-planning).

        The anterior cingulate cortex monitors errors (Botvinick et al.,
        2001) and the prefrontal cortex re-plans. The failed step is moved
        to the end of the plan (avoided), marked with a 重规划 reason, and
        the re-planning decision itself is stored so future plans remember
        what to avoid.
        """
        _ACTION_PREFIXES = "订买卖打包收拾请找定学搬选入"
        noun = failed_step.lstrip(_ACTION_PREFIXES) or failed_step
        # which person(s) actually failed this step? (evidence-weighted)
        failing_persons: dict[str, float] = {}
        for item in self.backend.list(kind=MemoryKind.EPISODIC):
            if "执行失败" not in item.content or len(item.cues) < 3:
                continue
            step_cue = item.cues[1]
            step_noun = step_cue.lstrip(_ACTION_PREFIXES)
            if noun and step_noun != noun and step_cue != failed_step:
                continue
            person = item.cues[0][:2]
            failing_persons[person] = (
                failing_persons.get(person, 0.0)
                + max(1, item.evidence_count)
            )
        plan = self.plan_for_goal(
            goal,
            top_k=top_k,
            now=now,
            effort="high",
            outcome_aware=True,
        )
        kept: list[RecallResult] = []
        failed: list[RecallResult] = []
        for r in plan:
            person = (
                r.item.cues[0][:2]
                if r.item.cues
                else r.item.content[:2]
            )
            should_avoid = bool(
                noun and noun in r.item.content
                and (
                    not failing_persons
                    or failing_persons.get(person, 0.0) > 0.0
                )
            )
            if should_avoid:
                if not any("重规划" in reason for reason in r.reasons):
                    r.reasons.append(
                        f"\u91cd\u89c4\u5212:\u5df2\u907f\u5f00"
                        f"\u5931\u8d25\u6b65\u9aa4{failed_step}"
                    )
                failed.append(r)
            else:
                kept.append(r)
        self.remember(
            f"项目“{goal[:8]}”重新规划：避开失败步骤“{failed_step}”。",
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.AGENT),
            cues=[goal[:8], failed_step, "重规划"],
            importance=0.75,
            evidence_count=1,
            created_at=now,
        )
        return kept + failed

    def _suggested_plan_size(self, goal: str) -> int:
        """Working-memory capacity matching (Miller, 1956).

        Plans need enough context slots to hold the whole step sequence:
        base 8, +2 per referenced person ("参考阿丽和小波"), +2 for chain
        or multi-step hints, capped at 14.
        """
        import re as _re

        size = 8
        refs = _re.findall(
            r"(?:参考|参照|学|模仿|按照|像)([\u4e00-\u9fff]{2})"
            r"|和([\u4e00-\u9fff]{2})",
            goal,
        )
        refs = [a or b for a, b in refs if (a or b)]
        if refs:
            size += 2 * (len(refs) - 1)
        if any(token in goal for token in (
            "三个步骤", "四个步骤", "五个步骤", "三步", "四步", "五步",
            "完整", "全部", "按顺序",
        )):
            size += 2
        return min(size, 14)

    def _apply_outcome_rerank(
        self,
        results: list[RecallResult],
        *,
        bonus_scale: float = 0.08,
    ) -> None:
        """Boost steps whose outcome history is successful; demote failures.

        Outcome records written by ``record_outcome`` carry cues
        ``[goal[:8], step[:8], result]``. One lightweight pass over the
        store collects evidence-weighted success/failure per step cue, then
        each plan step that matches a step cue is nudged by
        ``clamp((success_evidence - failure_evidence) * bonus_scale)``.
        """
        from .types import MemoryKind as _MemoryKind

        if not results:
            return
        _ACTION_PREFIXES = "订买卖打包收拾请找定学搬选入"
        outcome_by_step: dict[tuple[str, str], float] = {}
        for item in self.backend.list(kind=_MemoryKind.EPISODIC):
            if "执行成功" not in item.content and "执行失败" not in item.content:
                continue
            if len(item.cues) < 3:
                continue
            person = item.cues[0][:2]
            step_cue = item.cues[1]
            weight = max(1, item.evidence_count)
            delta = weight if "执行成功" in item.content else -weight
            nouns = {step_cue, step_cue.lstrip(_ACTION_PREFIXES)}
            for noun in nouns:
                key = (person, noun)
                outcome_by_step[key] = (
                    outcome_by_step.get(key, 0.0) + delta
                )
        if not outcome_by_step:
            return
        deltas: list[float] = []
        for result in results:
            content = result.item.content
            person = (
                result.item.cues[0][:2]
                if result.item.cues
                else content[:2]
            )
            match_key = ""
            for (operson, noun), total in outcome_by_step.items():
                if operson == person and noun and noun in content:
                    match_key = (operson, noun)
                    break
            if not match_key:
                deltas.append(0.0)
                continue
            delta = max(
                -0.15,
                min(0.15, outcome_by_step[match_key] * bonus_scale),
            )
            deltas.append(delta)
            result.score = round(result.score + delta, 4)
            if not any("结果加权" in reason for reason in result.reasons):
                result.reasons.append(
                    f"\u7ed3\u679c\u52a0\u6743({delta:+.2f},"
                    f"\u6210\u529f\u8ba1\u5212\u4f18\u5148)"
                )
        # group by outcome delta (successful plans first), keep original
        # chronological order inside each group
        results[:] = [
            results[i]
            for i in sorted(
                range(len(results)),
                key=lambda i: (-deltas[i], i),
            )
        ]

    def record_outcome(
        self,
        goal: str,
        step: str,
        *,
        success: bool,
        note: str | None = None,
        now: datetime | None = None,
    ) -> MemoryItem:
        """Record an execution outcome (agent judgment loop).

        The prefrontal cortex monitors action outcomes and updates
        predictions (Miller & Cohen, 2001; Smolen et al., 2016). The outcome
        is stored with evidence accumulation, so repeated success/failure
        strengthens the trace and future plans can prefer it.

        Prediction-error weighting (Schultz et al., 1997; Rescorla & Wagner,
        1972): outcomes that contradict the accumulated history get a higher
        importance and an "意外" cue, so surprising events are easy to find
        and the prediction is updated more visibly.
        """
        result = "成功" if success else "失败"
        prior = self._step_success_ratio(step)
        error = abs((1.0 if success else 0.0) - prior)
        importance = round(min(0.95, 0.75 + 0.15 * error), 3)
        cues = [goal[:8], step[:8], result]
        if error >= 0.6:
            cues.append("意外")
        content = (
            f"项目“{goal}”的步骤“{step}”执行{result}"
            + (f"（{note}）" if note else "")
            + "。"
        )
        return self.remember(
            content,
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.AGENT),
            cues=cues,
            importance=importance,
            evidence_count=1,
            created_at=now,
        )

    def _step_success_ratio(self, step: str) -> float:
        """Prior success probability of a step from its outcome records."""
        _ACTION_PREFIXES = "订买卖打包收拾请找定学搬选入"
        noun = step.lstrip(_ACTION_PREFIXES) or step
        success = failure = 0
        for item in self.backend.list(kind=MemoryKind.EPISODIC):
            if "执行成功" not in item.content and "执行失败" not in item.content:
                continue
            if len(item.cues) < 3:
                continue
            step_cue = item.cues[1]
            step_noun = step_cue.lstrip(_ACTION_PREFIXES)
            if step_cue != step and step_noun != noun:
                continue
            weight = max(1, item.evidence_count)
            if "执行成功" in item.content:
                success += weight
            else:
                failure += weight
        total = success + failure
        if total == 0:
            return 0.5
        return success / total

    def predict_step(self, step: str) -> dict:
        """Predict a step's success probability from outcome history."""
        _ACTION_PREFIXES = "订买卖打包收拾请找定学搬选入"
        noun = step.lstrip(_ACTION_PREFIXES) or step
        # fast path: consolidated step-experience summary from sleep replay
        for item in self.backend.list(kind=MemoryKind.SEMANTIC):
            if "历史成功率" not in item.content:
                continue
            if noun not in item.content and step not in item.content:
                continue
            match = __import__("re").search(
                r"(\d+)\s*/\s*(\d+)", item.content
            )
            if match:
                success = float(match.group(1))
                total = float(match.group(2))
                if total > 0:
                    ratio = success / total
                    return {
                        "step": step,
                        "success_probability": round(ratio, 3),
                        "confidence": round(abs(ratio - 0.5) * 2, 3),
                        "source": "consolidated",
                    }
        ratio = self._step_success_ratio(step)
        return {
            "step": step,
            "success_probability": round(ratio, 3),
            "confidence": round(abs(ratio - 0.5) * 2, 3),
            "source": "records",
        }

    def sleep_replay(self, now: datetime | None = None) -> dict:
        """Sleep replay: strengthen surprising events, consolidate experience.

        Hippocampal replay (Wilson & McNaughton, 1994) preferentially
        replays salient waking events; sleep-dependent consolidation
        (Stickgold & Walker, 2013) stabilizes them. Prediction-error marked
        records ("意外") get a small strength boost, and each step's outcome
        history is consolidated into a semantic "历史成功率" summary.
        """
        _ACTION_PREFIXES = "订买卖打包收拾请找定学搬选入"
        steps: dict[str, list[int]] = {}
        replayed = 0
        for item in self.backend.list(kind=MemoryKind.EPISODIC):
            if "执行成功" not in item.content and "执行失败" not in item.content:
                continue
            if len(item.cues) < 3:
                continue
            step_cue = item.cues[1]
            noun = step_cue.lstrip(_ACTION_PREFIXES) or step_cue
            steps.setdefault(noun, [0, 0])
            if "执行成功" in item.content:
                steps[noun][0] += max(1, item.evidence_count)
            else:
                steps[noun][1] += max(1, item.evidence_count)
            if "意外" in item.cues:
                item.retrieval_successes += 1
                if item.strength < 1.0:
                    item.strength = round(min(1.0, item.strength + 0.05), 4)
                self.backend.update(item)
                replayed += 1

        consolidated = 0
        source = SourceRecord(origin=SourceType.INFERENCE)
        for noun, (success, failure) in steps.items():
            total = success + failure
            if total < 2:
                continue
            self.remember(
                f"步骤“{noun}”的历史成功率：{success}/{total}。",
                kind=MemoryKind.SEMANTIC,
                source=source,
                cues=[noun, "成功率"],
                importance=0.5,
                evidence_count=total,
                created_at=now,
            )
            consolidated += 1
        return {
            "replayed_surprising": replayed,
            "consolidated_steps": consolidated,
        }

    def practice_due(
        self,
        limit: int = 5,
        now: datetime | None = None,
        *,
        kind: MemoryKind | None = None,
        desirable_difficulty: bool = True,
        min_gap_hours: float = 24.0,
        adaptive_gap: bool = True,
        interleave: bool = True,
        vary_cues: bool = True,
        arousal_priority: bool = True,
        fresh_priority: bool = False,
        fresh_window_hours: float = 6.0,
        review_score_priority: bool = False,
    ) -> list[dict]:
        """Active retrieval practice: due memories shown as cues only.

        Testing effect (Roediger & Karpicke, 2006): attempting retrieval
        and then receiving feedback strengthens a memory more than passive
        re-reading. Spacing effect (Cepeda et al., 2006): practice must be
        spaced - ``min_gap_hours`` prevents massed re-practice of the same
        item. Interleaving (Rohrer & Taylor, 2007): cards from different
        categories are mixed so consecutive cards rarely repeat a category.
        The agent sees only the cues (no content) and must recall the answer
        before it is revealed. Transfer-appropriate processing (Morris,
        Bransford & Franks, 1977): practice in the same kind/format as the
        upcoming test transfers best, so ``kind`` puts that kind of memory
        first in the session. Encoding variability (Martin, 1968):
        practising through different cues each session makes the memory
        robust across query phrasings, so ``vary_cues`` rotates the shown
        cue. Arousal-biased competition (Mather & Sutherland, 2011):
        emotionally arousing memories compete harder for consolidation, so
        ``arousal_priority`` rehearses them first within the quota. Early
        consolidation window (Gais et al., 2006): traces encoded within the
        last few hours are preferentially rehearsed, so ``fresh_priority``
        puts them first while they are still consolidating.
        Review score (importance x forgetting): when enabled, due items are
        ordered by how much they *need* review - important AND fading
        traces first - instead of importance-first alone.
        """
        now = now or utcnow()
        items = self.review_due(
            limit=max(limit * 2, 12),
            now=now,
            desirable_difficulty=desirable_difficulty,
        )
        if arousal_priority:
            # Arousal-biased competition (Mather & Sutherland, 2011):
            # arousing traces compete harder for rehearsal, so they enter
            # the practice queue at a higher retrievability threshold
            # (0.65 instead of 0.5).
            extra = self.review_due(
                limit=max(limit * 2, 12),
                now=now,
                desirable_difficulty=desirable_difficulty,
                due_threshold=0.65,
            )
            extra_ids = {item.id for item in items}
            extra_cap = max(1, limit // 2)
            items = items + [
                item
                for item in extra
                if (
                    item.id not in extra_ids
                    and item.affect in ("positive", "negative", "arousing")
                )
            ][:extra_cap]
        if fresh_priority:
            fresh_extra = self.review_due(
                limit=max(limit * 2, 12),
                now=now,
                desirable_difficulty=desirable_difficulty,
                due_threshold=0.65,
            )
            existing = {item.id for item in items}
            fresh_items = [
                item
                for item in fresh_extra
                if (
                    item.id not in existing
                    and (now - item.created_at).total_seconds()
                    < fresh_window_hours * 3600
                )
            ]
            extra_cap = max(1, limit // 2)
            items = fresh_items[:extra_cap] + items
        if min_gap_hours > 0:
            kept = []
            for item in items:
                gap = min_gap_hours
                if adaptive_gap:
                    rate = self._success_rate(item)
                    total = item.retrieval_successes + item.retrieval_failures
                    if total > 0 and rate < 0.5:
                        # struggling memory: practise again sooner
                        gap *= 0.6
                    elif total > 0 and rate >= 0.9:
                        gap *= 1.3
                is_fresh = (
                    fresh_priority
                    and (now - item.created_at).total_seconds()
                    < fresh_window_hours * 3600
                )
                if (
                    is_fresh
                    or self.curve.hours_since_last_access(item, now) >= gap
                ):
                    kept.append(item)
            if (
                kind is not None
                or arousal_priority
                or review_score_priority
            ):
                def _practice_key(item: MemoryItem) -> tuple:
                    fresh = (
                        (now - item.created_at).total_seconds()
                        < fresh_window_hours * 3600
                        if fresh_priority
                        else False
                    )
                    kind_mismatch = (
                        item.kind is not kind if kind is not None else 0
                    )
                    arousal_mismatch = (
                        item.affect not in ("positive", "negative", "arousing")
                        if arousal_priority
                        else 0
                    )
                    if review_score_priority:
                        need = item.importance * (
                            1.0 - self.curve.retrievability(item, now)
                        )
                        return (
                            -need,
                            kind_mismatch,
                            arousal_mismatch,
                        )
                    return (
                        0 if fresh else 1,
                        kind_mismatch,
                        arousal_mismatch,
                    )

                kept.sort(key=_practice_key)
            items = kept[:limit]
        else:
            if (
                kind is not None
                or arousal_priority
                or review_score_priority
            ):
                def _practice_key2(item: MemoryItem) -> tuple:
                    fresh = (
                        (now - item.created_at).total_seconds()
                        < fresh_window_hours * 3600
                        if fresh_priority
                        else False
                    )
                    kind_mismatch = (
                        item.kind is not kind if kind is not None else 0
                    )
                    arousal_mismatch = (
                        item.affect not in ("positive", "negative", "arousing")
                        if arousal_priority
                        else 0
                    )
                    if review_score_priority:
                        need = item.importance * (
                            1.0 - self.curve.retrievability(item, now)
                        )
                        return (
                            -need,
                            kind_mismatch,
                            arousal_mismatch,
                        )
                    return (
                        0 if fresh else 1,
                        kind_mismatch,
                        arousal_mismatch,
                    )

                items = sorted(items, key=_practice_key2)
            items = items[:limit]
        if interleave and len(items) > 1:
            items = self._interleave(items)
        out = []
        for item in items:
            if vary_cues and len(item.cues) >= 3:
                total_reviews = (
                    item.retrieval_successes + item.retrieval_failures
                )
                start = total_reviews % len(item.cues)
                window = item.cues[start:start + 2]
                if len(window) < 2:
                    window = window + item.cues[:2 - len(window)]
                cue = " / ".join(window)
            else:
                cue = (
                    " / ".join(item.cues[:2])
                    if item.cues
                    else item.content[:12]
                )
            out.append({"id": item.id, "cue": cue})
        return out

    def _interleave(self, items: list[MemoryItem]) -> list[MemoryItem]:
        """Order items so adjacent cards avoid the same category (cue)."""
        buckets: dict[str, list[MemoryItem]] = {}
        for item in items:
            cat = item.cues[0] if item.cues else item.id
            buckets.setdefault(cat, []).append(item)
        out: list[MemoryItem] = []
        last_cat = None
        while buckets:
            candidates = [
                cat for cat in buckets
                if cat != last_cat and buckets[cat]
            ]
            if not candidates:
                candidates = [cat for cat in buckets if buckets[cat]]
            if not candidates:
                break
            cat = candidates[0]
            out.append(buckets[cat].pop(0))
            if not buckets[cat]:
                del buckets[cat]
            last_cat = cat
        return out

    def _success_rate(self, item: MemoryItem) -> float:
        total = item.retrieval_successes + item.retrieval_failures
        if total == 0:
            return 0.5
        return item.retrieval_successes / total

    def practice_answer(
        self,
        memory_id: str,
        attempt: str,
        now: datetime | None = None,
        *,
        suppress_competitors: bool = True,
        suppression_factor: float = 0.97,
        generation_bonus: bool = True,
    ) -> dict:
        """Score a retrieval attempt and apply testing-effect reinforcement.

        A successful recall applies effort-scaled reinforcement (the harder
        the retrieval, the stronger the gain); a failure resets the review
        streak so the item is practised again soon. On success, competing
        memories sharing the item's primary cue are gently suppressed
        (Anderson, Bjork & Bjork, 1994 retrieval-induced forgetting):
        lowering the competing items' accessibility makes the practised
        target easier to discriminate later. Only the primary cue is used
        so auto-extracted content bigrams never misfire suppression.
        Generation effect (Slamecka & Graf, 1978): a successful recall
        phrased in the agent's own words ("generated") strengthens more
        than copying the stored sentence verbatim, so a small extra
        reinforcement is applied unless disabled. Emotionally enhanced
        """
        item = self.backend.get(memory_id)
        if item is None:
            raise ValueError(f"no memory with id {memory_id}")
        now = now or utcnow()
        norm_attempt = "".join(str(attempt or "").split())
        norm_content = "".join(str(item.content).split())
        attempt_chars = set(norm_attempt)
        shared = len(attempt_chars & set(norm_content))
        success = bool(
            norm_attempt
            and (
                norm_attempt in norm_content
                or norm_content in norm_attempt
                or (
                    len(norm_attempt) >= 2
                    and shared >= 2
                    and shared / max(len(attempt_chars), 1) >= 0.6
                )
            )
        )
        generated = success and norm_attempt != norm_content
        if success:
            retrievability = self.curve.retrievability(item, now)
            effort = max(0.0, min(1.0, 1.0 - retrievability))
            delta = 0.12
            if generation_bonus and generated:
                delta *= 1.15
            self.curve.reinforce_review(
                item, delta=delta, now=now, effort=effort
            )
            self.scheduler.record_outcome(item, True, now)
            suppressed = 0
            if suppress_competitors:
                seen = {item.id}
                primary = item.cues[0] if item.cues else ""
                if primary:
                    for rival in self.backend.find_by_cue(primary):
                        if (
                            rival.id in seen
                            or rival.status is not MemoryStatus.ACTIVE
                        ):
                            continue
                        seen.add(rival.id)
                        rival.strength = max(
                            0.05, rival.strength * suppression_factor
                        )
                        self.backend.update(rival)
                        suppressed += 1
        else:
            # Feedback effect: even a failed retrieval attempt with feedback
            # produces a small, plain reinforcement (no effort gain).
            self.curve.reinforce(item, delta=0.05, now=now)
            self.scheduler.record_outcome(item, False, now)
        self.backend.update(item)
        result = {
            "id": item.id,
            "success": success,
            "content": item.content,
            "retrievability": round(
                self.curve.retrievability(item, now), 3
            ),
        }
        if success:
            result["suppressed"] = suppressed
            result["generated"] = generated
        return result

    def practice_report(
        self,
        answers: list[dict],
        now: datetime | None = None,
    ) -> dict:
        """Score a whole practice round and return a session report.

        Each answer is ``{"id": memory_id, "attempt": str}``; results are
        aggregated so the agent gets one summary (success rate, per-card
        feedback) instead of calling ``practice_answer`` card by card.
        """
        details = [
            self.practice_answer(a["id"], a.get("attempt", ""), now=now)
            for a in answers
        ]
        now = now or utcnow()
        for detail in details:
            item = self.backend.get(detail["id"])
            if item is None:
                continue
            next_review = self.scheduler.next_review_at(item, now)
            detail["next_review_at"] = next_review.isoformat()
            detail["retry_hours"] = round(
                (next_review - now).total_seconds() / 3600.0, 1
            )
        retrievabilities = []
        for detail in details:
            item = self.backend.get(detail["id"])
            if item is not None:
                retrievabilities.append(
                    self.curve.retrievability(item, now)
                )
        successes = sum(1 for d in details if d["success"])
        difficulty = None
        if retrievabilities:
            mean_ret = sum(retrievabilities) / len(retrievabilities)
            difficulty = {
                "n": len(retrievabilities),
                "mean_retrievability": round(mean_ret, 3),
                "mean_difficulty": round(1.0 - mean_ret, 3),
                "min_retrievability": round(min(retrievabilities), 3),
                "max_retrievability": round(max(retrievabilities), 3),
            }
        return {
            "n": len(details),
            "successes": successes,
            "failures": len(details) - successes,
            "success_rate": round(
                successes / len(details), 3
            ) if details else 0.0,
            "difficulty": difficulty,
            "details": details,
        }

    def practice_plan(
        self,
        limit: int = 5,
        now: datetime | None = None,
    ) -> list[dict]:
        """Return the next practice session as a review plan.

        The agent gets, for every card in the coming session, the scheduled
        next review time (Smolen et al., 2016 adaptive spacing), current
        retrievability, and historical success rate - so it can plan around
        the memory system instead of treating practice as a black box.
        """
        now = now or utcnow()
        cards = self.practice_due(limit=limit, now=now)
        plan = []
        for card in cards:
            item = self.backend.get(card["id"])
            if item is None:
                continue
            next_review = self.scheduler.next_review_at(item, now)
            plan.append(
                {
                    "id": item.id,
                    "cue": card["cue"],
                    "next_review_at": next_review.isoformat(),
                    "overdue": next_review < now,
                    "retrievability": round(
                        self.curve.retrievability(item, now), 3
                    ),
                    "success_rate": round(
                        self._success_rate(item), 3
                    ),
                    "kind": item.kind.value,
                }
            )
        return plan

    def practice_forecast(
        self,
        days: int = 7,
        now: datetime | None = None,
    ) -> list[dict]:
        """Forecast which memories are due within the next ``days``.

        Extends practice_plan into a calendar (Smolen et al., 2016
        adaptive spacing): every active trace whose scheduled next review
        falls inside the window is returned with its due time, so agents
        can plan a week of reviews ahead of time.
        """
        from datetime import timedelta

        now = now or utcnow()
        horizon = now + timedelta(days=max(1, int(days)))
        forecast = []
        for item in self.store.all_active():
            next_review = self.scheduler.next_review_at(item, now)
            if not (next_review <= horizon):
                continue
            forecast.append(
                {
                    "id": item.id,
                    "cue": (
                        " / ".join(item.cues[:2])
                        if item.cues
                        else item.content[:12]
                    ),
                    "due_at": next_review.isoformat(),
                    "overdue": next_review < now,
                    "retrievability": round(
                        self.curve.retrievability(item, now), 3
                    ),
                    "success_rate": round(
                        self._success_rate(item), 3
                    ),
                    "kind": item.kind.value,
                }
            )
        forecast.sort(key=lambda entry: entry["due_at"])
        return forecast

    def memory_status(self, now: datetime | None = None) -> dict:
        """Return a compact memory-health snapshot.

        Gives agents the same numbers a human would check: how many
        memories (by kind), average strength/importance, how many are due
        right now, and how many conflicts exist.
        """
        now = now or utcnow()
        stats = self.backend.stats()
        due = len(
            self.scheduler.due_items(
                self.store.all_active(),
                now=now,
                limit=10**6,
            )
        )
        conflicts = len(self.consolidator.detect_conflicts())
        return {
            "stats": stats,
            "due_now": due,
            "conflicts": conflicts,
        }

    def review_batch(
        self,
        answers: list[dict],
        now: datetime | None = None,
    ) -> dict:
        """Apply a batch of spaced-repetition outcomes.

        Each answer is ``{"id": memory_id, "success": bool}``; results are
        aggregated with the adaptive scheduler state (review streak, next
        review time) so agents can drive review loops in bulk (Smolen et
        al., 2016).
        """
        now = now or utcnow()
        details = []
        for answer in answers:
            item = self.review(
                answer["id"],
                success=bool(answer.get("success", False)),
                now=now,
            )
            if item is None:
                continue
            next_review = self.scheduler.next_review_at(item, now)
            details.append(
                {
                    "id": item.id,
                    "success": bool(answer.get("success", False)),
                    "review_streak": item.review_streak,
                    "retrievability": round(
                        self.curve.retrievability(item, now), 3
                    ),
                    "next_review_at": next_review.isoformat(),
                    "retry_hours": round(
                        (next_review - now).total_seconds() / 3600.0, 1
                    ),
                }
            )
        successes = sum(1 for d in details if d["success"])
        return {
            "n": len(details),
            "successes": successes,
            "failures": len(details) - successes,
            "success_rate": round(
                successes / len(details), 3
            ) if details else 0.0,
            "details": details,
        }

    def export_memories(self) -> dict:
        """Export all active memories as a portable JSON payload."""
        items = [
            item
            for item in self.store.all_active()
            if item.status is MemoryStatus.ACTIVE
        ]
        return {
            "version": 1,
            "exported_at": utcnow().isoformat(),
            "memories": [item.to_dict() for item in items],
            "intents": [dict(r) for r in self._intents.values()],
            "suppressed_ids": dict(self._suppressed_ids),
        }

    def import_memories(self, payload: dict) -> int:
        """Import memories from an export payload (round 106).

        Rebuilds each MemoryItem from its dict and adds it back into the
        store with cues and associations. Ids are preserved for portability;
        importing the same payload twice creates duplicates.
        """
        from .types import MemoryItem

        imported = 0
        for data in payload.get("memories", []):
            item = MemoryItem.from_dict(data)
            self.backend.add(item)
            self.backend.add_cues(item.id, item.cues)
            self.associations.index(item)
            self.associations.link_related(item)
            imported += 1
        for record in payload.get("intents", []):
            record = dict(record)
            if record.get("id"):
                self._intents[record["id"]] = record
        for memory_id, suppressed_at in payload.get(
            "suppressed_ids", {}
        ).items():
            if self.backend.get(memory_id) is not None:
                self._suppressed_ids[memory_id] = suppressed_at
        return imported

    def practice_session(
        self,
        answers: list[dict],
        limit: int = 5,
        now: datetime | None = None,
    ) -> dict:
        """Run one complete practice session: plan + scored report.

        Returns the coming session's plan and the report for the answers
        just processed (difficulty, next-review suggestions), so agents
        can run a full review loop in one call.
        """
        now = now or utcnow()
        plan = self.practice_plan(limit=limit, now=now)
        report = self.practice_report(answers, now=now)
        return {"plan": plan, "report": report}

    def sleep_and_plan(
        self,
        days: int = 7,
        now: datetime | None = None,
        summarizer=None,
    ) -> dict:
        """Sleep consolidation + refreshed review plan in one call.

        Runs the full sleep cycle, then returns the consolidation summary,
        how many weak-important traces were replayed, and the refreshed
        practice plan/forecast (Stickgold & Walker, 2013; Smolen et al.,
        2016).
        """
        now = now or utcnow()
        report = self.sleep(now=now, summarizer=summarizer)
        plan = self.practice_plan(limit=10, now=now)
        forecast = self.practice_forecast(days=days, now=now)
        return {
            "sleep_summary": report.summary(),
            "weak_replayed": report.weak_replayed,
            "plan": plan,
            "forecast": forecast,
        }

    def memory_audit(self, now: datetime | None = None) -> dict:
        """Deep lifecycle audit beyond the quick status snapshot.

        Adds recycled count, revised traces, emotional traces, average
        retrievability, due and conflict counts - the numbers a maintainer
        would review before deciding what to keep, fix or rehearse.
        """
        now = now or utcnow()
        stats = self.backend.stats()
        items = self.store.all_active()
        retrievabilities = [
            self.curve.retrievability(item, now) for item in items
        ]
        recycled = len(
            self.backend.list(status=MemoryStatus.RECYCLED)
        )
        return {
            "active": len(items),
            "recycled": recycled,
            "semantic": stats["semantic"],
            "episodic": stats["episodic"],
            "revised": sum(1 for i in items if i.revision_count > 0),
            "emotional": sum(1 for i in items if i.affect),
            "conflicts": len(self.consolidator.detect_conflicts()),
            "due_now": len(
                self.scheduler.due_items(items, now=now, limit=10**6)
            ),
            "avg_retrievability": round(
                sum(retrievabilities) / len(retrievabilities), 3
            ) if retrievabilities else 0.0,
            "avg_importance": stats["avg_importance"],
        }

    def dedupe_memories(self, now: datetime | None = None) -> int:
        """Merge near-duplicate traces on demand.

        Complementary learning systems (McClelland et al., 1995): repeated
        episodes collapse into one strengthened trace. Exposes the sleep
        merge pass as an on-demand maintenance tool.
        """
        now = now or utcnow()
        return self.consolidator._merge_duplicates(now)

    def resolve_conflicts(self, now: datetime | None = None) -> dict:
        """Resolve memory conflicts on demand.

        Runs the same accommodation (lopsided evidence retires the stale
        trace) and REM-style resolution (balanced conflicts lose
        confidence) that sleep uses, without waiting for the sleep cycle
        (Nader et al., 2000 reconsolidation; Walker & Stickgold, 2004).
        """
        now = now or utcnow()
        accommodated = self.consolidator._accommodation_phase(now)
        rem_links, rem_resolved = self.consolidator._rem_phase(now)
        remaining = len(self.consolidator.detect_conflicts())
        return {
            "accommodated": accommodated,
            "rem_resolved": rem_resolved,
            "rem_links": rem_links,
            "remaining": remaining,
        }

    def review_load(
        self,
        days: int = 7,
        now: datetime | None = None,
    ) -> dict:
        """Estimate the upcoming review pressure.

        Returns how many traces are due right now, how many are overdue,
        how many will become due within ``days``, and how many are weak
        (retrievability < 0.3). A weighted load index (overdue x2) tells
        agents whether today needs a bigger quota.
        """
        from datetime import timedelta

        now = now or utcnow()
        items = self.store.all_active()
        due_now = 0
        overdue = 0
        due_soon = 0
        weak = 0
        horizon = now + timedelta(days=max(1, int(days)))
        for item in items:
            retrievability = self.curve.retrievability(item, now)
            if retrievability < 0.3:
                weak += 1
            next_review = self.scheduler.next_review_at(item, now)
            if next_review <= horizon:
                due_soon += 1
            if next_review < now:
                overdue += 1
            if retrievability < 0.5:
                due_now += 1
        return {
            "due_now": due_now,
            "overdue": overdue,
            "due_within_days": due_soon - overdue,
            "weak": weak,
            "load_index": due_soon + overdue,
        }

    def tag_memories(
        self,
        memory_ids: list[str],
        tags: list[str],
        action: str = "add",
    ) -> dict:
        """Add or remove tags (cues) on memories in bulk.

        Tags are first-class retrieval cues, so this is an indexing
        maintenance tool: add "工作" to a set of memories and they become
        reachable through that tag.
        """
        if action not in ("add", "remove"):
            raise ValueError("action must be 'add' or 'remove'")
        new_tags = set(normalize_cues(tags))
        updated = added = removed = 0
        for memory_id in memory_ids:
            item = self.backend.get(memory_id)
            if item is None:
                continue
            cues = set(item.cues)
            if action == "add":
                added += len(new_tags - cues)
                cues |= new_tags
            else:
                removed += len(cues & new_tags)
                cues -= new_tags
            item.cues = normalize_cues(list(cues))
            self.backend.update(item)
            self.backend.add_cues(item.id, item.cues)
            updated += 1
        return {"updated": updated, "added": added, "removed": removed}

    def cleanup_preview(
        self,
        now: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Preview which traces the sleep prune pass would recycle.

        Episodic traces that are unimportant, never accessed and old are
        prune candidates. This returns them without deleting anything, so
        agents can review before committing.
        """
        now = now or utcnow()
        preview = []
        for item in self.store.all_active(MemoryKind.EPISODIC):
            age_days = (
                now - item.created_at
            ).total_seconds() / 86400.0
            if (
                item.importance < self.consolidator.prune_importance
                and item.access_count == 0
                and age_days >= self.consolidator.prune_age_days
            ):
                preview.append(
                    {
                        "id": item.id,
                        "preview": item.content[:60],
                        "importance": round(item.importance, 3),
                        "age_days": round(age_days, 1),
                    }
                )
                if len(preview) >= max(1, int(limit)):
                    break
        return preview

    def similarity_report(
        self,
        threshold: float = 0.6,
        limit: int = 20,
    ) -> list[dict]:
        """Find confusable memory pairs by content-token overlap.

        Helps agents spot near-duplicates that dedupe may have missed or
        pairs that need better separation (pattern separation; Yassa &
        Stark, 2011).
        """
        from .types import tokenize

        items = self.store.all_active()
        pairs = []
        for i in range(len(items)):
            a = items[i]
            a_terms = set(tokenize(a.content))
            for j in range(i + 1, len(items)):
                b = items[j]
                b_terms = set(tokenize(b.content))
                common = len(a_terms & b_terms)
                denominator = max(1, min(len(a_terms), len(b_terms)))
                overlap = common / denominator
                if overlap >= threshold:
                    pairs.append(
                        {
                            "a_id": a.id,
                            "b_id": b.id,
                            "overlap": round(overlap, 3),
                            "a_preview": a.content[:40],
                            "b_preview": b.content[:40],
                        }
                    )
        pairs.sort(key=lambda p: p["overlap"], reverse=True)
        return pairs[: max(1, int(limit))]

    def association_report(self, limit: int = 10) -> dict:
        """Summarize the memory association network.

        Reports how well memories are interlinked (spreading activation;
        Collins & Loftus, 1975): total links, connected vs isolated
        memories, average degree, and the most-connected memories.
        """
        items = {item.id: item for item in self.store.all_active()}
        links = self.backend.all_links()
        degree: dict[str, int] = {mid: 0 for mid in items}
        unique_pairs: set[frozenset[str]] = set()
        directed = 0
        for src, dst, _weight in links:
            if src in items and dst in items:
                directed += 1
                degree[src] += 1
                degree[dst] += 1
                unique_pairs.add(frozenset((src, dst)))
        connected = sum(1 for d in degree.values() if d > 0)
        top = sorted(
            degree.items(), key=lambda kv: (-kv[1], kv[0])
        )[: max(1, int(limit))]
        top_connected = [
            {
                "id": mid,
                "preview": items[mid].content[:40],
                "link_count": degree[mid],
                "kind": items[mid].kind.value,
            }
            for mid, _count in top
            if degree[mid] > 0
        ]
        return {
            "memory_count": len(items),
            "directed_links": directed,
            "unique_pairs": len(unique_pairs),
            "connected_count": connected,
            "isolated_count": len(items) - connected,
            "avg_links": round(
                sum(degree.values()) / max(1, len(items)), 3
            ),
            "top_connected": top_connected,
        }

    # -- sleep cycle ----------------------------------------------------------

    def sleep(
        self,
        now: datetime | None = None,
        summarizer=None,
    ) -> ConsolidationReport:
        return self.consolidator.sleep(now, summarizer=summarizer)

    def reflect(self, summarizer=None, now: datetime | None = None) -> list[MemoryItem]:
        """Rewrite evidence-backed semantic facts as an abstraction of their
        supporting episodes (reflection; Park et al., 2023)."""
        return self.consolidator.reflect(summarizer, now)

    # -- active forgetting ----------------------------------------------------

    def forget(self, memory_id: str) -> bool:
        return self.recycle.trash(memory_id)

    def restore(self, memory_id: str) -> bool:
        return self.recycle.restore(memory_id)

    def purge(self, before: datetime | None = None, limit: int = 1000) -> int:
        return self.recycle.purge(before=before, limit=limit)

    def review_due(
        self,
        limit: int = 10,
        now: datetime | None = None,
        importance_first: bool = True,
        desirable_difficulty: bool = False,
        difficulty_target: float = 0.45,
        due_threshold: float = 0.5,
    ) -> list[MemoryItem]:
        return self.scheduler.due_items(
            self.store.all_active(),
            now=now,
            limit=limit,
            importance_first=importance_first,
            desirable_difficulty=desirable_difficulty,
            difficulty_target=difficulty_target,
            due_threshold=due_threshold,
        )

    def review(
        self,
        memory_id: str,
        *,
        success: bool,
        now: datetime | None = None,
        confidence_aware: bool = True,
    ) -> MemoryItem | None:
        """Record a spaced-repetition outcome for a memory.

        Spacing effect (Cepeda et al., 2006) + adaptive scheduling (Smolen
        et al., 2016): a successful review extends the streak and grows the
        next interval; a failed review resets the streak so the trace is
        re-presented sooner. Call this from the agent loop whenever the agent
        can judge whether the recalled content was actually correct.

        With ``confidence_aware`` (default on), a successful review of a
        memory the system is *not confident* about keeps the next interval
        shorter (more practice), mirroring the desirable-difficulty benefit:
        low-confidence-but-correct retrievals deserve more rehearsal
        (Bjork & Kroll, 2015; Koriat & Goldsmith, 1996).
        """
        item = self.backend.get(memory_id)
        if item is None:
            return None
        now = now or utcnow()
        self.scheduler.record_outcome(item, success=success, now=now)
        if success:
            self.curve.reinforce_review(item, delta=0.1, now=now)
            if confidence_aware:
                label, _ = self.calibrated_confidence(item, now)
                if label is not ConfidenceLabel.HIGH:
                    # practice sooner: cut the streak gain in half
                    item.review_streak = max(0.0, item.review_streak - 0.5)
        else:
            # failure slightly weakens retrieval strength: the trace was not
            # retrievable, so the forgetting curve reflects it.
            item.strength = max(0.3, item.strength - 0.05)
        self.backend.update(item)
        return item

    def working_set(self, limit: int = 8) -> list[MemoryItem]:
        """Recently used memories, newest first (working memory).

        Atkinson & Shiffrin (1968); CoALA working memory (Sumers et al., 2023):
        the working set is what should be injected into the agent's prompt.
        """
        touched = [
            item
            for item in self.backend.list()
            if item.last_access_at is not None
        ]
        touched.sort(key=lambda item: item.last_access_at, reverse=True)
        return touched[:limit]

    # -- metacognition ----------------------------------------------------------

    def check(
        self,
        query: str,
        top_k: int = 3,
        now: datetime | None = None,
        embedder: Embedder | None = None,
    ) -> MetacognitiveCheck:
        return self.meta.check(
            query, top_k=top_k, now=now, embedder=embedder or self.embedder
        )

    def confidence(
        self, item: MemoryItem, now: datetime | None = None
    ) -> tuple[ConfidenceLabel, float]:
        return self.meta.confidence(item, now)

    def calibrated_confidence(
        self, item: MemoryItem, now: datetime | None = None
    ) -> tuple[ConfidenceLabel, float]:
        """Confidence blended with the memory's empirical retrieval hit rate."""
        return self.meta.calibrated_confidence(item, now)

    # -- associations -------------------------------------------------------------

    def related(self, memory_id: str, depth: int = 1, max_nodes: int = 20) -> list[MemoryItem]:
        return self.associations.related(memory_id, depth=depth, max_nodes=max_nodes)

    # -- misc ------------------------------------------------------------------------

    def stats(self) -> dict:
        stats = self.backend.stats()
        stats["trash"] = len(self.recycle.list_trash())
        stats["review_due"] = len(self.review_due(limit=1000))
        return stats

    def close(self) -> None:
        if hasattr(self.backend, "close"):
            self.backend.close()


__all__ = ["MemoryEngine"]
