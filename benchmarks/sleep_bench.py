"""Sleep-consolidation benchmark (run manually).

Usage:
    python benchmarks/sleep_bench.py --count 20000

Builds a synthetic store with the batch-ingestion path and times the
offline sleep pass. Reference: ~2.7s on a 50k-row dev store (snapshot
sharing means the whole store is converted to Python objects once).
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time

_SRC = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)
sys.path.insert(0, _SRC)

from build_bench import generate_records

from mnemosis.engine import MemoryEngine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=20_000)
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
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
