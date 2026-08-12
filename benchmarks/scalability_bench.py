"""Scalability benchmark: build time, memory, DB size, query latency.

Usage:
    python benchmarks/scalability_bench.py --count 100000 --chunk 5000

Prints a JSON summary plus human-readable lines. Results are NOT stored
in the repo (write to work/ if a report file is wanted).
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import random
import sys
import tempfile
import time

_BENCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_BENCH, "..", "src")))

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def _peak_rss_mb() -> float:
    """Windows process peak working set (MB); 0.0 if unavailable."""
    try:
        psapi = ctypes.WinDLL("psapi")
        kernel32 = ctypes.WinDLL("kernel32")

        class _Counters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("page_fault_count", ctypes.c_ulong),
                ("peak_working_set", ctypes.c_size_t),
                ("working_set", ctypes.c_size_t),
                ("quota_peak_paged", ctypes.c_size_t),
                ("quota_paged", ctypes.c_size_t),
                ("quota_peak_nonpaged", ctypes.c_size_t),
                ("quota_nonpaged", ctypes.c_size_t),
                ("pagefile_usage", ctypes.c_size_t),
                ("peak_pagefile_usage", ctypes.c_size_t),
            ]

        psapi.GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_Counters),
            ctypes.c_ulong,
        ]
        psapi.GetProcessMemoryInfo.restype = ctypes.c_int
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        counters = _Counters()
        counters.cb = ctypes.sizeof(counters)
        ok = psapi.GetProcessMemoryInfo(
            kernel32.GetCurrentProcess(),
            ctypes.byref(counters),
            counters.cb,
        )
        return (
            counters.peak_working_set / (1024 * 1024)
            if ok
            else 0.0
        )
    except Exception:  # noqa: BLE001
        return 0.0


def _generate_records(count: int) -> list[dict]:
    rng = random.Random(42)
    products = [
        "投影仪", "手机", "空调", "冰箱",
        "洗衣机", "电脑", "电视", "耳机",
    ]
    source = SourceRecord(origin=SourceType.USER)
    records = []
    for _ in range(count):
        user = rng.randint(1, max(1000, count // 10))
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
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100_000)
    parser.add_argument("--chunk", type=int, default=5_000)
    args = parser.parse_args()

    db = os.path.join(
        tempfile.gettempdir(), f"mnemosis_scalability_{args.count}.db"
    )
    if os.path.exists(db):
        os.remove(db)
    records = _generate_records(args.count)

    t0 = time.perf_counter()
    engine = MemoryEngine(db)
    engine.remember_many_chunked(records, chunk_size=args.chunk)
    build_s = time.perf_counter() - t0
    peak_mb = _peak_rss_mb()

    memories = engine.store.backend.count()
    links = engine.backend._conn.execute(
        "SELECT COUNT(*) FROM links"
    ).fetchone()[0]
    terms = engine.backend._conn.execute(
        "SELECT COUNT(*) FROM terms"
    ).fetchone()[0]
    db_size_mb = os.path.getsize(db) / (1024 * 1024)
    engine.close()

    # Cold query: fresh engine, first recall (logical cold start).
    engine = MemoryEngine(db)
    t0 = time.perf_counter()
    engine.recall("投影仪", top_k=3)
    cold_ms = (time.perf_counter() - t0) * 1000
    engine.close()

    # Warm queries: re-open and sample after warmup.
    engine = MemoryEngine(db)
    warm_queries = ["投影仪 空调", "手机 冰箱", "洗衣机 耳机"]
    for query in warm_queries:
        engine.recall(query, top_k=3)
    runs = []
    for query in warm_queries + ["空调 投影仪"]:
        t0 = time.perf_counter()
        engine.recall(query, top_k=3)
        runs.append((time.perf_counter() - t0) * 1000)
    runs.sort()
    engine.close()

    result = {
        "count": args.count,
        "chunk": args.chunk,
        "build_s": round(build_s, 2),
        "memories": memories,
        "links_rows": links,
        "terms_rows": terms,
        "db_size_mb": round(db_size_mb, 1),
        "peak_rss_mb": round(peak_mb, 1),
        "cold_query_ms": round(cold_ms, 2),
        "warm_query_median_ms": round(runs[len(runs) // 2], 2),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(
        f"build {result['build_s']}s, db {result['db_size_mb']}MB, "
        f"peak rss {result['peak_rss_mb']}MB, "
        f"cold {result['cold_query_ms']}ms, "
        f"warm {result['warm_query_median_ms']}ms"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
