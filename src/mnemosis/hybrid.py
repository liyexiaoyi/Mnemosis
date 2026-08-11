"""Fused multi-path retrieval for long interactive memory.

Motivated by:
- LongMemEval (Wu et al., ICLR 2025): multi-key indexing and time-aware query
  expansion improve retrieval on long multi-session histories.
- Reciprocal Rank Fusion (Cormack, Clarke & Buettcher, SIGIR 2009): combining
  independent rankings is more robust than trusting any single scorer.
- Chronos (temporal-aware event retrieval): time cues and query time intents
  narrow the search space for temporal questions.
- Encoding specificity (Tulving & Thomson, 1973) and recency (Ebbinghaus,
  1885): cues stored with a memory and its time of encoding are legitimate
  retrieval signals.

The implementation is zero-dependency and deterministic: keyword recall,
character n-gram recall, RRF fusion, light English inflection expansion,
recency direction, cue overlap and date-range hints.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from .embedding import NGramEmbedder
from .types import RecallResult, utcnow


_DATE_RE = re.compile(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})")
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7,
    "jul": 7, "august": 8, "aug": 8, "september": 9, "sep": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}
_OLDEST_WORDS = {
    "first", "earliest", "initially", "started", "began",
}
_NEWEST_WORDS = {
    "latest", "recent", "recently", "current", "currently", "now", "since",
    "updated", "changed", "update", "newest",
}
_CUE_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "of",
    "for", "with", "was", "were", "is", "are", "be", "been", "being", "it",
    "this", "that", "these", "those", "i", "you", "he", "she", "we", "they",
    "my", "your", "me", "him", "her", "us", "them", "have", "has", "had",
    "do", "does", "did", "can", "could", "will", "would", "should", "from",
    "as", "by", "not", "no", "yes", "about", "into", "than", "then", "there",
}


def english_inflections(tokens: Iterable[str]) -> set[str]:
    """Light English inflection expansion (plural / tense variants)."""
    out = set(tokens)
    for token in tokens:
        if not re.fullmatch(r"[a-z]+", token) or len(token) < 4:
            continue
        if token.endswith("ies") and len(token) > 4:
            out.add(token[:-3] + "y")
        elif token.endswith("es") and len(token) > 3:
            out.add(token[:-2])
            out.add(token[:-1])
        elif token.endswith("s") and len(token) > 3:
            out.add(token[:-1])
        if token.endswith("ing") and len(token) > 5:
            out.add(token[:-3])
            out.add(token[:-3] + "e")
        if token.endswith("ed") and len(token) > 4:
            out.add(token[:-2])
            out.add(token[:-1])
        if token.endswith("ly") and len(token) > 5:
            out.add(token[:-2])
    return out


def _extract_date(text: str) -> datetime | None:
    match = _DATE_RE.search(text)
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def temporal_intent(query: str) -> dict:
    """Detect time intent and date hints from a query (time-aware expansion)."""
    lowered = query.lower()
    words = set(re.findall(r"[a-z']+", lowered))
    direction: str | None = None
    if words & _OLDEST_WORDS:
        direction = "oldest"
    if words & _NEWEST_WORDS:
        direction = "newest"
    hints: dict = {"direction": direction}
    date = _extract_date(lowered)
    after_match = re.search(r"after\s+([^.,;?]+)", lowered)
    before_match = re.search(r"before\s+([^.,;?]+)", lowered)
    if after_match:
        after = _extract_date(after_match.group(1))
        if after:
            hints["after"] = after
            hints["direction"] = "newest"
    if before_match:
        before = _extract_date(before_match.group(1))
        if before:
            hints["before"] = before
            hints["direction"] = "oldest"
    year_match = _YEAR_RE.search(lowered)
    if year_match:
        hints["year"] = int(year_match.group(0))
    if date:
        hints["date"] = date
        hints["year"] = date.year
        hints["month"] = date.month
    for month_name, month_num in _MONTHS.items():
        if month_name == "may":
            # "I may go" is a modal verb, not the month; only accept "may"
            # when followed by a day/year number or written as "May" in the
            # original query.
            if re.search(
                r"\bmay\s+(?:\d{1,2}(?:st|nd|rd|th)?|\d{4})", lowered
            ) or " May" in query:
                hints["month"] = month_num
                break
            continue
        if re.search(rf"\b{month_name}\b", lowered):
            hints["month"] = month_num
            break
    return hints


def rrf_scores(ranked_ids: list[list[str]], k: int = 60) -> dict[str, float]:
    """Reciprocal Rank Fusion over several id rankings."""
    scores: dict[str, float] = {}
    for ranking in ranked_ids:
        for rank, memory_id in enumerate(ranking):
            scores[memory_id] = scores.get(memory_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


def weighted_rrf(rankings: list[tuple[list[str], float]], k: int = 60) -> dict[str, float]:
    """RRF with a per-retriever weight."""
    scores: dict[str, float] = {}
    for ranking, weight in rankings:
        for rank, memory_id in enumerate(ranking):
            scores[memory_id] = scores.get(memory_id, 0.0) + weight / (k + rank + 1)
    return scores


def _item_date(item) -> datetime | None:
    for cue in getattr(item, "cues", []) or []:
        if cue.startswith("date:"):
            parsed = _extract_date(cue)
            if parsed:
                return parsed
    return None


def _date_boost(hints: dict, item) -> float:
    """1.0 when the query's date hints match the memory's stored date."""
    item_date = _item_date(item)
    if item_date is None:
        return 0.0
    if hints.get("after") and item_date < hints["after"]:
        return 0.0
    if hints.get("before") and item_date > hints["before"]:
        return 0.0
    if "date" in hints or "after" in hints or "before" in hints:
        return 1.0
    if hints.get("year") and item_date.year == hints["year"]:
        return 1.0
    if hints.get("month") and item_date.month == hints["month"]:
        return 1.0
    return 0.0


def _recency_score(item, now: datetime, direction: str, oldest_ts: float, newest_ts: float) -> float:
    stamp = item.created_at or now
    if item.updated_at is not None and stamp is not None:
        stamp = max(stamp, item.updated_at)
    ts = stamp.timestamp() if stamp else now.timestamp()
    span = newest_ts - oldest_ts
    if span <= 0:
        return 0.5
    normalized = (ts - oldest_ts) / span
    return normalized if direction == "newest" else 1.0 - normalized


def _cue_overlap(query_terms: set[str], item) -> float:
    cue_tokens: set[str] = set()
    for cue in getattr(item, "cues", []) or []:
        if not (
            cue.startswith(("sid:", "date:", "session:", "id:", "topic:"))
            or any(ch.isdigit() for ch in cue)
        ):
            continue
        cue = re.sub(r"^(?:sid|date|session|id|topic):", "", cue)
        for token in re.findall(r"[a-z0-9]+", cue):
            if token in _CUE_STOPWORDS or len(token) < 4:
                continue
            cue_tokens.add(token)
    if not query_terms or not cue_tokens:
        return 0.0
    meaningful = {
        token for token in query_terms
        if token not in _CUE_STOPWORDS and len(token) >= 4
    }
    if not meaningful:
        return 0.0
    hits = len(meaningful & cue_tokens)
    return hits / max(1.0, len(meaningful) ** 0.5)


def _rewritten_query(query: str, expanded: set[str], original: set[str]) -> str:
    additions = sorted(expanded - original)
    if not additions:
        return query
    return query + " " + " ".join(additions)


def _dense_results(
    engine,
    query: str,
    kind,
    embedder,
    top_k: int,
    vector_index=None,
) -> list:
    """Dense-only candidate pass that bypasses the lexical gate.

    The built-in recall path prunes candidates to memories sharing at least
    one query term; a pure semantic match (paraphrase with zero lexical
    overlap) would never enter. This pass scores every active memory directly
    with the external embedder, reusing the store's per-content cache.
    """
    store = getattr(engine, "store", None)
    if vector_index is not None:
        query_vector = embedder.embed(query)
        hits = vector_index.search(query_vector, top_k=top_k)
        results = []
        for memory_id, score in hits:
            item = store.backend.get(memory_id) if store is not None else None
            if item is not None:
                results.append(
                    RecallResult(item=item, score=score, reasons=["dense:index"])
                )
        return results
    items = store.all_active(kind=kind) if store is not None else []
    query_vector = embedder.embed(query)
    vectors = [embedder.embed(item.content) for item in items]
    try:
        import numpy as np  # noqa: PLC0415

        matrix = np.asarray(vectors, dtype=np.float32)
        query_vec = np.asarray(query_vector, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1)
        qnorm = float(np.linalg.norm(query_vec))
        if qnorm == 0.0:
            scores = np.zeros(len(items), dtype=np.float32)
        else:
            scores = matrix @ query_vec / (norms * qnorm + 1e-9)
        order = np.argsort(-scores)[:top_k]
        return [
            RecallResult(item=items[int(index)], score=float(scores[int(index)]), reasons=["dense"])
            for index in order
        ]
    except ImportError:
        scored = sorted(
            ((embedder.cosine(query_vector, vector), item) for vector, item in zip(vectors, items)),
            key=lambda row: -row[0],
        )
        return [
            RecallResult(item=item, score=score, reasons=["dense"])
            for score, item in scored[:top_k]
        ]


def fused_recall(
    engine,
    query: str,
    *,
    kind=None,
    top_k: int = 5,
    now: datetime | None = None,
    pass_k: int = 24,
    rrf_k: int = 60,
    kw_weight: float = 1.0,
    ng_weight: float = 1.0,
    dense_embedder=None,
    dense_weight: float = 1.6,
    vector_index=None,
    recency_weight: float = 0.08,
    cue_weight: float = 0.12,
    date_weight: float = 0.28,
    expansion: bool = True,
) -> list:
    """Fuse keyword + n-gram recalls with recency / cue / date signals."""
    from .types import tokenize

    now = now or utcnow()
    original = set(tokenize(query))
    expanded = set(original)
    if expansion:
        expanded |= english_inflections(original)
    rewritten = _rewritten_query(query, expanded, original)
    hints = temporal_intent(query)

    passes = []
    by_id: dict[str, object] = {}
    all_results = []
    if kw_weight > 0:
        kw_results = engine.recall(
            rewritten,
            kind=kind,
            top_k=pass_k,
            embedder=None,
            elaborate_links=False,
            suppression_factor=0.0,
            temporal_reason=False,
            reasoning_pack=False,
        )
        passes.append(([r.item.id for r in kw_results], kw_weight))
        all_results.extend(kw_results)
    if ng_weight > 0:
        ng_results = engine.recall(
            rewritten,
            kind=kind,
            top_k=pass_k,
            embedder=NGramEmbedder(),
            elaborate_links=False,
            suppression_factor=0.0,
            temporal_reason=False,
            reasoning_pack=False,
        )
        passes.append(([r.item.id for r in ng_results], ng_weight))
        all_results.extend(ng_results)
    dense_results = []
    if dense_embedder is not None:
        try:
            dense_results = _dense_results(
                engine,
                query,
                kind,
                dense_embedder,
                pass_k,
                vector_index=vector_index,
            )
        except Exception as exc:  # noqa: BLE001 - dense is an enhancement
            print(f"    dense pass failed, falling back: {exc}", flush=True)
            dense_results = []
        passes.append(([r.item.id for r in dense_results], dense_weight))
        all_results.extend(dense_results)
    for result in all_results:
        by_id.setdefault(result.item.id, result)

    ranked = weighted_rrf(passes, k=rrf_k)
    if not ranked:
        return []

    stamps = []
    for memory_id in ranked:
        item = by_id[memory_id].item
        stamp = item.created_at or now
        if item.updated_at is not None and stamp is not None:
            stamp = max(stamp, item.updated_at)
        stamps.append(stamp.timestamp() if stamp else now.timestamp())
    oldest_ts = min(stamps)
    newest_ts = max(stamps)

    scored = []
    for memory_id, fused in ranked.items():
        result = by_id[memory_id]
        item = result.item
        score = fused
        if hints.get("direction") and recency_weight:
            score += recency_weight * _recency_score(
                item, now, hints["direction"], oldest_ts, newest_ts
            )
        if cue_weight:
            score += cue_weight * _cue_overlap(expanded, item)
        if date_weight:
            score += date_weight * _date_boost(hints, item)
        scored.append((score, fused, memory_id))

    scored.sort(key=lambda row: (-row[0], -row[1]))
    return [by_id[mid] for _, _, mid in scored[:top_k]]


__all__ = [
    "english_inflections",
    "fused_recall",
    "rrf_scores",
    "temporal_intent",
]
