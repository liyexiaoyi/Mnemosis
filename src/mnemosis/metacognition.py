"""Metacognition: confidence, contradictions, knowledge gaps.

Human principle #8: humans doubt themselves, ask for confirmation, and notice
when they do not know. This module turns that into an API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .consolidation import Conflict
from .dual_track import DualTrackStore
from .embedding import Embedder
from .forgetting import ForgettingCurve
from .types import MemoryItem, SourceType, tokenize, utcnow


class ConfidenceLabel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(slots=True)
class MetacognitiveCheck:
    """Result of `engine.check(query)`: think before answering."""

    query: str
    items: list[tuple[MemoryItem, ConfidenceLabel, float]] = field(default_factory=list)
    contradictions: list[Conflict] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    blocked: list[MemoryItem] = field(default_factory=list)

    def should_confirm_any(self) -> bool:
        return any(label is ConfidenceLabel.LOW for _, label, _ in self.items)


class Metacognition:
    def __init__(
        self,
        store: DualTrackStore,
        curve: ForgettingCurve,
        consolidator=None,
        semantic_gap_threshold: float = 0.35,
    ) -> None:
        self.store = store
        self.curve = curve
        self.consolidator = consolidator
        self.semantic_gap_threshold = semantic_gap_threshold

    def confidence(
        self, item: MemoryItem, now: datetime | None = None
    ) -> tuple[ConfidenceLabel, float]:
        now = now or utcnow()
        retrievability = self.curve.retrievability(item, now)
        value = (
            item.confidence
            * (0.45 + 0.55 * retrievability)
            * (0.8 + 0.2 * min(item.access_count, 3) / 3.0)
            * (0.95 + 0.05 * min(item.evidence_count, 5) / 5.0)
        )
        value = max(0.0, min(1.0, value))
        return self._label_for(value), round(value, 3)

    def calibrate(self, item: MemoryItem, min_evidence: int = 2) -> float | None:
        """Beta-smoothed empirical accuracy from real retrieval outcomes.

        Lichtenstein, Fischhoff & Phillips (1977): a well-calibrated judge's
        confidence matches the actual hit rate. Each memory tracks how often
        retrieval hit or missed; with a Beta(1,1) prior, the empirical rate
        is (successes+1)/(trials+2). Returns None until enough evidence has
        accumulated.
        """
        trials = item.retrieval_successes + item.retrieval_failures
        if trials < min_evidence:
            return None
        return (item.retrieval_successes + 1.0) / (trials + 2.0)

    def calibrated_confidence(
        self,
        item: MemoryItem,
        now: datetime | None = None,
        *,
        evidence_weight: float = 0.5,
        evidence_scale: int = 5,
    ) -> tuple[ConfidenceLabel, float]:
        """Blend the heuristic confidence with the empirical hit rate.

        Yeung & Summerfield (2012): confidence and error monitoring are
        graded signals that should track actual performance. With little
        retrieval evidence the heuristic dominates; with more evidence the
        empirical rate takes over (up to `evidence_weight`).
        """
        label, value = self.confidence(item, now)
        empirical = self.calibrate(item)
        if empirical is None:
            return label, value
        trials = item.retrieval_successes + item.retrieval_failures
        weight = evidence_weight * min(1.0, trials / evidence_scale)
        calibrated = value * (1.0 - weight) + empirical * weight
        calibrated = max(0.0, min(1.0, calibrated))
        return self._label_for(calibrated), round(calibrated, 3)

    def calibration_stats(
        self,
        items: list[MemoryItem],
        now: datetime | None = None,
    ) -> dict:
        """Reliability table + expected calibration error (ECE)."""
        buckets: dict[int, dict] = {}
        for item in items:
            _, pred = self.confidence(item, now)
            bucket = min(4, int(pred * 5))
            entry = buckets.setdefault(
                bucket, {"pred_sum": 0.0, "n": 0, "hits": 0, "fails": 0}
            )
            entry["pred_sum"] += pred
            entry["n"] += 1
            entry["hits"] += item.retrieval_successes
            entry["fails"] += item.retrieval_failures
        rows = []
        ece_numerator = 0.0
        total = 0
        for bucket in range(5):
            bucket_entry = buckets.get(bucket)
            if not bucket_entry or bucket_entry["n"] == 0:
                continue
            trials = bucket_entry["hits"] + bucket_entry["fails"]
            empirical = (
                (bucket_entry["hits"] + 1.0) / (trials + 2.0)
                if trials > 0
                else None
            )
            mean_pred = bucket_entry["pred_sum"] / bucket_entry["n"]
            rows.append(
                {
                    "predicted_bucket": f"{bucket * 0.2:.1f}-{(bucket + 1) * 0.2:.1f}",
                    "n_items": bucket_entry["n"],
                    "mean_predicted": round(mean_pred, 3),
                    "empirical_hit_rate": (
                        round(empirical, 3) if empirical is not None else None
                    ),
                }
            )
            if empirical is not None:
                ece_numerator += entry["n"] * abs(mean_pred - empirical)
                total += entry["n"]
        return {
            "buckets": rows,
            "ece": round(ece_numerator / total, 4) if total else 0.0,
        }

    @staticmethod
    def _label_for(value: float) -> ConfidenceLabel:
        if value >= 0.7:
            return ConfidenceLabel.HIGH
        if value >= 0.4:
            return ConfidenceLabel.MEDIUM
        return ConfidenceLabel.LOW

    def contradictions(self) -> list[Conflict]:
        if self.consolidator is None:
            return []
        return self.consolidator.detect_conflicts()

    def knowledge_gaps(
        self,
        query: str,
        top_k: int = 8,
        embedder: Embedder | None = None,
    ) -> list[str]:
        """Query terms that no active memory can account for.

        With an embedder, a term is covered when it is semantically similar to
        at least one memory (e.g. "preference" ~ "prefers").
        """
        query_terms = set(tokenize(query))
        known: set[str] = set()
        items = self.store.all_active()
        for item in items:
            known |= set(tokenize(item.content))
            known |= set(item.cues)
        missing = [term for term in sorted(query_terms) if term not in known]
        if not missing or embedder is None:
            return missing[:top_k]
        vectors = [(item, embedder.embed(item.content)) for item in items]
        covered: set[str] = set()
        for term in missing:
            query_vector = embedder.embed(term)
            if any(
                embedder.cosine(query_vector, item_vector)
                > self.semantic_gap_threshold
                for _, item_vector in vectors
            ):
                covered.add(term)
        return [term for term in missing if term not in covered][:top_k]

    def blocked_retrievals(
        self,
        query: str,
        top_k: int = 3,
        now: datetime | None = None,
        embedder: Embedder | None = None,
    ) -> list[MemoryItem]:
        """Schacter's "blocking" sin: cues match, but the memory was not recalled.

        These are candidate memories that share cues with the query yet fell
        outside the top-k results — a feeling-of-knowing signal that the agent
        should try alternative retrieval routes instead of giving up.
        """
        query_terms = set(tokenize(query))
        results = self.store.recall(
            query, top_k=top_k, now=now, embedder=embedder
        )
        recalled = {r.item.id for r in results}
        return [
            item
            for item in self.store.all_active()
            if item.id not in recalled and set(item.cues) & query_terms
        ]

    def should_confirm(self, item: MemoryItem, now: datetime | None = None) -> bool:
        """Signal that the agent should double-check before asserting."""
        label, _ = self.confidence(item, now)
        if label is ConfidenceLabel.LOW:
            return True
        return item.source.origin is SourceType.INFERENCE and item.confidence < 0.8

    def check(
        self,
        query: str,
        top_k: int = 3,
        now: datetime | None = None,
        embedder: Embedder | None = None,
    ) -> MetacognitiveCheck:
        now = now or utcnow()
        results = self.store.recall(
            query, top_k=top_k, now=now, embedder=embedder
        )
        items = [(r.item, *self.confidence(r.item, now)) for r in results]
        return MetacognitiveCheck(
            query=query,
            items=items,
            contradictions=self.contradictions(),
            gaps=self.knowledge_gaps(query, embedder=embedder),
            blocked=self.blocked_retrievals(query, top_k, now, embedder),
        )


__all__ = ["ConfidenceLabel", "Metacognition", "MetacognitiveCheck"]
