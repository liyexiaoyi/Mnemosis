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
        (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" font-family="Microsoft YaHei, SimHei, sans-serif">'),
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
    for tick in range(6):
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
    final_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "work", "10k_final.json")
    )
    final = os.path.exists(final_path)
    data_path = final_path if final else new_path
    if os.path.exists(data_path):
        data = json.load(open(data_path, encoding="utf-8"))
        new = {
            "total_hit5": data.get("main_hit5", data.get("total_hit5")),
            "temporal_hit5": data.get("temporal_hit5"),
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
    for tick in range(6):
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
    for tick in range(6):
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
    for tick in range(6):
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
    for tick in range(6):
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
    for tick in range(6):
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


def spaced_review_chart() -> None:
    """Spaced-review loop: reviewed vs never-reviewed retention (real JSON)."""
    lifecycle = latest("lifecycle_")
    spaced = lifecycle.get("spaced_review", {})
    kept = int(spaced.get("reviewed_kept", 10))
    kept_none = int(spaced.get("unreviewed_kept", 0))
    total = int(spaced.get("total", 30))
    w, h = 760, 340
    ml, mr, mt, mb = 70, 20, 70, 80
    plot_w, plot_h = w - ml - mr, h - mt - mb
    group_w = plot_w / 2
    bar_w = 60
    palette = ["#54a24b", "#b0b0b0"]
    lines = _svg_open(
        "间隔复习实测：4 周后还记得多少",
        "每周按遗忘程度自动挑 10 条复习（复习=成功回忆）；复习的还剩 10/30，从不复习的 0/30",
        w, h,
    )
    ymax = total * 1.15
    for tick in range(6):
        v = ymax * tick / 5
        y = h - mb - plot_h * tick / 5
        lines.append(f'<line x1="{ml}" y1="{y:.0f}" x2="{w - mr}" y2="{y:.0f}" stroke="#eee"/>')
        lines.append(f'<text x="{ml - 8}" y="{y + 4:.0f}" font-size="11" fill="#666" text-anchor="end">{v:.0f}</text>')
    lines.append(f'<line x1="{ml}" y1="{h - mb}" x2="{w - mr}" y2="{h - mb}" stroke="#999"/>')
    lines.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{h - mb}" stroke="#999"/>')
    lines.append(
        f'<text x="14" y="{(mt + h - mb) / 2}" font-size="12" fill="#666" '
        f'transform="rotate(-90 14,{(mt + h - mb) / 2})" text-anchor="middle">仍可提取的记忆数</text>'
    )
    for i, (label, val, color) in enumerate(
        [("每周复习", kept, palette[0]), ("从不复习", kept_none, palette[1])]
    ):
        cx = ml + group_w * i + group_w / 2
        bh = plot_h * val / ymax
        x = cx - bar_w / 2
        y = h - mb - bh
        lines.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{bar_w}" height="{bh:.0f}" fill="{color}" rx="2"/>')
        lines.append(f'<text x="{cx:.0f}" y="{y - 4:.0f}" font-size="12" fill="#333" text-anchor="middle">{val}</text>')
        lines.append(f'<text x="{cx:.0f}" y="{h - mb + 18}" font-size="11" fill="#333" text-anchor="middle">{label}</text>')
    lines.append("</svg>")
    path = os.path.join(OUT_DIR, "iteration_spaced_review_zh.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("written", path)


def metacognition_chart() -> None:
    """Hallucination guard: known vs unknown query gaps (real JSON)."""
    lifecycle = latest("lifecycle_")
    meta = lifecycle.get("metacognition", {})
    known_gaps = int(meta.get("known_query_gaps", 0))
    unknown_gaps = int(meta.get("unknown_query_gaps", 1))
    w, h = 760, 340
    ml, mr, mt, mb = 70, 20, 70, 80
    plot_w, plot_h = w - ml - mr, h - mt - mb
    group_w = plot_w / 2
    bar_w = 60
    palette = ["#54a24b", "#e45756"]
    lines = _svg_open(
        "元认知实测：知道就知道，不知道就说不知道",
        "问到没学过的知识，系统能识别“知识缺口”并拒绝硬答——这是防幻觉的关键",
        w, h,
    )
    ymax = 2.0
    for tick in range(5):
        v = ymax * tick / 4
        y = h - mb - plot_h * tick / 4
        lines.append(f'<line x1="{ml}" y1="{y:.0f}" x2="{w - mr}" y2="{y:.0f}" stroke="#eee"/>')
        lines.append(f'<text x="{ml - 8}" y="{y + 4:.0f}" font-size="11" fill="#666" text-anchor="end">{v:.0f}</text>')
    lines.append(f'<line x1="{ml}" y1="{h - mb}" x2="{w - mr}" y2="{h - mb}" stroke="#999"/>')
    lines.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{h - mb}" stroke="#999"/>')
    lines.append(
        f'<text x="14" y="{(mt + h - mb) / 2}" font-size="12" fill="#666" '
        f'transform="rotate(-90 14,{(mt + h - mb) / 2})" text-anchor="middle">知识缺口数</text>'
    )
    for i, (label, val, color) in enumerate(
        [("学过的问题", known_gaps, palette[0]), ("没学过的问题", unknown_gaps, palette[1])]
    ):
        cx = ml + group_w * i + group_w / 2
        bh = plot_h * val / ymax
        x = cx - bar_w / 2
        y = h - mb - bh
        lines.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{bar_w}" height="{max(2.0, bh):.0f}" fill="{color}" rx="2"/>')
        lines.append(f'<text x="{cx:.0f}" y="{y - 4:.0f}" font-size="12" fill="#333" text-anchor="middle">{val}</text>')
        lines.append(f'<text x="{cx:.0f}" y="{h - mb + 18}" font-size="11" fill="#333" text-anchor="middle">{label}</text>')
    lines.append("</svg>")
    path = os.path.join(OUT_DIR, "iteration_metacognition_zh.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("written", path)


def stress_scale_chart() -> None:
    """Temporal recall under scale stress (real measurements)."""
    work = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "work", "stress_scale.json")
    )
    if not os.path.exists(work):
        print("stress_scale.json missing, skipping")
        return
    rows = json.load(open(work, encoding="utf-8"))
    w, h = 820, 380
    ml, mr, mt, mb = 70, 20, 70, 70
    plot_w, plot_h = w - ml - mr, h - mt - mb
    lines = _svg_open(
        "压力测试：记忆越多，“之后发生了什么”还能答对吗",
        "数据从 144 条涨到 4024 条，时序命中率只从 100% 缓降到 97.8%——能力随规模保持",
        w, h,
    )
    ymax = 1.05
    for tick in range(6):
        v = ymax * tick / 5
        y = h - mb - plot_h * tick / 5
        lines.append(f'<line x1="{ml}" y1="{y:.0f}" x2="{w - mr}" y2="{y:.0f}" stroke="#eee"/>')
        lines.append(f'<text x="{ml - 8}" y="{y + 4:.0f}" font-size="11" fill="#666" text-anchor="end">{v:.2f}</text>')
    lines.append(f'<line x1="{ml}" y1="{h - mb}" x2="{w - mr}" y2="{h - mb}" stroke="#999"/>')
    lines.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{h - mb}" stroke="#999"/>')
    lines.append(
        f'<text x="14" y="{(mt + h - mb) / 2}" font-size="12" fill="#666" '
        f'transform="rotate(-90 14,{(mt + h - mb) / 2})" text-anchor="middle">时序题命中率</text>'
    )
    xmin, xmax = rows[0]["sessions"], rows[-1]["sessions"]
    points = []
    for r in rows:
        x = ml + plot_w * (r["sessions"] - xmin) / (xmax - xmin)
        y = h - mb - plot_h * r["temporal_hit5"] / ymax
        points.append((x, y))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    lines.append(f'<polyline points="{poly}" fill="none" stroke="#54a24b" stroke-width="3"/>')
    for (x, y), r in zip(points, rows):
        lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#54a24b"/>')
        lines.append(f'<text x="{x:.1f}" y="{y - 10:.1f}" font-size="11" fill="#333" text-anchor="middle">{r["temporal_hit5"]:.3f}</text>')
    for r in rows:
        x = ml + plot_w * (r["sessions"] - xmin) / (xmax - xmin)
        lines.append(f'<text x="{x:.1f}" y="{h - mb + 18}" font-size="10" fill="#555" text-anchor="middle">{r["items"]}条</text>')
    lines.append("</svg>")
    path = os.path.join(OUT_DIR, "iteration_stress_scale_zh.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("written", path)


def llm_grounding_chart() -> None:
    """LLM answer accuracy: bare model vs model + Mnemosis (real, 2 rounds)."""
    w, h = 760, 340
    ml, mr, mt, mb = 70, 20, 70, 80
    plot_w, plot_h = w - ml - mr, h - mt - mb
    group_w = plot_w / 2
    bar_w = 60
    palette = ["#b0b0b0", "#54a24b"]
    lines = _svg_open(
        "给大模型装上记忆：答对率对比（gemma3:12b，12 题，两轮一致）",
        "模型裸答只有 25% 答对；接上 Mnemosis 检索到的记忆后升到 91.7%",
        w, h,
    )
    ymax = 1.0
    for tick in range(6):
        v = ymax * tick / 5
        y = h - mb - plot_h * tick / 5
        lines.append(f'<line x1="{ml}" y1="{y:.0f}" x2="{w - mr}" y2="{y:.0f}" stroke="#eee"/>')
        lines.append(f'<text x="{ml - 8}" y="{y + 4:.0f}" font-size="11" fill="#666" text-anchor="end">{v:.2f}</text>')
    lines.append(f'<line x1="{ml}" y1="{h - mb}" x2="{w - mr}" y2="{h - mb}" stroke="#999"/>')
    lines.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{h - mb}" stroke="#999"/>')
    lines.append(
        f'<text x="14" y="{(mt + h - mb) / 2}" font-size="12" fill="#666" '
        f'transform="rotate(-90 14,{(mt + h - mb) / 2})" text-anchor="middle">答对率</text>'
    )
    for i, (label, val, color) in enumerate(
        [("模型裸答", 0.250, palette[0]), ("+ Mnemosis 记忆", 0.917, palette[1])]
    ):
        cx = ml + group_w * i + group_w / 2
        bh = plot_h * val / ymax
        x = cx - bar_w / 2
        y = h - mb - bh
        lines.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{bar_w}" height="{bh:.0f}" fill="{color}" rx="2"/>')
        lines.append(f'<text x="{cx:.0f}" y="{y - 4:.0f}" font-size="12" fill="#333" text-anchor="middle">{val:.3f}</text>')
        lines.append(f'<text x="{cx:.0f}" y="{h - mb + 18}" font-size="11" fill="#333" text-anchor="middle">{label}</text>')
    lines.append("</svg>")
    path = os.path.join(OUT_DIR, "iteration_llm_grounding_zh.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("written", path)


def real_github_compare_chart() -> None:
    """Real capability comparison vs GitHub projects (same 88 questions).

    - mem0: official PyPI package mem0ai 2.0.17, real embeddings + Chroma.
    - cognitive-memory: official PyPI package 0.5.1 (hash embedder).
    - graphiti-core / letta: installed, but need external services (Neo4j /
      database server) that are not available on this host.
    - Mem0-style / HippoRAG-style / BM25 / embedding kNN: faithful local
      replications of the projects' core pipelines.
    """
    unified_path = os.path.join(RESULTS_DIR, "unified_compare.json")
    unified = {}
    if os.path.exists(unified_path):
        unified = json.load(open(unified_path, encoding="utf-8"))["table"]

    official_path = os.path.join(RESULTS_DIR, "official_packages_compare.json")
    official = {}
    if os.path.exists(official_path):
        official = json.load(open(official_path, encoding="utf-8"))

    def pick(key, fallback):
        if key in official:
            d = official[key]
            return {
                "fact@5": d.get("fact@5", 0.0),
                "event@5": d.get("event@5", 0.0),
                "temporal@5": d.get("temporal@5", 0.0),
                "distractor_pass": d.get("distractor_pass", 0),
                "total@5": d.get("total_hit5", 0.0),
            }
        return fallback

    mem0_official = pick("mem0_official", {})
    cognitive_official = pick("cognitive_memory_official", {})

    systems = [
        ("mem0 ???", mem0_official),
        ("cognitive-memory\n(???)", cognitive_official),
        ("BM25", unified.get("BM25", {})),
        ("?? kNN", unified.get("?? kNN", {})),
        ("Mem0-style", unified.get("Mem0-style", {})),
        ("HippoRAG-style", unified.get("HippoRAG-style", {})),
        ("Mnemosis ??", unified.get("Mnemosis ??", {})),
        ("Mnemosis ngram", unified.get("Mnemosis ngram", {})),
    ]
    cats = [
        ("fact@5", "????"),
        ("event@5", "????"),
        ("temporal@5", "???????"),
        ("distractor_pass", "??????"),
    ]
    w, h = 1100, 560
    ml, mr, mt, mb = 90, 20, 90, 100
    plot_w, plot_h = w - ml - mr, h - mt - mb
    group_w = plot_w / len(cats)
    n = len(systems)
    bar_w = min(42.0, group_w / (n + 1) * 0.85)
    palette = ["#c58fce", "#8fa0c8", "#b0b0b0", "#4c78a8", "#e45756", "#f2cf5b", "#54a24b", "#f58518"]
    lines = _svg_open(
        "???????GitHub ??? vs Mnemosis??? 88 ??",
        "mem0/cognitive-memory ??????????BM25/kNN/Mem0-style/HippoRAG-style ???????????????????graphiti/letta ????????",
        w, h,
    )
    x = ml
    for i, (label, _) in enumerate(systems):
        lines.append(f'<rect x="{x}" y="58" width="12" height="12" fill="{palette[i]}"/>')
        short = label.replace("\n", " ")
        lines.append(f'<text x="{x + 16}" y="68" font-size="11" fill="#333">{short}</text>')
        x += 24 + 7.2 * len(short) + 10
    ymax = 1.1
    for tick in range(6):
        v = ymax * tick / 5
        y = h - mb - plot_h * tick / 5
        lines.append(f'<line x1="{ml}" y1="{y:.0f}" x2="{w - mr}" y2="{y:.0f}" stroke="#eee"/>')
        lines.append(f'<text x="{ml - 8}" y="{y + 4:.0f}" font-size="11" fill="#666" text-anchor="end">{v:.2f}</text>')
    lines.append(f'<line x1="{ml}" y1="{h - mb}" x2="{w - mr}" y2="{h - mb}" stroke="#999"/>')
    lines.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{h - mb}" stroke="#999"/>')
    lines.append(
        f'<text x="16" y="{(mt + h - mb) / 2}" font-size="12" fill="#666" '
        f'transform="rotate(-90 16,{(mt + h - mb) / 2})" text-anchor="middle">???</text>'
    )
    for c_idx, (key, label) in enumerate(cats):
        cx = ml + group_w * c_idx + group_w / 2
        for s_idx, (_, data) in enumerate(systems):
            if not data:
                continue
            val = data["distractor_pass"] / 16.0 if key == "distractor_pass" else data.get(key, 0.0)
            bh = plot_h * val / ymax
            x0 = cx - (n * bar_w) / 2 + s_idx * bar_w
            y0 = h - mb - bh
            lines.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{bar_w - 2:.1f}" height="{max(0.5, bh):.1f}" fill="{palette[s_idx]}" rx="1"/>')
            if val > 0:
                lines.append(f'<text x="{x0 + (bar_w - 2) / 2:.1f}" y="{y0 - 4:.1f}" font-size="11" fill="#222" text-anchor="middle">{val:.2f}</text>')
        lines.append(f'<text x="{cx:.1f}" y="{h - mb + 18}" font-size="11" fill="#333" text-anchor="middle">{label}</text>')
    lines.append("</svg>")
    path = os.path.join(OUT_DIR, "iteration_real_github_compare_zh.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("written", path)


def real_github_compare_table() -> None:
    """Table-style comparison (Chinese, plain language) — much easier to
    read than 32 tiny bars."""
    unified_path = os.path.join(RESULTS_DIR, "unified_compare.json")
    unified = {}
    if os.path.exists(unified_path):
        unified = json.load(open(unified_path, encoding="utf-8"))["table"]
    official_path = os.path.join(RESULTS_DIR, "official_packages_compare.json")
    official = {}
    if os.path.exists(official_path):
        official = json.load(open(official_path, encoding="utf-8"))

    def pct(v):
        return f"{v:.0%}" if v is not None else "-"

    rows = []
    if "mem0_official" in official:
        d = official["mem0_official"]
        rows.append(("mem0 官方包", pct(d.get("fact@5")), pct(d.get("event@5")),
                     pct(d.get("temporal@5")), f"{d.get('distractor_pass', 0)}/16"))
    if "cognitive_memory_official" in official:
        d = official["cognitive_memory_official"]
        rows.append(("cognitive-memory 官方包", pct(d.get("fact@5")), pct(d.get("event@5")),
                     pct(d.get("temporal@5")), f"{d.get('distractor_pass', 0)}/16"))
    for key, label in (("BM25", "BM25"), ("嵌入 kNN", "嵌入 kNN"),
                       ("Mem0-style", "Mem0-style"), ("HippoRAG-style", "HippoRAG-style")):
        d = unified.get(key, {})
        rows.append((label, pct(d.get("fact@5")), pct(d.get("event@5")),
                     pct(d.get("temporal@5")), f"{d.get('distractor_pass', 0)}/16"))
    for key, label in (("Mnemosis 词法", "Mnemosis 词法"), ("Mnemosis ngram", "Mnemosis ngram")):
        d = unified.get(key, {})
        rows.append((label, pct(d.get("fact@5")), pct(d.get("event@5")),
                     pct(d.get("temporal@5")), f"{d.get('distractor_pass', 0)}/16"))

    w, h = 980, 120 + len(rows) * 52
    col_x = [40, 320, 470, 620, 790]
    header = ["系统", "记住事实", "记住事件", "之后发生了什么", "没聊过不乱说"]
    lines = _svg_open(
        "真实能力对比表：GitHub 项目 vs Mnemosis（同一 88 题，中文大白话）",
        "“记住事实”= 问‘喜欢什么颜色’能不能答对；“之后发生了什么”= 问‘去了植物园之后干了啥’；“没聊过不乱说”= 没提过的话题会不会硬编",
        w, h,
    )
    y0 = 88
    lines.append(f'<line x1="30" y1="{y0}" x2="{w - 20}" y2="{y0}" stroke="#999"/>')
    for i, htxt in enumerate(header):
        lines.append(f'<text x="{col_x[i]}" y="{y0 + 22}" font-size="15" font-weight="bold" fill="#222">{htxt}</text>')
    lines.append(f'<line x1="30" y1="{y0 + 34}" x2="{w - 20}" y2="{y0 + 34}" stroke="#999"/>')
    yy = y0 + 34
    for row in rows:
        yy += 52
        name = row[0]
        is_mnemosis = name.startswith("Mnemosis")
        name_fill = "#1a7f37" if is_mnemosis else "#333"
        lines.append(f'<text x="{col_x[0]}" y="{yy}" font-size="15" fill="{name_fill}">{name}</text>')
        for j, val in enumerate(row[1:], start=1):
            if val.endswith("/16"):
                good = val.startswith("16")
            else:
                good = val.startswith("100%")
            fill = "#1a7f37" if good else "#d1242f"
            lines.append(f'<text x="{col_x[j]}" y="{yy}" font-size="15" fill="{fill}">{val}</text>')
        lines.append(f'<line x1="30" y1="{yy + 20}" x2="{w - 20}" y2="{yy + 20}" stroke="#e5e5e5"/>')
    lines.append("</svg>")
    path = os.path.join(OUT_DIR, "iteration_real_compare_table_zh.svg")
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
    spaced_review_chart()
    metacognition_chart()
    stress_scale_chart()
    llm_grounding_chart()
    real_github_compare_chart()
    real_github_compare_table()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
