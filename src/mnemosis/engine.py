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
        fresh_priority: bool = True,
        fresh_window_hours: float = 6.0,
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
            items = items + [
                item
                for item in extra
                if (
                    item.id not in extra_ids
                    and item.affect in ("positive", "negative", "arousing")
                )
            ]
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
            items = fresh_items + items
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
            if kind is not None or arousal_priority:
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
                    return (
                        0 if fresh else 1,
                        kind_mismatch,
                        arousal_mismatch,
                    )

                kept.sort(key=_practice_key)
            items = kept[:limit]
        else:
            if kind is not None or arousal_priority:
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
            plan.append(
                {
                    "id": item.id,
                    "cue": card["cue"],
                    "next_review_at": self.scheduler.next_review_at(
                        item, now
                    ).isoformat(),
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
