"""Evaluation must exclude official abstention questions even with evidence flags."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"benchmarks"))
import bm25_cue_eval

class EvaluationLabelsTests(unittest.TestCase):
    def test_abstention_marker_overrides_incidental_evidence_flags(self):
        self.assertFalse(bm25_cue_eval.is_answerable("example_abs", {"incidental turn"}))
        self.assertTrue(bm25_cue_eval.is_answerable("example", {"gold turn"}))
        self.assertFalse(bm25_cue_eval.is_answerable("missing_labels", set()))
