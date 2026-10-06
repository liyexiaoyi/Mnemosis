"""Opt-in read-only recall with grounded annotations and required evidence."""
from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from enum import Enum
from fractions import Fraction
import re
import time
from typing import TYPE_CHECKING

from .evidence_annotation import (
    EvidenceAnnotator, EvidenceAspect, ModelReply, SkippedEvidence, SupportReplies,
    parse_question_plan, parse_support_batch,
)
from .evidence_selection import EvidenceCandidate, QueryAspect, RequiredEvidenceReport, select_required_evidence
from .ranked_evidence import RankedChannel, _identifier, _real, select_ranked_evidence
from .ranked_evidence_refinement import SupportSpan
from .types import MemoryKind, RecallResult, utcnow

if TYPE_CHECKING:
    from .engine import MemoryEngine

_OPEN_SET = re.compile(r"\b(?:all|every)\b|所有|全部|哪些", re.IGNORECASE)


def _serialize(value):
    if isinstance(value, Fraction):
        return f"{value.numerator}/{value.denominator}"
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {f.name: _serialize(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {key: _serialize(val) for key, val in value.items()}
    if isinstance(value, (tuple, list)):
        return [_serialize(v) for v in value]
    return value


@dataclass(frozen=True, slots=True)
class EvidenceRecallReport:
    status: str
    reason: str | None
    baseline: tuple[RecallResult, ...]
    results: tuple[RecallResult, ...]
    candidate_ids: tuple[str, ...]
    aspects: tuple[EvidenceAspect, ...]
    annotation_status: str
    annotation_errors: tuple[str, ...]
    skipped: tuple[SkippedEvidence, ...]
    support: dict[str, dict[str, int]]
    support_spans: dict[str, dict[str, SupportSpan]]
    relevance_by_id: dict[str, float]
    selector: RequiredEvidenceReport | None
    model_replies: tuple[ModelReply, ...]
    timings: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        return {f.name: _serialize(getattr(self, f.name)) for f in fields(self)
                if f.name != "model_replies"}


def _integer(value: int, name: str, lo: int, hi: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer, not bool")
    if not lo <= value <= hi:
        raise ValueError(f"{name} must be {lo}..{hi}")


def _validate(query: str, annotator: EvidenceAnnotator, top_k: int,
              relevance_weight: float, search_budget: int) -> None:
    if not isinstance(query, str) or not query.strip() or len(query) > 4096:
        raise ValueError("query must have 1..4096 codepoints and not be blank")
    query.encode("utf-8")
    _integer(top_k, "top_k", 1, 100)
    _integer(search_budget, "search_budget", 0, 100000)
    _real(relevance_weight, "relevance_weight", unit=True)
    if annotator is None or not callable(getattr(annotator, "plan", None)) or not callable(
            getattr(annotator, "support", None)):
        raise ValueError("an explicit evidence annotator is required")
    budget = getattr(annotator, "budget_seconds", None)
    if isinstance(budget, bool) or not isinstance(budget, (int, float)) or not 0 < budget <= 60:
        raise ValueError("annotator budget_seconds must be positive and <=60")


def select_from_snapshot(query: str, candidates: Sequence[RecallResult], *, annotator: EvidenceAnnotator,
                         top_k: int = 5, relevance_weight: float = .5,
                         search_budget: int = 10000) -> EvidenceRecallReport:
    """Same annotation/math path for an already retrieved, ordered candidate pool."""
    _validate(query, annotator, top_k, relevance_weight, search_budget)
    if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence) or len(candidates) > 100:
        raise ValueError("expected at most 100 recall results")
    start = time.monotonic()
    snapshot = tuple(deepcopy(candidates))
    ids = []
    for result in snapshot:
        if not isinstance(result, RecallResult) or not isinstance(result.item.content, str):
            raise TypeError("candidates must be RecallResult with text")
        ids.append(_identifier(result.item.id, "memory_id"))
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate candidate memory_id")
    baseline = snapshot[:top_k]
    texts = {r.item.id: r.item.content for r in snapshot}
    aspects: tuple[EvidenceAspect, ...] = ()
    errors: list[str] = []
    skipped: list[SkippedEvidence] = []
    replies: list[ModelReply] = []
    support: dict[str, dict[str, int]] = {}
    spans: dict[str, dict[str, SupportSpan]] = {}
    relevance: dict[str, float] = {}
    timings = dict(recall=0., plan=0., support=0., math=0., total=0.)

    def finish(status, reason=None, selected=(), annotation="not_run", selector=None):
        timings["total"] = time.monotonic() - start
        return EvidenceRecallReport(status, reason, baseline, tuple(selected), tuple(ids), aspects,
            annotation, tuple(errors), tuple(skipped), deepcopy(support), deepcopy(spans),
            dict(relevance), selector, tuple(replies), dict(timings))

    if not snapshot:
        return finish("not_applicable", "empty_candidate_pool")
    if _OPEN_SET.search(query):
        return finish("not_applicable", "open_set_guard", baseline)
    deadline = time.monotonic() + annotator.budget_seconds
    phase = time.monotonic()
    try:
        plan_reply = annotator.plan(query, deadline=deadline)
        if not isinstance(plan_reply, ModelReply):
            raise ValueError("invalid plan reply")
        replies.append(plan_reply)
        if plan_reply.error:
            raise ValueError(plan_reply.error)
        plan = parse_question_plan(plan_reply.payload)
    except (OSError, ValueError, TypeError) as exc:
        timings["plan"] = time.monotonic() - phase
        errors.append("plan: " + str(exc)[:200])
        return finish("annotation_failed", "invalid_plan", annotation="failed")
    timings["plan"] = time.monotonic() - phase
    aspects = plan.aspects
    if plan.scope != "finite" or not aspects:
        return finish("not_applicable", plan.scope if plan.scope != "finite" else "empty_aspects", baseline)
    phase = time.monotonic()
    try:
        annotated = annotator.support(query, aspects, dict(texts), deadline=deadline)
        if not isinstance(annotated, SupportReplies) or len(annotated.batches) > 13:
            raise ValueError("invalid support batch envelope")
        seen: set[str] = set()
        for batch in annotated.batches:
            batch_ids = batch.memory_ids
            try:
                if (not 1 <= len(batch_ids) <= 8 or len(set(batch_ids)) != len(batch_ids)
                        or any(i not in texts or i in seen for i in batch_ids)):
                    raise ValueError("invalid or repeated batch IDs")
                seen.update(batch_ids)
                if not isinstance(batch.reply, ModelReply):
                    raise ValueError("invalid support reply")
                replies.append(batch.reply)
                if batch.reply.error:
                    raise ValueError(batch.reply.error)
                parsed = parse_support_batch(batch.reply.payload, aspects=aspects,
                                             source_texts={i: texts[i] for i in batch_ids})
                support.update(parsed.support)
                spans.update(parsed.spans)
            except (ValueError, TypeError) as exc:
                errors.append("support: " + str(exc)[:200])
        for skip in annotated.skipped:
            if (not isinstance(skip, SkippedEvidence) or skip.memory_id not in texts
                    or skip.memory_id in seen):
                errors.append("support: invalid skipped ID")
            else:
                seen.add(skip.memory_id)
                skipped.append(skip)
        skipped.extend(SkippedEvidence(i, "provider_missing") for i in ids if i not in seen)
    except (OSError, ValueError, TypeError) as exc:
        errors.append("support: " + str(exc)[:200])
    timings["support"] = time.monotonic() - phase
    valid_pairs = sum(map(len, support.values()))
    if not valid_pairs:
        return finish("annotation_failed", "no_valid_support_decisions", annotation="failed")
    annotation = "complete" if valid_pairs == len(ids) * len(aspects) and not errors and not skipped else "partial"
    phase = time.monotonic()
    ranked = select_ranked_evidence((RankedChannel("recall", tuple(ids)),), (),
                                   limit=top_k, relevance_weight=1)
    relevance = ranked.relevance_by_id
    selector = select_required_evidence(
        [EvidenceCandidate(i, relevance[i], support.get(i, {})) for i in ids],
        [QueryAspect(a.aspect_id) for a in aspects], required_aspects=[a.aspect_id for a in aspects],
        limit=top_k, relevance_weight=relevance_weight, search_budget=search_budget)
    timings["math"] = time.monotonic() - phase
    by_id = {r.item.id: r for r in snapshot}
    selected = tuple(by_id[i] for i in selector.selection.selected_ids) if selector.selection else ()
    return finish(selector.status, selected=selected, annotation=annotation, selector=selector)


def recall_evidence(engine: MemoryEngine, query: str, *, annotator: EvidenceAnnotator,
                    top_k: int = 5, candidate_limit: int = 100, relevance_weight: float = .5,
                    search_budget: int = 10000, kind: MemoryKind | None = None,
                    now: datetime | None = None, context: str | None = None,
                    exclude_ids: set[str] | None = None, temporal_policy: str = "content",
                    lexical_policy: str = "literal", candidate_policy: str = "legacy",
                    rerank_policy: str = "legacy") -> EvidenceRecallReport:
    _validate(query, annotator, top_k, relevance_weight, search_budget)
    _integer(candidate_limit, "candidate_limit", 1, 100)
    if top_k > candidate_limit:
        raise ValueError("top_k exceeds candidate_limit")
    if kind is not None and not isinstance(kind, MemoryKind):
        raise TypeError("kind must be MemoryKind or None")
    if context is not None and not isinstance(context, str):
        raise TypeError("context must be text or None")
    if exclude_ids is not None:
        if not isinstance(exclude_ids, set):
            raise TypeError("exclude_ids must be a set")
        for key in exclude_ids:
            _identifier(key, "exclude_ids")
        exclude_ids = set(exclude_ids)
    now = utcnow() if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be an aware datetime")
    for value, allowed, name in (
        (temporal_policy, ("content", "source"), "temporal_policy"),
        (lexical_policy, ("literal", "inflection"), "lexical_policy"),
        (candidate_policy, ("legacy", "quota"), "candidate_policy"),
        (rerank_policy, ("legacy", "semantic_reserve"), "rerank_policy")):
        if value not in allowed:
            raise ValueError(f"invalid {name}")
    if rerank_policy == "semantic_reserve" and candidate_policy != "quota":
        raise ValueError("semantic_reserve requires quota")
    if candidate_policy == "quota" and (getattr(engine, "embedder", None) is None
            or getattr(engine, "vector_index", None) is None
            or engine.embedder is not getattr(engine, "index_embedder", None)):
        raise ValueError("quota requires matching index/embedder")
    phase = time.monotonic()
    with engine._lock:
        snapshot = tuple(deepcopy(engine.recall(query, kind=kind, top_k=candidate_limit,
            now=now, read_only=True, context=context, exclude_ids=exclude_ids,
            temporal_policy=temporal_policy, lexical_policy=lexical_policy,
            candidate_policy=candidate_policy, rerank_policy=rerank_policy)))
    recall_seconds = time.monotonic() - phase
    report = select_from_snapshot(query, snapshot, annotator=annotator, top_k=top_k,
                                  relevance_weight=relevance_weight, search_budget=search_budget)
    timings = {**report.timings, "recall": recall_seconds,
               "total": report.timings["total"] + recall_seconds}
    return replace(report, timings=timings)
