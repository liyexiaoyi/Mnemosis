"""Public ranked-evidence behavior; exact independent expectations."""
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction as F
import importlib
import math
import os
import unittest

from mnemosis.evidence_selection import QueryAspect


class RankedEvidenceTests(unittest.TestCase):
    def setUp(self):
        try:
            self.api = importlib.import_module("mnemosis.ranked_evidence")
        except ModuleNotFoundError as exc:
            if exc.name != "mnemosis.ranked_evidence":
                raise
            self.fail("ranked evidence interface is not implemented")
        self.C = self.api.RankedChannel
        self.select = self.api.select_ranked_evidence

    def sample(self):
        return ([self.C("L", ["A", "B", "C"]), self.C("D", ["A", "C", "B"])],
                [QueryAspect("X", .6), QueryAspect("Y", .4)],
                {"A": {"X": 1}, "B": {"X": 1}, "C": {"Y": 1}})

    def call(self, **kw):
        c, a, s = self.sample()
        c = kw.pop("channels", c)
        a = kw.pop("aspects", a)
        options = {"support": s, **kw}
        return self.select(c, a, **options)

    def plain(self, channels, **kw):
        return self.select(channels, [], **{"relevance_weight": 1, **kw})

    def test_complementary_selection_matches_fraction(self):
        r = self.call(limit=2)
        self.assertEqual(r.candidate_ids, ("A", "B", "C"))
        self.assertEqual(r.selection.selected_ids, ("A", "C"))
        self.assertAlmostEqual(r.relevance_by_id["B"], float(F(7625, 7812)), delta=1e-12)
        self.assertAlmostEqual(r.selection.objective, float(F(31061, 31248)), delta=1e-12)
        self.assertAlmostEqual(r.selection.relevance_component, float(F(15437, 15624)), delta=1e-12)
        self.assertEqual(r.selection.coverage_component, 1)
        self.assertEqual(r.support_state, "supplied")
        self.assertEqual(r.supplied_support_pairs, (("A", "X"), ("B", "X"), ("C", "Y")))
        self.assertEqual(r.underflow_channel_ids, ())
        self.assertEqual([(c.channel_id, c.status, c.enabled, c.normalized_weight, c.input_count)
                          for c in r.channels], [("L", "ok", True, .5, 3), ("D", "ok", True, .5, 3)])

    def test_empty_inner_maps_require_explicit_relevance(self):
        for support in (None, {}, {"A": {}}, {"A": {}, "B": {}}):
            with self.subTest(support=support):
                with self.assertRaises(ValueError):
                    self.call(support=support, limit=0)
                r = self.call(support=support, relevance_weight=1, limit=2)
                self.assertEqual(r.support_state, "not_supplied")
                self.assertEqual(r.supplied_support_pairs, ())
                self.assertEqual(r.selection.selected_ids, ("A", "B"))
                self.assertEqual(r.selection.uncovered_aspect_ids, ("X", "Y"))

    def test_failed_channel_is_not_empty(self):
        for k in (0, 5):
            with self.subTest(k=k), self.assertRaises(ValueError):
                self.plain([self.C("L", []), self.C("D", [], status="failed")], limit=k)
        with self.assertRaises(ValueError):
            self.plain([self.C("L", ["A"]), self.C("D", ["B"], weight=0, status="failed")])

    def test_disabled_channel_still_validates(self):
        bad = [self.C("D", ["B", "B"], weight=0), self.C("D", [" "], weight=0),
               self.C("D", ["B"], weight=0, status="other"), self.C("D", ["B"]*101, weight=0)]
        for channel in bad:
            with self.subTest(channel=channel), self.assertRaises(ValueError):
                self.plain([self.C("L", ["A"]), channel], limit=0)
        r = self.plain([self.C("L", ["A"]), self.C("D", ["B"], weight=0)])
        self.assertEqual(r.candidate_ids, ("A",))
        self.assertEqual(r.channels[1].input_count, 1)
        with self.assertRaises(ValueError):
            self.select([self.C("L", ["A"]), self.C("D", ["B"], weight=0)], [QueryAspect("X")],
                        support={"B": {"X": 1}}, relevance_weight=1)

    def test_explicit_zero_is_supplied(self):
        r = self.call(support={"A": {"X": 0}}, limit=2)
        self.assertEqual(r.support_state, "supplied")
        self.assertEqual(r.supplied_support_pairs, (("A", "X"),))
        self.assertEqual(r.selection.uncovered_aspect_ids, ("X", "Y"))

    def test_empty_channel_keeps_denominator(self):
        r = self.plain([self.C("L", ["A"]), self.C("D", [])])
        self.assertEqual(r.relevance_by_id, {"A": .5})
        r = self.plain([self.C("L", ["A"]), self.C("D", [], weight=0, status="failed")])
        self.assertEqual(r.relevance_by_id, {"A": 1})
        self.assertEqual((r.channels[1].enabled, r.channels[1].status), (False, "failed"))
        r = self.select([self.C("L", []), self.C("D", [])], [QueryAspect("X")],
                        relevance_weight=1)
        self.assertEqual(r.candidate_ids, ())
        self.assertEqual(r.selection.selected_ids, ())
        self.assertEqual(r.selection.uncovered_aspect_ids, ("X",))
        self.assertEqual([c.normalized_weight for c in r.channels], [.5, .5])

    def test_weight_scaling_and_mixed_reals(self):
        expected = float(F(103, 105))
        for scale in (1e-200, 1., 1e200):
            with self.subTest(scale=scale):
                r = self.plain([self.C("L", ["A"], 2*scale), self.C("D", ["B", "C", "A"], 3*scale)])
                self.assertAlmostEqual(r.relevance_by_id["A"], expected, delta=1e-12)
        for weight in (1e308, 10**400, F(10**400)):
            with self.subTest(weight=type(weight).__name__):
                r = self.plain([self.C("L", ["A"], weight), self.C("D", ["A"], weight)])
                self.assertEqual(r.relevance_by_id["A"], 1)
                self.assertEqual([c.normalized_weight for c in r.channels], [.5, .5])
        for weights in ((1., F(10**400)), (F(10**400), 1.)):
            with self.subTest(weights=weights):
                r = self.plain([self.C("L", ["A"], weights[0]), self.C("D", ["A"], weights[1])])
                self.assertEqual(r.relevance_by_id["A"], 1)

    def test_numpy_reals_use_actual_scalar_path(self):
        try:
            import numpy as np
        except ImportError:
            if os.environ.get("MNEMOSIS_TEST_NUMPY") == "1":
                raise
            self.skipTest("NumPy optional")
        for small in (np.int64(2), np.float64(2), np.float32(2)):
            for big in (10**400, F(10**400)):
                with self.subTest(small=type(small).__name__, big=type(big).__name__):
                    r = self.plain([self.C("L", ["A"], small), self.C("D", ["A"], big)])
                    self.assertEqual(r.relevance_by_id["A"], 1)
        r = self.call(limit=np.int64(2), relevance_weight=np.float64(.5),
                      support={"A": {"X": np.float64(1)}, "C": {"Y": np.float32(1)}})
        self.assertEqual(r.selection.selected_ids, ("A", "C"))

    def test_underflow_keeps_enabled_candidates(self):
        r = self.select([self.C("L", ["A"], 1e308), self.C("D", ["B"], 1e-308)],
                        [QueryAspect("X")], support={"A": {"X": 0}, "B": {"X": 1}},
                        relevance_weight=0, limit=1)
        self.assertEqual(r.candidate_ids, ("A", "B"))
        self.assertEqual(r.relevance_by_id["B"], 0)
        self.assertTrue(r.channels[1].enabled)
        self.assertEqual(r.underflow_channel_ids, ("D",))
        self.assertEqual(r.selection.selected_ids, ("B",))

    def test_identifiers_are_exact_and_ties_follow_input(self):
        for first, second in (("z", "A"), ("A", "a"), ("é", "e\u0301")):
            with self.subTest(ids=(first, second)):
                r = self.plain([self.C("L", [first]), self.C("D", [second])], limit=1)
                self.assertEqual(r.candidate_ids, (first, second))
                self.assertEqual(r.selection.selected_ids, (first,))

    def test_tail_append_and_shared_id(self):
        r1 = self.plain([self.C("L", ["A", "B"]), self.C("D", ["B", "A"])])
        r2 = self.plain([self.C("L", ["A", "B", "C"]), self.C("D", ["B", "A"])])
        for ident in ("A", "B"):
            self.assertEqual(r1.relevance_by_id[ident], r2.relevance_by_id[ident])
        r = self.plain([self.C("L", ["A"]), self.C("D", ["A"])])
        self.assertEqual(r.candidate_ids, ("A",))
        self.assertEqual(len(r.contributions_by_id["A"]), 2)

    def test_fraction_contributions_and_fixed_capacity(self):
        r = self.call(limit=2)
        independent = {"A": (F(1,2), F(1,2)),
                       "B": (F(61,124), F(61,126)), "C": (F(61,126), F(61,124))}
        for ident, values in independent.items():
            entries = r.contributions_by_id[ident]
            self.assertEqual([v.channel_id for v in entries], ["L", "D"])
            for contribution, exact in zip(entries, values):
                self.assertAlmostEqual(contribution.contribution, float(exact), delta=1e-12)
            self.assertAlmostEqual(r.relevance_by_id[ident], float(sum(values)), delta=1e-12)
        self.assertEqual([(x.rank) for x in r.contributions_by_id["B"]], [2,3])
        for k, expected in ((0, ()), (1, ("A",)), (100, ("A", "C", "B"))):
            with self.subTest(k=k):
                r = self.call(limit=k)
                self.assertEqual(r.selection.selected_ids, expected)
                exact_r = sum((F(1) if ident=="A" else F(7625,7812)
                               for ident in expected), F())/k if k else F()
                self.assertAlmostEqual(r.selection.relevance_component, float(exact_r), delta=1e-12)
        r = self.call(relevance_weight=0, limit=3)
        self.assertEqual(r.selection.selected_ids, ("A", "C"))

    def test_input_and_report_isolation(self):
        channels, aspects, support = self.sample()
        before = deepcopy((channels, aspects, support))
        r = self.select(channels, aspects, support=support, limit=2)
        r.relevance_by_id["A"] = 0
        r.contributions_by_id["A"] = ()
        r.selection.aspect_coverage["X"] = 0
        r.selection.normalized_aspect_weights["X"] = 0
        again = self.select(channels, aspects, support=support, limit=2)
        self.assertEqual((channels, aspects, support), before)
        self.assertEqual(again.relevance_by_id["A"], 1)
        self.assertEqual(again.selection.aspect_coverage["X"], 1)
        self.assertEqual(len(again.contributions_by_id["A"]), 2)
        with self.assertRaises(AttributeError):
            again.channels = ()

    def test_supplied_pair_order_and_partial_support(self):
        r = self.call(aspects=[QueryAspect("Y"), QueryAspect("X")],
                      support={"C": {"X": 0, "Y": .8}, "A": {"X": .6}, "B": {"X": .9}},
                      relevance_weight=0, limit=2)
        self.assertEqual(r.supplied_support_pairs, (("A","X"),("B","X"),("C","Y"),("C","X")))
        self.assertEqual(r.selection.selected_ids, ("B","C"))
        self.assertAlmostEqual(r.selection.coverage_component, .85, delta=1e-12)
        self.assertEqual(r.selection.partial_aspect_ids, ("Y","X"))

    def test_channel_shapes_and_identifiers(self):
        type_bad = [None, "L", b"L", bytearray(b"L"), {}, iter([]), [object()]]
        for value in type_bad:
            with self.subTest(value=repr(value)), self.assertRaises(TypeError):
                self.plain(value)
        bad = [[], [self.C(str(i), []) for i in range(9)],
               [self.C("L", ["A"]), self.C("L", ["B"])], [self.C("", [])],
               [self.C(" L", [])], [self.C("L", [""])], [self.C("L", ["A "])],
               [self.C("L", ["A","A"])], [self.C("L", [], status="wrong")]]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.plain(value, limit=0)
        for value in (self.C(1, []), self.C("L", [1]), self.C("L", "ABC"),
                      self.C("L", iter(["A"])), self.C("L", [], status=None)):
            with self.subTest(value=value), self.assertRaises(TypeError):
                self.plain([value])

    def test_channel_budget_is_union_not_entry_count(self):
        ids = [str(i) for i in range(100)]
        r = self.plain([self.C(str(i), ids) for i in range(8)])
        self.assertEqual(len(r.candidate_ids), 100)
        self.assertEqual(len(r.contributions_by_id["0"]), 8)
        for channels in ([self.C("L", ids+["100"])],
                         [self.C("L", ids), self.C("D", ["100"])]):
            with self.subTest(channels=channels), self.assertRaises(ValueError):
                self.plain(channels, limit=0)

    def test_weights_and_numeric_types(self):
        for value in (True, "1", None, Decimal("1"), 1+0j):
            with self.subTest(value=value), self.assertRaises(TypeError):
                self.plain([self.C("L", ["A"], value)])
        for value in (-1, math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.plain([self.C("L", ["A"], value)], limit=0)
        with self.assertRaises(ValueError):
            self.plain([self.C("L", ["A"], 0), self.C("D", [], 0)])

    def test_support_shapes_unknowns_and_numeric_domains(self):
        for support in ([], {"A":[]}, {"A":{"X":True}}, {"A":{"X":"1"}},
                        {1:{"X":1}}, {"A":{1:1}}):
            with self.subTest(support=support), self.assertRaises(TypeError):
                self.call(support=support, limit=0, relevance_weight=1)
        for support in ({"unknown":{}}, {"A":{"Z":0}}, {"A":{"X":-1}},
                        {"A":{"X":1.01}}, {"A":{"X":math.nan}}, {"A":{"X":math.inf}},
                        {" A":{"X":1}}, {"A":{" X":1}}):
            with self.subTest(support=support), self.assertRaises(ValueError):
                self.call(support=support, limit=0, relevance_weight=1)

    def test_selector_argument_validation_is_not_bypassed(self):
        for name, value, error in (
            ("limit", True, TypeError), ("limit", 1.5, TypeError),
            ("limit",-1, ValueError), ("limit",101, ValueError),
            ("relevance_weight",True,TypeError), ("relevance_weight","1",TypeError),
            ("relevance_weight",-1,ValueError), ("relevance_weight",1.1,ValueError),
            ("relevance_weight",math.nan,ValueError), ("relevance_weight",math.inf,ValueError)):
            with self.subTest(name=name,value=value), self.assertRaises(error):
                self.call(**{name:value})
        bad_aspects = ([QueryAspect("X"), QueryAspect("X")],
                       [QueryAspect("X",0)], [QueryAspect("X",math.inf)],
                       [QueryAspect(str(i)) for i in range(33)])
        for aspects in bad_aspects:
            with self.subTest(aspects=aspects), self.assertRaises(ValueError):
                self.call(aspects=aspects, support=None, relevance_weight=1, limit=0)
        for aspects in ("X", iter([]), [object()]):
            with self.subTest(aspects=aspects), self.assertRaises(TypeError):
                self.call(aspects=aspects, support=None, relevance_weight=1, limit=0)
        with self.assertRaises(ValueError):
            self.select([self.C("L", ["A"])], [], relevance_weight=.5)

    def test_time_chain_negative_is_preserved(self):
        channels = [self.C("L", ["B","C","A"]),self.C("D", ["B","C","A"])]
        r = self.call(channels=channels, support={"A":{"X":1,"Y":1},"B":{"X":1},"C":{"Y":1}},limit=2)
        self.assertEqual(r.candidate_ids[:2], ("B","C"))
        self.assertEqual(r.selection.selected_ids, ("A","B"))
        self.assertNotIn("C", r.selection.selected_ids)
        self.assertAlmostEqual(r.selection.objective, float(F(125,126)), delta=1e-12)

    def test_greedy_nonoptimal_is_preserved(self):
        r = self.select([self.C("L", ["A","B","C"]),self.C("D", ["B","C","A"])],
                        [QueryAspect(str(i)) for i in range(1,7)],
                        support={"A":dict.fromkeys(("1","2","3","4"),1),
                                 "B":dict.fromkeys(("1","2","5"),1),
                                 "C":dict.fromkeys(("3","4","6"),1)},limit=2,relevance_weight=0)
        self.assertEqual(r.selection.selected_ids, ("A","B"))
        self.assertAlmostEqual(r.selection.objective, float(F(5,6)), delta=1e-12)
