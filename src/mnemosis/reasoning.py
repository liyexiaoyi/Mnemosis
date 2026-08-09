"""Reasoning premise pack (dual-process / working-memory inspired).

Human principles (brain / cognition papers):

- *Dual-process theory* (Kahneman, 2011): System 1 is fast and associative
  (plain keyword recall), System 2 is slow and deliberative and needs ALL
  relevant premises in mind before it can reason.
- *Prefrontal working memory* (Miller & Cohen, 2001): PFC maintains
  task-relevant representations; a reasoning question ("谁最高", "单价贵
  多少") requires co-activating every premise on the same dimension, not
  just the lexically closest memory.
- *Arithmetic and the brain* (Dehaene, Molko, Wilson & Cohen, 2004): number
  and quantity live in a shared magnitude system (intraparietal sulcus);
  math questions should pull in all number-bearing memories of the asked
  person(s).
- *Chain-of-thought* (Wei et al., 2022) and *transitive inference* (Acuna
  et al., 2002): intermediate steps only work when the premises are present
  in the context; "A > B, B > C" questions need both links retrieved.

Implementation: for a detected reasoning question (math / compare /
transitive), memories that share the query's person cue AND carry the
reasoning dimension (a comparative word, or number+unit tokens) receive a
bounded boost, so the full "premise pack" surfaces in the top-k context.
Ordinary questions are untouched.
"""

from __future__ import annotations

import re

from .types import MemoryItem


_MATH_RE = re.compile(
    r"(多少|几(?:个|本|元|天|次|人|公里|岁)?|一共|总共|单价|每[本个元天公里]"
    r"|花了?\s*[\d一二三四五六七八九十百千万]+\s*(?:元|块)"
    r"|差多少|贵多少|便宜多少|多少钱|价格)"
)
_COMPARE_RE = re.compile(
    r"比.{1,8}(?:高|低|大|小|早|晚|贵|便宜|多|少|快|慢|长|短|好|近|远)"
    r"|(?:更|最)(?:高|低|大|小|早|晚|贵|便宜|昂贵|廉价|多|少|快|慢|长|短|好|近|远)"
    r"|(?:谁|哪个).{0,6}(?:更|最|比较)"
    r"|(?:更|最)(?:昂贵|廉价)"
)
_TRANSITIVE_RE = re.compile(
    r"(?:谁|哪个|几个人?中).{0,8}(?:最高|最矮|最贵|最便宜|最大|最小|最早|最晚|最近|最远)"
    r"|比.{1,8}(?:高|大|贵|早|晚|近|远).{0,12}比"
)

_DIMENSIONS = (
    "高", "低", "大", "小", "早", "晚", "贵", "便宜", "昂贵", "廉价",
    "多", "少", "快", "慢", "长", "短", "好", "近", "远",
)
_NUMBER_UNIT_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:元|块|本|个|天|次|人|公里|岁)")
_CN_NUMBER_UNIT_RE = re.compile(
    r"[一二三四五六七八九十百千万]+\s*(?:元|块|本|个|天|次|人|公里|岁)"
)


def reasoning_question_kind(query: str) -> str | None:
    """Return 'math' / 'compare' / 'transitive' for reasoning queries."""
    lowered = query.lower()
    if _MATH_RE.search(lowered):
        return "math"
    if _TRANSITIVE_RE.search(lowered):
        return "transitive"
    if _COMPARE_RE.search(lowered):
        return "compare"
    return None


def suggested_pack_size(query: str) -> int:
    """Estimate the working-memory set size a reasoning question needs.

    Prefrontal working memory (Miller & Cohen, 2001) holds the task-relevant
    premise set; a chain question ("A比B高，B比C高") or a multi-person
    question needs more premises held simultaneously, so the premise pack
    grows with the estimated premise count (bounded: 6..14).
    """
    size = 6
    lowered = query
    if lowered.count("比") >= 2:
        size = max(size, 10)
    for token, n in (
        ("三个人", 10),
        ("四个人", 12),
        ("五个人", 14),
        ("几个人", 10),
        ("三位", 10),
        ("四位", 12),
    ):
        if token in lowered:
            size = max(size, n)
    if ("、" in lowered) or ("分别" in lowered) or (
        "和" in lowered and "都" in lowered
    ):
        size = max(size, 8)
    if "差多少" in lowered or "单价" in lowered:
        size = max(size, 8)
    return min(size, 14)


def _has_dimension(content: str, kind: str) -> bool:
    if kind in ("compare", "transitive"):
        return any(ch in content for ch in ("比", "最")) or any(
            dim in content for dim in _DIMENSIONS
        ) or bool(
            _NUMBER_UNIT_RE.search(content) or _CN_NUMBER_UNIT_RE.search(content)
        )
    if kind == "math":
        return bool(
            _NUMBER_UNIT_RE.search(content) or _CN_NUMBER_UNIT_RE.search(content)
        )
    return False


def apply_premise_pack(
    scored: list[tuple[float, float, MemoryItem, list[str], bool]],
    candidates: list[MemoryItem],
    query: str,
    query_terms: set[str],
    *,
    boost_scale: float = 0.35,
    max_boost: float = 0.35,
) -> None:
    """Boost premise candidates for reasoning questions (in place)."""
    kind = reasoning_question_kind(query)
    if kind is None:
        return
    # persons referenced by the query (person cue of episodic/semantic items)
    persons: set[str] = set()
    for item in candidates:
        for cue in item.cues:
            if cue in query_terms and not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}", cue
            ):
                persons.add(cue)
    if not persons:
        return

    boosts: dict[str, float] = {}
    for item in candidates:
        if not (persons & set(item.cues)):
            continue
        if not _has_dimension(item.content, kind):
            continue
        boosts[item.id] = max(boosts.get(item.id, 0.0), max_boost)

    if not boosts:
        return
    by_id: dict[str, int] = {
        item.id: index for index, (_, _, item, _, _) in enumerate(scored)
    }
    by_item: dict[str, MemoryItem] = {item.id: item for item in candidates}
    reason = "\u63a8\u7406\u524d\u63d0\u5305\uff08\u540c\u7ef4\u5ea6\u8bb0\u5fc6\uff09"
    for memory_id, boost in boosts.items():
        index = by_id.get(memory_id)
        if index is not None:
            old_score, overlap, item, reasons, matched = scored[index]
            if boost > old_score:
                scored[index] = (
                    old_score + boost,
                    overlap,
                    item,
                    reasons + [reason],
                    matched,
                )
            elif not any(reason in r for r in reasons):
                scored[index] = (
                    old_score,
                    overlap,
                    item,
                    reasons + [reason],
                    matched,
                )
        else:
            item = by_item.get(memory_id)
            if item is not None:
                scored.append((boost, 0.0, item, [reason], False))
    scored.sort(key=lambda entry: entry[0], reverse=True)


__all__ = [
    "reasoning_question_kind",
    "suggested_pack_size",
    "apply_premise_pack",
]
