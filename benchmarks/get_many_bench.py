"""get_many latency baseline at 100k scale (run manually, no hard assert).

Usage:
    python benchmarks/get_many_bench.py

Build the 100k DB first if it is missing (the script reports the path it
expects). The planner CI test guards *plans*; this script guards *constants*
(row conversion, json_each parsing, SQLite version regressions).
"""

from __future__ import annotations

import os
import statistics
import sys
import tempfile
import time

_SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, _SRC)

from mnemosis.engine import MemoryEngine


def main() -> int:
    db_path = os.path.join(
        tempfile.gettempdir(), "mnemosis_prof_100k_v2.db"
    )
    if not os.path.exists(db_path):
        print(f"missing benchmark DB: {db_path}")
        return 1
    engine = MemoryEngine(memory_file=db_path)
    backend = engine.store.backend
    ids = [item.id for item in backend.list(limit=5000)]
    for count in (100, 1000, 5000):
        sample = ids[:count]
        backend.get_many(sample)  # warm
        runs = []
        for _ in range(5):
            start = time.perf_counter()
            items = backend.get_many(sample)
            runs.append((time.perf_counter() - start) * 1000)
            if len(items) != count:
                raise RuntimeError(
                    f"expected {count} items, got {len(items)}"
                )
        runs.sort()
        print(
            f"get_many {count}: avg {statistics.mean(runs):.2f} ms, "
            f"p50 {runs[2]:.2f} ms, max {runs[-1]:.2f} ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
