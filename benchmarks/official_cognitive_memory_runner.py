# -*- coding: utf-8 -*-
"""Run official cognitive-memory 0.5.1 benchmark (system Python 3.14)."""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict

# cognitive-memory 0.5.1 lives in the Windows user site-packages; make sure
# it is importable even when the runner runs from a sandboxed workdir.
_USER_SITE = os.path.join(
    os.environ.get("APPDATA", ""), "Python", "Python314", "site-packages"
)
if os.path.isdir(_USER_SITE) and _USER_SITE not in sys.path:
    sys.path.insert(0, _USER_SITE)

from cognitive_memory import SyncCognitiveMemory


def main() -> int:
    req = json.load(open(sys.argv[1], encoding="utf-8"))
    dataset, questions, top_k = req["dataset"], req["questions"], req["top_k"]
    mem = SyncCognitiveMemory(embedder="hash")
    t0 = time.perf_counter()
    for memory in dataset["facts"] + dataset["events"]:
        mem.add(
            memory["content"],
            category="core" if memory["kind"] == "semantic" else "episodic",
        )
    ingest = time.perf_counter() - t0

    def expected(q):
        return [t for t in q["answer"].lower().split() if t]

    def hit(c, e):
        return all(t in c.lower() for t in e)

    stats = defaultdict(lambda: {"n": 0, "hit1": 0, "hit5": 0, "pass": 0})
    t0 = time.perf_counter()
    for q in questions:
        kind = q["kind"]
        stats[kind]["n"] += 1
        if kind == "distractor":
            resp = mem.search(q["q"], top_k=top_k)
            rel = [r for r in resp.results if r.relevance_score > 0.05]
            stats[kind]["pass"] += int(len(rel) == 0)
            continue
        resp = mem.search(q["q"], top_k=top_k)
        contents = [r.memory.content for r in resp.results]
        e = expected(q)
        stats[kind]["hit1"] += int(bool(contents) and hit(contents[0], e))
        stats[kind]["hit5"] += int(any(hit(c, e) for c in contents))
    search = time.perf_counter() - t0

    totals = {"n": 0, "hit1": 0, "hit5": 0, "pass": 0}
    for v in stats.values():
        for k in totals:
            totals[k] += v[k]
    out = {
        "name": "cognitive-memory \u5b98\u65b9\u5305 (0.5.1)",
        "n": totals["n"],
        "total_hit1": round(totals["hit1"] / totals["n"], 3),
        "total_hit5": round(totals["hit5"] / totals["n"], 3),
        "fact@5": round(stats["fact"]["hit5"] / stats["fact"]["n"], 3),
        "event@5": round(stats["event"]["hit5"] / stats["event"]["n"], 3),
        "temporal@5": round(stats["temporal"]["hit5"] / stats["temporal"]["n"], 3),
        "distractor_pass": totals["pass"],
        "ingest_seconds": round(ingest, 1),
        "search_seconds": round(search, 1),
    }
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"))
    print("cognitive-memory done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
