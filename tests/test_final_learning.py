"""Candidate retrieval must not learn before final result selection."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mnemosis import MemoryEngine
from mnemosis.mcp_server import MCPServer
from mnemosis.types import MemoryKind

NOW = datetime(2026, 9, 26, tzinfo=timezone.utc)
QUERY = "现在小林住在哪里？"


class FinalLearningTests(unittest.TestCase):
    def build(self, disk=False):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        engine = MemoryEngine(str(Path(folder.name) / "memory.db") if disk else None,
                              auto_warmup=False)
        self.addCleanup(engine.close)
        items = [engine.remember(text, kind=MemoryKind.SEMANTIC,
            evidence_count=count, created_at=NOW, auto_cues=False, auto_context=False)
            for text, count in [("2026年1月1日小林住在北京。", 20),
                                ("2026年8月1日小林住在上海。", 1)]]
        return engine, items

    def state(self, engine):
        return ([i.to_dict() for i in engine.store.all_active()],
                sorted(engine.backend.all_links()), engine.get_recall_log())

    def test_only_final_time_anchor_learns(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine, (old, latest) = self.build(disk)
                old_state = engine.backend.get(old.id).to_dict()
                result = engine.recall(QUERY, top_k=1, now=NOW, learning_policy="final")
                self.assertEqual(result[0].item.id, latest.id)
                self.assertEqual(engine.backend.get(old.id).to_dict(), old_state)
                current = engine.backend.get(latest.id)
                self.assertEqual(current.access_count, 1)
                self.assertEqual(current.last_access_at, NOW)
                self.assertEqual(current.retrieval_successes, 0)
                self.assertEqual(current.verified_successes, 0)
                self.assertEqual(current.evidence_count, 1)
                self.assertAlmostEqual(current.storage_strength, 1.015)
                self.assertEqual(result[0].item.to_dict(), current.to_dict())

    def test_log_names_final_result_for_both_policies(self):
        for policy in ("legacy", "final"):
            with self.subTest(policy=policy):
                engine, _ = self.build()
                result = engine.recall(QUERY, top_k=1, now=NOW, learning_policy=policy)
                log = engine.get_recall_log()
                self.assertEqual(len(log), 1)
                self.assertEqual(log[0]["top_id"], result[0].item.id)
                self.assertEqual(log[0]["top_preview"], result[0].item.content[:40])
                self.assertEqual(log[0]["confident"], result[0].confident)

    def test_read_only_overrides_final_learning(self):
        engine, _ = self.build(True)
        before = self.state(engine)
        for _ in range(3):
            engine.recall(QUERY, top_k=1, now=NOW, read_only=True, learning_policy="final")
        self.assertEqual(before, self.state(engine))

    def test_repeated_final_recall_does_not_manufacture_evidence(self):
        engine, (old, latest) = self.build()
        before = engine.backend.get(old.id).to_dict()
        for _ in range(30):
            engine.recall(QUERY, top_k=1, now=NOW, learning_policy="final")
        self.assertEqual(engine.backend.get(old.id).to_dict(), before)
        item = engine.backend.get(latest.id)
        self.assertEqual(item.access_count, 30)
        self.assertEqual(item.evidence_count, 1)
        self.assertEqual((item.verified_successes, item.verified_failures), (0, 0))
        self.assertEqual((item.retrieval_successes, item.retrieval_failures), (0, 0))

    def test_final_results_match_read_only_candidate_ranking(self):
        engine, _ = self.build()
        expected = engine.recall(QUERY, top_k=2, now=NOW, read_only=True)
        links = sorted(engine.backend.all_links())
        actual = engine.recall(QUERY, top_k=2, now=NOW, learning_policy="final")
        self.assertEqual([(r.item.id, r.score) for r in actual],
                         [(r.item.id, r.score) for r in expected])
        self.assertEqual(sorted(engine.backend.all_links()), links)
        for r in actual:
            self.assertEqual(engine.backend.get(r.item.id).access_count, 1)

    def test_failed_postprocessing_does_not_learn_or_log(self):
        engine, _ = self.build()
        before = self.state(engine)
        with patch.object(engine, "_apply_scope_anchor", side_effect=RuntimeError("probe")):
            with self.assertRaisesRegex(RuntimeError, "probe"):
                engine.recall(QUERY, now=NOW, learning_policy="final")
        self.assertEqual(self.state(engine), before)

    def test_invalid_policy_fails_before_mutation(self):
        engine, _ = self.build()
        before = self.state(engine)
        for value in ("typo", None, 1, []):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    engine.recall(QUERY, learning_policy=value)
        self.assertEqual(self.state(engine), before)

    def test_unmatched_fallback_does_not_gain_success_or_access(self):
        engine, _ = self.build()
        before = [i.to_dict() for i in engine.store.all_active()]
        engine.recall("unknownxyz", top_k=1, now=NOW, learning_policy="final")
        self.assertEqual([i.to_dict() for i in engine.store.all_active()], before)

    def test_mcp_exposes_and_forwards_final_policy(self):
        engine, (old, latest) = self.build()
        server = MCPServer(engine=engine)
        schema = next(t for t in server._tools if t["name"] == "recall")["inputSchema"]["properties"]
        self.assertEqual(schema["learning_policy"]["enum"], ["legacy", "final"])
        result = server._call_tool("recall", {"query": QUERY, "top_k": 1, "learning_policy": "final"})
        self.assertEqual(result[0]["id"], latest.id)
        self.assertEqual(engine.backend.get(latest.id).access_count, 1)
        self.assertEqual(engine.backend.get(old.id).access_count, 0)

    def test_mcp_read_only_overrides_final_policy(self):
        engine, _ = self.build()
        server = MCPServer(engine=engine)
        before = self.state(engine)
        server._call_tool("recall", {"query": QUERY, "learning_policy": "final", "read_only": True})
        self.assertEqual(self.state(engine), before)

    def test_default_keeps_legacy_learning_for_compatibility(self):
        engine, (old, latest) = self.build()
        engine.recall(QUERY, top_k=1, now=NOW)
        self.assertEqual(engine.backend.get(old.id).access_count, 1)
        self.assertEqual(engine.backend.get(latest.id).access_count, 0)

    def test_final_learning_preserves_explicit_negative_feedback(self):
        engine, (_, latest) = self.build(True)
        engine.record_feedback(latest.id, useful=False)
        before = engine.backend.get(latest.id)
        engine.recall(QUERY, top_k=1, now=NOW, learning_policy="final")
        after = engine.backend.get(latest.id)
        self.assertEqual(after.verified_failures, before.verified_failures)
        self.assertEqual(after.verified_successes, before.verified_successes)
        self.assertEqual(after.confidence, before.confidence)
        self.assertEqual(after.evidence_sources, before.evidence_sources)

    def test_duplicate_final_ids_gain_at_most_one_access(self):
        engine, (_, latest) = self.build()
        from mnemosis.types import RecallResult
        with patch.object(engine, "_apply_scope_anchor", return_value=[
            RecallResult(latest, .8), RecallResult(latest, .7)
        ]):
            engine.recall(QUERY, now=NOW, learning_policy="final")
        self.assertEqual(engine.backend.get(latest.id).access_count, 1)

    def test_final_policy_without_anchors_learns_base_winner(self):
        engine, (old, latest) = self.build()
        result = engine.recall(QUERY, top_k=1, now=NOW, learning_policy="final",
            temporal_anchor=False)
        self.assertEqual(result[0].item.id, old.id)
        self.assertEqual(engine.backend.get(old.id).access_count, 1)
        self.assertEqual(engine.backend.get(latest.id).access_count, 0)

    def test_mcp_legacy_policy_keeps_final_log_and_invalid_policy_is_rejected(self):
        engine, (old, latest) = self.build()
        server = MCPServer(engine=engine)
        result = server._call_tool("recall", {"query": QUERY, "top_k": 1})
        self.assertEqual(result[0]["id"], latest.id)
        self.assertEqual(engine.backend.get(old.id).access_count, 1)
        self.assertEqual(engine.get_recall_log()[0]["top_id"], latest.id)
        before = self.state(engine)
        with self.assertRaises(ValueError):
            server._call_tool("recall", {"query": QUERY, "learning_policy": "invalid"})
        self.assertEqual(self.state(engine), before)


if __name__ == "__main__":
    unittest.main()
