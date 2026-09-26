"""Compare attribution over repeated queries, without claiming answer accuracy."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import tempfile

from mnemosis import MemoryEngine
import mnemosis.retrieval_mixin as retrieval
from mnemosis.types import MemoryKind
from temporal_selection_eval import CASES

NOW = datetime(2026, 9, 26, tzinfo=timezone.utc)


def run(workdir, policy, repeats):
    rows = []
    for name, query, distractor, target in CASES:
        for disk in (False, True):
            with tempfile.TemporaryDirectory(dir=workdir) as folder:
                with MemoryEngine(str(Path(folder) / "memory.db") if disk else None,
                                  auto_warmup=False) as engine:
                    items = [engine.remember(content, kind=MemoryKind.SEMANTIC,
                        cues=[], evidence_count=20 if i == 0 else 1,
                        created_at=NOW, auto_cues=False, auto_context=False)
                        for i, content in enumerate([distractor, target])]
                    before = [i.to_dict() for i in items]
                    kwargs = {"learning_policy": "final"} if policy == "final" else {}
                    correct = logged = 0
                    for _ in range(repeats):
                        result = engine.recall(query, top_k=1, now=NOW, **kwargs)
                        correct += bool(result and result[0].item.id == items[1].id)
                        logged += bool(result and engine.get_recall_log()[0]["top_id"] == result[0].item.id)
                    stored = [engine.backend.get(i.id) for i in items]
                    rows.append(dict(case=name, backend="sqlite" if disk else "dict",
                        returns_correct=correct, logs_match_final=logged,
                        accesses=[i.access_count for i in stored],
                        retrieval_successes=[i.retrieval_successes for i in stored],
                        verified_successes=[i.verified_successes for i in stored],
                        evidence=[i.evidence_count for i in stored],
                        distractor_unchanged=stored[0].to_dict() == before[0],
                        target_storage_strength=stored[1].storage_strength,
                        attribution_correct=stored[0].access_count == 0 and stored[1].access_count == repeats))
    return dict(policy=policy, repeats=repeats, paths=len(rows), queries=repeats*len(rows),
        correct_returns=sum(r["returns_correct"] for r in rows),
        correct_logs=sum(r["logs_match_final"] for r in rows),
        correct_attribution=sum(r["attribution_correct"] for r in rows), rows=rows,
        fixture_sha256=hashlib.sha256(json.dumps(CASES).encode()).hexdigest(),
        source_sha256=hashlib.sha256(Path(retrieval.__file__).read_bytes()).hexdigest(),
        note="Nine synthetic cases, two backends, repeated queries; not independent held-out questions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policy", choices=["legacy", "final"], default="legacy")
    parser.add_argument("--repeats", type=int, default=30)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be positive")
    result = run(args.workdir, args.policy, args.repeats)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ["policy", "paths", "queries", "correct_returns", "correct_logs", "correct_attribution"]}))
