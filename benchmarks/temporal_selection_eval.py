"""Public-API temporal selection regression, not held-out answer accuracy."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from mnemosis import MemoryEngine
import mnemosis.retrieval_mixin as retrieval
import mnemosis.dual_track as dual_track
from mnemosis.types import MemoryKind

NOW = datetime(2026, 9, 26, tzinfo=timezone.utc)
# Two records per case. The first is an intentionally strong distractor.
CASES = [
    ("current_address", "现在小林住在哪里？", "2026年1月1日小林住在北京。", "2026年8月1日小林住在上海。"),
    ("current_port", "目前服务端口是多少？", "2026年1月1日服务端口是443。", "2026年8月1日服务端口是8080。"),
    ("latest_class", "上次私教课练了什么？", "2026年1月1日私教课练胸。", "2026年8月1日私教课练腿。"),
    ("first_address", "第一次小林住在哪里？", "2026年8月1日小林住在上海。", "2026年1月1日小林住在北京。"),
    ("first_class", "第一次私教课练了什么？", "2026年8月1日私教课练腿。", "2026年1月1日私教课练胸。"),
    ("next_visit", "下次复诊是什么时候？", "2026年12月1日复诊。", "2026年10月1日复诊。"),
    ("next_class", "下次私教课什么时候？", "2026年12月1日私教课练腿。", "2026年10月1日私教课练胸。"),
    ("exact_address", "2026年1月1日小林住在哪里？", "2026年8月1日小林住在上海。", "2026年1月1日小林住在北京。"),
    ("exact_class", "2026年1月1日私教课练了什么？", "2026年8月1日私教课练腿。", "2026年1月1日私教课练胸。"),
]


def state(engine):
    return ([i.to_dict() for i in engine.store.all_active()],
            sorted(engine.backend.all_links()), engine.get_recall_log())


def run(workdir):
    rows = []
    for name, query, distractor, target in CASES:
        for disk in (False, True):
            for k in (1, 2, 5):
                with tempfile.TemporaryDirectory(dir=workdir) as folder:
                    with MemoryEngine(str(Path(folder) / "memory.db") if disk else None,
                                      auto_warmup=False) as engine:
                        items = [engine.remember(content, kind=MemoryKind.SEMANTIC,
                            cues=[], evidence_count=20 if i == 0 else 1,
                            created_at=NOW, auto_cues=False, auto_context=False)
                            for i, content in enumerate([distractor, target])]
                        before = state(engine)
                        results = engine.recall(query, top_k=k, now=NOW, read_only=True)
                        readonly = before == state(engine)
                        ids = [r.item.id for r in results]
                        rows.append(dict(case=name, backend="sqlite" if disk else "dict",
                            top_k=k, passed=bool(ids and ids[0] == items[1].id),
                            no_duplicates=len(ids) == len(set(ids)), read_only=readonly,
                            returned=[r.item.content for r in results]))
    diagnostics = []
    for disk in (False, True):
        with tempfile.TemporaryDirectory(dir=workdir) as folder:
            with MemoryEngine(str(Path(folder) / "memory.db") if disk else None,
                              auto_warmup=False) as engine:
                for content in CASES[0][2:]:
                    engine.remember(content, kind=MemoryKind.SEMANTIC,
                                    created_at=NOW, auto_cues=False, auto_context=False)
                before = state(engine)
                for _ in range(3):
                    engine.temporal_anchor(CASES[0][1], top_k=2, now=NOW)
                diagnostics.append(dict(backend="sqlite" if disk else "dict",
                                        read_only=before == state(engine)))
    return dict(fixture_sha256=hashlib.sha256(json.dumps(CASES).encode()).hexdigest(),
        source_sha256={name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
                       for name, module in [("retrieval_mixin", retrieval), ("dual_track", dual_track)]},
        total=len(rows), passed=sum(r["passed"] for r in rows), rows=rows,
        diagnostics=diagnostics, note="Nine synthetic cases; repeated backend/top_k coverage is not independent evidence.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.workdir)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total": result["total"], "passed": result["passed"], "diagnostics": result["diagnostics"]}))
