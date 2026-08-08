"""Unified regression: run all retrieval benchmarks at the current HEAD.

Every benchmark is retrieval-only (no cloud, no external packages), so this
can also run in CI. Prints a compact summary and writes one JSON.
"""

from __future__ import annotations

import json
import os
import sys
import time

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from locomo_bench import build_engine as build_en88  # noqa: E402
from locomo_bench import eval_retrieval as eval_en88  # noqa: E402
from locomo_bench import generate_dataset as gen_en88  # noqa: E402
from zh_locomo_bench import evaluate as eval_zh10k  # noqa: E402
from zh_locomo_bench import generate as gen_zh  # noqa: E402
from zh_locomo_bench import sample_questions  # noqa: E402
from zh_long_dialogue_eval import build as build_zh200  # noqa: E402
from zh_long_dialogue_eval import score_questions  # noqa: E402


def _run(name: str, fn) -> dict:
    t0 = time.perf_counter()
    result = fn()
    return {"name": name, "seconds": round(time.perf_counter() - t0, 1),
            "result": result}


def main() -> int:
    report: list[dict] = []

    def en88() -> dict:
        ds = gen_en88(42, 24, 5)
        e = build_en88(ds)
        r = eval_en88(e, ds["questions"], temporal_reason=True,
                      reasoning_pack=True)
        e.close()
        stats = r["stats"]
        return {
            "fact": stats["fact"]["hit5"],
            "event": stats["event"]["hit5"],
            "temporal": stats["temporal"]["hit5"],
            "distractor_pass": stats["distractor"]["pass"],
        }

    def zh200() -> dict:
        e, qs, _ = build_zh200(66)
        e.sleep()
        r = score_questions(e, qs, temporal_reason=True, reasoning_pack=True)
        e.close()
        return {"hit1": r["hit1"], "hit5": r["hit5"], "n": r["n"]}

    def zh10k() -> dict:
        ds = gen_zh(3333)
        ds["questions"] = sample_questions(ds["questions"], 2018)
        r = eval_zh10k(ds, True, temporal_reason=True, reasoning_pack=True)
        return {"total": r["total"],
                "temporal": r["kind_hit5"]["temporal"]}

    report.append(_run("en88", en88))
    report.append(_run("zh200", zh200))
    report.append(_run("zh10k", zh10k))

    def reasoning() -> dict:
        from reasoning_zh_bench import build_engine, eval_retrieval
        return {"stats": eval_retrieval(build_engine())}

    def conflict() -> dict:
        from conflict_evidence_bench import build_engine, eval_retrieval
        e = build_engine(use_evidence=True)
        r = eval_retrieval(e)
        e.close()
        return r

    def process() -> dict:
        from process_zh_bench import SCENARIOS, _coverage, _memories, _order_score
        from mnemosis import MemoryEngine
        from mnemosis.types import MemoryKind, SourceRecord, SourceType
        import re

        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        for content in _memories():
            cue = re.split(r"[在比喜欢最]", content, maxsplit=1)[0]
            kind = (MemoryKind.EPISODIC
                    if re.search(r"\d{4}年", content)
                    else MemoryKind.SEMANTIC)
            engine.remember(content, kind=kind, source=source, cues=[cue])
        cov = ordered = 0
        for s in SCENARIOS:
            ctx = [r.item.content for r in engine.recall_steps(s["question"], top_k=8)]
            c = _coverage(ctx, s["steps"])
            cov += c
            ordered += int(c == len(s["steps"])) and _order_score(ctx, s["steps"])
        engine.close()
        return {"coverage": cov, "ordered": ordered, "total_steps": 26}

    def conflict10k() -> dict:
        from conflict_evidence_10k_bench import build_engine, eval_retrieval
        e = build_engine(use_evidence=True)
        r = eval_retrieval(e)
        e.close()
        return r

    def synonym10k() -> dict:
        from synonym_zh_10k_bench import SCENARIOS, build_engine, _coverage, _ordered
        e = build_engine()
        cov = ordered = 0
        for s in SCENARIOS:
            ctx = [r.item.content for r in e.recall_steps(s["question"], top_k=8)]
            cov += _coverage(ctx, s["steps"])
            ordered += int(_ordered(ctx, s["steps"]))
        e.close()
        return {"coverage": cov, "ordered": ordered, "total_steps": 9}

    def compare10k() -> dict:
        from compare_zh_10k_bench import SCENARIOS, build_engine, _coverage
        e = build_engine()
        cov = 0
        for s in SCENARIOS:
            ctx = [r.item.content for r in e.recall_reasoning(s["question"], top_k=8)]
            cov += _coverage(ctx, s["premises"])
        e.close()
        return {"coverage": cov, "total_premises": 10}

    def outcome10k() -> dict:
        from outcome_evidence_10k_bench import TARGETS, build_engine
        e = build_engine(use_evidence=True)
        top1 = 0
        for t in TARGETS:
            ctx = [r.item.content for r in e.recall(t["q"], top_k=5)]
            top1 += int(bool(ctx) and ctx[0] == t["record"])
        e.close()
        return {"top1_target": top1, "n": len(TARGETS)}

    def plan_choice10k() -> dict:
        from plan_choice_10k_bench import GOAL, build_engine, ALI_STEPS, XIAOBO_STEPS
        e = build_engine()
        plan = e.plan_for_goal(GOAL, outcome_aware=True)
        ctx = [r.item.content for r in plan]
        e.close()
        return {
            "successful_first": int(
                ctx.index(XIAOBO_STEPS[0]) < ctx.index(ALI_STEPS[0])
            ),
            "steps_in": int(XIAOBO_STEPS[0] in ctx and ALI_STEPS[0] in ctx),
        }

    def plan_capacity() -> dict:
        from plan_capacity_bench import GOAL, STEPS, build_engine
        e = build_engine()
        plan = e.plan_for_goal(GOAL, outcome_aware=False)
        ctx = [r.item.content for r in plan]
        e.close()
        return {
            "coverage": sum(1 for s in STEPS if s in ctx),
            "total_steps": len(STEPS),
        }

    report.append(_run("reasoning_zh", reasoning))
    report.append(_run("conflict_evidence", conflict))
    report.append(_run("process_steps", process))
    report.append(_run("conflict_10k", conflict10k))
    report.append(_run("synonym_10k", synonym10k))
    report.append(_run("compare_10k", compare10k))
    report.append(_run("outcome_evidence_10k", outcome10k))
    report.append(_run("plan_choice_10k", plan_choice10k))
    report.append(_run("plan_capacity_10k", plan_capacity))

    for r in report:
        print(r["name"], r["result"], f"({r['seconds']}s)", flush=True)
    out = os.path.join(_BENCH, "results", "unified_regression.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
