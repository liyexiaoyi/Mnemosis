"""Forgetting-quality mixin: topic drift, forgetting export, coverage, source calibration, risk ranking, bridge suggestions."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from itertools import combinations

from .types import utcnow


class ForgettingQualityMixin:
    def topic_drift_report(
        self,
        period_days: int = 30,
        limit: int = 20,
    ) -> dict:
        """Compare topic distribution between the two most recent periods.

        Schemas are reconstructed and shift over time (Bartlett, 1932):
        this compares the newest time bucket against the previous one and
        reports which themes grew, shrank, appeared or disappeared.
        """
        story = self.life_story(
            period_days=max(1, int(period_days)),
            limit=max(2, int(limit)),
        )
        periods = story["periods"]
        if len(periods) < 2:
            return {
                "periods": [p["period_start"] for p in periods],
                "topics": [],
                "total_drift": 0,
            }
        old, new = periods[-2], periods[-1]
        old_counts = {t["cue"]: t["count"] for t in old["top_themes"]}
        new_counts = {t["cue"]: t["count"] for t in new["top_themes"]}
        all_topics = sorted(set(old_counts) | set(new_counts))
        topics = []
        for topic in all_topics:
            old_count = old_counts.get(topic, 0)
            new_count = new_counts.get(topic, 0)
            delta = new_count - old_count
            if old_count == 0:
                status = "new"
            elif new_count == 0:
                status = "gone"
            elif delta > 0:
                status = "grew"
            elif delta < 0:
                status = "shrank"
            else:
                status = "same"
            topics.append(
                {
                    "topic": topic,
                    "old_count": old_count,
                    "new_count": new_count,
                    "delta": delta,
                    "status": status,
                }
            )
        total_drift = sum(
            1 for t in topics if t["status"] not in ("same",)
        )
        return {
            "periods": [old["period_start"], new["period_start"]],
            "topics": topics,
            "total_drift": total_drift,
        }

    def forgetting_export(
        self,
        memory_id: str,
        days: int = 30,
        step_days: int = 1,
    ) -> dict | None:
        """Export a memory's predicted forgetting curve.

        The forgetting curve (Ebbinghaus, 1885) predicts retrievability
        over time; this returns the forecast at regular intervals so
        agents or dashboards can plot it.
        """

        item = self.backend.get(memory_id)
        if item is None:
            return None
        now = utcnow()
        points = []
        for offset in range(
            0,
            max(1, int(days)) + 1,
            max(1, int(step_days)),
        ):
            points.append(
                {
                    "days_from_now": offset,
                    "retrievability": round(
                        self.curve.retrievability(
                            item, now + timedelta(days=offset)
                        ),
                        3,
                    ),
                }
            )
        return {
            "memory_id": memory_id,
            "content": item.content[:40],
            "initial": points[0]["retrievability"],
            "final": points[-1]["retrievability"],
            "points": points,
        }

    def coverage_report(
        self,
        now: datetime | None = None,
        limit: int = 20,
    ) -> dict:
        """Report review coverage per topic schema.

        Spaced-review systems need coverage monitoring: a topic with many
        never-reviewed memories is a blind spot. This reports, per topic,
        memory count, reviewed count, coverage ratio, average
        retrievability/importance and a status.
        """
        schema = self.schema_report(limit=max(1, int(limit)))
        topics = []
        for group in schema["top_groups"]:
            topic = group["topic"]
            members = [
                item
                for item in self.store.all_active()
                if item.cues and item.cues[0] == topic
            ]
            reviewed = [
                item for item in members
                if item.retrieval_successes + item.retrieval_failures > 0
            ]
            count = len(members)
            coverage = round(len(reviewed) / count, 3) if count else 1.0
            if coverage == 0:
                status = "unreviewed"
            elif coverage < 0.5:
                status = "partial"
            else:
                status = "good"
            topics.append(
                {
                    "topic": topic,
                    "memory_count": count,
                    "reviewed_count": len(reviewed),
                    "coverage": coverage,
                    "avg_retrievability": round(
                        sum(
                            self.curve.retrievability(item, now)
                            for item in members
                        ) / max(1, count),
                        3,
                    ),
                    "avg_importance": group["avg_importance"],
                    "status": status,
                }
            )
        return {
            "topics": topics,
            "total_topics": len(topics),
        }

    def source_calibration(self) -> dict:
        """Score the trustworthiness of each memory source.

        Source monitoring (Johnson, Hashtroudi & Lindsay, 1993): agents
        should know which origins are reliable. This groups memories by
        source origin and scores each source from its average confidence,
        evidence and importance.
        """

        groups: dict[str, list] = defaultdict(list)
        for item in self.store.all_active():
            groups[item.source.origin.value].append(item)
        sources = []
        for origin, members in sorted(groups.items()):
            count = len(members)
            avg_confidence = (
                sum(item.confidence for item in members) / count
            )
            avg_evidence = (
                sum(item.evidence_count for item in members) / count
            )
            avg_importance = (
                sum(item.importance for item in members) / count
            )
            avg_trust = sum(item.source.trust for item in members) / count
            trust_score = round(
                0.4 * avg_confidence
                + 0.3 * min(1.0, avg_evidence / 3.0)
                + 0.2 * avg_importance
                + 0.1 * avg_trust,
                3,
            )
            sources.append(
                {
                    "origin": origin,
                    "memory_count": count,
                    "avg_confidence": round(avg_confidence, 3),
                    "avg_evidence": round(avg_evidence, 3),
                    "avg_importance": round(avg_importance, 3),
                    "avg_source_trust": round(avg_trust, 3),
                    "trust_score": trust_score,
                }
            )
        sources.sort(key=lambda s: -s["trust_score"])
        return {
            "sources": sources,
            "total_memories": sum(s["memory_count"] for s in sources),
        }

    def forgetting_risk(
        self,
        now: datetime | None = None,
        limit: int = 20,
    ) -> dict:
        """Rank memories by forgetting risk.

        The riskiest memories are the most important ones closest to
        being forgotten (importance x forgetting); agents should review
        those first.
        """
        scored = []
        for item in self.store.all_active():
            retrievability = self.curve.retrievability(item, now)
            risk = item.importance * (1.0 - retrievability)
            scored.append(
                {
                    "id": item.id,
                    "preview": item.content[:40],
                    "importance": round(item.importance, 3),
                    "retrievability": round(retrievability, 3),
                    "risk": round(risk, 3),
                }
            )
        scored.sort(key=lambda entry: (-entry["risk"], entry["id"]))
        riskiest = scored[: max(1, int(limit))]
        return {
            "total": len(scored),
            "avg_risk": round(
                sum(entry["risk"] for entry in scored) / max(1, len(scored)),
                3,
            ),
            "riskiest": riskiest,
        }

    def bridge_suggestions(
        self,
        limit: int = 20,
    ) -> dict:
        """Suggest missing links between memories sharing cues.

        Spreading activation works through links (Collins & Loftus, 1975):
        memories that share a cue but have no link are a gap in the
        network. This lists those pairs so the agent can add bridges.
        """

        items = self.store.all_active()
        existing: set[frozenset[str]] = set()
        for src, dst, _weight in self.backend.all_links():
            existing.add(frozenset((src, dst)))
        suggestions = []
        compare_items = items[: min(max(2, int(limit) * 3), 200)]
        for a, b in combinations(compare_items, 2):
            if len(suggestions) >= max(1, int(limit)):
                break
            shared = sorted(set(a.cues) & set(b.cues))
            if not shared:
                continue
            if frozenset((a.id, b.id)) in existing:
                continue
            suggestions.append(
                {
                    "id_a": a.id,
                    "id_b": b.id,
                    "a_preview": a.content[:24],
                    "b_preview": b.content[:24],
                    "shared_cues": shared[:4],
                }
            )
        return {
            "total": len(suggestions),
            "suggestions": suggestions,
        }
