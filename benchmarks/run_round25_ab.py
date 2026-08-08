"""Round-25 A/B: time-cell reasoning on vs off at 88 / 200 / 10k scales.

Runs the same real benchmarks with ``temporal_reason`` on and off:

  1. English LoCoMo 88 questions (locomo_bench.eval_retrieval)
  2. Chinese 200-session long dialogue (zh_long_dialogue_eval.score_questions)
  3. Chinese 10k-event store, 2018 sampled questions (zh_locomo_bench)
  4. Reasoning mini-bench (after1 / after2 / before1 / cross-person)

Writes one JSON with all four A/B pairs plus per-kind breakdowns.
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

from locomo_bench import build_engine, eval_retrieval, generate_dataset  # noqa: E402
from reasoning_mini_bench import build as build_reasoning  # noqa: E402
from reasoning_mini_bench import evaluate as eval_reasoning  # noqa: E402
from zh_locomo_bench import evaluate as eval_zh  # noqa: E402
from zh_locomo_bench import generate as generate_zh  # noqa: E402
from zh_locomo_bench import sample_questions  # noqa: E402
from zh_long_dialogue_eval import build as build_zh200  # noqa: E402
from zh_long_dialogue_eval import score_questions  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "round25_ab.json"),
    )
    parser.add_argument("--sessions-10k", type=int, default=3333)
    parser.add_argument("--max-questions-10k", type=int, default=2018)
    args = parser.parse_args()

    report: dict = {}

    # 1) English 88
    dataset88 = generate_dataset(seed=42, sessions=24, events_per_session=5)
    report["en88"] = {}
    for flag in (False, True):
        engine = build_engine(dataset88)
        report["en88"]["on" if flag else "off"] = eval_retrieval(
            engine, dataset88["questions"], temporal_reason=flag
        )["stats"]
        engine.close()

    # 2) Chinese 200-session
    report["zh200"] = {}
    for flag in (False, True):
        engine, questions, _ = build_zh200(66)
        engine.sleep()
        report["zh200"]["on" if flag else "off"] = score_questions(
            engine, questions, temporal_reason=flag
        )
        engine.close()

    # 3) Chinese 10k store, sampled questions
    dataset10k = generate_zh(args.sessions_10k)
    dataset10k["questions"] = sample_questions(
        dataset10k["questions"], args.max_questions_10k
    )
    report["zh10k"] = {}
    for flag in (False, True):
        report["zh10k"]["on" if flag else "off"] = eval_zh(
            dataset10k, True, temporal_reason=flag
        )

    # 4) Reasoning mini-bench
    rng_engine, questions = build_reasoning()
    report["reasoning_mini"] = {
        "on": eval_reasoning(rng_engine, questions, True),
        "off": eval_reasoning(rng_engine, questions, False),
    }
    rng_engine.close()

    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
