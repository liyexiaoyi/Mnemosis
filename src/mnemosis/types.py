"""Core data model for Mnemosis."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "you", "your",
    "they", "them", "what", "when", "where", "how", "was", "were", "are",
    "have", "has", "had", "will", "would", "can", "could", "should", "about",
    "into", "over", "after", "before", "during", "because", "been", "being",
    "not", "but", "his", "her", "its", "our", "their", "there", "here",
    "then", "than", "also", "very", "just", "only", "some", "such",
}


def hash_content(content: str) -> str:
    """Stable content hash used for semantic deduplication."""
    normalized = re.sub(r"\s+", " ", content).strip().lower()
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _from_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


class MemoryKind(str, Enum):
    """What kind of memory an item is."""

    EPISODIC = "episodic"  # what happened: events, experiences, narrative
    SEMANTIC = "semantic"  # what is true: facts, preferences, stable rules


class SourceType(str, Enum):
    """Where a memory came from."""

    USER = "user"
    DOCUMENT = "document"
    AGENT = "agent"
    INFERENCE = "inference"  # derived by the system, not observed
    EXTERNAL = "external"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    RECYCLED = "recycled"


AFFECT_TAGS = {"positive", "negative", "arousing", "mixed", "neutral"}


@dataclass(slots=True)
class SourceRecord:
    """Provenance for a memory (human principle #6: source monitoring)."""

    origin: SourceType
    ref: str | None = None
    occurred_at: datetime | None = None
    trust: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin": self.origin.value,
            "ref": self.ref,
            "occurred_at": _iso(self.occurred_at),
            "trust": self.trust,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceRecord":
        return cls(
            origin=SourceType(data.get("origin", SourceType.EXTERNAL.value)),
            ref=data.get("ref"),
            occurred_at=_from_iso(data.get("occurred_at")),
            trust=float(data.get("trust", 1.0)),
        )


@dataclass(slots=True)
class MemoryItem:
    """A single memory with its lifecycle state."""

    content: str
    kind: MemoryKind
    source: SourceRecord
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cues: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=utcnow)
    last_access_at: datetime | None = None
    access_count: int = 0
    importance: float = 0.5
    strength: float = 1.0
    confidence: float = 1.0
    status: MemoryStatus = MemoryStatus.ACTIVE
    content_hash: str = field(default="")
    context: str | None = None
    affect: str | None = None
    evidence_count: int = 1
    storage_strength: float = 1.0
    updated_at: datetime | None = None
    revision_count: int = 0
    seq: int = 0
    last_review_at: datetime | None = None
    review_streak: int = 0
    retrieval_successes: int = 0
    retrieval_failures: int = 0

    def __post_init__(self) -> None:
        self.content_hash = self.content_hash or hash_content(self.content)
        self.cues = normalize_cues(self.cues)
        self.importance = _clamp01(self.importance)
        self.strength = _clamp01(self.strength)
        self.confidence = _clamp01(self.confidence)
        self.source.trust = _clamp01(self.source.trust)
        if self.affect is not None:
            affect = self.affect.strip().lower()
            self.affect = affect if affect in AFFECT_TAGS else None
        self.evidence_count = max(1, int(self.evidence_count))
        if self.context is not None:
            self.context = self.context.strip() or None
        self.storage_strength = max(0.1, min(2.0, self.storage_strength))
        self.revision_count = max(0, int(self.revision_count))
        self.seq = max(0, int(self.seq))
        self.review_streak = max(0, int(self.review_streak))
        self.retrieval_successes = max(0, int(self.retrieval_successes))
        self.retrieval_failures = max(0, int(self.retrieval_failures))

    def touch(self, now: datetime | None = None) -> None:
        """Mark as accessed; used by the forgetting curve reinforcement."""
        self.last_access_at = now or utcnow()
        self.access_count += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "content": self.content,
            "content_hash": self.content_hash,
            "source": self.source.to_dict(),
            "cues": self.cues,
            "created_at": _iso(self.created_at),
            "last_access_at": _iso(self.last_access_at),
            "access_count": self.access_count,
            "importance": self.importance,
            "strength": self.strength,
            "confidence": self.confidence,
            "status": self.status.value,
            "context": self.context,
            "affect": self.affect,
            "evidence_count": self.evidence_count,
            "storage_strength": self.storage_strength,
            "updated_at": _iso(self.updated_at),
            "revision_count": self.revision_count,
            "seq": self.seq,
            "last_review_at": _iso(self.last_review_at),
            "review_streak": self.review_streak,
            "retrieval_successes": self.retrieval_successes,
            "retrieval_failures": self.retrieval_failures,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryItem":
        return cls(
            content=data["content"],
            kind=MemoryKind(data["kind"]),
            source=SourceRecord.from_dict(data["source"]),
            id=data.get("id", uuid.uuid4().hex),
            cues=data.get("cues", []),
            created_at=_from_iso(data.get("created_at")) or utcnow(),
            last_access_at=_from_iso(data.get("last_access_at")),
            access_count=int(data.get("access_count", 0)),
            importance=float(data.get("importance", 0.5)),
            strength=float(data.get("strength", 1.0)),
            confidence=float(data.get("confidence", 1.0)),
            status=MemoryStatus(data.get("status", MemoryStatus.ACTIVE.value)),
            content_hash=data.get("content_hash", ""),
            context=data.get("context"),
            affect=data.get("affect"),
            evidence_count=data.get("evidence_count", 1),
            storage_strength=data.get("storage_strength", 1.0),
            updated_at=_from_iso(data.get("updated_at")),
            revision_count=data.get("revision_count", 0),
            seq=data.get("seq", 0),
            last_review_at=_from_iso(data.get("last_review_at")),
            review_streak=int(data.get("review_streak", 0)),
            retrieval_successes=int(data.get("retrieval_successes", 0)),
            retrieval_failures=int(data.get("retrieval_failures", 0)),
        )


@dataclass(slots=True)
class RecallResult:
    """A recalled memory with its score and explanation."""

    item: MemoryItem
    score: float
    reasons: list[str] = field(default_factory=list)


def normalize_cues(cues: list[str]) -> list[str]:
    """Lowercase, trim, drop empties, deduplicate."""
    seen: set[str] = set()
    out: list[str] = []
    for cue in cues:
        c = re.sub(r"\s+", " ", cue.strip().lower())
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def tokenize(text: str) -> list[str]:
    """Tokenize for keyword recall.

    Dates and hyphenated compounds stay atomic ("2026-02-01" is one token),
    then latin words (stopword-filtered) + CJK chars and bigrams.
    """
    lowered = text.lower()
    tokens: list[str] = []
    compound_pattern = r"[a-z0-9]+(?:[-_][a-z0-9]+)+"
    for token in re.findall(compound_pattern, lowered):
        if token not in STOPWORDS:
            tokens.append(token)
    rest = re.sub(compound_pattern, " ", lowered)
    for word in re.findall(r"[a-z0-9]+", rest):
        if len(word) > 1 and word not in STOPWORDS:
            tokens.append(word)
    cjk = "".join(re.findall(r"[\u4e00-\u9fff]", lowered))
    for ch in cjk:
        tokens.append(ch)
    for i in range(len(cjk) - 1):
        tokens.append(cjk[i : i + 2])
    return tokens


def extract_cues(content: str, limit: int = 6) -> list[str]:
    """Derive retrieval cues from content (encoding specificity).

    Latin words (>= 4 chars) and CJK bigrams become additional retrieval
    routes, so a memory can be reached from more than one angle even when the
    caller supplied no explicit cues.
    """
    seen: set[str] = set()
    cues: list[str] = []
    for token in tokenize(content):
        if token in STOPWORDS or token in seen or len(token) < 2:
            continue
        if re.fullmatch(r"[a-z0-9]+", token) and len(token) < 4:
            continue
        seen.add(token)
        cues.append(token)
        if len(cues) >= limit:
            break
    return cues


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


__all__ = [
    "MemoryItem",
    "MemoryKind",
    "MemoryStatus",
    "RecallResult",
    "SourceRecord",
    "SourceType",
    "extract_cues",
    "hash_content",
    "normalize_cues",
    "tokenize",
    "utcnow",
]
