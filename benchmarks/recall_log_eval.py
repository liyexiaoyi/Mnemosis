"""Recall-log eval (round 120).

10 stores; 30 recalls per store. The bounded audit log should hold the
last 30 entries, the newest entry must match the last recall, limit must
work, and every entry must carry confidence.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for i in range(10):
        engine.remember(
            f"log{seed}-{i} value{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"log{seed}-{i}"],
            importance=0.6,
            strength=0.5,
        )
    return engine


def _run() -> dict:
    len_ok = 0
    last_ok = 0
    limit_ok = 0
    conf_ok = 0
    for seed in range(10):
        engine = _store(seed)
        for i in range(30):
            engine.recall(f"log{seed}-{i % 10}", top_k=3)
        log = engine.get_recall_log(limit=50)
        len_ok += int(len(log) == 30)
        last = log[-1]
        last_ok += int(
            last["query"] == f"log{seed}-{i % 10}"
            and last["top_id"] is not None
        )
        limit_ok += int(len(engine.get_recall_log(limit=5)) == 5)
        conf_ok += int(all("confident" in e for e in log))
    return {
        "stores": 10,
        "len_ok": len_ok,
        "last_ok": last_ok,
        "limit_ok": limit_ok,
        "conf_ok": conf_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "recall_log_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = all(v == 10 for k, v in report.items() if k != "stores")
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
