"""Full-chain combination eval (round 92).

End-to-end pipeline on one store (56 memories):
  write (auto cues/context) -> sleep (weak-important replay + consolidation)
  -> 14 days of practice (recommended defaults) -> 40 retrieval questions
  (facts/conflicts/emotional/gist/context/revised flags).

Full arm uses every mechanism; baseline disables sleep, practice flags and
retrieval boosts. Expect full >= baseline with a clear margin.
"""

from __future__ import annotations

import argparse
import json
import os
import random
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
    for i in range(10):
        engine.remember(
            f"事实{i}：编号{i}的稳定事实。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"fact{i}"],
            importance=0.8,
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    for i in range(8):
        engine.remember(
            f"conflict{i} single",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"conflict{i}"],
            importance=0.77,
            strength=0.5,
            evidence_count=1,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
        engine.remember(
            f"conflict{i} confirmed",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"conflict{i}"],
            importance=0.5,
            strength=0.5,
            evidence_count=3,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    for i in range(8):
        engine.remember(
            f"emo{i} neutral",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"emo{i}"],
            importance=0.7,
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
        engine.remember(
            f"emo{i} nervous",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"emo{i}"],
            affect="negative",
            importance=0.5,
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    for i in range(6):
        engine.remember(
            f"要点：主题{i}喜欢红色。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"gist{i}"],
            importance=0.5,
            strength=0.5,
            created_at=now - timedelta(days=60),
        )
        engine.remember(
            f"主题{i}说：我喜欢红色。",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=[f"gist{i}"],
            importance=0.5,
            strength=0.5,
            created_at=now - timedelta(days=2),
        )
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
    for i in range(4):
        item = engine.remember(
            f"rev{i} v0",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"rev{i}"],
            importance=0.5,
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
        engine.update(item.id, content=f"rev{i} v1", now=now)
    return engine


def _questions():
    qs = []
    for i in range(10):
        qs.append(("fact", f"fact{i}", f"事实{i}"))
    for i in range(8):
        qs.append(("conflict", f"conflict{i}", "confirmed"))
    for i in range(8):
        qs.append(("emotional", f"emo{i}", "nervous"))
    for i in range(6):
        qs.append(("gist", f"gist{i}", "要点"))
    for i, loc in enumerate(["会议室", "餐厅", "图书馆", "家里"]):
        qs.append(("context", f"ctx{i}", loc))
    for i in range(4):
        qs.append(("revised", f"rev{i}", "已修订"))
    return qs


def run_full_chain_eval(full: bool, seed: int) -> dict:
    engine = _build_engine()
    now = utcnow()
    rng = random.Random(seed)
    if full:
        engine.sleep(now=now)
        for day in range(14):
            day_now = now + timedelta(days=day)
            due = engine.practice_due(
                limit=4,
                now=day_now,
                min_gap_hours=24.0,
                adaptive_gap=False,
                arousal_priority=True,
                interleave=True,
                vary_cues=True,
                fresh_priority=False,
            )
            for card in due:
                item = engine.backend.get(card["id"])
                if item is None:
                    continue
                retrievability = engine.curve.retrievability(item, day_now)
                ok = rng.random() < retrievability
                engine.practice_answer(
                    item.id,
                    item.content if ok else "错误答案",
                    now=day_now,
                )
    locs = ["会议室", "餐厅", "图书馆", "家里"]
    by_kind: dict[str, int] = {}
    totals: dict[str, int] = {}
    for kind, key, expected in _questions():
        kwargs = {}
        if kind == "gist":
            query = f"总结一下{key}喜欢什么颜色？"
        elif kind == "context":
            query = "讨论过的方案是什么？"
            kwargs["context"] = f"正在{locs[int(key[3:])]}里开会"
        else:
            query = key
        if not full:
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
                    "revision_flag": False,
                    "second_look": False,
                }
            )
        else:
            kwargs["second_look"] = True
        results = engine.recall(query, top_k=3, **kwargs)
        top = results[0]
        if kind == "revised":
            ok = any("已修订" in r for r in top.reasons)
        elif kind in ("conflict", "emotional", "fact"):
            ok = expected in top.item.content
        elif kind == "gist":
            ok = "要点" in top.item.content
        else:
            ok = locs[int(key[3:])] in top.item.content
        by_kind[kind] = by_kind.get(kind, 0) + int(ok)
        totals[kind] = totals.get(kind, 0) + 1
    return {
        "full": full,
        "by_kind": by_kind,
        "total": sum(by_kind.values()),
        "n": sum(totals.values()),
        "ratio": round(sum(by_kind.values()) / sum(totals.values()), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "full_chain_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "full": run_full_chain_eval(True, args.seed),
        "baseline": run_full_chain_eval(False, args.seed),
    }
    report["all_ok"] = bool(
        report["full"]["total"] >= report["baseline"]["total"] + 5
        and all(
            report["full"]["by_kind"].get(k, 0)
            >= report["baseline"]["by_kind"].get(k, 0)
            for k in (
                "fact", "conflict", "emotional", "gist", "context",
                "revised",
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
