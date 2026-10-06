"""Explicit candidate mapping is read-only on both real backends."""
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryItem, MemoryKind, SourceRecord, SourceType
from mnemosis.evidence_selection import EvidenceCandidate, QueryAspect, select_evidence
from verification_utils import ReadOnlyGuard

NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)


class EvidenceSelectionIntegrationTests(unittest.TestCase):
    def test_two_backends_preserve_memories_links_log_and_all_sqlite_state(self):
        for backend in ("dict", "sqlite"):
            with self.subTest(backend=backend), tempfile.TemporaryDirectory() as tmp:
                engine = MemoryEngine(str(Path(tmp) / "memory.sqlite")
                                      if backend == "sqlite" else None,
                                      auto_warmup=False)
                try:
                    items = [MemoryItem(
                        id=label, content=content, kind=MemoryKind.EPISODIC,
                        source=SourceRecord(SourceType.USER, ref="given-source", occurred_at=NOW),
                        cues=["mina"], context="Mina/trip", created_at=NOW,
                        last_access_at=NOW, access_count=3, confidence=.7,
                        retrieval_successes=4, retrieval_failures=2,
                        verified_successes=5, verified_failures=1,
                        evidence_sources={"given-source": 2})
                        for label, content in (("A", "Mina visited Osaka."),
                                               ("B", "Osaka was the destination."),
                                               ("C", "The trip occurred in October."))]
                    engine.backend.add_many(items)
                    engine.backend.add_link("A", "C", .5)
                    engine._recall_log.append({"query": "earlier", "ids": ["B"]})
                    def snapshot():
                        return deepcopy((
                            sorted((i.to_dict() for i in engine.backend.list_items()),
                                   key=lambda row: row["id"]),
                            sorted(engine.backend.all_links()), list(engine._recall_log)))
                    before = snapshot()
                    conn = getattr(engine.backend, "_conn", None)
                    sql_before = list(conn.iterdump()) if conn is not None else None
                    guard = ReadOnlyGuard(conn) if conn is not None else nullcontext()
                    with guard:
                        actual = engine.backend.get_many(["A", "B", "C"])
                        by_id = {i.id: i for i in actual}
                        self.assertEqual(set(by_id), {"A", "B", "C"})
                        candidates = [EvidenceCandidate(by_id[label].id, relevance, support)
                                      for label, relevance, support in (
                                          ("A", 1., {"X": 1.}),
                                          ("B", .95, {"X": 1.}),
                                          ("C", .4, {"Y": 1.}))]
                        aspects = [QueryAspect("X", .6), QueryAspect("Y", .4)]
                        report = select_evidence(candidates, aspects, limit=2)
                        self.assertEqual(report.selected_ids, ("A", "C"))
                        self.assertAlmostEqual(report.objective, .85)
                        self.assertEqual(select_evidence(candidates, aspects,
                                                        limit=1).selected_ids, ("A",))
                    self.assertEqual(before, snapshot())
                    if conn is not None:
                        self.assertEqual(sql_before, list(conn.iterdump()))
                finally:
                    engine.close()
