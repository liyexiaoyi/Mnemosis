"""Association strength changes relevance, never evidence or traversal budgets."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mnemosis import MemoryEngine, MemoryKind, SourceRecord, SourceType
from mnemosis.embedding import Embedder

NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)


class RecordingEmbedder(Embedder):
    def __init__(self):
        self.queries = []
        self.batches = []

    def embed(self, text):
        self.queries.append(text)
        return [1.0, 0.0]

    def embed_many(self, texts):
        self.batches.append(list(texts))
        return [[1.0, 0.0] for _ in texts]


class AssociationStrengthTests(unittest.TestCase):
    def engine(self, disk=False, **kwargs):
        path = None
        if disk:
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            path = str(Path(tmp.name) / "memory.sqlite")
        engine = MemoryEngine(path, auto_warmup=False, **kwargs)
        self.addCleanup(engine.close)
        return engine

    def put(self, engine, text, **kwargs):
        return engine.remember(text, cues=[], auto_cues=False, auto_context=False,
            created_at=NOW, importance=.5, source=SourceRecord(SourceType.USER), **kwargs)

    def graph(self, engine, weight=.05):
        root = self.put(engine, "coral research expedition")
        weak = [self.put(engine, "unrelated laundry receipt " + str(i)) for i in range(5)]
        strong = self.put(engine, "The specimens were analyzed using a microscope.")
        direct = self.put(engine, "research seminars discuss restoration methods")
        for item in weak:
            engine.backend.add_link(root.id, item.id, weight)
        engine.backend.add_link(root.id, strong.id, 1.0)
        return root, weak, strong, direct

    def recall(self, engine, query="coral research", **kwargs):
        return engine.recall(query, now=NOW, read_only=True,
            association_policy="weighted", pattern_completion=False, **kwargs)

    def state(self, engine):
        return ([i.to_dict() for i in engine.store.all_active()],
                sorted(engine.backend.all_links()), engine.get_recall_log())

    def test_weak_clutter_keeps_strong_and_direct_evidence_in_top_five(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                root, weak, strong, direct = self.graph(engine)
                rows = self.recall(engine, top_k=5)
                self.assertTrue({root.id, strong.id, direct.id} <= {r.item.id for r in rows})
                scores = {r.item.id: r.score for r in rows}
                self.assertGreater(scores[direct.id], max(scores[i.id] for i in weak if i.id in scores))

    def test_zero_weight_does_not_activate_unmatched_neighbors(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                root, weak, strong, direct = self.graph(engine, weight=0.0)
                rows = self.recall(engine, top_k=10)
                self.assertEqual({r.item.id for r in rows}, {root.id, strong.id, direct.id})

    def test_weight_is_monotonic_and_strength_above_one_saturates(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                root = self.put(engine, "coral research expedition")
                neighbor = self.put(engine, "unrelated laundry receipt")
                values = []
                for weight in (.05, .5, 1.0, 1.2):
                    engine.backend.add_link(root.id, neighbor.id, weight)
                    rows = self.recall(engine, top_k=10)
                    values.append(next(r.score for r in rows if r.item.id == neighbor.id))
                self.assertLess(values[0], values[1])
                self.assertLess(values[1], values[2])
                self.assertEqual(values[2], values[3])

    def test_nonfinite_or_negative_custom_backend_weights_do_not_activate(self):
        engine = self.engine()
        root = self.put(engine, "coral research expedition")
        neighbor = self.put(engine, "unrelated laundry receipt")
        engine.backend.add_link(root.id, neighbor.id, 1.0)
        for weight in (float("nan"), float("inf"), float("-inf"), -1.0):
            with self.subTest(weight=weight):
                # Corrupt/custom backend values cannot all be persisted by SQLite.
                with patch.object(engine.backend, "link_weight", return_value=weight):
                    rows = self.recall(engine, top_k=10)
                self.assertEqual([r.item.id for r in rows], [root.id])

    def test_existing_direct_match_keeps_its_own_score_under_weak_activation(self):
        engine = self.engine()
        root = self.put(engine, "coral research expedition")
        direct = self.put(engine, "research seminars discuss restoration methods")
        before = {r.item.id: r.score for r in self.recall(engine)}
        engine.backend.add_link(root.id, direct.id, .05)
        after = {r.item.id: r.score for r in self.recall(engine)}
        self.assertEqual(after[direct.id], before[direct.id])

    def test_only_one_hop_is_expanded(self):
        engine = self.engine()
        root = self.put(engine, "coral research expedition")
        first = self.put(engine, "microscope specimens")
        second = self.put(engine, "lab schedules")
        engine.backend.add_link(root.id, first.id, 1.0)
        engine.backend.add_link(first.id, second.id, 1.0)
        rows = self.recall(engine, top_k=10)
        self.assertEqual({r.item.id for r in rows}, {root.id, first.id})

    def test_root_neighbor_and_weight_lookup_budgets_are_unchanged(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                roots = [self.put(engine, "anchorneedle record " + str(i)) for i in range(5)]
                for root in roots:
                    for i in range(12):
                        neighbor = self.put(engine, "unrelated note " + str(root.seq) + " " + str(i))
                        engine.backend.add_link(root.id, neighbor.id, 1.0)
                with patch.object(engine.backend, "related", wraps=engine.backend.related) as related, \
                     patch.object(engine.backend, "link_weight", wraps=engine.backend.link_weight) as weights:
                    rows = engine.store.recall("anchorneedle", now=NOW, read_only=True,
                        association_policy="weighted", max_expansion_roots=2,
                        max_expansion_neighbors=3, top_k=20, pattern_completion=False,
                        temporal_reason=False, reasoning_pack=False)
                self.assertEqual(related.call_count, 2)
                self.assertTrue(all(c.kwargs == dict(depth=1, max_nodes=1000) for c in related.call_args_list))
                self.assertEqual(weights.call_count, 6)
                self.assertEqual(len(rows), 11)

    def test_neighbor_selection_still_prefers_sequence_distance(self):
        engine = self.engine()
        root = self.put(engine, "coral research expedition")
        near = self.put(engine, "unrelated laundry receipt")
        far = self.put(engine, "microscope specimens")
        engine.backend.add_link(root.id, near.id, .05)
        engine.backend.add_link(root.id, far.id, 1.0)
        rows = engine.store.recall("coral research", now=NOW, read_only=True,
            association_policy="weighted", max_expansion_neighbors=1,
            pattern_completion=False, temporal_reason=False, reasoning_pack=False)
        self.assertEqual({r.item.id for r in rows}, {root.id, near.id})

    def test_zero_hit_fallback_does_not_read_graph_weights(self):
        engine = self.engine()
        self.graph(engine)
        with patch.object(engine.backend, "link_weight", side_effect=AssertionError("fallback expanded")):
            self.recall(engine, "xyzzy absent")

    def test_filters_exclude_suppressed_recycled_and_other_kind(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                root = self.put(engine, "anchorneedle", kind=MemoryKind.SEMANTIC)
                wanted = self.put(engine, "allowed neighbor", kind=MemoryKind.SEMANTIC)
                excluded = self.put(engine, "excluded neighbor", kind=MemoryKind.SEMANTIC)
                suppressed = self.put(engine, "suppressed neighbor", kind=MemoryKind.SEMANTIC)
                recycled = self.put(engine, "recycled neighbor", kind=MemoryKind.SEMANTIC)
                other = self.put(engine, "other neighbor", kind=MemoryKind.EPISODIC)
                for item in (wanted, excluded, suppressed, recycled, other):
                    engine.backend.add_link(root.id, item.id, 1.0)
                engine.suppress_memories([suppressed.id])
                engine.forget(recycled.id)
                rows = self.recall(engine, "anchorneedle", top_k=10,
                    kind=MemoryKind.SEMANTIC, exclude_ids={excluded.id})
                self.assertEqual({r.item.id for r in rows}, {root.id, wanted.id})

    def test_read_only_queries_preserve_items_links_evidence_and_log(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                self.graph(engine)
                before = self.state(engine)
                for _ in range(3):
                    self.recall(engine)
                self.assertEqual(self.state(engine), before)

    def test_final_learning_is_not_verified_or_independent_evidence(self):
        engine = self.engine()
        root, weak, strong, direct = self.graph(engine)
        engine.recall("coral research", now=NOW, learning_policy="final",
                      association_policy="weighted", pattern_completion=False)
        for item in (root, *weak, strong, direct):
            fresh = engine.backend.get(item.id)
            self.assertEqual(fresh.evidence_count, 1)
            self.assertEqual(fresh.verified_successes, 0)
            self.assertEqual(fresh.retrieval_successes, 0)
            self.assertEqual(fresh.access_count, 1 if item.id in (root.id, direct.id) else 0)

    def test_default_is_explicit_legacy_and_unit_weights_keep_ranking(self):
        engine = self.engine()
        self.graph(engine, weight=1.0)
        kwargs = dict(now=NOW, read_only=True, pattern_completion=False)
        default = engine.recall("coral research", **kwargs)
        legacy = engine.recall("coral research", association_policy="legacy", **kwargs)
        weighted = engine.recall("coral research", association_policy="weighted", **kwargs)
        self.assertEqual([(r.item.id, r.score, r.reasons) for r in default],
                         [(r.item.id, r.score, r.reasons) for r in legacy])
        self.assertEqual([(r.item.id, r.score) for r in legacy],
                         [(r.item.id, r.score) for r in weighted])

    def test_invalid_policy_is_rejected_before_embedding_at_both_entry_points(self):
        embedder = RecordingEmbedder()
        engine = self.engine(embedder=embedder)
        for call in (engine.recall, engine.store.recall):
            with self.subTest(entry=call.__qualname__):
                with self.assertRaises(ValueError):
                    call("coral research", association_policy="unknown", embedder=embedder)
                self.assertEqual(embedder.queries, [])

    def test_original_query_and_dense_budget_are_preserved(self):
        embedder = RecordingEmbedder()
        engine = self.engine(embedder=embedder)
        self.graph(engine)
        query = "coral research"
        self.recall(engine, query)
        self.assertEqual(embedder.queries, [query])
        self.assertLessEqual(sum(map(len, embedder.batches)), 64)


if __name__ == "__main__":
    unittest.main()
