"""Render a human-readable memory-map chart (stdlib-only SVG, Chinese labels).

Usage:
    python benchmarks/render_memory_map.py --db memory.db --out map.svg
"""

from __future__ import annotations

import argparse
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_BENCH, "..", "src")))

from mnemosis import MemoryEngine
from mnemosis.render import render_memory_map_svg as render_svg


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=None, help="SQLite path (default: in-memory)")
    parser.add_argument("--out", default="memory_map.svg")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    engine = MemoryEngine(args.db)
    data = engine.memory_map(limit=args.limit)
    engine.close()
    svg = render_svg(data, "Mnemosis 记忆地图")
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(svg)
    print(f"saved {args.out} ({len(data['topics'])} topics)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
