"""Render a human-readable memory-map chart (stdlib-only SVG, Chinese labels).

Usage:
    python benchmarks/render_memory_map.py --db memory.db --out map.svg
"""

from __future__ import annotations

import argparse
import html
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_BENCH, "..", "src")))

from mnemosis import MemoryEngine


def render_svg(data: dict, title: str) -> str:
    topics = data["topics"][:20]
    strength = data["strength"]
    width, pad, row_h = 900, 24, 30
    height = pad * 2 + 40 + len(topics) * row_h + 110
    max_count = max([t["count"] for t in topics] or [1])
    parts = [
        (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}">'),
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        (f'<text x="{pad}" y="34" font-size="20" font-weight="bold" '
        f'fill="#111">{html.escape(title)}</text>'),
    ]
    for index, topic in enumerate(topics):
        y = pad + 50 + index * row_h
        bar_w = max(8, int(320 * topic["count"] / max_count))
        retrievability = topic["avg_retrievability"]
        color = (
            "#16a34a"
            if retrievability >= 0.7
            else ("#f59e0b" if retrievability >= 0.3 else "#dc2626")
        )
        parts.append(
            f'<text x="{pad}" y="{y + 15}" font-size="14" fill="#333">'
            f"{html.escape(topic['topic'][:18])}</text>"
            f'<rect x="150" y="{y}" width="{bar_w}" height="20" rx="4" '
            f'fill="{color}"/>'
            f'<text x="490" y="{y + 15}" font-size="13" fill="#555">'
            f"{topic['count']} 条 · 可回忆度 {retrievability:.2f} · "
            f"重要度 {topic['avg_importance']:.2f}</text>"
        )
    base_y = pad + 50 + len(topics) * row_h + 16
    labels = [("weak", "弱（快忘了）"), ("ok", "中等"), ("strong", "强")]
    colors = {"weak": "#dc2626", "ok": "#f59e0b", "strong": "#16a34a"}
    max_strength = max([strength[k] for k, _ in labels] or [1])
    parts.append(
        f'<text x="{pad}" y="{base_y + 18}" font-size="15" '
        f'font-weight="bold" fill="#111">记忆强度分布</text>'
    )
    x = pad
    for key, label in labels:
        value = strength[key]
        bar_w = max(8, int(220 * value / max_strength))
        parts.append(
            f'<text x="{x}" y="{base_y + 52}" font-size="13" fill="#333">'
            f"{label} {value} 条</text>"
            f'<rect x="{x}" y="{base_y + 60}" width="{bar_w}" height="18" '
            f'rx="4" fill="{colors[key]}"/>'
        )
        x += 300
    parts.append("</svg>")
    return "\n".join(parts)


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
