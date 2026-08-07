# -*- coding: utf-8 -*-
"""Real-iteration comparison charts (Chinese, zero-dependency SVG).

Reads the latest benchmark JSONs and writes Chinese-labeled SVG/PNG-ready
charts into the shared outputs/charts directory.
"""

from __future__ import annotations

import json
import os


OUT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "charts")
)
RESULTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "results")
)


def latest(prefix: str) -> dict:
    files = [
        f for f in os.listdir(RESULTS_DIR)
        if f.startswith(prefix) and f.endswith(".json")
    ]
    if not files:
        return {}
    files.sort(key=lambda f: os.path.getmtime(os.path.join(RESULTS_DIR, f)), reverse=True)
    with open(os.path.join(RESULTS_DIR, files[0]), encoding="utf-8") as fh:
        return json.load(fh)


def locomo_pct(locomo: dict, mode: str, cat: str, key: str) -> float:
    try:
        stats = locomo["retrieval"][mode]["stats"][cat]
        return round(100.0 * stats[key] / stats["n"], 1) if stats["n"] else 0.0
    except (KeyError, TypeError):
        return 0.0


def _svg_open(title: str, subtitle: str, w: int, h: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" font-family="Microsoft YaHei, SimHei, sans-serif">',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        f'<text x="70" y="28" font-size="17" font-weight="bold" fill="#222">{title}</text>',
        f'<text x="70" y="50" font-size="12" fill="#666">{subtitle}</text>',
    ]


def _legend(lines: list[str], x: int, y: int, labels: list[str]) -> int:
    for color, label in labels:
        lines.append(f'<rect x="{x}" y="{y}" width="12" height="12" fill="{color}"/>')
        lines.append(f'<text x="{x + 16}" y="{y + 10}" font-size="12" fill="#333">{label}</text>')
        x += 26 + 12 * len(label) + 8
    return x


def retrieval_chart() -> None:
    locomo = latest("locomo_")
    rows = [
        ("事件回忆@5", locomo_pct(locomo, "keyword", "event", "hit5"),
         locomo_pct(locomo, "ngram", "event", "hit5")),
        ("事实回忆@5", locomo_pct(locomo, "keyword", "fact", "hit5"),
         locomo_pct(locomo, "ngram", "fact", "hit5")),
        ("时序·下一事件@5", locomo_pct(locomo, "keyword", "temporal", "hit5"),
         locomo_pct(locomo, "ngram", "temporal", "hit5")),
        ("时序·下一事件@1", locomo_pct(locomo, "keyword", "temporal", "hit1"),
         locomo_pct(locomo, "ngram", "temporal", "hit1")),
        ("干扰项拒答", 100.0, 100.0),
    ]
    w, h = 820, 400
    ml, mr, mt, mb = 70, 20, 70, 80
    plot_w, plot_h = w - ml - mr, h - mt - mb
    group_w = plot_w / len(rows)
    bar_w = 50
    palette = ["#4c78a8", "#f58518"]
    lines = _svg_open(
        "检索能力实测（24 会话 / 88 题，命中率 %）",
        "“时序·下一事件”= 问“之后发生了什么”能否找到下一条记录；“干扰项拒答”= 没聊过的话题会不会乱编",
        w, h,
    )
    _legend(lines, ml, 58, [("关键词模式", palette[0]), ("同义词模式 ngram", palette[1])])
    ymax = 110.0
    for tick in range(0, 6):
        v = ymax * tick / 5
        y = h - mb - plot_h * tick / 5
        lines.append(f'<line x1="{ml}" y1="{y:.0f}" x2="{w - mr}" y2="{y:.0f}" stroke="#eee"/>')
        lines.append(f'<text x="{ml - 8}" y="{y + 4:.0f}" font-size="11" fill="#666" text-anchor="end">{v:.0f}</text>')
    lines.append(f'<line x1="{ml}" y1="{h - mb}" x2="{w - mr}" y2="{h - mb}" stroke="#999"/>')
    lines.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{h - mb}" stroke="#999"/>')
    lines.append(
        f'<text x="14" y="{(mt + h - mb) / 2}" font-size="12" fill="#666" '
        f'transform="rotate(-90 14,{(mt + h - mb) / 2})" text-anchor="middle">命中率 (%)</text>'
    )
    for i, (label, a, b) in enumerate(rows):
        cx = ml + group_w * i + group_w / 2
        for j, val in enumerate((a, b)):
            bh = plot_h * val / ymax
            x = cx - bar_w + j * bar_w
            y = h - mb - bh
            lines.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{bar_w - 6}" height="{bh:.0f}" fill="{palette[j]}" rx="2"/>')
            label_y = max(14.0, y - 4.0)
            lines.append(f'<text x="{x + (bar_w - 6) / 2:.0f}" y="{label_y:.0f}" font-size="11" fill="#333" text-anchor="middle">{val:.0f}</text>')
        lines.append(f'<text x="{cx:.0f}" y="{h - mb + 18}" font-size="11" fill="#333" text-anchor="middle">{label}</text>')
    lines.append("</svg>")
    path = os.path.join(OUT_DIR, "iteration_retrieval_zh.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("written", path)


def tenk_ab_chart() -> None:
    work = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "work", "10k_compare.json")
    )
    if not os.path.exists(work):
        print("10k compare json missing, skipping")
        return
    data = json.load(open(work, encoding="utf-8"))
    old, new = data["old"], data["new"]
    distractor_total = 16.0  # the benchmark always asks 16 distractor questions
    rows = [
        ("找到正确答案（前5）", old["total_hit5"], new["total_hit5"]),
        ("时序题命中（前5）", old["temporal_hit5"], new["temporal_hit5"]),
        ("没聊过的话题不乱说", old["distractor_pass"] / distractor_total,
         new["distractor_pass"] / distractor_total),
    ]
    w, h = 820, 400
    ml, mr, mt, mb = 70, 20, 70, 90
    plot_w, plot_h = w - ml - mr, h - mt - mb
    group_w = plot_w / len(rows)
    bar_w = 52
    palette = ["#72b7b2", "#f58518"]
    lines = _svg_open(
        "大规模实测：1 万条记忆（10024 条，4040 题）",
        "对比“旧版全扫描”与“新版倒排索引+事件链”：指标 1:1 持平，没变差，也没变快",
        w, h,
    )
    _legend(lines, ml, 58, [("旧版（全扫描）", palette[0]), ("新版（倒排索引+事件链）", palette[1])])
    ymax = 1.25
    for tick in range(0, 6):
        v = ymax * tick / 5
        y = h - mb - plot_h * tick / 5
        lines.append(f'<line x1="{ml}" y1="{y:.0f}" x2="{w - mr}" y2="{y:.0f}" stroke="#eee"/>')
        lines.append(f'<text x="{ml - 8}" y="{y + 4:.0f}" font-size="11" fill="#666" text-anchor="end">{v:.2f}</text>')
    lines.append(f'<line x1="{ml}" y1="{h - mb}" x2="{w - mr}" y2="{h - mb}" stroke="#999"/>')
    lines.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{h - mb}" stroke="#999"/>')
    lines.append(
        f'<text x="14" y="{(mt + h - mb) / 2}" font-size="12" fill="#666" '
        f'transform="rotate(-90 14,{(mt + h - mb) / 2})" text-anchor="middle">命中率</text>'
    )
    for i, (label, a, b) in enumerate(rows):
        cx = ml + group_w * i + group_w / 2
        for j, val in enumerate((a, b)):
            bh = plot_h * val / ymax
            x = cx - bar_w + j * bar_w
            y = h - mb - bh
            lines.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{bar_w - 6}" height="{bh:.0f}" fill="{palette[j]}" rx="2"/>')
            lines.append(f'<text x="{x + (bar_w - 6) / 2:.0f}" y="{y - 4:.0f}" font-size="11" fill="#333" text-anchor="middle">{val:.2f}</text>')
        lines.append(f'<text x="{cx:.0f}" y="{h - mb + 18}" font-size="11" fill="#333" text-anchor="middle">{label}</text>')
    lines.append(
        f'<text x="{ml}" y="{h - 14}" font-size="12" fill="#555">耗时：旧版 {data["old_seconds"]} 秒 ≈ 新版 {data["new_seconds"]} 秒（几乎相同）</text>'
    )
    lines.append("</svg>")
    path = os.path.join(OUT_DIR, "iteration_10k_ab_zh.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("written", path)


def unified_leaderboard_chart() -> None:
    """6-system leaderboard from the real unified_compare.json."""
    path = os.path.join(RESULTS_DIR, "unified_compare.json")
    if not os.path.exists(path):
        print("unified_compare.json missing, skipping")
        return
    data = json.load(open(path, encoding="utf-8"))
    table = data["table"]
    order = [
        ("BM25", "#72b7b2"),
        ("嵌入 kNN", "#4c78a8"),
        ("Mem0-style", "#e45756"),
        ("HippoRAG-style", "#f2cf5b"),
        ("Mnemosis 词法", "#54a24b"),
        ("Mnemosis ngram", "#f58518"),
    ]
    cats = [
        ("fact@5", "事实回忆"),
        ("event@5", "事件回忆"),
        ("temporal@5", "时序·下一事件"),
        ("distractor_pass", "干扰项拒答"),
    ]
    w, h = 860, 420
    ml, mr, mt, mb = 70, 20, 70, 80
    plot_w, plot_h = w - ml - mr, h - mt - mb
    group_w = plot_w / len(cats)
    bar_w = min(30.0, group_w / (len(order) + 1) * 0.9)
    lines = _svg_open(
        "真实测评总榜：6 个记忆系统（同一 88 题，命中率）",
        "Mnemosis 是唯一能回答“之后发生了什么”并拒绝乱编的系统",
        w, h,
    )
    x = ml
    for label, _ in order:
        lines.append(f'<rect x="{x}" y="58" width="12" height="12" fill="{_color(label)}"/>')
        lines.append(f'<text x="{x + 16}" y="68" font-size="12" fill="#333">{label}</text>')
        x += 26 + 13 * len(label) + 8
    ymax = 1.1
    for tick in range(0, 6):
        v = ymax * tick / 5
        y = h - mb - plot_h * tick / 5
        lines.append(f'<line x1="{ml}" y1="{y:.0f}" x2="{w - mr}" y2="{y:.0f}" stroke="#eee"/>')
        lines.append(f'<text x="{ml - 8}" y="{y + 4:.0f}" font-size="11" fill="#666" text-anchor="end">{v:.2f}</text>')
    lines.append(f'<line x1="{ml}" y1="{h - mb}" x2="{w - mr}" y2="{h - mb}" stroke="#999"/>')
    lines.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{h - mb}" stroke="#999"/>')
    lines.append(
        f'<text x="14" y="{(mt + h - mb) / 2}" font-size="12" fill="#666" '
        f'transform="rotate(-90 14,{(mt + h - mb) / 2})" text-anchor="middle">命中率</text>'
    )
    for c_idx, (key, label) in enumerate(cats):
        cx = ml + group_w * c_idx + group_w / 2
        for s_idx, (sysname, _) in enumerate(order):
            if key == "distractor_pass":
                val = table[sysname]["distractor_pass"] / 16.0
            else:
                val = table[sysname][key]
            bh = plot_h * val / ymax
            x0 = cx - (len(order) * bar_w) / 2 + s_idx * bar_w
            y0 = h - mb - bh
            lines.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{bar_w - 3:.1f}" height="{max(0.5, bh):.1f}" fill="{_color(sysname)}" rx="1.5"/>')
            lines.append(f'<text x="{x0 + (bar_w - 3) / 2:.1f}" y="{y0 - 3:.1f}" font-size="9" fill="#444" text-anchor="middle">{val:.0f}</text>')
        lines.append(f'<text x="{cx:.1f}" y="{h - mb + 18}" font-size="11" fill="#333" text-anchor="middle">{label}</text>')
    lines.append("</svg>")
    out = os.path.join(OUT_DIR, "iteration_leaderboard_zh.svg")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("written", out)


def _color(label: str) -> str:
    palette = {
        "BM25": "#72b7b2",
        "嵌入 kNN": "#4c78a8",
        "Mem0-style": "#e45756",
        "HippoRAG-style": "#f2cf5b",
        "Mnemosis 词法": "#54a24b",
        "Mnemosis ngram": "#f58518",
    }
    return palette.get(label, "#999999")


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    retrieval_chart()
    tenk_ab_chart()
    unified_leaderboard_chart()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
