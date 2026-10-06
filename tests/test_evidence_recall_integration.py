"""New automatic path must preserve real backend and vector state."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from threading import Thread

import pytest

from evidence_fixtures import FixedAnnotator
from mnemosis import MemoryEngine
from mnemosis.embedding import CallableEmbedder
from mnemosis.vector_index import VectorIndex
from verification_utils import ReadOnlyGuard


@pytest.mark.parametrize("backend", ["dict", "sqlite"])
@pytest.mark.parametrize("vector", [False, True])
def test_actual_recall_is_readonly_releases_lock_and_returns_detached_items(backend, vector, tmp_path):
    emb = CallableEmbedder(lambda text: [1., 0.], cache_key="fixed-evidence-test") if vector else None
    index = VectorIndex(str(tmp_path / "vectors.sqlite"), dim=2) if vector else None
    engine = MemoryEngine(str(tmp_path / "memory.sqlite") if backend == "sqlite" else None,
                          embedder=emb, vector_index=index, index_embedder=emb, auto_warmup=False)
    try:
        now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
        for text in ("Mina trip destination was Osaka.", "Mina trip was in October."):
            engine.remember(text, cues=["mina", "trip"], created_at=now)
        engine._recall_log.append({"query": "previous", "ids": []})
        connections = [c for c in (getattr(engine.backend, "_conn", None),
                                   getattr(index, "_conn", None)) if c is not None]
        def snapshot():
            return deepcopy((sorted((i.to_dict() for i in engine.backend.list_items()), key=lambda x:x["id"]),
                             sorted(engine.backend.all_links()), list(engine._recall_log),
                             [list(c.iterdump()) for c in connections]))
        before = snapshot()
        lock_acquired = []
        def hook():
            def acquire():
                with engine._lock:
                    lock_acquired.append(True)
            t = Thread(target=acquire, daemon=True)
            t.start(); t.join(timeout=1)
            assert lock_acquired == [True]
        with ExitStack() as stack:
            for c in connections:
                stack.enter_context(ReadOnlyGuard(c))
            report = engine.recall_evidence("Mina trip destination and date?", now=now,
                annotator=FixedAnnotator(hook=hook), top_k=2)
            assert report.status == "feasible"
            assert len(report.results) == 2
            report.results[0].item.content = "caller modified result"
            assert engine.recall_evidence("Mina trip?", now=now,
                annotator=FixedAnnotator(batch_error="timeout")).status == "annotation_failed"
        assert snapshot() == before
    finally:
        engine.close()
