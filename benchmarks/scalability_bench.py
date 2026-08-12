"""Scalability benchmark: build time, memory, DB size, query latency.

Usage:
    python benchmarks/scalability_bench.py --count 100000 --chunk 5000

Prints a JSON summary plus human-readable lines. Results are NOT stored
in the repo (write to work/ if a report file is wanted).
"""

from __future__ import annotations

import argparse
import ctypes
import gc
import json
import os
import random
import sys
import tempfile
import time
from contextlib import suppress
from ctypes import wintypes

_BENCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_BENCH, "..", "src")))

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def _peak_memory_mb() -> tuple[float, float]:
    """Peak (working set MB, commit MB); (0.0, 0.0) if unavailable."""
    if sys.platform == "win32":
        try:
            kernel32 = ctypes.WinDLL("kernel32")
            try:
                get_mem_info = kernel32.K32GetProcessMemoryInfo
            except AttributeError:
                psapi = ctypes.WinDLL("psapi")
                get_mem_info = psapi.GetProcessMemoryInfo

            class _Counters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("page_fault_count", wintypes.DWORD),
                    ("peak_working_set", ctypes.c_size_t),
                    ("working_set", ctypes.c_size_t),
                    ("quota_peak_paged", ctypes.c_size_t),
                    ("quota_paged", ctypes.c_size_t),
                    ("quota_peak_nonpaged", ctypes.c_size_t),
                    ("quota_nonpaged", ctypes.c_size_t),
                    ("pagefile_usage", ctypes.c_size_t),
                    ("peak_pagefile_usage", ctypes.c_size_t),
                ]

            get_mem_info.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(_Counters),
                wintypes.DWORD,
            ]
            get_mem_info.restype = wintypes.BOOL
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            kernel32.GetCurrentProcess.argtypes = []
            counters = _Counters()
            counters.cb = ctypes.sizeof(counters)
            if counters.cb not in (40, 72):
                return 0.0, 0.0
            ok = get_mem_info(
                kernel32.GetCurrentProcess(),
                ctypes.byref(counters),
                counters.cb,
            )
            if ok:
                return (
                    counters.peak_working_set / (1024 * 1024),
                    counters.peak_pagefile_usage / (1024 * 1024),
                )
            return 0.0, 0.0
        except Exception:  # noqa: BLE001
            return 0.0, 0.0
    try:
        import resource

        # Linux ru_maxrss is KiB; macOS reports bytes.
        maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
        return maxrss / divisor, 0.0
    except Exception:  # noqa: BLE001
        return 0.0, 0.0


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
    if hasattr(sys.stdout, "reconfigure"):
        with suppress(Exception):
            sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100_000)
    parser.add_argument("--chunk", type=int, default=5_000)
    args = parser.parse_args()

    db = os.path.join(
        tempfile.gettempdir(), f"mnemosis_scalability_{args.count}.db"
    )
    try:
        if os.path.exists(db):
            os.remove(db)
        records = _generate_records(args.count)
        base_mb, _ = _peak_memory_mb()

        t0 = time.perf_counter()
        cpu0 = time.process_time()
        engine = MemoryEngine(db)
        engine.remember_many_chunked(records, chunk_size=args.chunk)
        build_s = time.perf_counter() - t0
        build_cpu_s = time.process_time() - cpu0
        peak_mb, peak_commit_mb = _peak_memory_mb()

        memories = engine.store.backend.count()
        links = engine.backend.count_links()
        terms = engine.backend.count_terms()
        db_size_mb = os.path.getsize(db) / (1024 * 1024)
        engine.close()

        # Cold query: fresh engine, first recall (first-touch latency,
        # looped three times but only the first sample is reported). This
        # is an application-level cold start; the OS page cache may still
        # be warm from the build.
        gc.collect()
        app_cold_ms = 0.0
        for _ in range(3):
            engine = MemoryEngine(db)
            t0 = time.perf_counter()
            engine.recall("投影仪", top_k=3)
            sample = (time.perf_counter() - t0) * 1000
            app_cold_ms = sample if _ == 0 else app_cold_ms
            engine.close()
            gc.collect()

        # Warm queries: re-open and sample after warmup.
        engine = MemoryEngine(db)
        warm_queries = ["投影仪 空调", "手机 冰箱", "洗衣机 耳机"]
        for _ in range(10):
            for query in warm_queries:
                engine.recall(query, top_k=3)
        runs = []
        gc.disable()
        try:
            for index in range(200):
                query = warm_queries[index % len(warm_queries)]
                t0 = time.perf_counter()
                engine.recall(query, top_k=3)
                runs.append((time.perf_counter() - t0) * 1000)
        finally:
            gc.enable()
        runs.sort()
        engine.close()
        qps = 200 / (sum(runs) / 1000)

        result = {
            "count": args.count,
            "chunk": args.chunk,
            "build_s": round(build_s, 2),
            "build_cpu_s": round(build_cpu_s, 2),
            "build_cpu_utilization": round(
                build_cpu_s / build_s, 2
            ),
            "memories": memories,
            "links_rows": links,
            "terms_rows": terms,
            "db_size_mb": round(db_size_mb, 1),
            "base_rss_mb": round(base_mb, 1),
            "peak_rss_mb": round(peak_mb, 1),
            "rss_delta_mb": round(peak_mb - base_mb, 1),
            "peak_commit_mb": round(peak_commit_mb, 1),
            "app_cold_query_ms": round(app_cold_ms, 2),
            "warm_query_p50_ms": round(runs[99], 2),
            "warm_query_p95_ms": round(runs[189], 2),
            "warm_query_p99_ms": round(runs[197], 2),
            "warm_query_qps": round(qps, 1),
        }
        print(json.dumps(result, ensure_ascii=True, indent=2))
        print(
            f"build {result['build_s']}s "
            f"(cpu {result['build_cpu_s']}s, "
            f"util {result['build_cpu_utilization']}), "
            f"db {result['db_size_mb']}MB, "
            f"rss {result['base_rss_mb']}->{result['peak_rss_mb']}MB "
            f"(delta {result['rss_delta_mb']}MB), "
            f"app-cold {result['app_cold_query_ms']}ms, "
            f"warm p50 {result['warm_query_p50_ms']}ms / "
            f"p95 {result['warm_query_p95_ms']}ms / "
            f"p99 {result['warm_query_p99_ms']}ms / "
            f"{result['warm_query_qps']} qps"
        )
        return 0
    finally:
        if os.path.exists(db):
            with suppress(Exception):
                os.remove(db)


if __name__ == "__main__":
    raise SystemExit(main())
