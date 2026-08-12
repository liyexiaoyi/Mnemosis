"""Plan-rewrite eval (round 184, executive planning).

10 stores. Each store rewrites the weak plan ["功能","部署","功能","需求"]
into ["调研需求","开发功能","部署上线"]: verbs added, duplicates removed,
standard order restored.
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
from mnemosis.mcp_server import MCPServer


def _run() -> dict:
    count_ok = content_ok = verb_ok = changes_ok = empty_ok = fields_ok = (
        mcp_ok
    ) = 0
    for seed in range(10):
        engine = MemoryEngine()
        server = MCPServer(engine=engine)
        report = engine.plan_rewrite(["功能", "部署", "功能", "需求"])
        count_ok += int(len(report["rewritten"]) == 3)
        content_ok += int(
            report["rewritten"]
            == ["调研需求", "开发功能", "部署上线"]
        )
        verb_ok += int(
            all(
                any(verb in step for verb in engine._PLAN_VERBS)
                for step in report["rewritten"]
            )
        )
        changes_ok += int(bool(report["changes"]))
        empty_ok += int(engine.plan_rewrite([])["rewritten"] == [])
        fields_ok += int(
            {"original", "rewritten", "changes"} <= set(report)
            and all(
                {"index", "original", "rewritten", "reason"}
                <= set(change)
                for change in report["changes"]
            )
        )
        via_mcp = server._call_tool(
            "plan_rewrite", {"plan": ["功能", "部署", "功能", "需求"]}
        )
        mcp_ok += int(
            via_mcp["rewritten"]
            == ["调研需求", "开发功能", "部署上线"]
        )
    return {
        "stores": 10,
        "count_ok": count_ok,
        "content_ok": content_ok,
        "verb_ok": verb_ok,
        "changes_ok": changes_ok,
        "empty_ok": empty_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "plan_rewrite_eval.json"),
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
