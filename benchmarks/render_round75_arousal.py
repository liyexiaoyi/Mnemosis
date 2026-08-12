"""Round-75 chart: arousal-priority practice."""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont

_BENCH = os.path.dirname(os.path.abspath(__file__))
_OUT = os.path.normpath(os.path.join(_BENCH, "..", "..", "outputs", "charts"))


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simsun.ttc"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def chart() -> str:
    data = json.load(
        open(os.path.join(_BENCH, "results", "arousal_priority_eval.json"),
             encoding="utf-8")
    )
    W, H = 1450, 860
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 26), "第 75 轮：情绪唤醒的记忆，优先多练",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Mather & Sutherland (2011) 唤醒偏向竞争——情绪唤醒的记忆"
              "在竞争中更占资源，练习时应先照顾它们。",
              fill="#555", font=f_sub)

    # Panel 1: arousal mean
    x0 = 90
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 14 天后“情绪唤醒记忆”平均强度（越高越好）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.4, "0.4"), (0.8, "0.8")):
        y = base_y - frac / 0.9 * chart_h
        draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 38, y - 9), label, fill="#666", font=f_val)
    rows1 = [
        ("唤醒优先(新)", data["priority"]["arousal_mean"], "#7b2ff7"),
        ("不优先", data["no_priority"]["arousal_mean"], "#9ecbff"),
        ("不复习", data["none"]["arousal_mean"], "#d97706"),
    ]
    for i, (name, val, color) in enumerate(rows1):
        bx = x0 + 45 + i * 160
        bh = val / 0.9 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 110, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 6), f"{val:.3f}",
                  fill="white", font=f_val)
        draw.text((bx - 10, base_y + 10), name, fill="#111", font=f_label)

    # Panel 2: neutral mean
    x0 = 800
    draw.text((x0, 120), "② 14 天后“中性记忆”平均强度（诚实代价）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.4, "0.4"), (0.8, "0.8")):
        y = base_y - frac / 0.9 * chart_h
        draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 38, y - 9), label, fill="#666", font=f_val)
    rows2 = [
        ("唤醒优先(新)", data["priority"]["neutral_mean"], "#7b2ff7"),
        ("不优先", data["no_priority"]["neutral_mean"], "#9ecbff"),
        ("不复习", data["none"]["neutral_mean"], "#d97706"),
    ]
    for i, (name, val, color) in enumerate(rows2):
        bx = x0 + 45 + i * 160
        bh = val / 0.9 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 110, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 6), f"{val:.3f}",
                  fill="white", font=f_val)
        draw.text((bx - 10, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 610),
              "怎么看：唤醒优先让情绪记忆平均 0.854（不优先 0.616）——因为情绪记忆"
              "衰减慢、平时不容易“到期”，",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "新机制在可提取度 0.65 时就提前捞出来练。代价是中性记忆少练（0.58 vs "
              "0.65，15 条达标变 13 条）——真实取舍。",
              fill="#555", font=f_note)
    draw.text((42, 720),
              "实现：practice_due 新增 arousal_priority（默认开）——情绪唤醒记忆"
              "按更高阈值提前进入练习队列并排前面；已接入 MCP。",
              fill="#555", font=f_note)
    draw.text((42, 780),
              "回归：197 测试全过，88/200/10k 零差异（基准里没有情绪记忆，调度不受影响）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round75_arousal_priority.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
