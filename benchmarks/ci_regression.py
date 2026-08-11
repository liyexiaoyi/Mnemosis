"""Fast capability regression gate for CI (no external services).

Runs the deterministic lifecycle evaluations plus a small LoCoMo retrieval
set, then asserts minimum scores. Any silent capability regression fails the
build. All datasets are generated locally with fixed seeds.
"""

from __future__ import annotations

import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BENCH)
sys.path.insert(0, os.path.normpath(os.path.join(_BENCH, "..", "src")))

import lifecycle_eval  # noqa: E402
from locomo_bench import (  # noqa: E402
    build_engine,
    eval_retrieval,
    generate_dataset,
)

_CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    _CHECKS.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail)


def main() -> int:
    decay = lifecycle_eval.run_decay_eval()
    check(
        "decay: reviewed beats unreviewed",
        decay["reviewed_avg_score"] > decay["unreviewed_avg_score"],
        f"{decay['reviewed_avg_score']:.3f} vs {decay['unreviewed_avg_score']:.3f}",
    )
    check(
        "decay: emotional beats neutral",
        decay["emotional_retrievability"] > decay["neutral_retrievability"],
        (
            f"{decay['emotional_retrievability']:.3f} vs "
            f"{decay['neutral_retrievability']:.3f}"
        ),
    )

    update = lifecycle_eval.run_update_eval()
    check("update: stale fact gone", not update["stale_content_survives"])
    check(
        "update: conflicts detected",
        update["conflicts_detected"] >= 1,
        str(update["conflicts_detected"]),
    )

    scale = lifecycle_eval.run_update_at_scale()
    check("update@1000: stale fact gone", not scale["stale_survives"])

    concurrency = lifecycle_eval.run_concurrency_check()
    check(
        "concurrency: WAL reader sees writer",
        concurrency["reader_sees_writer_data"],
    )

    learning = lifecycle_eval.run_learning_curve()
    check(
        "learning: hit@1 >= 0.70",
        max(learning["hit1_by_round"]) >= 0.70,
        str(learning["hit1_by_round"]),
    )

    merge = lifecycle_eval.run_merge_eval()
    check(
        "sleep dedup >= 90%",
        merge["storage_saved_pct"] >= 90.0,
        f"{merge['storage_saved_pct']}%",
    )

    spaced = lifecycle_eval.run_spaced_review_eval()
    check(
        "spaced review advantage >= 5",
        spaced["review_advantage"] >= 5,
        f"+{spaced['review_advantage']}",
    )

    meta = lifecycle_eval.run_metacognition_eval()
    check("metacognition guard", meta["hallucination_guard"])

    dataset = generate_dataset(seed=7, sessions=4, events_per_session=3)
    report = eval_retrieval(build_engine(dataset), dataset["questions"])["stats"]
    fact, event, distractor = (
        report["fact"],
        report["event"],
        report["distractor"],
    )
    check(
        "locomo fact hit@1 >= 0.95",
        fact["hit1"] / fact["n"] >= 0.95,
        f"{fact['hit1']}/{fact['n']}",
    )
    check(
        "locomo event hit@1 >= 0.80",
        event["hit1"] / event["n"] >= 0.80,
        f"{event['hit1']}/{event['n']}",
    )
    check(
        "locomo distractor pass >= 0.95",
        distractor["pass"] / distractor["n"] >= 0.95,
        f"{distractor['pass']}/{distractor['n']}",
    )

    failed = [name for name, ok, _ in _CHECKS if not ok]
    print(f"\nCI REGRESSION: {len(_CHECKS) - len(failed)}/{len(_CHECKS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
