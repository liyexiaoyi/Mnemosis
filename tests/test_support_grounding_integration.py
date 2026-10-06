"""Valid and rejected source-span calls preserve two real backends."""
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timezone
import importlib

import pytest
from mnemosis import MemoryEngine, MemoryItem, MemoryKind, SourceRecord, SourceType
from mnemosis.evidence_selection import QueryAspect
from mnemosis.ranked_evidence import RankedChannel
from verification_utils import ReadOnlyGuard


@pytest.mark.parametrize("backend", ["dict", "sqlite"])
def test_grounded_calls_preserve_memory_links_logs_and_complete_sqlite_state(backend, tmp_path):
    try:
        api = importlib.import_module("mnemosis.ranked_evidence_refinement")
        if not hasattr(api, "SupportSpan"):
            pytest.fail("approved optional support-span validation is not implemented")
        refine = api.refine_ranked_evidence
    except ModuleNotFoundError as exc:
        if exc.name != "mnemosis.ranked_evidence_refinement":
            raise
        pytest.fail("approved ranked evidence refinement is not implemented")
    now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
    engine = MemoryEngine(str(tmp_path / "memory.sqlite") if backend == "sqlite" else None, auto_warmup=False)
    try:
        items = [MemoryItem(id=label, content=content, kind=MemoryKind.EPISODIC,
                            source=SourceRecord(SourceType.USER, ref="explicit-fixture", occurred_at=now),
                            cues=["trip"], context="explicit-support", created_at=now,
                            last_access_at=now, access_count=3, confidence=.7,
                            retrieval_successes=4, retrieval_failures=2,
                            verified_successes=5, verified_failures=1,
                            evidence_sources={"explicit-fixture": 2})
                 for label, content in (("A", "Facts 1 2 3 4."),
                                        ("B", "Facts 1 2 5."), ("C", "Facts 3 4 6."))]
        engine.backend.add_many(items)
        engine.backend.add_link("A", "C", .5)
        engine._recall_log.append({"query": "earlier", "ids": ["B"]})
        def snapshot():
            return deepcopy((sorted((i.to_dict() for i in engine.backend.list_items()), key=lambda r:r["id"]),
                             sorted(engine.backend.all_links()), list(engine._recall_log)))
        before = snapshot()
        conn = getattr(engine.backend, "_conn", None)
        sql_before = list(conn.iterdump()) if conn is not None else None
        with ReadOnlyGuard(conn) if conn is not None else nullcontext():
            actual = {i.id:i for i in engine.backend.get_many(["A", "B", "C"])}
            channels = [RankedChannel("L", [actual[i].id for i in ("A", "B", "C")]),
                        RankedChannel("D", [actual[i].id for i in ("A", "C", "B")])]
            support = {label: {str(a): 1 for a in covered} for label, covered in
                       (("A", (1,2,3,4)), ("B", (1,2,5)), ("C", (3,4,6)))}
            texts = {i: item.content for i, item in actual.items()}
            spans = {i: {a: api.SupportSpan(0, len(texts[i]), texts[i]) for a in values}
                     for i, values in support.items()}
            report = refine(channels, [QueryAspect(str(i)) for i in range(1,7)],
                            support=support, limit=2, relevance_weight=0,
                            source_texts=texts, support_spans=spans)
            assert report.refinement.selected_ids == ("C", "B")
            assert report.refinement.objective == 1
            assert report.ranked_report.selection.selected_ids == ("A", "B")
            assert report.refinement.original_report == report.ranked_report.selection
            spans["A"]["1"] = api.SupportSpan(0, len(texts["B"]), texts["B"])
            with pytest.raises(ValueError):
                refine(channels, [QueryAspect(str(i)) for i in range(1,7)],
                       support=support, limit=0, relevance_weight=0,
                       source_texts=texts, support_spans=spans)
        assert snapshot() == before
        if conn is not None:
            assert list(conn.iterdump()) == sql_before
    finally:
        engine.close()
