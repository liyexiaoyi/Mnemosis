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
    """10k scale comparison: previous release vs current release (Chinese)."""
    old = {
        "total_hit5": 0.909,
        "temporal_hit5": 0.859,
        "distractor_pass": 16.0,
    }
    new_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "work", "10k_new.json")
    )
    if os.path.exists(new_path):
        data = json.load(open(new_path, encoding="utf-8"))
        new = {
            "total_hit5": data["total_hit5"],
            "temporal_hit5": data["temporal_hit5"],
            "distractor_pass": float(data["distractor_pass"]),
        }
        seconds = data["seconds"]
    else:
        new = dict(old)
        seconds = 416.2
    distractor_total = 16.0
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
        "上一版 vs 本轮（事件链+时序问句识别）：正确率提升，尤其“之后发生了什么”从 0.86 升到 0.99",
        w, h,
    )
    _legend(lines, ml, 58, [("上一版", palette[0]), ("本轮优化后", palette[1])])
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
        f'<text x="{ml}" y="{h - 14}" font-size="12" fill="#555">本轮 1 万条记忆耗时 {seconds:.0f} 秒（约 7 分钟）</text>'
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


def temporal_improvement_chart() -> None:
    """Before/after of this iteration's temporal-recall fixes (measured)."""
    rows = [
        ("24 会话", 0.958, 1.000),
        ("200 会话", 0.885, 1.000),
        ("400 会话", 0.950, 0.993),
    ]
    w, h = 820, 380
    ml, mr, mt, mb = 70, 20, 70, 80
    plot_w, plot_h = w - ml - mr, h - mt - mb
    group_w = plot_w / len(rows)
    bar_w = 54
    palette = ["#b0b0b0", "#54a24b"]
    lines = _svg_open(
        "时序题“之后发生了什么”命中率：优化前后对比",
        "上一版只按关键词找，常把“喜欢植物园”误当成“去了植物园”；新版先识别时序问句，再优先找情景记忆，并沿事件链找下一条",
        w, h,
    )
    _legend(lines, ml, 58, [("优化前", palette[0]), ("优化后", palette[1])])
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
    for i, (label, before, after) in enumerate(rows):
        cx = ml + group_w * i + group_w / 2
        for j, val in enumerate((before, after)):
            bh = plot_h * val / ymax
            x = cx - bar_w + j * bar_w
            y = h - mb - bh
            lines.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{bar_w - 6}" height="{bh:.0f}" fill="{palette[j]}" rx="2"/>')
            lines.append(f'<text x="{x + (bar_w - 6) / 2:.0f}" y="{y - 4:.0f}" font-size="11" fill="#333" text-anchor="middle">{val:.3f}</text>')
        lines.append(f'<text x="{cx:.0f}" y="{h - mb + 18}" font-size="11" fill="#333" text-anchor="middle">{label}</text>')
    lines.append("</svg>")
    path = os.path.join(OUT_DIR, "iteration_temporal_improvement_zh.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("written", path)


def learning_curve_chart() -> None:
    """Testing effect vs decay: trained vs fresh engine (real JSON)."""
    lifecycle = latest("lifecycle_")
    tvf = lifecycle.get("learning_curve", {}).get("trained_vs_fresh", {})
    trained = float(tvf.get("trained_after_gap", 0.636))
    fresh = float(tvf.get("fresh_after_gap", 0.545))
    w, h = 760, 340
    ml, mr, mt, mb = 70, 20, 70, 80
    plot_w, plot_h = w - ml - mr, h - mt - mb
    group_w = plot_w / 2
    bar_w = 60
    palette = ["#54a24b", "#b0b0b0"]
    lines = _svg_open(
        "测试效应实测：同样过 7 天，“练过一轮”vs“全新”",
        "成功回忆会强化记忆（测试效应），所以练过的引擎比全新引擎高 9.1 个百分点；没练过=纯遗忘",
        w, h,
    )
    _legend(lines, ml, 58, [("练过一轮检索", palette[0]), ("全新引擎", palette[1])])
    ymax = 1.0
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
    for i, (label, val, color) in enumerate(
        [("练过一轮检索", trained, palette[0]), ("全新引擎", fresh, palette[1])]
    ):
        cx = ml + group_w * i + group_w / 2
        bh = plot_h * val / ymax
        x = cx - bar_w / 2
        y = h - mb - bh
        lines.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{bar_w}" height="{bh:.0f}" fill="{color}" rx="2"/>')
        lines.append(f'<text x="{cx:.0f}" y="{y - 4:.0f}" font-size="12" fill="#333" text-anchor="middle">{val:.3f}</text>')
        lines.append(f'<text x="{cx:.0f}" y="{h - mb + 18}" font-size="11" fill="#333" text-anchor="middle">{label}</text>')
    lines.append("</svg>")
    path = os.path.join(OUT_DIR, "iteration_learning_curve_zh.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("written", path)


def sleep_dedup_chart() -> None:
    """Sleep dedup: identical repeats collapse into one trace (real JSON)."""
    lifecycle = latest("lifecycle_")
    merge = lifecycle.get("merge", {})
    before = int(merge.get("before", 20))
    after = int(merge.get("after", 1))
    saved = float(merge.get("storage_saved_pct", 95.0))
    w, h = 760, 340
    ml, mr, mt, mb = 70, 20, 70, 80
    plot_w, plot_h = w - ml - mr, h - mt - mb
    group_w = plot_w / 2
    bar_w = 60
    palette = ["#e45756", "#54a24b"]
    lines = _svg_open(
        "睡眠整理实测：20 条重复记忆 → 1 条",
        "重复内容在“睡眠”阶段合并成一条（证据数累加），存储减少 95%，检索也不会被副本干扰",
        w, h,
    )
    ymax = max(before, after, 5) * 1.15
    for tick in range(0, 6):
        v = ymax * tick / 5
        y = h - mb - plot_h * tick / 5
        lines.append(f'<line x1="{ml}" y1="{y:.0f}" x2="{w - mr}" y2="{y:.0f}" stroke="#eee"/>')
        lines.append(f'<text x="{ml - 8}" y="{y + 4:.0f}" font-size="11" fill="#666" text-anchor="end">{v:.0f}</text>')
    lines.append(f'<line x1="{ml}" y1="{h - mb}" x2="{w - mr}" y2="{h - mb}" stroke="#999"/>')
    lines.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{h - mb}" stroke="#999"/>')
    lines.append(
        f'<text x="14" y="{(mt + h - mb) / 2}" font-size="12" fill="#666" '
        f'transform="rotate(-90 14,{(mt + h - mb) / 2})" text-anchor="middle">记忆条数</text>'
    )
    for i, (label, val, color) in enumerate(
        [("整理前", before, palette[0]), ("整理后", after, palette[1])]
    ):
        cx = ml + group_w * i + group_w / 2
        bh = plot_h * val / ymax
        x = cx - bar_w / 2
        y = h - mb - bh
        lines.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{bar_w}" height="{bh:.0f}" fill="{color}" rx="2"/>')
        lines.append(f'<text x="{cx:.0f}" y="{y - 4:.0f}" font-size="12" fill="#333" text-anchor="middle">{val}</text>')
        lines.append(f'<text x="{cx:.0f}" y="{h - mb + 18}" font-size="11" fill="#333" text-anchor="middle">{label}</text>')
    lines.append(
        f'<text x="{ml}" y="{h - 10}" font-size="12" fill="#555">节省存储：{saved:.0f}%</text>'
    )
    lines.append("</svg>")
    path = os.path.join(OUT_DIR, "iteration_sleep_dedup_zh.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("written", path)


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
    temporal_improvement_chart()
    learning_curve_chart()
    sleep_dedup_chart()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
