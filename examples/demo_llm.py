"""Mnemosis + any OpenAI-compatible LLM.

Retrieve memories with Mnemosis, then answer with a stronger model of your
choice (local or cloud) using only the retrieved context. Zero runtime
dependencies: the chat call uses urllib, so it works with Ollama, vLLM,
or any OpenAI-compatible endpoint.

Run:
    python examples/demo_llm.py --db memory.db --question "用户喜欢什么语言？"

Optional env vars:
    LLM_BASE_URL  (default http://127.0.0.1:11434/v1)
    LLM_MODEL     (default qwen2.5:3b)
    LLM_API_KEY   (only needed for cloud endpoints)
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.request

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def chat(prompt: str) -> str:
    base = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
    model = os.environ.get("LLM_MODEL", "qwen2.5:3b")
    api_key = os.environ.get("LLM_API_KEY", "")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="memory.db")
    parser.add_argument("--question", default="用户喜欢什么语言？")
    args = parser.parse_args()

    engine = MemoryEngine(args.db)
    if engine.store.all_active() == []:
        user = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "用户喜欢用中文讨论技术问题。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["语言", "偏好"],
            importance=0.9,
        )

    results = engine.recall_fused(args.question, top_k=5)
    context = "\n".join(f"- {r.item.content}" for r in results)
    prompt = (
        "请只根据下面的记忆回答问题；记忆里没有答案就回答“unknown”。\n"
        f"记忆：\n{context}\n\n问题：{args.question}"
    )
    answer = chat(prompt)
    print(f"问题：{args.question}")
    print(f"答案：{answer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
