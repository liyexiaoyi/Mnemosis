"""Mnemosis public facade."""

from __future__ import annotations

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

    # -- wake cycle ---------------------------------------------------------

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
    ) -> MemoryItem:
        source = source or SourceRecord(origin=SourceType.USER)
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
    ) -> list[RecallResult]:
        embedder = embedder or self.embedder
        return self.store.recall(
            query,
            kind=kind,
            top_k=top_k,
            now=now,
            context=context,
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
        )

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
            top_k=max(top_k, 12),
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
            r for r in results if r.item.kind is MemoryKind.EPISODIC
        ]
        others = [
            r for r in results if r.item.kind is not MemoryKind.EPISODIC
        ]
        if plan_reuse:
            import re as _re

            ref_persons = _re.findall(
                r"(?:参考|参照|学|模仿|按照|像)([\u4e00-\u9fff]{2})"
                r"|和([\u4e00-\u9fff]{2})",
                query,
            )
            ref_persons = [
                (a or b) for a, b in ref_persons if (a or b)
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
        episodic.sort(key=_event_date)
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
        """
        result = "成功" if success else "失败"
        content = (
            f"项目“{goal}”的步骤“{step}”执行{result}"
            + (f"（{note}）" if note else "")
            + "。"
        )
        return self.remember(
            content,
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.AGENT),
            cues=[goal[:8], step[:8], result],
            importance=0.75,
            evidence_count=1,
            created_at=now,
        )

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
    ) -> list[MemoryItem]:
        return self.scheduler.due_items(
            self.store.all_active(),
            now=now,
            limit=limit,
            importance_first=importance_first,
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
