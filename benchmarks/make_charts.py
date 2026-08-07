"""Generate comparison charts (SVG, zero-dependency) for the comparison report.

Reads the saved benchmark JSONs and writes SVGs to
`<repo>/../../outputs/charts` (or `--out-dir`).

Usage:
    python benchmarks/make_charts.py
"""

from __future__ import annotations

import argparse
import json
import math
import os


WIDTH, HEIGHT = 820, 460
MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B = 70, 20, 60, 60
PALETTE = ["#4c78a8", "#f58518", "#54a24b", "#e45756", "#72b7b2", "#f2cf5b"]


def _svg_open(title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="Segoe UI, Arial, sans-serif">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>',
        f'<text x="{MARGIN_L}" y="28" font-size="17" font-weight="bold" fill="#222">{title}</text>',
    ]


def _axes(ymax: float, ylabel: str) -> list[str]:
    lines = [
        f'<line x1="{MARGIN_L}" y1="{HEIGHT - MARGIN_B}" x2="{WIDTH - MARGIN_R}" '
        f'y2="{HEIGHT - MARGIN_B}" stroke="#999" stroke-width="1"/>',
        f'<line x1="{MARGIN_L}" y1="{MARGIN_T}" x2="{MARGIN_L}" '
        f'y2="{HEIGHT - MARGIN_B}" stroke="#999" stroke-width="1"/>',
        f'<text x="16" y="{(MARGIN_T + HEIGHT - MARGIN_B) / 2}" font-size="12" fill="#666" '
        f'transform="rotate(-90 16,{(MARGIN_T + HEIGHT - MARGIN_B) / 2})" text-anchor="middle">{ylabel}</text>',
    ]
    for tick in range(0, 5):
        value = ymax * tick / 4
        y = HEIGHT - MARGIN_B - (HEIGHT - MARGIN_T - MARGIN_B) * tick / 4
        lines.append(f'<line x1="{MARGIN_L}" y1="{y:.1f}" x2="{WIDTH - MARGIN_R}" y2="{y:.1f}" stroke="#eee" stroke-width="1"/>')
        lines.append(
            f'<text x="{MARGIN_L - 8}" y="{y + 4:.1f}" font-size="11" fill="#666" text-anchor="end">{value:.0f}</text>'
        )
    return lines


def grouped_bar_chart(
    filename: str,
    title: str,
    ylabel: str,
    categories: list[str],
    series: list[tuple[str, list[float]]],
    ymax: float | None = None,
    fmt: str = "{:.0f}",
) -> None:
    if ymax is None:
        ymax = max(max(values) for _, values in series) * 1.15
    plot_w = WIDTH - MARGIN_L - MARGIN_R
    plot_h = HEIGHT - MARGIN_T - MARGIN_B
    group_w = plot_w / len(categories)
    n_series = len(series)
    bar_w = min(34.0, group_w / (n_series + 1) * 0.9)

    lines = _svg_open(title)
    # legend
    legend_x = MARGIN_L
    for index, (label, _) in enumerate(series):
        lines.append(
            f'<rect x="{legend_x}" y="38" width="14" height="14" fill="{PALETTE[index % len(PALETTE)]}"/>'
        )
        lines.append(
            f'<text x="{legend_x + 18}" y="50" font-size="12" fill="#333">{label}</text>'
        )
        legend_x += 26 + 10 * len(label) + 24
    lines += _axes(ymax, ylabel)

    for c_index, category in enumerate(categories):
        cx = MARGIN_L + group_w * c_index + group_w / 2
        for s_index, (_, values) in enumerate(series):
            value = values[c_index]
            bar_h = plot_h * (value / ymax) if ymax else 0
            x = cx - (n_series * bar_w) / 2 + s_index * bar_w
            y = HEIGHT - MARGIN_B - bar_h
            lines.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" '
                f'fill="{PALETTE[s_index % len(PALETTE)]}" rx="2"/>'
            )
            if value > 0:
                lines.append(
                    f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" font-size="10" '
                    f'fill="#444" text-anchor="middle">{fmt.format(value)}</text>'
                )
        lines.append(
            f'<text x="{cx:.1f}" y="{HEIGHT - MARGIN_B + 18}" font-size="12" fill="#333" '
            f'text-anchor="middle">{category}</text>'
        )
    lines.append("</svg>")
    with open(filename, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def dot_matrix_chart(
    filename: str,
    title: str,
    rows: list[str],
    columns: list[str],
    values: list[list[str]],
) -> None:
    """values: "y" / "p" / "n" -> filled / half / hollow dot."""
    cell_w = 78
    cell_h = 40
    width = MARGIN_L + len(columns) * cell_w + 20
    height = MARGIN_T + len(rows) * cell_h + 30
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Segoe UI, Arial, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{MARGIN_L}" y="28" font-size="17" font-weight="bold" fill="#222">{title}</text>',
    ]
    for c_index, column in enumerate(columns):
        x = MARGIN_L + c_index * cell_w + cell_w / 2
        lines.append(
            f'<text x="{x}" y="52" font-size="11" fill="#333" text-anchor="middle">{column}</text>'
        )
    for r_index, row in enumerate(rows):
        y = 76 + r_index * cell_h
        lines.append(
            f'<text x="{MARGIN_L - 8}" y="{y + 6}" font-size="12" fill="#333" text-anchor="end">{row}</text>'
        )
        for c_index, value in enumerate(values[r_index]):
            x = MARGIN_L + c_index * cell_w + cell_w / 2
            color = {"y": "#2e7d32", "p": "#f9a825", "n": "#bdbdbd"}[value]
            if value == "y":
                lines.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{color}"/>')
            elif value == "p":
                lines.append(f'<circle cx="{x}" cy="{y}" r="9" fill="none" stroke="{color}" stroke-width="2"/>')
                lines.append(f'<line x1="{x - 5}" y1="{y + 5}" x2="{x + 5}" y2="{y - 5}" stroke="{color}" stroke-width="2"/>')
            else:
                lines.append(f'<circle cx="{x}" cy="{y}" r="9" fill="none" stroke="{color}" stroke-width="2"/>')
    lines.append("</svg>")
    with open(filename, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default=os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "charts")
        ),
    )
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    grouped_bar_chart(
        os.path.join(args.out_dir, "retrieval_comparison.svg"),
        "检索层对比（24 会话 / 88 题，命中率 %）",
        "命中率 (%)",
        ["event@1", "fact@1", "temporal@5", "distractor 拒答"],
        [
            ("BM25", [100, 100, 8.3, 0]),
            ("嵌入 kNN", [33.3, 91.7, 8.3, 0]),
            ("Mnemosis 词法", [100, 100, 100, 100]),
            ("Mnemosis ngram", [100, 100, 100, 100]),
        ],
        ymax=110,
    )

    grouped_bar_chart(
        os.path.join(args.out_dir, "llm_comparison.svg"),
        "LLM 接地对比（12 题，准确率 %）",
        "准确率 (%)",
        ["gemma3:12b", "qwen2.5-vl", "qwen2.5:3b"],
        [
            ("裸答（无记忆）", [25.0, 25.0, 25.0]),
            ("+ Mnemosis 检索", [91.7, 83.3, 75.0]),
        ],
        ymax=110,
    )

    stars = [
        ("Mem0", 62726),
        ("Graphiti", 29641),
        ("Cognee", 29839),
        ("Letta", 24133),
        ("HippoRAG", 3918),
        ("hippo-memory", 724),
        ("cognitive-memory", 5),
        ("Mnemosis", 0),
    ]
    log_values = [math.log10(max(1, s)) for _, s in stars]
    grouped_bar_chart(
        os.path.join(args.out_dir, "project_landscape.svg"),
        "GitHub 项目关注度（star 数，对数刻度）",
        "log10(stars)",
        [name for name, _ in stars],
        [("stars", log_values)],
        ymax=5.2,
        fmt="{:.1f}",
    )

    columns = ["Mem0", "Letta", "Graphiti", "Cognee", "HippoRAG", "cognitive-memory", "hippo-memory", "Mnemosis"]
    rows = [
        "情景/语义双轨",
        "遗忘曲线",
        "睡眠巩固",
        "主动遗忘/回收",
        "来源+置信度",
        "元认知(缺口/矛盾)",
        "关联/图召回",
        "本地零依赖",
    ]
    values = [
        ["p", "n", "p", "n", "n", "n", "p", "y"],
        ["n", "n", "n", "n", "n", "y", "y", "y"],
        ["n", "p", "n", "n", "n", "p", "y", "y"],
        ["n", "n", "n", "n", "n", "p", "p", "y"],
        ["p", "n", "n", "n", "n", "p", "y", "y"],
        ["n", "p", "n", "n", "n", "p", "p", "y"],
        ["p", "n", "y", "y", "y", "n", "p", "y"],
        ["n", "n", "n", "n", "n", "n", "y", "y"],
    ]
    dot_matrix_chart(
        os.path.join(args.out_dir, "feature_matrix.svg"),
        "能力矩阵（实心=有，半实=部分，空心=无）",
        rows,
        columns,
        values,
    )

    grouped_bar_chart(
        os.path.join(args.out_dir, "lifecycle.svg"),
        "生命周期测试（30 天模拟）",
        "分数/可提取性",
        ["周复习召回分", "不复习召回分", "情绪可提取性", "中性可提取性"],
        [("数值", [0.343, 0.260, 0.421, 0.237])],
        ymax=0.6,
        fmt="{:.3f}",
    )

    grouped_bar_chart(
        os.path.join(args.out_dir, "head_to_head.svg"),
        "真实对决：Mem0-style vs Mnemosis（同一 88 题，hit@5 %）",
        "命中率 (%)",
        ["fact", "event", "temporal", "distractor 拒答"],
        [
            ("Mem0-style", [100, 66.7, 8.3, 0]),
            ("Mnemosis", [100, 100, 100, 100]),
        ],
        ymax=110,
    )

    print(f"charts written to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
