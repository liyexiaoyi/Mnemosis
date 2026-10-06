"""Bounded model annotation protocol; literal grounding is not entailment."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Protocol

from .evidence_selection import QueryAspect
from .ranked_evidence import RankedChannel, _identifier
from .ranked_evidence_refinement import SupportSpan, _validate_grounding


@dataclass(frozen=True, slots=True)
class EvidenceAspect:
    aspect_id: str
    description: str


@dataclass(frozen=True, slots=True)
class QuestionPlan:
    scope: str
    aspects: tuple[EvidenceAspect, ...]


@dataclass(frozen=True, slots=True)
class ModelReply:
    payload: object | None
    request: Mapping[str, object] | None
    response: Mapping[str, object] | None
    elapsed_seconds: float
    error: str | None

    def __post_init__(self) -> None:
        for name in ("payload", "request", "response"):
            object.__setattr__(self, name, deepcopy(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class SupportBatchReply:
    memory_ids: tuple[str, ...]
    reply: ModelReply


@dataclass(frozen=True, slots=True)
class SkippedEvidence:
    memory_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class SupportReplies:
    batches: tuple[SupportBatchReply, ...]
    skipped: tuple[SkippedEvidence, ...]


class EvidenceAnnotator(Protocol):
    budget_seconds: float

    def plan(self, query: str, *, deadline: float) -> ModelReply: ...

    def support(self, query: str, aspects: Sequence[EvidenceAspect],
                source_texts: Mapping[str, str], *, deadline: float) -> SupportReplies: ...


@dataclass(frozen=True, slots=True)
class ParsedSupportBatch:
    support: dict[str, dict[str, int]]
    spans: dict[str, dict[str, SupportSpan]]
    unknown_pairs: tuple[tuple[str, str], ...]


def _object(value: object, keys: set[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{name}: invalid object fields")
    return value


def parse_question_plan(payload: object) -> QuestionPlan:
    value = _object(payload, {"scope", "aspects"}, "plan")
    if not isinstance(value["scope"], str) or value["scope"] not in (
            "finite", "open_set", "unsupported"):
        raise ValueError("plan: invalid scope")
    rows = value["aspects"]
    if not isinstance(rows, list) or len(rows) > 8:
        raise ValueError("plan: expected at most 8 aspects")
    aspects = []
    for index, description in enumerate(rows):
        if not isinstance(description, str) or not 1 <= len(description.strip()) <= 512:
            raise ValueError("plan: description must have 1..512 codepoints")
        aspects.append(EvidenceAspect(f"a{index}", description.strip()))
    return QuestionPlan(value["scope"], tuple(aspects))


def parse_support_batch(payload: object, *, aspects: Sequence[EvidenceAspect],
                        source_texts: Mapping[str, str]) -> ParsedSupportBatch:
    value = _object(payload, {"decisions"}, "support")
    rows = value["decisions"]
    if not isinstance(rows, list) or len(rows) > 64:
        raise ValueError("support: expected at most 64 decisions")
    if len(aspects) > 8 or len(source_texts) > 8:
        raise ValueError("support batch exceeds 8 aspects/texts")
    roles = tuple(_identifier(a.aspect_id, "aspect_id") for a in aspects)
    if len(roles) != len(set(roles)):
        raise ValueError("duplicate aspect_id")
    texts = dict(source_texts)
    for key, text in texts.items():
        _identifier(key, "memory_id")
        if not isinstance(text, str) or len(text) > 2048:
            raise ValueError("support text exceeds 2048 codepoints")
    support: dict[str, dict[str, int]] = {}
    spans: dict[str, dict[str, SupportSpan]] = {}
    seen: set[tuple[str, str]] = set()
    for raw in rows:
        row = _object(raw, {"memory_id", "aspect_id", "verdict", "quote"}, "decision")
        key = _identifier(row["memory_id"], "memory_id")
        role = _identifier(row["aspect_id"], "aspect_id")
        if key not in texts or role not in roles:
            raise ValueError("unknown memory/aspect ID")
        if (key, role) in seen:
            raise ValueError("duplicate support decision")
        seen.add((key, role))
        verdict, quote = row["verdict"], row["quote"]
        if not isinstance(verdict, str) or verdict not in ("supported", "not_supported", "unknown"):
            raise ValueError("invalid verdict")
        if verdict != "supported":
            if quote is not None:
                raise ValueError("only supported decisions may have a quote")
            if verdict == "not_supported":
                support.setdefault(key, {})[role] = 0
            continue
        if not isinstance(quote, str) or not quote:
            raise ValueError("supported requires nonempty exact quote")
        start = texts[key].find(quote)
        if start < 0 or texts[key].find(quote, start + 1) >= 0:
            raise ValueError("quote must occur exactly once in this text")
        support.setdefault(key, {})[role] = 1
        spans.setdefault(key, {})[role] = SupportSpan(start, start + len(quote), quote)
    _validate_grounding((RankedChannel("recall", tuple(texts)),),
                        tuple(QueryAspect(role) for role in roles), support, texts, spans)
    missing = tuple((key, role) for key in texts for role in roles
                    if role not in support.get(key, {}))
    return ParsedSupportBatch(support, spans, missing)
