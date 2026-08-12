"""Sleep-consolidation benchmark (run manually).

Usage:
    python benchmarks/sleep_bench.py --count 20000

Builds a synthetic store with the batch-ingestion path and times the
offline sleep pass. Reference: ~2.7s on a 50k-row dev store (snapshot
sharing means the whole store is converted to Python objects once).
"""

from __future__ import annotations

import argparse
import math
import os
import random
import statistics
import tempfile
import time

from bench_utils import pin_local_src

pin_local_src()


from build_bench import generate_records

from mnemosis.engine import MemoryEngine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=20_000)
    parser.add_argument(
        "--tail-queries",
        type=int,
        default=100,
        help="recalls right after sleep to measure wake-up tail latency",
    )
    parser.add_argument(
        "--steady-runs",
        type=int,
        default=0,
        help="additional sleep calls after the first, to time steady-state "
        "sleep (first sleep includes consolidation of the whole store)",
    )
    args = parser.parse_args()
    db_path = os.path.join(tempfile.gettempdir(), "mnemosis_sleep_bench.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = MemoryEngine(db_path)
    records = generate_records(args.count)
    engine.remember_many_chunked(records, chunk_size=2_000)
    start = time.perf_counter()
    report = engine.sleep()
    elapsed = time.perf_counter() - start
    print(f"sleep {elapsed:.2f}s -> {report.summary()}")
    if args.steady_runs > 0:
        # The first sleep already ran whole-store consolidation; subsequent
        # calls measure steady-state/no-op cost (sleep is idempotent).
        steady = []
        for _ in range(args.steady_runs):
            t0 = time.perf_counter()
            engine.sleep()
            steady.append(time.perf_counter() - t0)
        steady.sort()
        median = statistics.median(steady)
        p99 = steady[max(0, math.ceil(len(steady) * 0.99) - 1)]
        print(
            f"steady-state sleep seconds (n={len(steady)}): "
            f"median={median:.3f} p99={p99:.3f}"
        )
    if args.tail_queries > 0:
        times = []
        for _ in range(args.tail_queries):
            query = f"用户{random.randint(1, 10_000)} 投影仪"
            t0 = time.perf_counter()
            engine.recall(query, top_k=3)
            times.append((time.perf_counter() - t0) * 1000)
        times.sort()
        p50 = times[len(times) // 2]
        p95 = times[max(0, int(len(times) * 0.95) - 1)]
        p99 = times[max(0, int(len(times) * 0.99) - 1)]
        print(
            f"post-sleep recall ms (n={len(times)}): "
            f"p50={p50:.2f} p95={p95:.2f} p99={p99:.2f}"
        )
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
