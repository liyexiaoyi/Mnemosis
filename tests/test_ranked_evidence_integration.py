"""Both real backends preserve all memory, provenance and query state."""
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryItem, MemoryKind, SourceRecord, SourceType
from mnemosis.evidence_selection import QueryAspect
from mnemosis.ranked_evidence import RankedChannel, select_ranked_evidence
from verification_utils import ReadOnlyGuard

NOW = datetime(2026,10,6,12,tzinfo=timezone.utc)


class RankedEvidenceIntegrationTests(unittest.TestCase):
    def test_real_backend_mapping_preserves_every_field_and_sql_state(self):
        for backend in ("dict","sqlite"):
            with self.subTest(backend=backend), tempfile.TemporaryDirectory() as tmp:
                engine = MemoryEngine(str(Path(tmp)/"memory.sqlite") if backend=="sqlite" else None,
                                      auto_warmup=False)
                try:
                    engine.backend.add_many([MemoryItem(
                        id=ident,content=content,kind=MemoryKind.EPISODIC,
                        source=SourceRecord(SourceType.USER,ref="given-source",occurred_at=NOW),
                        cues=["mina"],context="Mina/trip",created_at=NOW,
                        last_access_at=NOW,access_count=7,confidence=.7,
                        retrieval_successes=4,retrieval_failures=2,
                        verified_successes=5,verified_failures=1,
                        evidence_sources={"given-source":2})
                        for ident,content in (("A","Mina visited Osaka."),
                                              ("B","Osaka was the destination."),
                                              ("C","The trip occurred in October."))])
                    engine.backend.add_link("A","C",.5)
                    engine._recall_log.append({"query":"earlier","ids":["B"]})
                    conn=getattr(engine.backend,"_conn",None)
                    def snapshot():
                        return deepcopy((sorted((i.to_dict() for i in engine.backend.list_items()),
                                                key=lambda d:d["id"]),
                            sorted(engine.backend.all_links()),list(engine._recall_log),
                            list(conn.iterdump()) if conn is not None else None))
                    before=snapshot()
                    with ReadOnlyGuard(conn) if conn is not None else nullcontext():
                        actual={i.id:i for i in engine.backend.get_many(["A","B","C"])}
                        self.assertEqual(set(actual),{"A","B","C"})
                        channels=[RankedChannel("L",[actual[i].id for i in ("A","B","C")]),
                                  RankedChannel("D",[actual[i].id for i in ("A","C","B")])]
                        for k,ids in ((0,()),(1,("A",)),(2,("A","C"))):
                            report=select_ranked_evidence(channels,[QueryAspect("X",.6),QueryAspect("Y",.4)],
                                support={"A":{"X":1},"B":{"X":1},"C":{"Y":1}},limit=k)
                            self.assertEqual(report.selection.selected_ids,ids)
                            if k==2:
                                self.assertAlmostEqual(report.selection.objective,
                                                       float(Fraction(31061,31248)),delta=1e-12)
                        report.relevance_by_id["A"]=0
                        report.selection.aspect_coverage["X"]=0
                    self.assertEqual(before,snapshot())
                finally:
                    engine.close()
