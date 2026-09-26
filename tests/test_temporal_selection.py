"""Temporal winners must not depend on whether they were already retrieved."""
from datetime import datetime, timezone
from itertools import permutations
from pathlib import Path
import tempfile
import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, RecallResult

NOW = datetime(2026, 9, 26, tzinfo=timezone.utc)


class TemporalSelectionTests(unittest.TestCase):
    def engine(self, disk=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        engine = MemoryEngine(str(Path(directory.name) / "memory.db") if disk else None,
                              auto_warmup=False)
        self.addCleanup(engine.close)
        return engine

    def fact(self, engine, text, evidence=1, kind=MemoryKind.SEMANTIC):
        return engine.remember(text, kind=kind, cues=["小林", "住在"],
            evidence_count=evidence, created_at=NOW, auto_cues=False, auto_context=False)

    def anchor(self, engine, query, rows, **kwargs):
        return engine._apply_temporal_anchor(query, rows, top_k=5, kind=None,
                                             exclude_ids=set(), now=NOW, **kwargs)

    def test_current_public_recall_does_not_flip_with_top_k(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                self.fact(engine, "2026年1月1日小林住在北京。", evidence=20)
                latest = self.fact(engine, "2026年8月1日小林住在上海。")
                for k in (1, 2, 5):
                    results = engine.recall("现在小林住在哪里？", top_k=k,
                                            now=NOW, read_only=True)
                    self.assertEqual(results[0].item.id, latest.id)
                    self.assertEqual(len({r.item.id for r in results}), len(results))

    def test_latest_of_all_seen_rows_wins_every_input_order(self):
        engine = self.engine()
        items = [self.fact(engine, f"2026年{month}月1日小林住在城市{month}。")
                 for month in (1, 5, 8)]
        for order in permutations(items):
            rows = [RecallResult(item, 0.9 - i * 0.1) for i, item in enumerate(order)]
            result = self.anchor(engine, "现在小林住在哪里？", rows)
            self.assertEqual(result[0].item.id, items[-1].id)
            self.assertEqual(len(result), 3)

    def test_earliest_seen_row_wins(self):
        engine = self.engine()
        first = self.fact(engine, "2026年1月1日小林住在北京。")
        last = self.fact(engine, "2026年8月1日小林住在上海。")
        result = self.anchor(engine, "第一次小林住在哪里？",
                             [RecallResult(last, .9), RecallResult(first, .6)])
        self.assertEqual(result[0].item.id, first.id)

    def test_nearest_future_seen_row_wins_and_past_drops(self):
        engine = self.engine()
        past = self.fact(engine, "2026年9月1日小林复诊。")
        near = self.fact(engine, "2026年10月1日小林复诊。")
        far = self.fact(engine, "2026年12月1日小林复诊。")
        result = self.anchor(engine, "下次小林复诊是什么时候？",
            [RecallResult(far, .9), RecallResult(past, .8), RecallResult(near, .7)])
        self.assertEqual(result[0].item.id, near.id)
        self.assertNotIn(past.id, {r.item.id for r in result})

    def test_exact_date_seen_row_wins(self):
        engine = self.engine()
        target = self.fact(engine, "2026年1月1日小林住在北京。")
        other = self.fact(engine, "2026年8月1日小林住在上海。")
        result = self.anchor(engine, "2026年1月1日小林住在哪里？",
                             [RecallResult(other, .9), RecallResult(target, .6)])
        self.assertEqual(result[0].item.id, target.id)
        self.assertIn("时间锚点(日期:1月1日)", result[0].reasons)

    def test_time_diagnostic_leaves_items_links_and_log_unchanged(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                self.fact(engine, "2026年1月1日小林住在北京。", evidence=20)
                self.fact(engine, "2026年8月1日小林住在上海。")
                def state():
                    return ([i.to_dict() for i in engine.store.all_active()],
                            sorted(engine.backend.all_links()), engine.get_recall_log())
                before = state()
                for _ in range(3):
                    engine.temporal_anchor("现在小林住在哪里？", now=NOW)
                self.assertEqual(state(), before)

    def test_existing_uncertainty_and_reasons_survive_reranking(self):
        engine = self.engine()
        old = self.fact(engine, "2026年1月1日小林住在北京。")
        latest = self.fact(engine, "2026年8月1日小林住在上海。")
        rows = [RecallResult(old, .9), RecallResult(latest, .4, ["unverified"], False)]
        result = self.anchor(engine, "现在小林住在哪里？", rows)
        self.assertEqual(result[0].item.id, latest.id)
        self.assertFalse(result[0].confident)
        self.assertIn("unverified", result[0].reasons)
        self.assertEqual(rows[1].score, .4)
        self.assertEqual(rows[1].reasons, ["unverified"])

    def test_plain_query_is_unchanged(self):
        engine = self.engine()
        old = self.fact(engine, "2026年1月1日小林住在北京。")
        latest = self.fact(engine, "2026年8月1日小林住在上海。")
        rows = [RecallResult(old, .9), RecallResult(latest, .4)]
        self.assertEqual(self.anchor(engine, "小林的居住地址", rows), rows)

    def test_excluded_recycled_and_wrong_kind_do_not_win(self):
        engine = self.engine()
        wanted = self.fact(engine, "2026年1月1日小林住在北京。")
        excluded = self.fact(engine, "2026年5月1日小林住在上海。")
        recycled = self.fact(engine, "2026年6月1日小林住在苏州。")
        self.fact(engine, "2026年8月1日小林住在杭州。", kind=MemoryKind.EPISODIC)
        engine.forget(recycled.id)
        result = engine.recall("现在小林住在哪里？", top_k=5, now=NOW,
            read_only=True, kind=MemoryKind.SEMANTIC, exclude_ids={excluded.id})
        self.assertEqual([r.item.id for r in result], [wanted.id])

    def test_anchor_reapplication_is_idempotent(self):
        engine = self.engine()
        a = self.fact(engine, "2026年1月1日小林住在北京。")
        b = self.fact(engine, "2026年8月1日小林住在上海。")
        rows = [RecallResult(a, .9), RecallResult(b, .4, ["weak"], False)]
        once = self.anchor(engine, "现在小林住在哪里？", rows)
        twice = self.anchor(engine, "现在小林住在哪里？", once)
        self.assertEqual(once, twice)

    def test_bounded_pool_still_compares_existing_rows(self):
        from unittest.mock import patch
        engine = self.engine()
        a = self.fact(engine, "2026年1月1日小林住在北京。")
        b = self.fact(engine, "2026年8月1日小林住在上海。")
        with patch("mnemosis.retrieval_mixin._ANCHOR_CANDIDATE_LIMIT", 1):
            result = self.anchor(engine, "现在小林住在哪里？",
                                 [RecallResult(a, .9), RecallResult(b, .4)])
        self.assertEqual(result[0].item.id, b.id)

    def test_graph_routes_respect_filters_but_keep_allowed_association(self):
        for disk in (False, True):
            for route in ("spread", "pattern"):
                with self.subTest(disk=disk, route=route):
                    engine = self.engine(disk)
                    items = [self.fact(engine, text, kind=kind) for text, kind in [
                        ("anchorneedle orange apple", MemoryKind.SEMANTIC),
                        ("allowedrelated", MemoryKind.SEMANTIC),
                        ("excludedrelated", MemoryKind.SEMANTIC),
                        ("archivedrelated", MemoryKind.SEMANTIC),
                        ("episoderelated", MemoryKind.EPISODIC)]]
                    for item in items[1:]:
                        engine.backend.add_link(items[0].id, item.id, weight=1.0)
                    engine.forget(items[3].id)
                    kwargs = dict(kind=MemoryKind.SEMANTIC, top_k=10, now=NOW,
                        read_only=True, exclude_ids={items[2].id}, temporal_reason=False,
                        reasoning_pack=False, separation=False,
                        max_expansion_roots=5 if route == "spread" else 0,
                        pattern_completion=route == "pattern",
                        pc_min_overlap=0.0, pc_max_overlap=1.1)
                    result = engine.store.recall("anchorneedle", **kwargs)
                    self.assertEqual({r.item.id for r in result}, {i.id for i in items[:2]})

    def test_cached_event_successor_cannot_bypass_exclusion_or_recycle(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                a = engine.remember("anchorneedle 2026-01-01", cues=["alice", "session1"],
                                    auto_cues=False, auto_context=False, created_at=NOW)
                b = engine.remember("destination 2026-01-02", cues=["alice", "session1"],
                                    auto_cues=False, auto_context=False, created_at=NOW)
                self.assertEqual(engine.event_chain.next_event_id(a.id), b.id)
                for recycled in (False, True):
                    if recycled:
                        stale = engine.backend.get(b.id)
                        from mnemosis.types import MemoryStatus
                        stale.status = MemoryStatus.RECYCLED
                        engine.backend.update(stale)
                    result = engine.store.recall("anchorneedle", top_k=5, now=NOW,
                        read_only=True, max_expansion_roots=0, pattern_completion=False,
                        event_chain=engine.event_chain, temporal_reason=False,
                        reasoning_pack=False, exclude_ids=set() if recycled else {b.id})
                    self.assertEqual([r.item.id for r in result], [a.id])

    def test_suppressed_memory_cannot_return_via_association(self):
        engine = self.engine()
        a = self.fact(engine, "2026年1月1日小林住在北京。")
        b = self.fact(engine, "2026年8月1日小林住在上海。")
        engine.suppress_memories([b.id])
        result = engine.recall("现在小林住在哪里？", top_k=5, now=NOW, read_only=True)
        self.assertEqual([r.item.id for r in result], [a.id])


if __name__ == "__main__":
    unittest.main()
