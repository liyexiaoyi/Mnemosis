"""Affective mixin: sleep/emotion advice, difficulty, integration and schema-fit reports."""
# mypy: disable-error-code="attr-defined"

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime

from .types import (
    MemoryKind,
    SourceRecord,
    SourceType,
    tokenize,
)


class AffectiveMixin:
    def sleep_advice(self, now: datetime | None = None) -> dict:
        """Advise what to review before sleep for better consolidation.

        Sleep consolidates memories, and pre-sleep rehearsal of important
        material strengthens it (Rasch & Born, 2013). This tool collects
        weak-but-important memories to review before sleep, plus conflicts,
        overdue intentions and tomorrow's unreviewed topics.
        """
        items = self.store.all_active()
        weak_important = [
            item for item in items
            if item.importance >= 0.6
            and self.curve.retrievability(item, now) < 0.5
        ]
        weak_important.sort(key=lambda item: -item.importance)
        pre_sleep_review = [
            {
                "id": item.id,
                "preview": item.content[:40],
                "importance": round(item.importance, 3),
                "retrievability": round(
                    self.curve.retrievability(item, now), 3
                ),
            }
            for item in weak_important[:5]
        ]
        conflicts = len(self.consolidator.detect_conflicts())
        queue = self.action_queue(now=now)
        coverage = self.coverage_report(now=now)
        tomorrow_priorities = [
            {
                "topic": topic["topic"],
                "memory_count": topic["memory_count"],
                "coverage": topic["coverage"],
            }
            for topic in coverage["topics"]
            if topic["status"] == "unreviewed"
        ][:3]
        advice = (
            "睡前先过一遍“重要但快忘”的记忆，"
            "冲突留到明天集中处理，过期待办尽快收尾"
        )
        return {
            "pre_sleep_review": pre_sleep_review,
            "conflicts_to_resolve": conflicts,
            "overdue_intents": queue["overdue"],
            "tomorrow_priorities": tomorrow_priorities,
            "advice": advice,
        }
    def emotion_advice(
        self,
        memory_ids: list[str] | None = None,
    ) -> dict:
        """Profile emotional tone of memories and advise regulation.

        Emotion regulation (Gross, 2002) starts with awareness of the
        emotional load: this tool counts positive/negative/neutral/
        arousing traces, reports the negative ratio and suggests
        reappraisal or spacing when negativity is high.
        """

        if memory_ids:
            items = []
            for memory_id in memory_ids:
                item = self.backend.get(memory_id)
                if item is not None:
                    items.append(item)
        else:
            items = self.store.all_active()
        counts = Counter(
            item.affect or "neutral" for item in items
        )
        total = len(items)
        negative = counts["negative"]
        negative_ratio = round(negative / max(1, total), 3)
        flagged_topics = []
        topic_negative: dict[str, int] = {}
        for item in items:
            if item.affect == "negative" and item.cues:
                topic = item.cues[0]
                topic_negative[topic] = topic_negative.get(topic, 0) + 1
        for topic, count in sorted(
            topic_negative.items(), key=lambda kv: -kv[1]
        )[:3]:
            flagged_topics.append({"topic": topic, "negative_count": count})
        if negative_ratio >= 0.4:
            advice = (
                "消极记忆占比偏高：先重评一次（换个角度看待），"
                "重要的单独处理，避免整体情绪被带偏"
            )
        elif negative_ratio >= 0.2:
            advice = (
                "消极记忆有一定占比：建议逐条重评，"
                "把“当时很糟”改写为“当时学到什么”"
            )
        else:
            advice = "情绪分布较均衡，保持现状即可"
        return {
            "total_memories": total,
            "mood_profile": {
                "positive": counts["positive"],
                "negative": counts["negative"],
                "neutral": counts["neutral"],
                "arousing": counts["arousing"],
                "mixed": counts["mixed"],
            },
            "negative_ratio": negative_ratio,
            "flagged_topics": flagged_topics,
            "advice": advice,
        }
    def difficulty_estimator(
        self,
        limit: int = 10,
        now: datetime | None = None,
    ) -> dict:
        """Estimate current learning difficulty of each memory.

        Desirable difficulties (Bjork, 1994): learning benefits most when
        retrieval is effortful but still possible. This tool buckets every
        active memory by current retrievability into too-easy / sweet-spot /
        hard / very-hard, highlights the sweet-spot workload and gives
        concrete next actions per bucket.
        """
        items = self.store.all_active()
        buckets = {"too_easy": 0, "sweet_spot": 0, "hard": 0, "very_hard": 0}
        rows: list[dict] = []
        for item in items:
            r = self.curve.retrievability(item, now)
            if r >= 0.75:
                level = "too_easy"
            elif r >= 0.35:
                level = "sweet_spot"
            elif r >= 0.12:
                level = "hard"
            else:
                level = "very_hard"
            buckets[level] += 1
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:36],
                    "topic": item.cues[0] if item.cues else item.content[:10],
                    "level": level,
                    "retrievability": round(r, 3),
                    "importance": round(item.importance, 3),
                    "reviews": item.review_streak,
                }
            )
        rows.sort(key=lambda row: (-row["importance"], row["retrievability"]))
        total = len(items)
        sweet_ratio = round(buckets["sweet_spot"] / max(1, total), 3)
        topic_rows: list[dict] = []
        topic_buckets: dict[str, dict] = {}
        for row in rows:
            entry = topic_buckets.setdefault(
                row["topic"],
                {
                    "topic": row["topic"],
                    "count": 0,
                    "sweet_spot": 0,
                    "hard": 0,
                    "very_hard": 0,
                },
            )
            entry["count"] += 1
            if row["level"] == "sweet_spot":
                entry["sweet_spot"] += 1
            elif row["level"] == "hard":
                entry["hard"] += 1
            elif row["level"] == "very_hard":
                entry["very_hard"] += 1
        for entry in topic_buckets.values():
            if entry["count"] >= 2:
                topic_rows.append(entry)
        topic_rows.sort(
            key=lambda entry: (-entry["very_hard"], -entry["hard"], -entry["count"])
        )
        if buckets["very_hard"] and sweet_ratio < 0.3:
            advice = (
                "太难的太多：先给小步重编码（加线索、拆成更小的点），"
                "把 very_hard 拉回 hard 再进 sweet_spot，不要直接硬背。"
            )
        elif buckets["too_easy"] and sweet_ratio < 0.3:
            advice = (
                "太容易的太多：容易的推迟复习（间隔），等它掉进"
                " sweet_spot 再练，避免假熟练。"
            )
        elif sweet_ratio >= 0.3:
            advice = (
                "难度分布良好：重点保持 sweet_spot 节奏，"
                "太难的拆解、太容易的延后。"
            )
        else:
            advice = "按 importance 优先：sweet_spot 先练，hard 拆解，very_hard 重编码。"
        return {
            "total_memories": total,
            "buckets": buckets,
            "sweet_spot_ratio": sweet_ratio,
            "rows": rows[: max(1, int(limit))],
            "topic_summary": topic_rows[:5],
            "advice": advice,
        }
    def memory_integration(
        self,
        limit: int = 10,
        now: datetime | None = None,
    ) -> dict:
        """Suggest how related memories can be integrated or composed.

        Compositional inference in the hippocampal-prefrontal circuit
        (Schwartenbeck et al., 2023; Spens & Burgess, 2024): related
        traces replayed together form higher-level schemas; nearby
        episodes form event chains; unresolved contradictions block
        clean integration.
        """

        items = self.store.all_active()
        topic_groups: dict[str, list] = defaultdict(list)
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            topic_groups[topic].append(item)
        member_links: set[frozenset[str]] = set()
        for src, dst, _weight in self.backend.all_links():
            member_links.add(frozenset({src, dst}))

        schema_candidates: list[dict] = []
        event_chains: list[dict] = []
        for topic, members in topic_groups.items():
            member_ids = {member.id for member in members}
            linked_pairs = sum(
                1
                for pair in member_links
                if pair <= member_ids and len(pair) == 2
            )
            if len(members) >= 2:
                avg_importance = round(
                    sum(member.importance for member in members)
                    / len(members),
                    3,
                )
                schema_candidates.append(
                    {
                        "topic": topic,
                        "count": len(members),
                        "avg_importance": avg_importance,
                        "linked_pairs": linked_pairs,
                        "suggestion": (
                            "把同主题记忆重放并整合成一条总结记忆"
                            "（组合推理），减少碎片化"
                        ),
                    }
                )
            episodes = [
                member
                for member in members
                if member.kind == MemoryKind.EPISODIC
                and member.source.occurred_at is not None
            ]
            episodes.sort(key=lambda member: member.source.occurred_at)  # type: ignore[arg-type]
            chain = episodes
            if len(chain) >= 2:
                span_days = round(
                    (
                        chain[-1].source.occurred_at
                        - chain[0].source.occurred_at
                    ).total_seconds()
                    / 86400.0,
                    1,
                )
                if span_days <= 14:
                    event_chains.append(
                        {
                            "topic": topic,
                            "events": len(chain),
                            "span_days": span_days,
                            "suggestion": (
                                "把这段时间内的事件串成一条事件链，"
                                "回忆时按顺序重放"
                            ),
                        }
                    )
        schema_candidates.sort(
            key=lambda candidate: (
                -candidate["count"],
                -candidate["avg_importance"],
            )
        )
        event_chains.sort(key=lambda chain: -chain["events"])
        conflicts = self.consolidator.detect_conflicts()
        if conflicts:
            advice = (
                "先解决冲突再整合：同主题记忆互相矛盾时，"
                "先裁定哪条更可信，再合成总结。"
            )
        elif schema_candidates:
            advice = (
                "整合时机已到：同主题记忆可以重放整合成高层图式，"
                "近段事件可以串成事件链。"
            )
        else:
            advice = "当前记忆较分散，暂无整合候选；持续记录后会自动出现。"
        return {
            "total_memories": len(items),
            "schema_candidates": schema_candidates[: max(1, int(limit))],
            "event_chains": event_chains[: max(1, int(limit))],
            "conflicts": len(conflicts),
            "advice": advice,
        }
    def reasoning_trace(
        self,
        problem: str,
        *,
        topic: str | None = None,
        top_k: int = 4,
        store_conclusion: bool = True,
        now: datetime | None = None,
    ) -> dict:
        """Build a replay-friendly reasoning trace from stored memories.

        Mathematical reasoning relies on working memory + prefrontal
        control over quantity representations (Menon, 2016; Dehaene),
        and complex problem solving cycles through goal states that are
        replayed (Watanabe et al., 2023; Jensen et al., 2024). This tool
        recalls premise memories relevant to the problem, extracts the
        quantities, builds a step trace with per-step evidence, and can
        store the derived conclusion as an inference memory so the next
        reasoning round starts from a richer base.
        """

        topic = topic or (self.store.all_active()[0].cues[0] if self.store.all_active() else problem[:12])
        results = self.recall(problem, top_k=max(1, int(top_k)), now=now)
        evidence = [
            {
                "id": result.item.id,
                "preview": result.item.content[:48],
                "confidence": round(result.item.confidence, 3),
                "score": round(result.score, 3),
            }
            for result in results
            if result.score >= 0.05
        ]
        numbers: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for text in [problem] + [item["preview"] for item in evidence]:
            for raw in re.findall(r"-?\d+(?:\.\d+)?", text):
                key = (raw, text[:20])
                if key in seen:
                    continue
                seen.add(key)
                numbers.append(
                    {
                        "value": float(raw),
                        "raw": raw,
                        "where": "problem" if text == problem else "memory",
                    }
                )
        steps = [
            {
                "order": 1,
                "step": "读题：列出已知条件",
                "evidence_ids": [item["id"] for item in evidence],
                "verdict": "ok" if evidence else "weak",
            },
            {
                "order": 2,
                "step": "从记忆中核对已知量",
                "evidence_ids": [item["id"] for item in evidence[:2]],
                "verdict": "ok" if len(numbers) >= 2 else "weak",
            },
            {
                "order": 3,
                "step": "按数量关系计算",
                "evidence_ids": [item["id"] for item in evidence[:1]],
                "verdict": "ok" if numbers else "weak",
            },
            {
                "order": 4,
                "step": "得出结论并准备固化",
                "evidence_ids": [],
                "verdict": "ok",
            },
        ]
        stored_id = None
        if store_conclusion and evidence:
            conclusion = (
                f"推理结论：{problem}（依据 {len(evidence)} 条记忆，"
                f"提取 {len(numbers)} 个数量）"
            )
            item = self.remember(
                conclusion,
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.INFERENCE),
                cues=[topic],
                importance=0.6,
                confidence=0.7,
                evidence_count=len(evidence),
                auto_cues=False,
            )
            stored_id = item.id
        return {
            "problem": problem,
            "topic": topic,
            "evidence_used": evidence[: max(1, int(top_k))],
            "numbers": numbers,
            "steps": steps,
            "verdict": "consistent" if evidence else "review_needed",
            "stored_memory_id": stored_id,
            "advice": (
                "推理链已按记忆证据逐步展开；结论已存入记忆库，"
                "下次同类问题可直接引用。"
                if stored_id
                else "证据不足：先补充相关记忆，再重新推理。"
            ),
        }
    def sleep_inference(
        self,
        *,
        limit: int = 5,
        now: datetime | None = None,
    ) -> dict:
        """Find memory pairs that sleep can weave into new inferences.

        NREM/REM sleep coordinates the weaving of inferential knowledge:
        the brain replays learned pairs offline and the prefrontal cortex
        codes the inferred outcome (Abdou, Nomoto et al., Nature
        Communications, 2024). This tool finds same-topic memory pairs
        that are consolidated enough to support a new inference, ranks
        them by readiness, and tells the agent what to "let sleep
        integrate" next.
        """

        items = self.store.all_active()
        topic_groups: dict[str, list] = defaultdict(list)
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            topic_groups[topic].append(item)
        candidates: list[dict] = []
        for topic, members in topic_groups.items():
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    a, b = members[i], members[j]
                    if a.content_hash == b.content_hash:
                        continue
                    shared_cues = len(set(a.cues) & set(b.cues))
                    ra = self.curve.retrievability(a, now)
                    rb = self.curve.retrievability(b, now)
                    need_consolidation = int(
                        min(ra, rb) < 0.6
                        and min(a.importance, b.importance) >= 0.4
                    )
                    readiness = round(
                        min(1.0, 0.5 * min(1.0, shared_cues)
                            + 0.5 * need_consolidation),
                        3,
                    )
                    candidates.append(
                        {
                            "topic": topic,
                            "a_preview": a.content[:36],
                            "b_preview": b.content[:36],
                            "shared_cues": shared_cues,
                            "retrievability_a": round(ra, 3),
                            "retrievability_b": round(rb, 3),
                            "readiness": readiness,
                            "reason": (
                                "同一主题、遗忘到需要巩固的程度，"
                                "睡眠重放后可组合出新推断"
                            ),
                        }
                    )
        candidates.sort(key=lambda candidate: -candidate["readiness"])
        ready = [candidate for candidate in candidates if candidate["readiness"] >= 0.5]
        return {
            "total_pairs": len(candidates),
            "ready_pairs": len(ready),
            "candidates": candidates[: max(1, int(limit))],
            "advice": (
                "睡眠整合窗口：已找到可组合的推断对，"
                "睡前复习一遍、睡后再查一次，把新推断补进记忆库。"
                if ready
                else "暂无可组合推断对：继续积累同主题记忆，睡眠后再看。"
            ),
        }
    def schema_fit(
        self,
        *,
        limit: int = 20,
    ) -> dict:
        """Measure how new memories fit existing schemas.

        Schemas speed up consolidation: memories congruent with an
        existing schema integrate rapidly in the neocortex (Tse et al.,
        Science, 2007), and reconstruction follows assimilation or
        accommodation (Bartlett, 1932). This tool scores each memory's
        fit to the best-matching schema (topic group) and labels it
        assimilate / borderline / accommodate.
        """


        items = self.store.all_active()
        groups: dict[str, list] = defaultdict(list)
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            groups[topic].append(item)
        schemas = {
            topic: members
            for topic, members in groups.items()
            if len(members) >= 2
        }
        rows: list[dict] = []
        for item in items:
            best_topic = None
            best_fit = 0.0
            item_cues = set(item.cues)
            item_terms = set(tokenize(item.content))
            for topic, members in schemas.items():
                if any(member.id == item.id for member in members):
                    members = [member for member in members if member.id != item.id]
                    if not members:
                        continue
                cue_union: set[str] = set()
                term_union: set[str] = set()
                for member in members:
                    cue_union.update(member.cues)
                    term_union.update(tokenize(member.content))
                cue_overlap = (
                    len(item_cues & cue_union) / max(1, len(item_cues | cue_union))
                    if (item_cues or cue_union)
                    else 0.0
                )
                term_overlap = (
                    len(item_terms & term_union) / max(1, len(item_terms | term_union))
                    if (item_terms or term_union)
                    else 0.0
                )
                fit = min(1.0, 0.6 * cue_overlap + 0.4 * term_overlap)
                if fit > best_fit:
                    best_fit = fit
                    best_topic = topic
            verdict = (
                "assimilate"
                if best_fit >= 0.5
                else "borderline"
                if best_fit >= 0.3
                else "accommodate"
            )
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:36],
                    "topic": item.cues[0] if item.cues else item.content[:10],
                    "best_schema": best_topic,
                    "fit": round(best_fit, 3),
                    "verdict": verdict,
                }
            )
        counts: defaultdict[str, int] = defaultdict(int)
        for row in rows:
            counts[row["verdict"]] += 1
        schema_summary = []
        for topic, members in schemas.items():
            schema_rows = [row for row in rows if row["topic"] == topic]
            avg_fit = round(
                sum(row["fit"] for row in schema_rows) / max(1, len(schema_rows)),
                3,
            )
            schema_summary.append(
                {
                    "topic": topic,
                    "member_count": len(members),
                    "avg_fit": avg_fit,
                    "assimilate": sum(
                        1 for row in schema_rows if row["verdict"] == "assimilate"
                    ),
                    "accommodate": sum(
                        1 for row in schema_rows if row["verdict"] == "accommodate"
                    ),
                }
            )
        schema_summary.sort(key=lambda s: -s["member_count"])
        if counts["accommodate"] > counts["assimilate"]:
            advice = "新知识不成体系：多数记忆找不到合适图式，建议先建新图式再积累。"
        elif counts["assimilate"] >= max(1, counts["accommodate"]):
            advice = "记忆正顺利并入现有图式：与图式一致的记忆巩固更快（Tse 2007）。"
        else:
            advice = "有图式可并入，也有新图式在形成，按主题分别维护即可。"
        return {
            "total_memories": len(items),
            "schema_count": len(schemas),
            "rows": rows[: max(1, int(limit))],
            "verdict_counts": dict(counts),
            "schema_summary": schema_summary,
            "advice": advice,
        }



__all__ = ["AffectiveMixin"]
