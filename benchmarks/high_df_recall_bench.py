"""High-document-frequency keyword recall benchmark (run manually).

Why this exists: the old round-13 smoke script imported ``mnemosis`` from
site-packages, silently measuring a stale installed release (~1.8s per
high-df query) instead of the local source (~1-5ms). This benchmark pins
the local source on ``sys.path`` and prints the module path, so the
numbers always describe the code under test.

Usage::

    python benchmarks/high_df_recall_bench.py --count 100000 --chunk 5000

Builds a fresh store where every record contains the term "用户", then
measures cold + warm recall latency for high-df queries and a zero-hit
query. Fails (exit 1) if the warm p99 exceeds the generous guard.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time

from bench_utils import assert_local_mnemosis, percentile, pin_local_src

pin_local_src()

from build_bench import generate_records

from mnemosis import MemoryEngine

_MNEMOSIS_FILE = assert_local_mnemosis()

WARM_RUNS = 100
WARM_P99_GUARD_MS = 100.0
ZERO_HIT_QUERY = "量子鲽鱼 火星 茶壶"  # never mentioned in the corpus


def _timed(label: str, fn) -> float:
    start = time.perf_counter()
    fn()
    return (time.perf_counter() - start) * 1000.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100_000)
    parser.add_argument("--chunk", type=int, default=5000)
    parser.add_argument(
        "--db-dir",
        default=".",
        help="directory for the built database (default: cwd, avoids tmpfs)",
    )
    parser.add_argument(
        "--keep-db",
        action="store_true",
        help="keep the built database file and print its path",
    )
    args = parser.parse_args()

    os.makedirs(args.db_dir, exist_ok=True)
    db_path = os.path.join(args.db_dir, f"mnemosis_hidf_{args.count}.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    print(f"module under test: {_MNEMOSIS_FILE}")
    engine = MemoryEngine(db_path)
    records = generate_records(args.count)

    start = time.perf_counter()
    engine.remember_many_chunked(records, chunk_size=args.chunk)
    build_s = time.perf_counter() - start
    active = len(engine.store.backend.list())

    def _q(query: str) -> None:
        engine.recall(query, top_k=3)

    # Measure the first recall right after build: the df lookup below must
    # run AFTER this, otherwise it pre-warms the same pages/caches.
    first_after_build_ms = _timed("first 用户", lambda: _q("用户"))

    # Reopen the store and measure the first recall again: this reflects a
    # fresh engine loading the database (closer to a real cold start).
    engine.close()
    engine = MemoryEngine(db_path)

    def _cold_start() -> None:
        engine.recall("用户", top_k=3)

    cold_start_ms = _timed("reopen 用户", _cold_start)

    def _df() -> None:
        engine.store.backend.find_by_terms(["用户"], None)

    df_samples = [_timed("df", _df) for _ in range(5)]
    df_ms = statistics.median(df_samples)
    runs = {
        "用户": [],
        "用户 投影仪": [],
        "zero-hit": [],
    }
    for _ in range(WARM_RUNS):
        for key, query in (
            ("用户", "用户"),
            ("用户 投影仪", "用户 投影仪"),
            ("zero-hit", ZERO_HIT_QUERY),
        ):
            runs[key].append(_timed(key, lambda q=query: _q(q)))

    summary = {
        "count": args.count,
        "active": active,
        "module": _MNEMOSIS_FILE,
        "build_s": round(build_s, 2),
        "df_query_ms": round(df_ms, 2),
        "first_after_build_ms": round(first_after_build_ms, 2),
        "cold_start_ms": round(cold_start_ms, 2),
        "warm": {
            key: {
                "p50_ms": round(percentile(values, 0.50), 2),
                "p95_ms": round(percentile(values, 0.95), 2),
                "p99_ms": round(percentile(values, 0.99), 2),
            }
            for key, values in runs.items()
        },
    }
    guard = summary["warm"]["用户"]["p99_ms"]
    passed = guard <= WARM_P99_GUARD_MS
    summary["gate_passed"] = passed
    summary["gate"] = f"warm 用户 p99 <= {WARM_P99_GUARD_MS}ms"

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(
        f"build {build_s:.2f}s, df {df_ms:.2f}ms, "
        f"first {first_after_build_ms:.2f}ms, cold {cold_start_ms:.2f}ms, "
        f"warm 用户 p99 {guard:.2f}ms "
        f"({'PASS' if passed else 'FAIL'})"
    )
    if args.keep_db:
        print(f"db kept at: {db_path}")
    else:
        try:
            os.remove(db_path)
        except OSError:
            pass
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
