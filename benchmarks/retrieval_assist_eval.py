"""Retrieval-assist eval (round 130, Tulving & Thomson 1973).

10 stores. Each store has 2 memories whose cues differ from the query
words (Chinese synonyms). retrieval_assist must surface the stored cue as
a suggestion, report the new synonym terms, still recall the right
memory, respect limit, order suggestions by overlap, and fill fields.
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
    engine.remember(
        f"用户喜欢颜色偏蓝的配色{seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["颜色偏好", "蓝色主题"],
    )
    engine.remember(
        f"计划去北京旅行{seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["旅行计划"],
    )
    return engine


def _run() -> dict:
    cue_ok = syn_ok = recall_ok = limit_ok = order_ok = fields_ok = 0
    for seed in range(10):
        engine = _store(seed)
        a = engine.retrieval_assist("色彩", limit=8)
        b = engine.retrieval_assist("旅游", limit=8)
        cue_ok += int(
            "颜色偏好" in [s["cue"] for s in a["suggestions"]]
            and "旅行计划" in [s["cue"] for s in b["suggestions"]]
        )
        syn_ok += int(
            "颜色" in a["new_synonyms"] and "旅行" in b["new_synonyms"]
        )
        recall_ok += int(
            "颜色" in a["top_recall"][0]["preview"]
            and "旅行" in b["top_recall"][0]["preview"]
        )
        limit_ok += int(
            len(a["suggestions"]) <= 8 and len(b["suggestions"]) <= 8
        )
        order_ok += int(
            all(
                a["suggestions"][i]["matched_count"]
                >= a["suggestions"][i + 1]["matched_count"]
                for i in range(len(a["suggestions"]) - 1)
            )
            and all(
                b["suggestions"][i]["matched_count"]
                >= b["suggestions"][i + 1]["matched_count"]
                for i in range(len(b["suggestions"]) - 1)
            )
        )
        fields_ok += int(
            {"query", "expanded_terms", "new_synonyms", "suggestions",
             "top_recall"} <= set(a)
            and all(
                {"cue", "source", "matched_count"} <= set(s)
                for s in a["suggestions"]
            )
            and all(
                {"id", "preview", "score", "confident"} <= set(r)
                for r in a["top_recall"]
            )
        )
    return {
        "stores": 10,
        "cue_ok": cue_ok,
        "syn_ok": syn_ok,
        "recall_ok": recall_ok,
        "limit_ok": limit_ok,
        "order_ok": order_ok,
        "fields_ok": fields_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "retrieval_assist_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = all(
        v == 10 for k, v in report.items() if k != "stores"
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
