"""Retrieval-side combination eval (round 87).

30 questions on one mixed store:
  1-6   corroboration (single impression vs multi-confirmed)
  7-10  gist preference (old gist vs fresh verbatim, summary question)
  11-14 emotional salience (neutral rival more salient)
  15-18 context matching (location disambiguates an ambiguous query)
  19-24 second look (evidence-backed rival behind a shaky top)
  25-30 plain facts (sanity: both modes answer)
Combined mode enables all retrieval mechanisms (incl. second_look);
baseline disables every boost. Combined should match or beat baseline and
win every mechanism-specific subset.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import timedelta

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


def _build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    # 1-6 corroboration
    for i in range(6):
        engine.remember(
            f"c{i} single",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"c{i}"],
            importance=0.77,
            strength=0.5,
            evidence_count=1,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
        engine.remember(
            f"c{i} confirmed",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"c{i}"],
            importance=0.5,
            strength=0.5,
            evidence_count=3,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    # 7-10 gist
    for i in range(4):
        engine.remember(
            f"要点：主题{i}喜欢红色。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"g{i}"],
            importance=0.5,
            strength=0.5,
            created_at=now - timedelta(days=60),
        )
        engine.remember(
            f"主题{i}说：我喜欢红色。",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=[f"g{i}"],
            importance=0.5,
            strength=0.5,
            created_at=now - timedelta(days=2),
        )
    # 11-14 emotional salience
    for i in range(4):
        engine.remember(
            f"e{i} neutral",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"e{i}"],
            importance=0.7,
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
        engine.remember(
            f"e{i} nervous",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"e{i}"],
            affect="negative",
            importance=0.5,
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    # 15-18 context
    locs = ["会议室", "餐厅", "图书馆", "家里"]
    for i, loc in enumerate(locs):
        engine.remember(
            f"ctx{i} 在{loc}里讨论了方案。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"ctx{i}"],
            context=loc,
            importance=0.5,
            strength=0.5,
            created_at=now - timedelta(days=10),
        )
    # 19-24 second look
    for i in range(6):
        engine.remember(
            f"s{i} weak",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"s{i}"],
            importance=0.7,
            strength=0.6,
            evidence_count=1,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
        engine.remember(
            f"s{i} strong",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"s{i}"],
            importance=0.55,
            strength=0.5,
            evidence_count=2,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    # 25-30 plain facts
    for i in range(6):
        engine.remember(
            f"事实{i}：编号{i}的稳定事实。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"plain{i}"],
            importance=0.8,
            strength=0.5,
            created_at=now - timedelta(days=10),
        )
    return engine


def _questions():
    qs = []
    for i in range(6):
        qs.append(("corroboration", f"c{i}", f"c{i} confirmed"))
    for i in range(4):
        qs.append(("gist", f"g{i}", "要点"))
    for i in range(4):
        qs.append(("emotional", f"e{i}", "nervous"))
    for i, loc in enumerate(["会议室", "餐厅", "图书馆", "家里"]):
        qs.append(("context", f"ctx{i}", loc))
    for i in range(6):
        qs.append(("second_look", f"s{i}", f"s{i} strong"))
    for i in range(6):
        qs.append(("plain", f"plain{i}", f"事实{i}"))
    return qs


def _run(combined: bool) -> dict:
    engine = _build_engine()
    locs = ["会议室", "餐厅", "图书馆", "家里"]
    counts: dict[str, int] = {}
    totals: dict[str, int] = {}
    for kind, key, expected in _questions():
        if kind == "gist":
            query = f"总结一下{key}喜欢什么颜色？"
            kwargs = {}
        elif kind == "context":
            query = "讨论过的方案是什么？"
            idx = int(key[3:])
            kwargs = {"context": f"正在{locs[idx]}里开会"}
        else:
            query = key
            kwargs = {}
        if not combined:
            kwargs.update(
                {
                    "context_boost": False,
                    "gist_preference": False,
                    "emotional_salience_boost": False,
                    "corroboration_boost": False,
                    "mood_congruent_boost": False,
                    "self_reference_boost": False,
                    "source_trust_boost": False,
                    "conflict_flag": False,
                    "second_look": False,
                }
            )
        else:
            kwargs["second_look"] = True
        results = engine.recall(query, top_k=3, **kwargs)
        top = results[0].item.content
        ok = (
            top == expected
            if kind in ("corroboration", "second_look")
            else (
                expected in top
                if kind in ("gist", "emotional", "plain")
                else locs[int(key[3:])] in top
            )
        )
        counts[kind] = counts.get(kind, 0) + int(ok)
        totals[kind] = totals.get(kind, 0) + 1
    return {
        "combined": combined,
        "by_kind": counts,
        "total": sum(counts.values()),
        "n": sum(totals.values()),
        "ratio": round(sum(counts.values()) / sum(totals.values()), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "retrieval_combo_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "combined": _run(True),
        "baseline": _run(False),
    }
    report["all_ok"] = bool(
        report["combined"]["total"] >= report["baseline"]["total"]
        and all(
            report["combined"]["by_kind"].get(k, 0)
            >= report["baseline"]["by_kind"].get(k, 0)
            for k in (
                "corroboration", "gist", "emotional", "context",
                "second_look", "plain",
            )
        )
    )
    for v in report.values():
        print(v, flush=True)
    print("all_ok:", report["all_ok"], flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
