"""Learner-profile eval (round 146, Mozer et al. 2009).

10 stores: 5 fast learners (12/12 successful reviews) and 5 struggling
ones (4/16 successful). learner_profile must estimate the success rate
and return matching profiles with suggested interval scales.
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

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.mcp_server import MCPServer  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402


def _store(successes: int, failures: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for i in range(4):
        item = engine.remember(
            f"learner {i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"lp-{i}"],
            auto_cues=False,
        )
        item.retrieval_successes = successes
        item.retrieval_failures = failures
        engine.backend.update(item)
    return engine


def _run() -> dict:
    rate_ok = profile_ok = scale_ok = total_ok = fields_ok = mcp_ok = 0
    for seed in range(5):
        fast = _store(3, 0)
        slow = _store(1, 3)
        fp = fast.learner_profile()
        sp = slow.learner_profile()
        rate_ok += int(
            fp["success_rate"] == 1.0 and sp["success_rate"] == 0.25
        )
        profile_ok += int(
            fp["profile"] == "fast" and sp["profile"] == "struggling"
        )
        scale_ok += int(
            fp["suggested_interval_scale"] == 1.2
            and sp["suggested_interval_scale"] == 0.8
        )
        total_ok += int(
            fp["total_memories"] == 4
            and fp["total_reviews"] == 12
            and sp["total_reviews"] == 16
        )
        fields_ok += int(
            {
                "total_memories", "total_reviews", "success_rate",
                "avg_retrievability", "avg_importance", "profile",
                "suggested_interval_scale",
            }
            <= set(fp)
            and 0.0 <= fp["avg_retrievability"] <= 1.0
        )
        via_mcp = MCPServer(engine=_store(2, 1))._call_tool(
            "learner_profile", {}
        )
        mcp_ok += int(
            via_mcp["profile"] == "steady"
            and via_mcp["suggested_interval_scale"] == 1.0
        )
    return {
        "stores": 10,
        "rate_ok": rate_ok,
        "profile_ok": profile_ok,
        "scale_ok": scale_ok,
        "total_ok": total_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "learner_profile_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = all(
        v == 5 for k, v in report.items() if k != "stores"
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
