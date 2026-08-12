"""Local model answer for the sleep-replay dimension (round 53)."""

from __future__ import annotations

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from compare_with_models import ollama_generate

from mnemosis import MemoryEngine

MODEL = "qwen2.5:3b"
URL = "http://127.0.0.1:11434"


def main() -> int:
    engine = MemoryEngine()
    for _ in range(5):
        engine.record_outcome("旅行", "订机票", success=True)
    engine.record_outcome("旅行", "订机票", success=False, note="航班取消")
    engine.sleep_replay()
    ctx = [
        r.item.content
        for r in engine.recall("订机票 历史成功率", top_k=5)
        if "历史成功率" in r.item.content
    ]
    if not ctx:
        ctx = [
            i.content for i in engine.store.all_active()
            if "历史成功率" in i.content and "订机票" in i.content
        ]
    answer = ollama_generate(
        MODEL,
        "只用下面的记忆上下文回答；没有就答unknown。\n\n"
        "上下文：\n" + "\n".join(f"- {c}" for c in ctx)
        + "\n\n问题：订机票的历史成功率是多少？",
        URL,
        timeout=60,
    )
    report = {
        "identifies_ratio": int("5" in answer and "6" in answer),
        "answer": answer,
    }
    print(report, flush=True)
    out = os.path.join(_BENCH, "results", "local_model_v3_extra.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
