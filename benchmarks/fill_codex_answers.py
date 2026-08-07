"""Fill the Codex-as-model answers for the model x project matrix.

The answers below were written by the agent (Codex) from the exact retrieval
contexts in work/project_contexts.json, following the same instruction given
to the Qwen models: "Answer using ONLY the memory context below. If the
context lacks the answer, answer 'unknown'." Temporal questions use the
earliest date strictly after the anchor date found in the context.
"""

from __future__ import annotations

import json
import os


_WORK = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "work")
)


def _matches(question: str, key: str) -> bool:
    return key.lower() in question.lower()


MNEMOSIS = [
    ("favorite color", "amber"),
    ("favorite food", "ramen"),
    ("favorite city", "Chiang Mai"),
    ("Bob buy on 2026-02-02", "vinyl record"),
    ("have for dinner on 2026-02-12", "pad thai"),
    ("have for dinner on 2026-02-17", "ramen"),
    ("having couscous for dinner on 2026-02-04", "ramen"),
    ("visiting aquarium on 2026-02-10", "ramen"),
    ("buying notebook on 2026-02-16", "ramen"),
    ("favorite music genre", "unknown"),
    ("favorite sports team", "unknown"),
    ("favorite season", "unknown"),
]

MEM0 = [
    ("favorite color", "amber"),
    ("favorite food", "ramen"),
    ("favorite city", "Chiang Mai"),
    ("Bob buy on 2026-02-02", "unknown"),
    ("have for dinner on 2026-02-12", "pad thai"),
    ("have for dinner on 2026-02-17", "unknown"),
    ("having couscous for dinner on 2026-02-04", "ramen"),
    ("visiting aquarium on 2026-02-10", "ramen"),
    ("buying notebook on 2026-02-16", "coffee beans"),
    ("favorite music genre", "unknown"),
    ("favorite sports team", "unknown"),
    ("favorite season", "unknown"),
]

COGNITIVE = [
    ("favorite color", "unknown"),
    ("favorite food", "unknown"),
    ("favorite city", "unknown"),
    ("Bob buy on 2026-02-02", "unknown"),
    ("have for dinner on 2026-02-12", "unknown"),
    ("have for dinner on 2026-02-17", "unknown"),
    ("having couscous for dinner on 2026-02-04", "unknown"),
    ("visiting aquarium on 2026-02-10", "unknown"),
    ("buying notebook on 2026-02-16", "unknown"),
    ("favorite music genre", "unknown"),
    ("favorite sports team", "unknown"),
    ("favorite season", "unknown"),
]


def _apply(pending: dict, project: str, mapping: list) -> None:
    rows = pending.get(project, {})
    for question in rows:
        for key, answer in mapping:
            if _matches(question, key):
                rows[question] = answer
                break
        else:
            rows[question] = "unknown"


def main() -> int:
    path = os.path.join(_WORK, "codex_project_answers.json")
    if not os.path.exists(path):
        print("pending file missing; run model_x_project.py first")
        return 1
    with open(path, encoding="utf-8") as handle:
        pending = json.load(handle)
    _apply(pending, "mnemosis", MNEMOSIS)
    _apply(pending, "mem0", MEM0)
    _apply(pending, "cognitive", COGNITIVE)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(pending, handle, ensure_ascii=False, indent=2)
    print("codex answers filled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
