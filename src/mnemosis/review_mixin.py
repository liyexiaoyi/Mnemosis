"""Review mixin: spaced practice, sleep consolidation and workload."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta

from .consolidation import ConsolidationReport
from .metacognition import ConfidenceLabel
from .types import (
    MemoryItem,
    MemoryKind,
    MemoryStatus,
    SourceRecord,
    SourceType,
    utcnow,
)


class ReviewMixin:
    def spacing_plan(
        self,
        *,
        days: int = 7,
        limit: int = 20,
        now: datetime | None = None,
    ) -> dict:
        """Build a spaced review schedule for the coming days.

        Distributed practice with longer gaps improves long-term
        retention (Cepeda et al., 2006). Memories close to fading are
        scheduled early; stronger ones wait; topics are interleaved so
        consecutive items in the same session differ.
        """
        days = min(max(1, int(days)), 365)
        items = self.store.all_active()
        items.sort(key=lambda item: -item.importance)
        items = items[: max(1, int(limit))]
        rows: list[dict] = []
        for item in items:
            r = self.curve.retrievability(item, now)
            review_day = min(
                days - 1,
                max(0, round(r * (days - 1))),
            )
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:32],
                    "topic": item.cues[0] if item.cues else item.content[:10],
                    "importance": round(item.importance, 3),
                    "retrievability": round(r, 3),
                    "review_day": review_day,
                }
            )
        buckets: dict[int, list[dict]] = {day: [] for day in range(days)}
        for row in rows:
            buckets[row["review_day"]].append(row)
        daily_plan: list[dict] = []
        for day in range(days):
            bucket = buckets[day]
            bucket.sort(key=lambda row: -row["importance"])
            by_topic: dict[str, list[dict]] = {}
            for row in bucket:
                by_topic.setdefault(row["topic"], []).append(row)
            interleaved: list[dict] = []
            while by_topic:
                for topic in list(by_topic):
                    interleaved.append(by_topic[topic].pop(0))
                    if not by_topic[topic]:
                        del by_topic[topic]
            daily_plan.append(
                {
                    "day": day,
                    "items": [
                        {
                            "id": row["id"],
                            "preview": row["preview"],
                            "importance": row["importance"],
                            "retrievability": row["retrievability"],
                        }
                        for row in interleaved
                    ],
                }
            )
        return {
            "days": days,
            "total_scheduled": len(rows),
            "daily_plan": daily_plan,
            "advice": (
                "间隔复习：快忘的先复习，熟的后复习，同主题交错开"
                "（Cepeda et al. 2006）。"
            ),
        }
    def next_interval(
        self,
        memory_id: str | None = None,
        *,
        now: datetime | None = None,
    ) -> dict:
        """Recommend each memory's next review interval (adaptive spacing).

        Adaptive spacing schedules intervals just long enough for
        effortful retrieval (Karpicke & Bauernschmidt, 2011; Cepeda et
        al., 2006). Base 24h grows with success streak, stretches with
        high accuracy and high retrievability, shrinks for failures,
        low retrievability and high importance.
        """
        if memory_id:
            item = self.backend.get(memory_id)
            items = [item] if item is not None else []
        else:
            items = self.store.all_active()
        rows: list[dict] = []
        for item in items:
            r = self.curve.retrievability(item, now)
            base = 24.0
            streak_mult = min(4.0, 1.5 ** min(item.review_streak, 12))
            attempts = item.retrieval_successes + item.retrieval_failures
            if attempts >= 3:
                accuracy = item.retrieval_successes / attempts
                acc_mult = 1.2 if accuracy >= 0.8 else (
                    0.5 if accuracy < 0.5 else 1.0
                )
            else:
                accuracy = None
                acc_mult = 1.0
            imp_mult = 0.8 if item.importance >= 0.7 else 1.0
            if r >= 0.7:
                r_mult = 1.3
            elif r < 0.3:
                r_mult = 0.6
            else:
                r_mult = 1.0
            interval = round(
                base * streak_mult * acc_mult * imp_mult * r_mult,
                1,
            )
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:32],
                    "review_streak": item.review_streak,
                    "accuracy": accuracy,
                    "retrievability": round(r, 3),
                    "next_interval_hours": interval,
                    "reason": (
                        "连对多、准确率高、还熟练：间隔拉长"
                        if interval >= 100
                        else "失败多/快忘/重要：间隔缩短，早点复习"
                        if interval < 24
                        else "中等状态：保持当前间隔"
                    ),
                }
            )
        rows.sort(key=lambda row: -row["next_interval_hours"])
        return {
            "count": len(rows),
            "rows": rows,
            "advice": (
                "自适应间隔：按每次回忆表现调整下次复习时间，"
                "让回忆“有点难但能想起来”（Karpicke & Bauernschmidt 2011）。"
            ),
        }
    def curve_fit(
        self,
        memory_id: str | None = None,
        *,
        horizon_days: int = 30,
        threshold: float = 0.4,
        now: datetime | None = None,
    ) -> dict:
        """Personalize each memory's forgetting forecast.

        Forgetting rates vary across individuals and items (Murre &
        Chessa, 2011): repeated successful retrieval builds storage
        strength (Bjork & Bjork, 1992) and slows decay. This tool
        estimates a per-memory decay rate from retrieval history and
        predicts the day retrievability crosses a threshold.
        """

        threshold = max(0.05, min(0.95, float(threshold)))
        if memory_id:
            item = self.backend.get(memory_id)
            items = [item] if item is not None else []
        else:
            items = self.store.all_active()
        rows: list[dict] = []
        for item in items:
            r = self.curve.retrievability(item, now)
            attempts = item.retrieval_successes + item.retrieval_failures
            if attempts:
                success_rate = item.retrieval_successes / attempts
                history_factor = min(2.0, 0.5 + success_rate)
            else:
                history_factor = 1.0
            base_rate = self.curve.effective_decay_rate(item)
            estimated_rate = base_rate / history_factor
            if r > threshold and estimated_rate > 0:
                days_to = round(
                    math.log(r / threshold) / estimated_rate / 24.0,
                    1,
                )
            elif r > threshold:
                days_to = float(horizon_days)
            else:
                days_to = 0.0
            days_to = min(float(horizon_days), days_to)
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:32],
                    "retrievability": round(r, 3),
                    "attempts": attempts,
                    "success_rate": (
                        round(item.retrieval_successes / attempts, 3)
                        if attempts
                        else None
                    ),
                    "estimated_rate_per_hour": round(estimated_rate, 5),
                    "days_to_threshold": days_to,
                    "reason": (
                        "回忆成功率越高，遗忘越慢"
                        if history_factor > 1.0
                        else "暂无历史记录，按默认速率预测"
                    ),
                }
            )
        rows.sort(key=lambda row: row["days_to_threshold"])
        return {
            "count": len(rows),
            "threshold": threshold,
            "rows": rows,
            "advice": (
                "个性化遗忘曲线：用每条记忆的真实回忆记录调衰减速率，"
                "预测多久后会跌破复习阈值（Murre & Chessa 2011）。"
            ),
        }
    def affect_decay(
        self,
        *,
        limit: int = 20,
    ) -> dict:
        """Forecast emotional charge persistence for emotional memories.

        Emotional memories persist longer, but repeated successful
        processing reduces the charge (Gross, 2002; extinction-like
        regulation). Residual charge drops with the review streak (3
        consecutive successes = processed). This reports current charge,
        estimated persistence and a regulation hint.
        """

        emotional = [
            item
            for item in self.store.all_active()
            if item.affect in ("positive", "negative", "arousing", "mixed")
        ]
        rows: list[dict] = []
        for item in emotional:
            charge = round(max(0.0, 1.0 - item.review_streak / 3.0), 3)
            persistence_days = round(charge * 30.0, 1)
            if charge == 0:
                status = "processed"
            elif charge <= 0.5:
                status = "fading"
            else:
                status = "persistent"
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:32],
                    "affect": item.affect,
                    "review_streak": item.review_streak,
                    "charge": charge,
                    "persistence_days": persistence_days,
                    "status": status,
                    "hint": (
                        "情绪已处理：正常间隔复习即可"
                        if status == "processed"
                        else "情绪在消退：保持重评式复习"
                        if status == "fading"
                        else "情绪仍强：用重评+更新处理，别反复回放"
                    ),
                }
            )
        rows.sort(
            key=lambda row: (-row["charge"], row["persistence_days"])
        )
        counts = defaultdict(int)
        for row in rows:
            counts[row["status"]] += 1
        persistent = [row for row in rows if row["status"] == "persistent"]
        return {
            "total_emotional": len(emotional),
            "status_counts": dict(counts),
            "rows": rows[: max(1, int(limit))],
            "advice": (
                "仍有高情绪记忆：先重评（换个角度），再趁提取窗口更新"
                "结论（Gross 2002；Nader 2000）。"
                if persistent
                else "情绪记忆处理良好：按间隔复习保持即可。"
            ),
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

        now = now or utcnow()
        horizon = now + timedelta(days=min(max(1, int(days)), 365))
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
        due = sum(
            1
            for item in self.store.all_active()
            if self.scheduler.is_due(item, now)
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
            "due_now": sum(
                1 for item in items if self.scheduler.is_due(item, now)
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

        now = now or utcnow()
        items = self.store.all_active()
        due_now = 0
        overdue = 0
        due_soon = 0
        weak = 0
        horizon = now + timedelta(days=min(max(1, int(days)), 365))
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
    def working_set_budget(
        self,
        *,
        limit: int = 8,
        capacity: int = 7,
        optimal: int = 4,
    ) -> dict:
        """Check whether the working set fits the agent's working memory.

        Working memory is limited to roughly 7±2 chunks (Miller, 1956),
        with a more realistic focus of 4±1 (Cowan, 2001); cognitive load
        theory says overload hurts learning and planning (Sweller, 1988).
        This tool compares the current working set against capacity and
        recommends chunking by topic when overloaded.
        """

        items = self.working_set(limit=max(1, int(limit)))
        count = len(items)
        capacity = max(1, int(capacity))
        optimal = min(max(1, int(optimal)), capacity)
        load_ratio = round(count / capacity, 3)
        if count > capacity:
            verdict = "overloaded"
        elif count > optimal:
            verdict = "optimal"
        else:
            verdict = "underutilized"
        topic_chunks: dict[str, list[str]] = defaultdict(list)
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            topic_chunks[topic].append(item.id)
        chunks = [
            {
                "topic": topic,
                "count": len(memory_ids),
                "memory_ids": memory_ids,
            }
            for topic, memory_ids in topic_chunks.items()
        ]
        chunks.sort(key=lambda chunk: -chunk["count"])
        if verdict == "overloaded":
            advice = (
                "一次装不下：按主题分批（每批不超过 4 条），"
                "先处理最重要的主题，降低认知负荷。"
            )
        elif verdict == "optimal":
            advice = "负载合适：保持当前节奏，先做最重要主题即可。"
        else:
            advice = "负载偏低：可以把最相关的记忆也放进工作集，充分用满。"
        return {
            "count": count,
            "capacity": capacity,
            "optimal": optimal,
            "load_ratio": load_ratio,
            "verdict": verdict,
            "chunks": chunks,
            "advice": advice,
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
