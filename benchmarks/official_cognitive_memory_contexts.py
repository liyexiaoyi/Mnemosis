"""Dump cognitive-memory 0.5.1 search contexts (system Python 3.14)."""

from __future__ import annotations

import json
import os
import sys

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
    for memory in dataset["facts"] + dataset["events"]:
        mem.add(
            memory["content"],
            category="core" if memory["kind"] == "semantic" else "episodic",
        )
    contexts = {}
    for q in questions:
        resp = mem.search(q["q"], top_k=top_k)
        contexts[q["q"]] = [r.memory.content for r in resp.results]
    json.dump(contexts, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
    print("cognitive-memory contexts done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
