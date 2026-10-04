"""Optional native BM25 must preserve Python ranking and lifecycle semantics."""
import importlib.util
import os
import random
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from mnemosis import MemoryEngine
from mnemosis.bm25 import BM25Index

NATIVE = importlib.util.find_spec("_mnemosis_rust") is not None
native = pytest.mark.skipif(not NATIVE and os.environ.get("MNEMOSIS_TEST_RUST") != "1",
                            reason="optional Rust extension not installed")

def test_default_is_python_and_invalid_selection_is_rejected():
    engine = MemoryEngine(auto_warmup=False)
    try:
        assert engine.bm25_backend == "python"
    finally:
        engine.close()
    with pytest.raises(ValueError, match="bm25_backend"):
        MemoryEngine(auto_warmup=False, bm25_backend="unknown")

def test_explicit_rust_missing_is_diagnostic_and_python_remains_available():
    engine = MemoryEngine(auto_warmup=False, bm25_backend="rust")
    try:
        engine.remember("tea")
        with patch.dict("sys.modules", {"_mnemosis_rust": None}):
            with pytest.raises(ImportError, match="Rust.*bm25_backend.*python"):
                engine.recall_bm25("tea")
        assert getattr(engine, "_bm25_cache", None) is None
        engine.bm25_backend = "python"
        assert engine.recall_bm25("tea")
    finally:
        engine.close()

@native
def test_native_seeded_rank_scores_mutations_unicode_ties_exclusions():
    from mnemosis.bm25 import RustBM25Index
    rng = random.Random(20261004)
    words = ["tea", "coffee", "旅行", "预算", "café", "𠮷", "music", "2026-10-04"]
    rows = [SimpleNamespace(id=f"文档{i:03}", seq=i // 3,
            content=" ".join(rng.choices(words, k=rng.randrange(0, 20))),
            cues=rng.choices(words, k=rng.randrange(4))) for i in range(150)]
    # Identical scores/order must fall back to Unicode ID ordering.
    rows += [SimpleNamespace(id=i, seq=-1, content="tie tie", cues=[])
             for i in ["𠮷", "é", "a", "中"]]
    python, rust = BM25Index(rows), RustBM25Index(rows)
    assert rust.backend_name == "rust"
    for step in range(35):
        for query in ("tea coffee 旅行", "tie", "zzunknown", "𠮷", "2026-10-04"):
            for k in (0, 1, 5, 20, 1000):
                excluded = {rows[step].id, "a"} if step % 2 else set()
                a, b = python.search(query, k, excluded), rust.search(query, k, excluded)
                assert [i for i, s in a] == [i for i, s in b]
                assert [s for i, s in b] == pytest.approx([s for i, s in a], abs=1e-12, rel=0)
        row = rows[step]
        python.remove(row.id); rust.remove(row.id)
        if step % 3:
            row.content = "tea tea 预算"; row.cues = ["coffee", "coffee"]
            python.upsert(row); rust.upsert(row)

@native
def test_switching_implementation_rebuilds_single_cache():
    engine = MemoryEngine(auto_warmup=False)
    try:
        engine.remember("tea coffee")
        a = engine.recall_bm25("tea")
        old = engine._bm25_cache[2]
        engine.bm25_backend = "rust"
        b = engine.recall_bm25("tea")
        assert engine._bm25_cache[2] is not old
        assert engine._bm25_cache[2].backend_name == "rust"
        assert [r.item.id for r in a] == [r.item.id for r in b]
        assert [r.score for r in b] == pytest.approx([r.score for r in a], abs=1e-12, rel=0)
        engine.bm25_backend = "python"
        engine.recall_bm25("tea")
        assert engine._bm25_cache[2].backend_name == "python"
    finally:
        engine.close()

# Reuse every existing incremental/lifecycle case against the native adapter.
# This includes external connections, rollback, pruned logs, recycling, bulk
# import, kind changes, sleep integration and atomic failure of cache updates.
import test_bm25_incremental as incremental_cases
import test_bm25_cues as cue_cases

@native
class TestRustIncremental(incremental_cases.IncrementalBM25Tests):
    def setUp(self):
        original = MemoryEngine
        factory = lambda *a, **kw: original(*a, bm25_backend="rust", **kw)
        context = patch.object(incremental_cases, "MemoryEngine", factory)
        context.start()
        self.addCleanup(context.stop)

@native
class TestRustCueContracts(cue_cases.BM25CueTests):
    def setUp(self):
        original = MemoryEngine
        factory = lambda *a, **kw: original(*a, bm25_backend="rust", **kw)
        context = patch.object(cue_cases, "MemoryEngine", factory)
        context.start()
        self.addCleanup(context.stop)

@native
def test_native_batch_validation_does_not_partially_publish():
    import _mnemosis_rust as native_module
    kernel = native_module.BM25Kernel(1.5, 0.75)
    kernel.upsert_batch([("keep", 1, {"tea": 2})])
    before = kernel.search(["tea"], 10, set())
    with pytest.raises(ValueError):
        kernel.upsert_batch([("added", 2, {"tea": 1}), ("bad", 3, {"tea": 0})])
    assert kernel.search(["tea"], 10, set()) == before
    assert kernel.n == 1

@native
def test_native_total_length_overflow_is_atomic():
    import _mnemosis_rust as native_module
    kernel = native_module.BM25Kernel(1.5, 0.75)
    kernel.upsert_batch([("keep", 1, {"tea": 2**64-1})])
    before = kernel.search(["tea"], 10, set())
    with pytest.raises(ValueError, match="total length"):
        kernel.upsert_batch([("added", 2, {"tea": 1})])
    assert kernel.search(["tea"], 10, set()) == before
    assert kernel.n == 1

@native
def test_native_internal_timer_returns_same_rank_and_score():
    import _mnemosis_rust as native_module
    kernel = native_module.BM25Kernel(1.5, 0.75)
    kernel.upsert_batch([("one", 1, {"tea": 2}), ("two", 2, {"tea": 1})])
    ordinary = kernel.search(["tea"], 2, set())
    rows, nanoseconds = kernel.search_timed(["tea"], 2, set())
    assert rows == ordinary
    assert isinstance(nanoseconds, int) and nanoseconds >= 0
