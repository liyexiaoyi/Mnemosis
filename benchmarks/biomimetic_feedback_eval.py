"""Deterministic mechanism checks, not a market/answer-quality benchmark.

Run: python benchmarks/biomimetic_feedback_eval.py --output report.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bench_utils import pin_local_src
pin_local_src()

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def state(engine):
    return ([item.to_dict() for item in engine.store.all_active()],
            sorted(engine.backend.all_links()), engine.get_recall_log())


def evaluate():
    start = datetime(2030, 1, 1, tzinfo=timezone.utc)
    engine = MemoryEngine(auto_warmup=False)
    try:
        for ref in ("meeting:1:turn:1", "meeting:1:turn:1", "meeting:2:turn:1"):
            item = engine.remember("Alice prefers green tea", kind=MemoryKind.EPISODIC,
                source=SourceRecord(origin=SourceType.USER, ref=ref), importance=0.9)
            item.created_at = start - timedelta(days=4)
            item.access_count = 3
            engine.backend.update(item)
        engine.sleep(now=start)
        semantic = engine.store.all_active(MemoryKind.SEMANTIC)[0]
        evidence_before = semantic.evidence_count
        rows = []
        for day in (0, 7, 30, 90):
            now = start + timedelta(days=day)
            before = state(engine)
            results = engine.recall_fused("Alice green tea", top_k=1,
                kind=MemoryKind.SEMANTIC, read_only=True, now=now)
            unchanged = state(engine) == before
            assert unchanged, "probe wrote learning state"
            rows.append({"day": day, "hit_at_1": bool(results and results[0].item.id == semantic.id),
                         "probe_read_only": unchanged,
                         "retrievability": round(engine.curve.retrievability(semantic, now), 6)})
        for _ in range(9):
            engine.sleep(now=start + timedelta(days=90))
        final = engine.backend.get(semantic.id)
        assert final.evidence_count == evidence_before == 2
        assert len(final.evidence_sources) == 2
        assert engine.verified_retrieval_confidence(final) is None
        for _ in range(2):
            engine.record_feedback(final.id, useful=False, now=start + timedelta(days=90))
        final = engine.backend.get(final.id)
        posterior = engine.verified_retrieval_confidence(final)
        assert posterior == 0.25
        assert final.evidence_count == 2
        return {"scope": "synthetic mechanism regression; not answer quality or competitor ranking",
                "days": rows, "sleep_cycles": 10, "evidence_before": evidence_before,
                "evidence_after": final.evidence_count, "unique_sources": len(final.evidence_sources),
                "verified_failures": final.verified_failures, "usefulness_posterior": posterior,
                "passed": True}
    finally:
        engine.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate()
    # Re-run in the same process to catch cross-engine clock/state leakage.
    assert evaluate() == report, "lifecycle evaluation is not reproducible"
    content = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(content + "\n", encoding="utf-8")
    print(content)
