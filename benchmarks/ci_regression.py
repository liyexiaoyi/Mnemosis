"""Fast capability regression gate for CI (no external services).

Runs the deterministic lifecycle evaluations plus a small LoCoMo retrieval
set, then asserts minimum scores. Any silent capability regression fails the
build. All datasets are generated locally with fixed seeds.
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import tempfile
from collections import Counter

from bench_utils import BENCH, pin_local_src

pin_local_src()


import lifecycle_eval
from full_chain_eval import run_full_chain_eval
from locomo_bench import (
    build_engine,
    eval_retrieval,
    generate_dataset,
)
from plan_choice_10k_bench import (
    ALI_STEPS,
    GOAL,
    XIAOBO_STEPS,
)
from plan_choice_10k_bench import (
    build_engine as build_plan_engine,
)

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

_CHECKS: list[tuple[str, bool, str]] = []

_FULL_CHAIN_KINDS = (
    "fact", "conflict", "emotional",
    "gist", "context", "revised",
)
_FULL_CHAIN_MIN_MARGIN = 5


def _full_chain_ok(full: dict, baseline: dict) -> bool:
    """Full mechanisms must beat baseline by a clear margin.

    The eval is fully deterministic (local engine, fixed seed, no LLM),
    so a strict per-kind comparison is stable rather than flaky.
    """
    if full["n"] != baseline["n"] or full["n"] == 0:
        return False
    return (
        full["total"] >= baseline["total"] + _FULL_CHAIN_MIN_MARGIN
        and all(
            full["by_kind"].get(kind, 0)
            >= baseline["by_kind"].get(kind, 0)
            for kind in _FULL_CHAIN_KINDS
        )
    )


def _run_zh_retrieval_gate(script: str, project: str) -> tuple[bool, str]:
    """Run a Chinese retrieval benchmark in retrieval-only mode and parse
    the final multi-line JSON stats (subprocess isolation + UTF-8 pipes).
    """
    proc = subprocess.run(
        [
            sys.executable,
            os.path.join(BENCH, script),
            "--project",
            project,
            "--retrieval-only",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        check=False,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    stats: dict = {}
    lines = proc.stdout.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if line.strip() == "{"),
        None,
    )
    if start is not None:
        try:
            stats = json.loads("\n".join(lines[start:])).get(
                "stats", {}
            )
        except json.JSONDecodeError:
            pass
    ok = (
        proc.returncode == 0
        and bool(stats)
        and stats.get("n", 0) > 0
        and stats.get("ordered", 0) == stats.get("n", 0)
        and stats.get("coverage", 0) >= stats.get("n", 0)
    )
    return ok, str(stats)


def run_chunked_build_snapshot() -> dict[str, int]:
    """Deterministic chunked-build graph snapshot.

    Guards the incremental association builder: a change to link
    selection or bucket handling must keep the exact edge count of a
    fixed seed/records dataset.
    """
    rng = random.Random(42)
    products = [
        "投影仪", "手机", "空调", "冰箱",
        "洗衣机", "电脑", "电视", "耳机",
    ]
    source = SourceRecord(origin=SourceType.USER)
    records = []
    for _ in range(240):
        user = rng.randint(1, 1000)
        product = rng.choice(products)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        records.append(
            {
                "content": (
                    f"用户{user}在2026年{month}月{day}日购买了"
                    f"{product}，花了{rng.randint(100, 999)}元。"
                ),
                "kind": MemoryKind.EPISODIC,
                "source": source,
                "importance": 0.5,
            }
        )
    with tempfile.TemporaryDirectory() as tmp:
        engine = MemoryEngine(os.path.join(tmp, "snapshot.db"))
        try:
            engine.remember_many_chunked(records, chunk_size=40)
            memories = engine.store.backend.count()
            links = engine.backend.all_links()
            out_degree = Counter(src for src, _, _ in links)
            hits = len(engine.recall("投影仪", top_k=3))
            # Baseline values come from this exact seed-42 dataset:
            # memories=240, API link views=14304 (7152 canonical rows),
            # distinct src=240, max out-degree=105, recall hits=3.
            # all_terms(None) loads everything into memory: safe at this
            # 240-record scale, but revisit if the CI dataset grows.
            term_rows = sum(
                len(ids)
                for ids in engine.backend.all_terms(None).values()
            )
        finally:
            engine.close()
    return {
        "memories": memories,
        "links": len(links),
        "distinct_src": len(out_degree),
        "max_out_degree": max(out_degree.values(), default=0),
        "term_rows": term_rows,
        "hits": hits,
    }


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

    snapshot = run_chunked_build_snapshot()
    check(
        "chunked build graph snapshot",
        (
            snapshot["memories"] == 240
            and snapshot["links"] == 14304
            and snapshot["distinct_src"] == 240
            and snapshot["max_out_degree"] == 105
            and snapshot["term_rows"] == 3729
            and snapshot["hits"] == 3
        ),
        (
            f"{snapshot['memories']} memories, "
            f"links {snapshot['links']} (expected 14304), "
            f"distinct src {snapshot['distinct_src']} (expected 240), "
            f"max degree {snapshot['max_out_degree']} (expected 105), "
            f"term rows {snapshot['term_rows']} (expected 3729), "
            f"recall hits {snapshot['hits']} (expected 3)"
        ),
    )

    full = run_full_chain_eval(True, seed=42)
    baseline = run_full_chain_eval(False, seed=42)
    check(
        "full chain beats baseline",
        _full_chain_ok(full, baseline),
        (
            f"{full['total']}/{full['n']} vs "
            f"{baseline['total']}/{baseline['n']}"
        ),
    )

    # 0.2 noise (~2k memories) keeps the fast CI gate; top_k=30 keeps the
    # down-weighted plan safely inside the window so the assertion checks
    # ranking, not recall. The full 10k run is available standalone.
    plan_engine = build_plan_engine(noise_scale=0.2)
    try:
        plan_on = plan_engine.plan_for_goal(
            GOAL, top_k=30, outcome_aware=True
        )
        plan_off = plan_engine.plan_for_goal(
            GOAL, top_k=30, outcome_aware=False
        )
    finally:
        plan_engine.close()

    def _rank(plan: list, content: str) -> int | None:
        contents = [r.item.content for r in plan]
        return contents.index(content) if content in contents else None

    on_x = _rank(plan_on, XIAOBO_STEPS[0])
    on_a = _rank(plan_on, ALI_STEPS[0])
    off_x = _rank(plan_off, XIAOBO_STEPS[0])
    off_a = _rank(plan_off, ALI_STEPS[0])
    check(
        "zh planning: outcome-aware ranks successful plan",
        (
            on_x is not None
            and on_a is not None
            and off_x is not None
            and off_a is not None
            and on_x < on_a
            and off_x > off_a
        ),
        (
            f"on 小波@{on_x} 阿丽@{on_a}; "
            f"off 小波@{off_x} 阿丽@{off_a}"
        ),
    )

    zh_ok, zh_detail = _run_zh_retrieval_gate(
        "process_zh_bench.py", "mnemosis_steps"
    )
    check(
        "zh process: recall_steps covers and orders all steps",
        zh_ok,
        zh_detail,
    )

    reuse_ok, reuse_detail = _run_zh_retrieval_gate(
        "plan_reuse_zh_bench.py", "mnemosis"
    )
    check(
        "zh reuse: recall_steps retrieves reference plan steps",
        reuse_ok,
        reuse_detail,
    )

    failed = [name for name, ok, _ in _CHECKS if not ok]
    print(f"\nCI REGRESSION: {len(_CHECKS) - len(failed)}/{len(_CHECKS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
