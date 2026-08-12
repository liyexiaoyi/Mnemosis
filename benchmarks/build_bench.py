"""Batch-ingestion benchmark for Mnemosis (run manually).

Usage:
    python benchmarks/build_bench.py --count 20000 --chunk-size 2000

With the chunked bulk path this is the reproducibility baseline for the
100k build scalability work (100k measured ~50s on a dev machine vs ~6-7
minutes before the incremental-linking + bulk-mode optimizations).
"""

from __future__ import annotations

import argparse
import os
import random
import tempfile
import time
import tracemalloc

from bench_utils import pin_local_src

pin_local_src()


from mnemosis.engine import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

_PRODUCTS = ["投影仪", "手机", "空调", "冰箱", "洗衣机", "电脑", "电视", "耳机"]


def generate_records(count: int, seed: int = 42) -> list[dict]:
    random.seed(seed)
    user = SourceRecord(origin=SourceType.USER)
    records = []
    for _ in range(count):
        records.append(
            {
                "content": (
                    f"用户{random.randint(1, 10_000)}在2026年"
                    f"{random.randint(1, 12)}月{random.randint(1, 28)}日"
                    f"购买了{random.choice(_PRODUCTS)}，"
                    f"花了{random.randint(100, 999)}元。"
                ),
                "kind": MemoryKind.EPISODIC,
                "source": user,
                "importance": 0.5,
            }
        )
    return records


def giant_component_ratio(engine: MemoryEngine, total: int) -> float:
    """Union-find over links: share of nodes in the largest component."""
    rows = engine.backend._conn.execute(
        "SELECT src, dst FROM links"
    ).fetchall()
    parent: dict[str, str] = {}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: str, b: str) -> None:
        parent.setdefault(a, a)
        parent.setdefault(b, b)
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for row in rows:
        union(row[0], row[1])
    sizes: dict[str, int] = {}
    for node in parent:
        root = find(node)
        sizes[root] = sizes.get(root, 0) + 1
    return max(sizes.values(), default=0) / max(1, total)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=20_000)
    parser.add_argument("--chunk-size", type=int, default=2_000)
    parser.add_argument(
        "--check-graph",
        action="store_true",
        help="also report the largest connected component share of the "
        "link graph (quality evidence that the link budget keeps the "
        "graph connected)",
    )
    args = parser.parse_args()
    db_path = os.path.join(tempfile.gettempdir(), "mnemosis_build_bench.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = MemoryEngine(db_path)
    records = generate_records(args.count)
    tracemalloc.start()
    start = time.perf_counter()
    stored = engine.remember_many_chunked(
        records, chunk_size=args.chunk_size
    )
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(
        f"built {len(stored)} memories in {elapsed:.1f}s "
        f"({len(stored) / elapsed:.0f} items/s)"
    )
    print(f"peak python memory: {peak / 1e6:.0f} MB")
    if args.check_graph:
        ratio = giant_component_ratio(engine, len(stored))
        print(f"giant component share: {ratio:.3f}")
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
