"""Static regression for accepted scalar types; checked by the typecheck job.

Keep runtime numerical regressions in the existing evidence test suites.
The checker must accept int/float/Fraction without optional Rust installed.
"""
from fractions import Fraction

from mnemosis.evidence_selection import QueryAspect, select_evidence, select_required_evidence
from mnemosis.evidence_refinement import refine_evidence
from mnemosis.ranked_evidence import RankedChannel, select_ranked_evidence
from mnemosis.ranked_evidence_refinement import refine_ranked_evidence


def numeric_api() -> None:
    aspects = [QueryAspect("role", 10**400), QueryAspect("other", Fraction(1, 3))]
    channels = [RankedChannel("lexical", [], 2), RankedChannel("semantic", [], Fraction(1, 3))]
    select_evidence([], aspects, relevance_weight=.5)
    select_required_evidence([], aspects, required_aspects={"role": 1}, relevance_weight=Fraction(1, 2))
    refine_evidence([], aspects, relevance_weight=Fraction(1, 2))
    select_ranked_evidence(channels, aspects, support={}, relevance_weight=1)
    refine_ranked_evidence(channels, aspects, support={}, relevance_weight=1.0)
