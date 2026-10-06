"""Explicit mapping from real stores must preserve every persisted state."""
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timezone

import pytest
from mnemosis import MemoryEngine
from mnemosis.types import MemoryItem, MemoryKind, SourceRecord, SourceType
from mnemosis.evidence_selection import EvidenceCandidate, QueryAspect, select_required_evidence
from verification_utils import ReadOnlyGuard


@pytest.mark.parametrize("backend", ["dict", "sqlite"])
def test_required_selection_does_not_change_memory_links_log_or_sqlite(backend, tmp_path):
    engine = MemoryEngine(str(tmp_path / "memory.sqlite") if backend == "sqlite" else None,
                          auto_warmup=False)
    try:
        now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
        engine.backend.add_many([MemoryItem(id=i, content=text, kind=MemoryKind.EPISODIC,
            source=SourceRecord(SourceType.USER, ref="given-source", occurred_at=now),
            created_at=now, last_access_at=now, access_count=3, confidence=.7)
            for i, text in (("A", "Mina visited Osaka."), ("B", "The destination was Osaka."),
                            ("C", "The trip was in October."))])
        engine.backend.add_link("A", "C", .5)
        engine._recall_log.append({"query": "earlier", "ids": ["B"]})
        conn = getattr(engine.backend, "_conn", None)

        def snapshot():
            return deepcopy((sorted((i.to_dict() for i in engine.backend.list_items()),
                                    key=lambda i: i["id"]),
                             sorted(engine.backend.all_links()), list(engine._recall_log),
                             list(conn.iterdump()) if conn is not None else None))

        before = snapshot()
        with ReadOnlyGuard(conn) if conn is not None else nullcontext():
            items = {i.id: i for i in engine.backend.get_many(["A", "B", "C"])}
            cs = [EvidenceCandidate(items[i].id, r, s) for i, r, s in (
                ("A", 1, {"place": 1}), ("B", 1, {"place": 1}), ("C", .6, {"time": 1}))]
            aspects = [QueryAspect("place"), QueryAspect("time")]
            for budget, limit, status in ((10000, 2, "feasible"), (0, 2, "undetermined"),
                                           (10000, 1, "infeasible"), (0, 0, "infeasible")):
                r = select_required_evidence(cs, aspects,
                    required_aspects={"place": 1, "time": 1},
                    limit=limit, relevance_weight=.8, search_budget=budget)
                assert r.status == status
                if status == "feasible":
                    assert r.selection.selected_ids == ("A", "C")
                else:
                    assert r.selection is None
            with pytest.raises(ValueError):
                select_required_evidence(cs, aspects, required_aspects={"time": 0}, limit=0)
        assert snapshot() == before
    finally:
        engine.close()
