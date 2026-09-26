"""Targeted lifecycle comparison; synthetic fixtures, not an accuracy benchmark.

Run with PYTHONPATH pointing to the source revision being evaluated.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from mnemosis import MemoryEngine
import mnemosis.consolidation as consolidation
from mnemosis.types import MemoryKind, SourceRecord, SourceType

NOW = datetime(2026, 9, 26, tzinfo=timezone.utc)
CASES = [
    dict(id="unrelated_en", a="Alice enjoys cycling.", b="Alice avoids peanuts.",
         cue="alice", expected="preserve"),
    dict(id="unrelated_zh", a="小林喜欢骑自行车。", b="小林花生过敏。",
         cue="小林", expected="preserve"),
    dict(id="environment_en", a="The server port is 443.", b="The server port is 8080.",
         cue="server", contexts=["production", "development"], expected="preserve"),
    dict(id="entity_context_zh", a="小王喜欢红茶。", b="小王喜欢绿茶。",
         cue="小王", contexts=["sales/person-17", "engineering/person-42"], expected="preserve"),
    dict(id="history_en", a="Alice lives in Paris.", b="Alice lives in Berlin.",
         cue="alice", dates=[-90, 0], expected="preserve"),
    dict(id="history_zh", a="小林住在北京。", b="小林住在上海。",
         cue="小林", dates=[-90, 0], expected="preserve"),
    dict(id="dominant_en", a="The API rate limit is 500 per minute.",
         b="The API rate limit is 200 per minute.", cue="api", expected="retire"),
    dict(id="dominant_zh", a="服务端口是443。", b="服务端口是8080。",
         cue="服务", expected="retire"),
    dict(id="balanced_en", a="Alice lives in Paris.", b="Alice lives in Berlin.",
         cue="alice", evidence=1, expected="uncertain"),
    dict(id="trust_en", a="Alice lives in Paris.", b="Alice lives in Berlin.",
         cue="alice", trust=0.2, expected="uncertain"),
]


def run(workdir):
    rows = []
    for case in CASES:
        for disk in (False, True):
            for mode in ("sleep", "resolve_conflicts"):
                with tempfile.TemporaryDirectory(dir=workdir) as directory:
                    path = str(Path(directory) / "memory.db") if disk else None
                    with MemoryEngine(path, auto_warmup=False) as engine:
                        items = []
                        for i, content in enumerate([case["a"], case["b"]]):
                            dates = case.get("dates")
                            items.append(engine.remember(content, kind=MemoryKind.SEMANTIC,
                                source=SourceRecord(origin=SourceType.USER,
                                    trust=case.get("trust", 1.0) if i == 0 else 1.0,
                                    occurred_at=NOW + timedelta(days=dates[i]) if dates else None),
                                cues=[case["cue"]], context=case.get("contexts", [None, None])[i],
                                evidence_count=case.get("evidence", 9) if i == 0 else 1,
                                confidence=0.9, created_at=NOW,
                                auto_cues=False, auto_context=False))
                        engine.recall_bm25(case["b"], top_k=10)
                        checkpoints = []
                        for day in (0, 7, 30, 90):
                            getattr(engine, mode)(now=NOW + timedelta(days=day))
                            stored = [engine.backend.get(item.id) for item in items]
                            before = [item.to_dict() for item in stored]
                            results = engine.recall_bm25(case["b"], top_k=10)
                            assert before == [engine.backend.get(item.id).to_dict() for item in items]
                            statuses = [item.status.value for item in stored]
                            confidence = [round(item.confidence, 8) for item in stored]
                            found_b = items[1].id in {r.item.id for r in results}
                            expected = case["expected"]
                            passed = ((statuses == ["active", "active"] and found_b and
                                       confidence == [0.9, 0.9]) if expected == "preserve" else
                                      (statuses == ["active", "recycled"] and not found_b)
                                      if expected == "retire" else
                                      (statuses == ["active", "active"] and found_b and
                                       all(0.4 <= c < 0.9 for c in confidence)))
                            checkpoints.append(dict(day=day, status=statuses, confidence=confidence,
                                                    target_retrievable=found_b, passed=passed))
                        rows.append(dict(case=case["id"], backend="sqlite" if disk else "dict",
                                         mode=mode, expected=case["expected"], checkpoints=checkpoints,
                                         passed=all(c["passed"] for c in checkpoints)))
    return dict(fixture_sha256=hashlib.sha256(json.dumps(CASES, sort_keys=True).encode()).hexdigest(),
                source_sha256=hashlib.sha256(Path(consolidation.__file__).read_bytes()).hexdigest(),
                total=len(rows), passed=sum(r["passed"] for r in rows),
                note="Synthetic targeted regression cases, no held-out accuracy claim.", rows=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.workdir.mkdir(parents=True, exist_ok=True)
    result = run(args.workdir)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total": result["total"], "passed": result["passed"]}))
