"""Conflict resolution at 10k scale (round 30).

Embeds the 8 conflict scenarios (loser first, evidence winner second) into
~10k deterministic noise memories (same-person facts + 150 distractor
people). Verifies that evidence-weighted protection still picks the winner
first when the same-pattern rivals are buried at scale.
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
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402

from conflict_evidence_bench import SCENARIOS  # noqa: E402
from reasoning_zh_10k_bench import generate_memories  # noqa: E402


def build_engine(use_evidence: bool) -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    # conflict memories first (so noise does not win by insertion order)
    for s in SCENARIOS:
        engine.remember(
            s["loser"],
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[s["person"]],
            evidence_count=1,
        )
        engine.remember(
            s["winner"],
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[s["person"]],
            evidence_count=s["winner_evidence"] if use_evidence else 1,
        )
        for d in s["distractors"]:
            engine.remember(
                d,
                kind=MemoryKind.SEMANTIC,
                source=source,
                cues=[s["person"]],
                evidence_count=1,
            )
    for content in generate_memories():
        cue = content.split("最")[0].split("比")[0].split("买")[0]
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[cue],
            importance=0.7,
        )
    return engine


def eval_retrieval(engine: MemoryEngine) -> dict:
    stats = {"top1_winner": 0, "winner_in5": 0, "n": len(SCENARIOS)}
    rows = []
    for s in SCENARIOS:
        results = engine.recall(s["question"], top_k=5)
        contents = [r.item.content for r in results]
        rows.append(
            {
                "question": s["question"],
                "top1": contents[0] if contents else "",
                "context": contents,
            }
        )
        stats["top1_winner"] += int(
            bool(contents) and contents[0] == s["winner"]
        )
        stats["winner_in5"] += int(s["winner"] in contents)
    return {"stats": stats, "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-limit", type=int, default=4)
    parser.add_argument(
        "--out",
        default=os.path.join(
            _BENCH, "results", "conflict_evidence_10k_bench.json"
        ),
    )
    args = parser.parse_args()
    on = build_engine(use_evidence=True)
    off = build_engine(use_evidence=False)
    report = {
        "memories": len(on.store.all_active()),
        "on": eval_retrieval(on),
        "off": eval_retrieval(off),
        "llm": [],
    }
    print("memories:", report["memories"], flush=True)
    print("on:", report["on"]["stats"], flush=True)
    print("off:", report["off"]["stats"], flush=True)

    if args.llm:
        from cloud_qwen_matrix import cloud_generate

        for label, engine, rows in (
            ("evidence_on", on, report["on"]["rows"]),
            ("evidence_off", off, report["off"]["rows"]),
        ):
            hits = 0
            details = []
            for s, row in zip(SCENARIOS[: args.llm_limit], rows[: args.llm_limit]):
                context = "\n".join(f"- {c}" for c in row["context"])
                prompt = (
                    "只用下面的记忆上下文回答中文问题；上下文里没有答案就回答'unknown'。\n\n"
                    f"上下文：\n{context}\n\n问题：{s['question']}"
                )
                answer = cloud_generate(prompt, max_tokens=200)
                score = int(any(k in answer for k in s["keys"]))
                hits += score
                details.append(
                    {
                        "question": s["question"],
                        "answer": answer,
                        "keys": s["keys"],
                        "score": score,
                    }
                )
                print(f"  [{label}] {s['question'][:22]:24s} score={score}",
                      flush=True)
            report["llm"].append(
                {
                    "condition": label,
                    "n": args.llm_limit,
                    "accuracy": round(hits / args.llm_limit, 3),
                    "details": details,
                }
            )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    on.close()
    off.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
