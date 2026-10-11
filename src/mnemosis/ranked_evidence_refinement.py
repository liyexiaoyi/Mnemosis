"""Independent ranked fusion plus one-swap evidence composition.

Rank agreement and supplied support are proxies, not factual verification.
No retrieval, models, storage, feedback or default-policy side effects.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Integral
from typing import cast

from .evidence_selection import EvidenceCandidate, QueryAspect, _RealValue
from .evidence_refinement import EvidenceRefinementReport, refine_evidence
from .ranked_evidence import (
    RankedChannel, RankedEvidenceReport, _identifier, _real, _sequence, select_ranked_evidence,
)


@dataclass(frozen=True, slots=True)
class SupportSpan:
    """Caller-supplied Python-string codepoint offsets and exact quotation."""
    start: int
    end: int
    quote: str


def _validate_grounding(
    channels: Sequence[RankedChannel],
    aspects: Sequence[QueryAspect],
    support: Mapping[str, Mapping[str, _RealValue]] | None,
    source_texts: Mapping[str, str],
    support_spans: Mapping[str, Mapping[str, SupportSpan]],
) -> tuple[RankedChannel, ...]:
    """Validate supplied text consistency before either scoring stage.

    This does not establish semantic entailment or independent provenance.
    Snapshot channels so membership checks and the ranking use the same IDs.
    """
    _sequence(channels, "channels", 8)
    snapshot = []
    eligible: set[str] = set()
    for channel in channels:
        if not isinstance(channel, RankedChannel):
            raise TypeError("channels must contain RankedChannel values")
        _sequence(channel.memory_ids, "memory_ids", 100)
        ids = tuple(_identifier(i, "memory_id") for i in channel.memory_ids)
        weight = _real(channel.weight, "channel weight")
        snapshot.append(RankedChannel(channel.channel_id, ids, weight, channel.status))
        if weight > 0:
            eligible.update(ids)
    if len(eligible) > 100:
        raise ValueError("enabled candidate union exceeds 100")
    aspect_ids = set()
    for aspect in aspects:
        if not isinstance(aspect, QueryAspect):
            raise TypeError("aspects must contain QueryAspect values")
        key = _identifier(aspect.aspect_id, "aspect_id")
        if key in aspect_ids:
            raise ValueError("duplicate aspect_id")
        aspect_ids.add(key)

    supplied = {}
    if support is not None:
        if not isinstance(support, Mapping):
            raise TypeError("support must be a mapping")
        for memory_id, values in support.items():
            key = _identifier(memory_id, "support memory_id")
            if key not in eligible:
                raise ValueError("unknown support memory_id")
            if not isinstance(values, Mapping):
                raise TypeError("candidate support must be a mapping")
            for aspect_id, value in values.items():
                aspect_id = _identifier(aspect_id, "support aspect_id")
                if aspect_id not in aspect_ids:
                    raise ValueError("unknown support aspect_id")
                supplied[key, aspect_id] = _real(value, "support", unit=True)

    if not isinstance(source_texts, Mapping):
        raise TypeError("source_texts must be a mapping")
    if len(source_texts) > 100:
        raise ValueError("source_texts exceeds 100")
    texts = {}
    total_chars = 0
    for memory_id, content in source_texts.items():
        key = _identifier(memory_id, "source_texts memory_id")
        if key not in eligible:
            raise ValueError("unknown source_texts memory_id")
        if not isinstance(content, str):
            raise TypeError("source text must be a string")
        if len(content) > 65536:
            raise ValueError("source text exceeds 65536 characters")
        total_chars += len(content)
        if total_chars > 1048576:
            raise ValueError("source texts exceed 1048576 total characters")
        texts[key] = content

    if not isinstance(support_spans, Mapping):
        raise TypeError("support_spans must be a mapping")
    if len(support_spans) > 100:
        raise ValueError("support_spans exceeds 100")
    witnessed = set()
    for memory_id, spans in support_spans.items():
        key = _identifier(memory_id, "support_spans memory_id")
        if key not in eligible:
            raise ValueError("unknown support_spans memory_id")
        if not isinstance(spans, Mapping):
            raise TypeError("candidate support_spans must be a mapping")
        if len(spans) > 32:
            raise ValueError("candidate support_spans exceeds 32")
        for aspect_id, span in spans.items():
            aspect_id = _identifier(aspect_id, "support_spans aspect_id")
            label = f"{key}/{aspect_id}"
            if (key, aspect_id) not in supplied:
                raise ValueError(f"{label}: span has no supplied support pair")
            if not isinstance(span, SupportSpan):
                raise TypeError(f"{label}: span must be a SupportSpan")
            for offset in (span.start, span.end):
                if isinstance(offset, bool) or not isinstance(offset, Integral):
                    raise TypeError(f"{label}: offsets must be integers, not bool")
            if not isinstance(span.quote, str):
                raise TypeError(f"{label}: quote must be a string")
            if not span.quote:
                raise ValueError(f"{label}: quote must be nonempty")
            if key not in texts:
                raise ValueError(f"{label}: missing source text")
            start, end = int(span.start), int(span.end)
            if not 0 <= start < end <= len(texts[key]):
                raise ValueError(f"{label}: span outside source text")
            if texts[key][start:end] != span.quote:
                raise ValueError(f"{label}: quote does not match source text")
            witnessed.add((key, aspect_id))
    for pair, value in supplied.items():
        # Check original Real positivity before any binary64 underflow.
        if value > 0 and pair not in witnessed:
            raise ValueError(f"{pair[0]}/{pair[1]}: missing support span")
    return tuple(snapshot)


@dataclass(frozen=True, slots=True)
class RankedEvidenceRefinementReport:
    ranked_report: RankedEvidenceReport
    refinement: EvidenceRefinementReport


def refine_ranked_evidence(
    channels: Sequence[RankedChannel],
    aspects: Sequence[QueryAspect],
    *,
    support: Mapping[str, Mapping[str, _RealValue]] | None = None,
    limit: int = 5,
    relevance_weight: _RealValue = .5,
    source_texts: Mapping[str, str] | None = None,
    support_spans: Mapping[str, Mapping[str, SupportSpan]] | None = None,
) -> RankedEvidenceRefinementReport:
    """Compose the existing public models with identical supplied inputs.

    The old ranked API/report is unchanged. Final IDs are available through
    refinement.selected_ids; ranked_report.selection retains the original
    greedy trace. Refine once in ranked candidate order, using fused relevance
    and the same raw aspect weights/support, capacity and relevance weight.
    All original validation/bounds apply, including failure and absent support.
    Support maps are copied before either stage, within the 100/32 bounds.
    Inputs must not be concurrently mutated. No support is inferred from text.

    To preserve the existing public models, refinement recomputes the greedy
    baseline. This costs an extra greedy pass; it does not perform a second
    swap round or extra retrieval. Both old reports and default recall remain
    unchanged. One-swap optimality is only over the original neighborhood.

    Optional source_texts and support_spans must be supplied together. Both
    None preserve the existing behavior/report. When enabled, every raw
    positive supplied support pair needs one exact nonempty source quotation.
    All supplied spans (including zero support) are validated before ranking,
    even at capacity0. No normalization, automatic extraction or semantic
    entailment is performed; matching a quote does not prove its relevance.
    Source text is caller-provided, not independently fetched from storage.
    Bounds:100 texts,32 spans/candidate,65536 characters/text,1048576 total.
    """
    _sequence(aspects, "aspects", 32)
    aspect_snapshot = tuple(aspects)
    support_snapshot = support
    if isinstance(support, Mapping):
        # Valid support cannot exceed the enabled union/aspect bounds. Check
        # before copying, rather than allocating an unbounded malformed map.
        if len(support) > 100:
            raise ValueError("support exceeds 100 candidates")
        copied = {}
        for memory_id, values in support.items():
            if isinstance(values, Mapping):
                if len(values) > 32:
                    raise ValueError("candidate support exceeds 32 aspects")
                copied[memory_id] = dict(values)
            else:
                # Let the original validator reject malformed nested values.
                copied[memory_id] = values
        support_snapshot = copied
    if (source_texts is None) != (support_spans is None):
        raise ValueError("source_texts and support_spans must be supplied together")
    if source_texts is not None:
        assert support_spans is not None  # paired-input validation above
        channels = _validate_grounding(channels, aspect_snapshot, support_snapshot,
                                       source_texts, support_spans)
    ranked = select_ranked_evidence(
        channels, aspect_snapshot, support=support_snapshot,
        limit=limit, relevance_weight=relevance_weight,
    )
    candidates = [
        EvidenceCandidate(memory_id, ranked.relevance_by_id[memory_id],
                          # Ranked validation has checked these real scalars.
                          # Keep the originals for refinement's own validator;
                          # do not round raw support here.
                          cast(Mapping[str, float], support_snapshot.get(memory_id, {}))
                          if support_snapshot is not None else {})
        for memory_id in ranked.candidate_ids
    ]
    refinement = refine_evidence(
        candidates, aspect_snapshot, limit=ranked.selection.requested_limit,
        relevance_weight=relevance_weight,
    )
    return RankedEvidenceRefinementReport(ranked, refinement)


__all__ = ["SupportSpan", "RankedEvidenceRefinementReport", "refine_ranked_evidence"]
