"""Actual selection behavior and independent exact-arithmetic boundaries."""
from copy import deepcopy
from fractions import Fraction as F
import importlib
import math
import unittest


class EvidenceSelectionTest(unittest.TestCase):
    def setUp(self):
        try:
            self.api = importlib.import_module("mnemosis.evidence_selection")
        except ModuleNotFoundError as exc:
            if exc.name != "mnemosis.evidence_selection":
                raise
            self.fail("explicit evidence selector is not implemented")
        self.C = self.api.EvidenceCandidate
        self.A = self.api.QueryAspect
        self.select = self.api.select_evidence

    def fixture(self):
        return ([self.C("A", 1, {"X": 1}), self.C("B", .95, {"X": 1}),
                 self.C("C", .4, {"Y": 1})], [self.A("X", .6), self.A("Y", .4)])

    def test_fixed_capacity_prefers_complementary_support(self):
        candidates, aspects = self.fixture()
        report = self.select(candidates, aspects, limit=2)
        self.assertEqual(report.selected_ids, ("A", "C"))
        for got, want in ((report.objective, .85), (report.relevance_component, .7),
                          (report.coverage_component, 1),
                          (report.steps[0].total_gain, .55),
                          (report.steps[1].relevance_gain, .1),
                          (report.steps[1].coverage_gain, .2),
                          (report.steps[1].total_gain, .3)):
            self.assertAlmostEqual(got, want, delta=1e-12)
        self.assertEqual(report.aspect_coverage, {"X": 1, "Y": 1})
        self.assertEqual(report.uncovered_aspect_ids, ())
        self.assertEqual(report.partial_aspect_ids, ())
        self.assertAlmostEqual(report.steps[-1].objective_after, report.objective, delta=1e-12)

    def test_capacity_zero_one_and_underfilled_budget(self):
        candidates, aspects = self.fixture()
        for k, ids, objective in ((0, (), 0), (1, ("A",), .8),
                                 (5, ("A", "C", "B"), .735)):
            with self.subTest(k=k):
                r = self.select(candidates, aspects, limit=k)
                self.assertEqual(r.selected_ids, ids)
                self.assertAlmostEqual(r.objective, objective, delta=1e-12)
                self.assertEqual(r.requested_limit, k)
                self.assertEqual(r.candidate_count, 3)
        r = self.select([], aspects)
        self.assertEqual((r.selected_ids, r.objective), ((), 0))
        self.assertEqual(r.uncovered_aspect_ids, ("X", "Y"))

    def test_repeated_support_saturates_without_forced_filling(self):
        cs = [self.C("A", 1, {"X": 1}), self.C("B", .9, {"X": 1})]
        r = self.select(cs, [self.A("X")], limit=2, relevance_weight=0)
        self.assertEqual(r.selected_ids, ("A",))
        self.assertEqual(r.objective, 1)
        r = self.select([self.C("Z", 0, {})], [self.A("X")])
        self.assertEqual(r.selected_ids, ())

    def test_partial_and_multi_aspect_gains_are_reported(self):
        cs = [self.C("A", 0, {"X": .8, "Y": .1}),
              self.C("B", 0, {"X": .4, "Y": 1})]
        r = self.select(cs, [self.A("X"), self.A("Y")], limit=2, relevance_weight=0)
        self.assertEqual(r.selected_ids, ("B", "A"))
        self.assertAlmostEqual(r.objective, .9, delta=1e-12)
        self.assertAlmostEqual(r.steps[1].coverage_gain, .2, delta=1e-12)
        self.assertEqual(r.partial_aspect_ids, ("X",))
        self.assertEqual(r.aspect_coverage, {"X": .8, "Y": 1})

    def test_same_support_ids_and_ties_preserve_input_order(self):
        cs = [self.C("Z", 1, {"X": 1}), self.C("A", 1, {"X": 1})]
        for ids in (("Z", "A"), ("A", "Z")):
            with self.subTest(ids=ids):
                ordered = [next(c for c in cs if c.memory_id == i) for i in ids]
                self.assertEqual(self.select(ordered, [self.A("X")], limit=2,
                                            relevance_weight=1).selected_ids, ids)

    def test_empty_aspects_require_explicit_pure_relevance(self):
        cs = [self.C("A", .9, {}), self.C("B", 0, {})]
        r = self.select(cs, [], limit=2, relevance_weight=1)
        self.assertEqual(r.selected_ids, ("A",))
        self.assertAlmostEqual(r.objective, .45, delta=1e-12)
        self.assertEqual(r.aspect_coverage, {})
        for k in (0, 5):
            with self.subTest(k=k):
                with self.assertRaises(ValueError):
                    self.select([], [], limit=k)

    def test_missing_support_is_a_gap_not_an_answer_confirmation(self):
        r = self.select([self.C("A", .8, {}), self.C("B", .7, {})],
                        [self.A("X", 1), self.A("ignored", 0)], limit=2)
        self.assertEqual(r.selected_ids, ("A", "B"))
        self.assertEqual(r.coverage_component, 0)
        self.assertEqual(r.uncovered_aspect_ids, ("X",))
        self.assertEqual(r.partial_aspect_ids, ())

    def test_invalid_parameters_and_collections_do_not_bypass_zero_budget(self):
        candidates, aspects = self.fixture()
        cases = [({"limit": x}, ValueError) for x in (-1, 101)]
        cases += [({"limit": x}, TypeError) for x in (True, .5, "2", None)]
        cases += [({"relevance_weight": x, "limit": 0}, ValueError)
                  for x in (-.1, 1.1, float("nan"), float("inf"), -float("inf"))]
        cases += [({"relevance_weight": x, "limit": 0}, TypeError)
                  for x in (True, "0.5", None, 1j)]
        for kwargs, error in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(error):
                    self.select(candidates, aspects, **kwargs)
        for cs, aa in ((None, aspects), ("", aspects), ({}, aspects),
                       (candidates, None), (candidates, ""), ([object()], aspects),
                       (candidates, [object()])):
            with self.subTest(cs=type(cs).__name__, aa=type(aa).__name__):
                with self.assertRaises(TypeError):
                    self.select(cs, aa, limit=0)

    def test_invalid_candidate_fields_and_unknown_aspect(self):
        aspects = [self.A("X")]
        bad = [(self.C("A", v, {}), ValueError)
               for v in (-1, 2, float("nan"), float("inf"), -float("inf"))]
        bad += [(self.C("A", v, {}), TypeError) for v in (True, "1", None, 1j)]
        bad += [(self.C(i, 1, {}), ValueError) for i in ("", " A", "A ", " ")]
        bad += [(self.C(None, 1, {}), TypeError), (self.C("A", 1, []), TypeError),
                (self.C("A", 1, {"unknown": 1}), ValueError)]
        bad += [(self.C("A", 1, {"X": v}), ValueError)
                for v in (-.1, 1.1, float("nan"), float("inf"))]
        bad += [(self.C("A", 1, {"X": v}), TypeError) for v in (True, "1", None)]
        for candidate, error in bad:
            with self.subTest(candidate=candidate):
                with self.assertRaises(error):
                    self.select([candidate], aspects, limit=0)
        with self.assertRaises(ValueError):
            self.select([self.C("A", 1, {}), self.C("A", .5, {})], aspects)

    def test_invalid_aspect_fields_and_weights(self):
        for weight, error in ((-1, ValueError), (float("nan"), ValueError),
                              (float("inf"), ValueError), (True, TypeError),
                              (None, TypeError), ("1", TypeError)):
            with self.subTest(weight=weight):
                with self.assertRaises(error):
                    self.select([], [self.A("X", weight)], limit=0)
        for aspects in ([self.A("X", 0)], [self.A("X"), self.A("X")],
                        [self.A("")], [self.A(" X")]):
            with self.subTest(aspects=aspects):
                with self.assertRaises(ValueError): self.select([], aspects, limit=0)
        with self.assertRaises(TypeError): self.select([], [self.A(1)], limit=0)

    def test_candidate_and_aspect_budgets_are_enforced(self):
        cs = [self.C(str(i), 1, {}) for i in range(101)]
        aspects = [self.A(str(i)) for i in range(33)]
        r = self.select(cs[:100], aspects[:32], limit=100, relevance_weight=1)
        self.assertEqual(r.selected_ids, tuple(str(i) for i in range(100)))
        self.assertEqual(r.objective, 1)
        self.assertEqual(len(r.uncovered_aspect_ids), 32)
        with self.assertRaises(ValueError): self.select(cs, aspects[:32])
        with self.assertRaises(ValueError): self.select(cs[:100], aspects)

    def test_extreme_equal_weights_and_rescaling_are_stable(self):
        cs, aspects = self.fixture()
        for value in (1e308, 10**400):
            with self.subTest(value_type=type(value).__name__):
                r = self.select(cs, [self.A("X", value), self.A("Y", value)], limit=2)
                self.assertEqual(r.normalized_aspect_weights, {"X": .5, "Y": .5})
                self.assertEqual(r.selected_ids, ("A", "C"))
        for scale in (1e-200, 1, 1e200):
            with self.subTest(scale=scale):
                r = self.select(cs, [self.A("X", 3*scale), self.A("Y", 2*scale)], limit=2)
                self.assertEqual(r.selected_ids, ("A", "C"))
                self.assertAlmostEqual(r.objective, .85, delta=1e-12)

    def test_mixed_huge_integer_and_float_weights_do_not_overflow(self):
        for maximum in (10**400, F(10**400)):
            with self.subTest(maximum_type=type(maximum).__name__):
                r = self.select([self.C("A", 0, {"big": 1})],
                    [self.A("big", maximum), self.A("small", 1e308)],
                    limit=1, relevance_weight=0)
                self.assertEqual(r.selected_ids, ("A",))
                self.assertGreater(r.normalized_aspect_weights["small"], 0)
                self.assertTrue(math.isclose(r.normalized_aspect_weights["small"],
                                            1e-92, rel_tol=1e-12, abs_tol=0))
                self.assertEqual(r.uncovered_aspect_ids, ("small",))

    def test_numpy_real_and_huge_rational_weights(self):
        try:
            import numpy as np
        except ImportError:
            import os
            if os.environ.get("MNEMOSIS_TEST_NUMPY") == "1":
                raise
            self.skipTest("optional NumPy is not installed")
        for value in (np.float32(1e30), np.float64(1e308)):
            for maximum in (10**400, F(10**400)):
                with self.subTest(value_type=type(value).__name__,
                                  maximum_type=type(maximum).__name__):
                    r = self.select([self.C("A", 0, {"big": 1})],
                        [self.A("big", maximum), self.A("small", value)],
                        limit=1, relevance_weight=0)
                    exact = float(F(*value.as_integer_ratio()) / F(maximum))
                    self.assertTrue(math.isclose(r.normalized_aspect_weights["small"],
                                                exact, rel_tol=1e-12, abs_tol=0))
                    self.assertEqual(r.selected_ids, ("A",))
                    self.assertEqual(r.uncovered_aspect_ids, ("small",))

    def test_underflow_does_not_hide_original_positive_aspect(self):
        r = self.select([self.C("A", 0, {"big": 1})],
            [self.A("tiny", 1e-308), self.A("big", 1e308), self.A("ignored", 0)],
            limit=1, relevance_weight=0)
        self.assertEqual(r.selected_ids, ("A",))
        self.assertEqual(r.normalized_aspect_weights["tiny"], 0)
        self.assertEqual(r.uncovered_aspect_ids, ("tiny",))
        self.assertEqual(r.objective, 1)

    def test_input_and_report_mutation_do_not_leak_between_calls(self):
        cs, aspects = self.fixture()
        before = deepcopy((cs, aspects))
        first = self.select(cs, aspects, limit=2)
        first.aspect_coverage["X"] = 0
        first.normalized_aspect_weights["X"] = 99
        second = self.select(cs, aspects, limit=2)
        self.assertEqual((cs, aspects), before)
        self.assertEqual(second.aspect_coverage, {"X": 1, "Y": 1})
        self.assertAlmostEqual(second.objective, .85, delta=1e-12)

    def test_fixed_budget_score_ignores_null_candidate(self):
        cs, _ = self.fixture()
        weights = {"X": .6, "Y": .4}
        for candidates in (cs, [*cs, self.C("null", 0, {})]):
            with self.subTest(n=len(candidates)):
                scores = self.api._score_subset(candidates, weights, [0], limit=5, relevance_weight=.5)
                for got, want in zip(scores, (.2, .6, .4)):
                    self.assertAlmostEqual(got, want, delta=1e-12)

    def test_greedy_is_not_always_optimal(self):
        cs = [self.C(i, 0, {str(x): 1 for x in cover})
              for i, cover in (("A", (1,2,3,4)), ("B", (1,2,5)), ("C", (3,4,6)))]
        aspects = [self.A(str(i)) for i in range(1,7)]
        r = self.select(cs, aspects, limit=2, relevance_weight=0)
        self.assertEqual(r.selected_ids, ("A", "B"))
        self.assertAlmostEqual(r.objective, 5/6, delta=1e-12)
        self.assertAlmostEqual(self.api._score_subset(cs, {str(i): 1/6 for i in range(1,7)},
                              [1,2], limit=2, relevance_weight=0)[2], 1, delta=1e-12)

    def test_actual_subset_scores_obey_exact_oracle_and_diminishing_returns(self):
        # Exact rational inputs and expectations are independent of product helpers.
        matrices = [
            ([F(1), F(19,20), F(2,5)], [[F(1),F(0)],[F(1),F(0)],[F(0),F(1)]], [F(3,5),F(2,5)], F(1,2)),
            ([F(0)]*3, [[F(int(j in cover)) for j in range(6)]
                       for cover in ((0,1,2,3),(0,1,4),(2,3,5))], [F(1,6)]*6, F(0)),
            ([F(1,i+1) for i in range(8)], [[F((i+2*j)%5,4) for j in range(3)]
                                           for i in range(8)], [F(1,3)]*3, F(1,2))]
        for index, (rs, gs, ws, lam) in enumerate(matrices):
            cs = [self.C(str(i), float(rs[i]), {str(j):float(g) for j,g in enumerate(gs[i])}) for i in range(len(rs))]
            aa = [self.A(str(j),float(w)) for j,w in enumerate(ws)]
            for k in sorted(set((1,2,5,len(rs)))):
                with self.subTest(matrix=index, k=k):
                    actual, exact = {}, {}
                    for mask in range(1<<len(rs)):
                        ids = [i for i in range(len(rs)) if mask & (1<<i)]
                        if len(ids)>k: continue
                        R = sum((rs[i] for i in ids), F(0))/k
                        C = sum((ws[j]*max((gs[i][j] for i in ids),default=F(0)) for j in range(len(ws))),F(0))
                        want = (R,C,lam*R+(1-lam)*C)
                        got = self.api._score_subset(cs, {str(j):float(w) for j,w in enumerate(ws)}, ids, limit=k, relevance_weight=float(lam))
                        for a,b in zip(got,want): self.assertAlmostEqual(a,float(b),delta=1e-12)
                        self.assertGreaterEqual(got[2],-1e-12);self.assertLessEqual(got[2],1+1e-12)
                        actual[mask], exact[mask] = got[2], want[2]
                    for mask,value in actual.items():
                        for i in range(len(rs)):
                            bigger = mask | (1<<i)
                            if bigger not in actual or bigger == mask: continue
                            gain = actual[bigger]-value
                            self.assertGreaterEqual(gain,-1e-12)
                            for j in range(len(rs)):
                                sup = mask | (1<<j); both = bigger | (1<<j)
                                if j==i or sup==mask or both not in actual: continue
                                self.assertGreaterEqual(gain+1e-12,actual[both]-actual[sup])
                    report = self.select(cs,aa,limit=k,relevance_weight=float(lam))
                    chosen = sum(1<<int(i) for i in report.selected_ids)
                    self.assertAlmostEqual(report.objective,float(exact[chosen]),delta=1e-12)
                    self.assertGreaterEqual(report.objective+1e-12,(1-math.exp(-1))*float(max(exact.values())))


if __name__ == "__main__":
    unittest.main()
