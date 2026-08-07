"""Lifecycle behavior evaluation: decay, review, emotion, update, conflicts.

Deterministic and LLM-free. Answers:
  1. Do memories decay without review? (forgetting curve)
  2. Does spaced review preserve them?
  3. Do emotionally tagged memories persist longer?
  4. Does update() replace stale facts cleanly?
  5. Are contradictions detected during sleep?
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import timedelta

from mnemosis import MemoryEngine
from mnemosis.embedding import NGramEmbedder
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow

try:
    from locomo_bench import build_engine, eval_retrieval, generate_dataset
except ImportError:
    from benchmarks.locomo_bench import (
        build_engine,
        eval_retrieval,
        generate_dataset,
    )


def run_decay_eval(days: int = 30, review_every_days: int = 7) -> dict:
    now = utcnow()
    user = SourceRecord(origin=SourceType.USER)
    engine = MemoryEngine()

    def remember_topic(i: int, **kwargs) -> None:
        engine.remember(
            f"User {i} prefers topic-{i}.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"topic-{i}"],
            importance=0.3,
            created_at=now - timedelta(days=days),
            **kwargs,
        )

    for i in range(30):
        remember_topic(i)

    # weekly reviews for the first half
    for week in range(1, days // review_every_days + 1):
        review_time = now - timedelta(days=days - week * review_every_days)
        for i in range(15):
            engine.recall(f"topic-{i}", top_k=1, now=review_time)

    def correct_metric(indices: range) -> tuple[float, float]:
        hits = 0
        total_score = 0.0
        for i in indices:
            results = engine.recall(f"topic-{i}", top_k=1, now=now)
            if results and f"topic-{i}" in results[0].item.content:
                hits += 1
                total_score += results[0].score
        return hits / len(indices), total_score / len(indices)

    reviewed_hit, reviewed_score = correct_metric(range(15))
    unreviewed_hit, unreviewed_score = correct_metric(range(15, 30))

    # emotional memory decays slower
    emotional = engine.remember(
        "The user was anxious about the outage.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        affect="negative",
        created_at=now - timedelta(days=days),
    )
    neutral = engine.remember(
        "A routine note about the build.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        created_at=now - timedelta(days=days),
    )
    emotional_retrievability = engine.curve.retrievability(emotional, now)
    neutral_retrievability = engine.curve.retrievability(neutral, now)
    engine.close()
    return {
        "days": days,
        "reviewed_retention": round(reviewed_hit, 3),
        "unreviewed_retention": round(unreviewed_hit, 3),
        "reviewed_avg_score": round(reviewed_score, 3),
        "unreviewed_avg_score": round(unreviewed_score, 3),
        "emotional_retrievability": round(emotional_retrievability, 3),
        "neutral_retrievability": round(neutral_retrievability, 3),
    }


def run_update_eval() -> dict:
    user = SourceRecord(origin=SourceType.USER)
    engine = MemoryEngine()
    item = engine.remember(
        "The API rate limit is 100 per minute.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["api", "rate"],
    )
    engine.update(item.id, content="The API rate limit is 200 per minute.")
    results = engine.recall("api rate limit", top_k=3)
    top_content = results[0].item.content if results else ""
    stale_survives = any("100 per minute" in r.item.content for r in results)

    a = engine.remember(
        "Deploy takes 3 minutes.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["deploy", "time"],
        confidence=0.9,
    )
    b = engine.remember(
        "Deploy takes 30 minutes.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["deploy", "time"],
        confidence=0.9,
    )
    report = engine.sleep()
    engine.close()
    return {
        "updated_top_content": top_content,
        "stale_content_survives": stale_survives,
        "conflicts_detected": len(report.conflicts),
        "revision_count": item.revision_count,
    }


def run_update_at_scale(count: int = 1000) -> dict:
    user = SourceRecord(origin=SourceType.USER)
    engine = MemoryEngine()
    target_index = min(777, count - 1)
    target = None
    for i in range(count):
        item = engine.remember(
            f"Setting {i} is enabled.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"setting-{i}"],
            importance=0.3,
        )
        if i == target_index:
            target = item
    engine.update(target.id, content=f"Setting {target_index} is disabled.")
    results = engine.recall(f"setting-{target_index}", top_k=5)
    top = results[0].item.content if results else ""
    stale = any(
        r.item.content == f"Setting {target_index} is enabled." for r in results
    )
    engine.close()
    return {"top_content": top, "stale_survives": stale}


def run_concurrency_check() -> dict:
    """Two connections on the same WAL database: write from one, read from other."""
    import os
    import tempfile

    path = os.path.join(tempfile.gettempdir(), "mnemosis_concurrency.db")
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            os.remove(candidate)
    writer = MemoryEngine(path)
    reader = MemoryEngine(path)
    writer.remember(
        "Shared memory works across connections.",
        kind=MemoryKind.SEMANTIC,
        source=SourceRecord(origin=SourceType.USER),
        cues=["shared"],
    )
    results = reader.recall("shared memory works", top_k=3)
    ok = bool(results)
    writer.close()
    reader.close()
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            os.remove(candidate)
    return {"reader_sees_writer_data": ok}


def run_learning_curve(rounds: int = 3, gap_days: int = 7) -> dict:
    """Testing effect vs time decay, measured as a controlled comparison.

    Two identical engines are built. One is "trained": the full question set
    is asked once, then again after ``gap_days`` (with time advancing, so the
    successful retrievals get spaced reinforcement). The other engine is
    untouched and evaluated at the same final time. The trained engine should
    recall better than the fresh one — that gap is the net testing effect
    (Roediger & Karpicke, 2006) minus pure decay.
    """
    dataset = generate_dataset(seed=42, sessions=24, events_per_session=5)
    embedder = NGramEmbedder()
    trained = build_engine(dataset, embedder=embedder)
    fresh = build_engine(dataset, embedder=embedder)
    t0 = utcnow()

    def hit1_at(engine, when) -> float:
        report = eval_retrieval(engine, dataset["questions"], now=when)
        stats = report["stats"]
        n = sum(values["n"] for values in stats.values())
        hits = sum(values["hit1"] for values in stats.values())
        return round(hits / n, 3)

    # same engine trains at t0, then is re-tested after gap_days (spacing).
    t1 = t0 + timedelta(days=gap_days)
    by_round: list[float] = [hit1_at(trained, t0)]
    trained_hit1 = hit1_at(trained, t1)
    fresh_hit1 = hit1_at(fresh, t1)
    trained.close()
    fresh.close()
    return {
        "hit1_by_round": by_round,
        "trained_vs_fresh": {
            "trained_after_gap": trained_hit1,
            "fresh_after_gap": fresh_hit1,
            "testing_effect_gain": round(trained_hit1 - fresh_hit1, 3),
        },
    }


def run_merge_eval(repeats: int = 20) -> dict:
    """Sleep deduplication: identical experiences collapse into one trace."""
    user = SourceRecord(origin=SourceType.USER)
    engine = MemoryEngine()
    for _ in range(repeats):
        engine.remember(
            "Alice visited the harbor on 2026-02-01.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["alice", "harbor"],
            importance=0.5,
        )
    before = len(engine.store.all_active(MemoryKind.EPISODIC))
    report = engine.sleep()
    after = len(engine.store.all_active(MemoryKind.EPISODIC))
    survivor = engine.store.all_active(MemoryKind.EPISODIC)[0]
    engine.close()
    return {
        "before": before,
        "merged": report.merged,
        "after": after,
        "storage_saved_pct": round(100.0 * report.merged / before, 1),
        "survivor_evidence": survivor.evidence_count,
    }


def run_spaced_review_eval(
    n_memories: int = 30,
    weeks: int = 4,
    review_limit: int = 10,
) -> dict:
    """End-to-end spaced-repetition loop: review_due + review() feedback.

    Every week the 10 most-forgotten memories are reviewed (marked success);
    without review, decay wins. We measure how many memories stay above a
    0.5 retrievability threshold after ``weeks``.
    """
    user = SourceRecord(origin=SourceType.USER)
    engine = MemoryEngine()
    for i in range(n_memories):
        engine.remember(
            f"fact-{i} value-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"fact-{i}"],
            importance=0.5,
        )
    now = utcnow()
    for _ in range(weeks):
        for item in engine.review_due(limit=review_limit, now=now):
            engine.review(item.id, success=True, now=now)
        now = now + timedelta(days=7)
    kept = sum(
        1
        for item in engine.backend.list()
        if engine.curve.retrievability(item, now) > 0.5
    )
    engine.close()

    engine2 = MemoryEngine()
    for i in range(n_memories):
        engine2.remember(
            f"fact-{i} value-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"fact-{i}"],
            importance=0.5,
        )
    kept_no_review = sum(
        1
        for item in engine2.backend.list()
        if engine2.curve.retrievability(item, now) > 0.5
    )
    engine2.close()
    return {
        "reviewed_kept": kept,
        "unreviewed_kept": kept_no_review,
        "total": n_memories,
        "review_advantage": kept - kept_no_review,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--review-every", type=int, default=7)
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__),
            "results",
            f"lifecycle_{time.strftime('%Y%m%d_%H%M%S')}.json",
        ),
    )
    args = parser.parse_args()

    decay = run_decay_eval(args.days, args.review_every)
    update = run_update_eval()
    scale = run_update_at_scale()
    concurrency = run_concurrency_check()
    learning = run_learning_curve()
    merge = run_merge_eval()
    spaced = run_spaced_review_eval()
    print("== decay ==")
    print(f"  retention after {args.days} days:")
    print(f"    reviewed weekly : {decay['reviewed_retention']:.3f}")
    print(f"    never reviewed  : {decay['unreviewed_retention']:.3f}")
    print(f"  avg recall score of the correct memory:")
    print(f"    reviewed weekly : {decay['reviewed_avg_score']:.3f}")
    print(f"    never reviewed  : {decay['unreviewed_avg_score']:.3f}")
    print(
        f"  emotional vs neutral retrievability: "
        f"{decay['emotional_retrievability']} vs {decay['neutral_retrievability']}"
    )
    print("== update & conflicts ==")
    print(f"  top content after update: {update['updated_top_content']!r}")
    print(f"  stale content survives  : {update['stale_content_survives']}")
    print(f"  conflicts detected      : {update['conflicts_detected']}")
    print("== update at scale (1000 memories) ==")
    print(f"  top content             : {scale['top_content']!r}")
    print(f"  stale fact survives     : {scale['stale_survives']}")
    print("== concurrency (WAL, two connections) ==")
    print(f"  reader sees writer data : {concurrency['reader_sees_writer_data']}")
    print("== learning curve (same 88 questions, repeated) ==")
    print(f"  hit@1 by round          : {learning['hit1_by_round']}")
    trained_vs_fresh = learning["trained_vs_fresh"]
    print(
        f"  trained after 7d gap    : {trained_vs_fresh['trained_after_gap']}"
    )
    print(f"  fresh after 7d          : {trained_vs_fresh['fresh_after_gap']}")
    print(
        f"  net testing effect      : {trained_vs_fresh['testing_effect_gain']:+.3f}"
    )
    print("== sleep dedup (identical repeats) ==")
    print(f"  before sleep            : {merge['before']} memories")
    print(f"  merged during sleep     : {merge['merged']}")
    print(f"  after sleep             : {merge['after']} memories")
    print(f"  storage saved           : {merge['storage_saved_pct']}%")
    print("== spaced-review loop (4 weeks, 30 memories) ==")
    print(f"  reviewed : {spaced['reviewed_kept']}/{spaced['total']} still retrievable")
    print(f"  never    : {spaced['unreviewed_kept']}/{spaced['total']} still retrievable")
    print(f"  advantage: +{spaced['review_advantage']} memories kept")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "decay": decay,
                "update": update,
                "update_at_scale": scale,
                "concurrency": concurrency,
                "learning_curve": learning,
                "merge": merge,
                "spaced_review": spaced,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\nresults saved to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
