"""Bounded regular English word-form cues, never semantic equivalence.

Forms are query-local and checked through existing term postings. No corpus
scan, persisted stem index, external lemmatizer or derivational expansion.
"""
from __future__ import annotations
import re

_MAX_FORMS = 32
_WORD = re.compile(r"[a-z]{3,}")

def _undouble(stem: str) -> str:
    if len(stem) > 2 and stem[-1] == stem[-2] and stem[-1] not in "aeiou":
        return stem[:-1]
    return stem

def inflection_forms(token: str) -> frozenset[str]:
    """Generate conservative regular plural/tense cues, at most 32 forms.

    English spelling is ambiguous: these are relevance hints, not a claim
    that every generated form has the same meaning. Irregular verbs and
    derivational relations (research/researcher) are deliberately absent.
    """
    if not _WORD.fullmatch(token):
        return frozenset((token,))
    stems = {token}
    if token.endswith("ies") and len(token) > 4:
        stems.add(token[:-3] + "y")
    elif token.endswith("es") and len(token) > 4:
        stems.update((token[:-2], token[:-1]))
    elif token.endswith("s") and not token.endswith(("ss", "us", "is")):
        stems.add(token[:-1])
    if token.endswith("ing") and len(token) > 5:
        stem = token[:-3]
        stems.update((stem, stem + "e", _undouble(stem)))
    if token.endswith("ied") and len(token) > 4:
        stems.add(token[:-3] + "y")
    elif token.endswith("ed") and len(token) > 4:
        stem = token[:-2]
        stems.update((stem, stem + "e", _undouble(stem)))
    forms = {token}
    for stem in stems:
        if len(stem) < 3:
            continue
        forms.update((stem, stem + "s", stem + "es", stem + "ing", stem + "ed"))
        if stem.endswith("e"):
            forms.update((stem + "d", stem[:-1] + "ing"))
        if stem.endswith("y") and stem[-2] not in "aeiou":
            forms.update((stem[:-1] + "ies", stem[:-1] + "ied"))
        if (stem[-1] not in "aeiouwxy" and stem[-2] in "aeiou"
                and stem[-3] not in "aeiou"):
            forms.update((stem + stem[-1] + "ing", stem + stem[-1] + "ed"))
    return frozenset([token] + sorted(forms - {token})[:_MAX_FORMS - 1])

def inflection_groups(terms: set[str]) -> tuple[frozenset[str], ...]:
    """Merge intersecting word-form families so repeated forms count once."""
    groups: list[set[str]] = []
    owners: dict[str, int] = {}
    for term in sorted(terms):
        forms = set(inflection_forms(term))
        shared = {owners[form] for form in forms if form in owners}
        if shared:
            index = min(shared)
            for other in shared:
                forms.update(groups[other])
                groups[other].clear()
            groups[index] = forms
        else:
            index = len(groups)
            groups.append(forms)
        for form in forms:
            owners[form] = index
    return tuple(frozenset(group) for group in groups if group)


def _mean_idf_scale(hit_weight: float, total_weight: float,
                    group_count: int, matched_count: int) -> float:
    """Bound mean specificity for nonnegative cue weights; coverage is separate.

    Divide the sums first, avoiding an arbitrary floor on a tiny query mean.
    No hits or no positive query weight leaves the overlap neutral.
    """
    if total_weight <= 0.0 or matched_count <= 0:
        return 1.0
    relative_mean = (hit_weight / total_weight) * (group_count / matched_count)
    return min(2.0, 0.5 + 0.5 * relative_mean)
