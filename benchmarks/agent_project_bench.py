"""Agent project end-to-end benchmark (round 36).

Three mini-projects (trip / party / move). A cloud qwen3.7-plus agent:
  1. plans by reusing a referenced old project ("参考阿丽是怎么准备的");
  2. executes and records one outcome (success/fail) into memory;
  3. later judges "which step failed" and answers a never-seen question.

Backends: Mnemosis (plan_for_goal / record_outcome / recall) vs the real
mem0 package (search / add). Same goals, same agent prompts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

os.environ["MEM0_TELEMETRY"] = "False"

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

SCENARIOS = [
    {
        "goal": "大壮想去京都旅行，参考阿丽是怎么准备的？",
        "steps": [
            "阿丽在2026年4月1日订了去京都的机票。",
            "阿丽在2026年4月2日买了相机。",
            "阿丽在2026年4月3日收拾了行李。",
            "阿丽在2026年4月4日去了京都。",
        ],
        "keys": ["机票", "相机", "行李", "京都"],
        "outcome_question": "大壮的京都旅行计划中，哪一步出了问题？",
        "outcome_answer": "订机票",
        "outcome_step": "订机票",
        "outcome_fail": True,
        "outcome_note": "航班取消",
    },
    {
        "goal": "琳琳想办生日派对，参照小波是怎么准备的？",
        "steps": [
            "小波在2026年5月1日买了蛋糕。",
            "小波在2026年5月2日订了餐厅。",
            "小波在2026年5月3日买了气球。",
            "小波在2026年5月4日请了朋友来家里。",
        ],
        "keys": ["蛋糕", "餐厅", "气球", "朋友"],
        "outcome_question": "琳琳的生日派对计划中，哪一步出了问题？",
        "outcome_answer": "订餐厅",
        "outcome_step": "订餐厅",
        "outcome_fail": True,
        "outcome_note": "餐厅满座",
    },
    {
        "goal": "强强想搬家，模仿琳琳是怎么做的？",
        "steps": [
            "琳琳在2026年6月1日找了搬家公司。",
            "琳琳在2026年6月2日打包了箱子。",
            "琳琳在2026年6月3日搬到了新家。",
            "琳琳在2026年6月4日收拾了新房间。",
        ],
        "keys": ["搬家公司", "箱子", "新家", "房间"],
        "outcome_question": "强强的搬家计划中，哪一步出了问题？",
        "outcome_answer": "打包箱子",
        "outcome_step": "打包箱子",
        "outcome_fail": True,
        "outcome_note": "箱子不够",
    },
]

JUDGE_QUESTIONS = [
    {
        "q": "阿丽上次旅行顺利吗？",
        "answer": "unknown",
        "note": "从未记录过阿丽旅行的总体评价，应诚实答unknown",
    },
    {
        "q": "哪次项目的订机票环节出过问题？",
        "answer": "京都旅行",
        "note": "应检索到 大壮京都旅行计划·订机票 失败记录",
    },
]


def _cloud(prompt: str) -> str:
    from cloud_qwen_matrix import cloud_generate

    return cloud_generate(prompt, max_tokens=400)


def _answer_contains_keys(answer: str, keys: list[str]) -> bool:
    return all(k in answer for k in keys)


def _ordered_in_answer(answer: str, keys: list[str]) -> bool:
    indexes = [answer.index(k) for k in keys if k in answer]
    return bool(indexes and indexes == sorted(indexes) and len(indexes) == len(keys))


def _mnemosis_backend() -> dict:
    from mnemosis import MemoryEngine
    from mnemosis.types import MemoryKind, SourceRecord, SourceType

    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for s in SCENARIOS:
        for step in s["steps"]:
            cue = re.split(r"[在]", step, maxsplit=1)[0]
            engine.remember(
                step,
                kind=MemoryKind.EPISODIC,
                source=source,
                cues=[cue],
            )
    return {"engine": engine, "name": "Mnemosis"}


def _mem0_backend() -> dict:
    from mem0 import Memory

    cfg = {
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "qwen2.5:3b",
                "ollama_base_url": "http://127.0.0.1:11434",
                "temperature": 0,
                "max_tokens": 100,
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": "nomic-embed-text",
                "ollama_base_url": "http://127.0.0.1:11434",
            },
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "mem0_agent_project_bench",
                "path": os.path.join(_BENCH, "..", "..", "work", "mem0db"),
            },
        },
    }
    mem = Memory.from_config(cfg)
    for s in SCENARIOS:
        for step in s["steps"]:
            mem.add(step, user_id="u1", infer=False)
    return {"mem": mem, "name": "mem0"}


def _run_backend(backend: dict) -> dict:
    rows = []
    for s in SCENARIOS:
        if "engine" in backend:
            plan_ctx = [
                r.item.content
                for r in backend["engine"].plan_for_goal(s["goal"], top_k=8)
            ]
        else:
            resp = backend["mem"].search(
                s["goal"], filters={"user_id": "u1"}, limit=5
            )
            plan_ctx = [r.get("memory", "") for r in resp.get("results", [])]
        plan_answer = _cloud(
            "下面是记忆上下文。请为问题中的目标写一个按时间顺序的步骤计划，"
            "每步一行，只列步骤。\n\n"
            f"上下文：\n" + "\n".join(f"- {c}" for c in plan_ctx)
            + f"\n\n目标：{s['goal']}"
        )
        # record the outcome
        if "engine" in backend:
            backend["engine"].record_outcome(
                s["goal"][:8],
                s["outcome_step"],
                success=s["outcome_fail"] is False,
                note=s["outcome_note"],
            )
        else:
            backend["mem"].add(
                f"项目“{s['goal'][:8]}”的步骤“{s['outcome_step']}”执行失败"
                f"（{s['outcome_note']}）。",
                user_id="u1",
                infer=False,
            )
        # ask which step failed
        if "engine" in backend:
            out_ctx = [
                r.item.content
                for r in backend["engine"].recall(
                    s["outcome_question"], top_k=5
                )
            ]
        else:
            resp = backend["mem"].search(
                s["outcome_question"], filters={"user_id": "u1"}, limit=5
            )
            out_ctx = [r.get("memory", "") for r in resp.get("results", [])]
        out_answer = _cloud(
            "只用下面的记忆上下文回答；没有就答unknown。\n\n"
            f"上下文：\n" + "\n".join(f"- {c}" for c in out_ctx)
            + f"\n\n问题：{s['outcome_question']}"
        )
        rows.append(
            {
                "goal": s["goal"],
                "plan_ctx_order": int(
                    all(st in plan_ctx for st in s["steps"])
                    and [
                        plan_ctx.index(st) for st in s["steps"]
                    ] == sorted(
                        [plan_ctx.index(st) for st in s["steps"]]
                    )
                ),
                "plan_ctx": plan_ctx,
                "plan_coverage": int(_answer_contains_keys(plan_answer, s["keys"])),
                "plan_ordered": int(_ordered_in_answer(plan_answer, s["keys"])),
                "plan_answer": plan_answer,
                "outcome_recalled": int(s["outcome_answer"] in out_answer),
                "outcome_answer": out_answer,
            }
        )
        print(
            f"  [{backend['name']}] {s['goal'][:24]:26s} "
            f"plan_cov={rows[-1]['plan_coverage']} plan_order="
            f"{rows[-1]['plan_ordered']} outcome={rows[-1]['outcome_recalled']}",
            flush=True,
        )
    # judge questions
    judge = []
    for jq in JUDGE_QUESTIONS:
        if "engine" in backend:
            ctx = [
                r.item.content
                for r in backend["engine"].recall(jq["q"], top_k=5)
            ]
        else:
            resp = backend["mem"].search(
                jq["q"], filters={"user_id": "u1"}, limit=5
            )
            ctx = [r.get("memory", "") for r in resp.get("results", [])]
        answer = _cloud(
            "只用下面的记忆上下文回答；没有就答unknown。\n\n"
            f"上下文：\n" + "\n".join(f"- {c}" for c in ctx)
            + f"\n\n问题：{jq['q']}"
        )
        if jq["answer"] == "unknown":
            ok = int("unknown" in answer.lower())
        else:
            ok = int(jq["answer"] in answer)
        judge.append({"question": jq["q"], "ok": ok, "answer": answer})
        print(
            f"  [{backend['name']}] judge: {jq['q'][:20]} -> {answer[:28]} "
            f"ok={ok}",
            flush=True,
        )
    return {
        "name": backend["name"],
        "rows": rows,
        "judge": judge,
        "plan_coverage": sum(r["plan_coverage"] for r in rows),
        "plan_ordered": sum(r["plan_ordered"] for r in rows),
        "plan_ctx_order": sum(r["plan_ctx_order"] for r in rows),
        "outcome_recalled": sum(r["outcome_recalled"] for r in rows),
        "judge_ok": sum(j["ok"] for j in judge),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend", choices=["mnemosis", "mem0"], default="mnemosis"
    )
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    backend = _mnemosis_backend() if args.backend == "mnemosis" else _mem0_backend()
    report = _run_backend(backend)
    print(json.dumps(
        {
            "name": report["name"],
            "plan_coverage": report["plan_coverage"],
            "plan_ordered": report["plan_ordered"],
            "plan_ctx_order": report["plan_ctx_order"],
            "outcome_recalled": report["outcome_recalled"],
            "judge_ok": report["judge_ok"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    out = args.out or os.path.join(
        _BENCH, "results", f"agent_project_{args.backend}.json"
    )
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
