"""Normalized rank relevance connected to explicitly supplied evidence support.

Pure, bounded inputs only. Neither rank agreement nor coverage proves truth.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
import math
from numbers import Real

from .evidence_selection import (
    EvidenceCandidate, EvidenceSelectionReport, QueryAspect, select_evidence,
)


@dataclass(frozen=True, slots=True)
class RankedChannel:
    channel_id: str
    memory_ids: Sequence[str]
    weight: Real = 1.0
    status: str = "ok"


@dataclass(frozen=True, slots=True)
class ChannelSummary:
    channel_id: str
    status: str
    enabled: bool
    normalized_weight: float
    input_count: int


@dataclass(frozen=True, slots=True)
class RankContribution:
    channel_id: str
    rank: int
    contribution: float


@dataclass(frozen=True, slots=True)
class RankedEvidenceReport:
    channels: tuple[ChannelSummary, ...]
    candidate_ids: tuple[str, ...]
    relevance_by_id: dict[str, float]
    contributions_by_id: dict[str, tuple[RankContribution, ...]]
    support_state: str
    supplied_support_pairs: tuple[tuple[str, str], ...]
    underflow_channel_ids: tuple[str, ...]
    selection: EvidenceSelectionReport


def _identifier(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{name} must be nonempty and trimmed")
    return value


def _sequence(value: Sequence, name: str, maximum: int) -> None:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum}")


def _real(value: Real, name: str, *, unit: bool = False) -> Real:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number, not bool")
    if value != value or value == math.inf or value == -math.inf:
        raise ValueError(f"{name} must be finite")
    if value < 0 or (unit and value > 1):
        raise ValueError(f"{name} outside its allowed range")
    return value


def _exact(value: Real) -> Fraction:
    ratio = getattr(value, "as_integer_ratio", None)
    return Fraction(*ratio()) if ratio is not None else Fraction(value)


def _normalized(weights: Sequence[Real]) -> list[float]:
    try:
        maximum = max(weights)
    except OverflowError:
        maximum = max(weights, key=_exact)
    if maximum == 0:
        raise ValueError("at least one channel weight must be positive")
    scaled = []
    for value in weights:
        # Foreign scalars can divide in float16/32 before float conversion.
        if any(type(operand) not in (int, float, Fraction)
               and callable(getattr(operand, "as_integer_ratio", None))
               for operand in (value, maximum)):
            scaled.append(float(_exact(value) / _exact(maximum)))
            continue
        try:
            scaled.append(float(value / maximum))
        except OverflowError:
            scaled.append(float(_exact(value) / _exact(maximum)))
    total = math.fsum(scaled)
    return [value / total for value in scaled]


def _unit(value: float) -> float:
    if not -1e-12 <= value <= 1.0 + 1e-12:
        raise ArithmeticError("rank relevance outside its mathematical range")
    return max(0.0, min(1.0, value))


def select_ranked_evidence(
    channels: Sequence[RankedChannel],
    aspects: Sequence[QueryAspect],
    *,
    support: Mapping[str, Mapping[str, Real]] | None = None,
    limit: int = 5,
    relevance_weight: Real = .5,
) -> RankedEvidenceReport:
    """Fuse ranked IDs with fixed channel weights, then select supplied support.

    At most 8 channels, 100 IDs per channel, 100 enabled unique candidates,
    and 32 aspects. Normal empty channels keep their weight. Enabled failed
    channels raise; disabling one is an explicit caller decision. No supplied
    support values requires relevance_weight=1, including at zero capacity.
    All validation is retained by the existing evidence selector.
    """
    _sequence(channels, "channels", 8)
    if not channels:
        raise ValueError("at least one channel is required")
    _sequence(aspects, "aspects", 32)
    lam = _real(relevance_weight, "relevance_weight", unit=True)
    aspect_snapshot = []
    aspect_ids = set()
    for aspect in aspects:
        if not isinstance(aspect, QueryAspect):
            raise TypeError("aspects must contain QueryAspect values")
        ident = _identifier(aspect.aspect_id, "aspect_id")
        if ident in aspect_ids:
            raise ValueError("duplicate aspect_id")
        aspect_ids.add(ident)
        aspect_snapshot.append(QueryAspect(ident, aspect.weight))

    snapshot = []
    channel_ids = set()
    first_seen: dict[str, int] = {}
    for channel in channels:
        if not isinstance(channel, RankedChannel):
            raise TypeError("channels must contain RankedChannel values")
        ident = _identifier(channel.channel_id, "channel_id")
        if ident in channel_ids:
            raise ValueError("duplicate channel_id")
        channel_ids.add(ident)
        weight = _real(channel.weight, "channel weight")
        if not isinstance(channel.status, str):
            raise TypeError("channel status must be a string")
        if channel.status not in ("ok", "failed"):
            raise ValueError("channel status must be ok or failed")
        _sequence(channel.memory_ids, "memory_ids", 100)
        ids = tuple(_identifier(i, "memory_id") for i in channel.memory_ids)
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate memory_id within channel")
        if channel.status == "failed":
            if ids:
                raise ValueError("failed channel must have empty memory_ids")
            if weight > 0:
                raise ValueError(f"enabled channel failed: {ident}")
        snapshot.append(RankedChannel(ident, ids, weight, channel.status))
        if weight > 0:
            for memory_id in ids:
                if memory_id not in first_seen:
                    first_seen[memory_id] = len(first_seen)
    if len(first_seen) > 100:
        raise ValueError("enabled candidate union exceeds 100")

    probabilities = _normalized([c.weight for c in snapshot])
    summaries = tuple(ChannelSummary(c.channel_id, c.status, bool(c.weight > 0),
                                     p, len(c.memory_ids))
                      for c, p in zip(snapshot, probabilities))
    underflow = tuple(c.channel_id for c, p in zip(snapshot, probabilities)
                      if c.weight > 0 and p == 0)
    contributions: dict[str, list[RankContribution]] = {i: [] for i in first_seen}
    for channel, p in zip(snapshot, probabilities):
        if channel.weight <= 0:
            continue
        for rank, memory_id in enumerate(channel.memory_ids, 1):
            contributions[memory_id].append(
                RankContribution(channel.channel_id, rank, p * (61.0 / (60 + rank))))
    relevance = {i: _unit(math.fsum(v.contribution for v in values))
                 for i, values in contributions.items()}
    ordered = tuple(sorted(first_seen, key=lambda i: (-relevance[i], first_seen[i])))

    support_snapshot: dict[str, dict[str, float]] = {}
    if support is not None:
        if not isinstance(support, Mapping):
            raise TypeError("support must be a mapping")
        for key, values in support.items():
            ident = _identifier(key, "support memory_id")
            if ident not in first_seen:
                raise ValueError("unknown support memory_id")
            if not isinstance(values, Mapping):
                raise TypeError("candidate support must be a mapping")
            copied = {}
            for aspect, value in values.items():
                aspect = _identifier(aspect, "support aspect_id")
                if aspect not in aspect_ids:
                    raise ValueError("unknown support aspect_id")
                copied[aspect] = float(_real(value, "support", unit=True))
            support_snapshot[ident] = copied
    pairs = tuple((i, a.aspect_id) for i in ordered for a in aspect_snapshot
                  if a.aspect_id in support_snapshot.get(i, {}))
    if not pairs and lam != 1:
        raise ValueError("no supplied support values require relevance_weight=1")
    candidates = [EvidenceCandidate(i, relevance[i], support_snapshot.get(i, {}))
                  for i in ordered]
    selection = select_evidence(candidates, aspect_snapshot, limit=limit, relevance_weight=lam)
    return RankedEvidenceReport(
        summaries, ordered, {i: relevance[i] for i in ordered},
        {i: tuple(contributions[i]) for i in ordered},
        "supplied" if pairs else "not_supplied", pairs, underflow, selection,
    )


__all__ = ["RankedChannel", "ChannelSummary", "RankContribution",
           "RankedEvidenceReport", "select_ranked_evidence"]
