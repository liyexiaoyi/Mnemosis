"""Chinese reasoning bench contexts from official cognitive-memory 0.5.1."""

from __future__ import annotations

import json
import os
import sys
import time

_USER_SITE = os.path.join(
    os.environ.get("APPDATA", ""), "Python", "Python314", "site-packages"
)
if os.path.isdir(_USER_SITE) and _USER_SITE not in sys.path:
    sys.path.insert(0, _USER_SITE)
_BENCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BENCH)

from cognitive_memory import SyncCognitiveMemory
from reasoning_zh_bench import MEMORIES, QUESTIONS


def main() -> int:
    mem = SyncCognitiveMemory(embedder="hash")
    t0 = time.perf_counter()
    for content in MEMORIES:
        mem.add(content, category="core")
    ingest = time.perf_counter() - t0

    rows = []
    coverage = {"n": 0, "premises5": 0}
    t0 = time.perf_counter()
    for q in QUESTIONS:
        resp = mem.search(q["q"], top_k=5)
        contents = [r.memory.content for r in resp.results]
        rows.append(
            {
                "kind": q["kind"],
                "question": q["q"],
                "context": contents,
            }
        )
        coverage["n"] += 1
        coverage["premises5"] += int(
            all(p in contents for p in q["premises"])
        )
    search = time.perf_counter() - t0
    report = {
        "system": "cognitive-memory 0.5.1 (hash embedder)",
        "retrieval": coverage,
        "ingest_seconds": round(ingest, 1),
        "search_seconds": round(search, 1),
        "rows": rows,
    }
    out = os.path.join(_BENCH, "results", "reasoning_ctx_cognitive.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
