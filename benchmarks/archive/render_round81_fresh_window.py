"""Round-81 chart: early consolidation window (fresh traces first)."""

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
        open(os.path.join(_BENCH, "results", "fresh_window_eval.json"),
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

    draw.text((42, 26), "第 81 轮：刚发生的事，趁还在巩固期先练一遍",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Gais et al. (2006) 早期巩固窗口——编码后几小时是记忆固化的"
              "黄金期，新鲜记忆应该优先复习。",
              fill="#555", font=f_sub)

    # Panel 1: fresh mean
    x0 = 90
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 第 7 天“刚发生 2 小时”记忆的平均强度（越高越好）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.4, "0.4"), (0.8, "0.8")):
        y = base_y - frac / 0.9 * chart_h
        draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 38, y - 9), label, fill="#666", font=f_val)
    rows1 = [
        ("新鲜优先(新)", data["priority"]["fresh_mean"], "#7b2ff7"),
        ("不优先", data["no_priority"]["fresh_mean"], "#9ecbff"),
        ("不复习", data["none"]["fresh_mean"], "#d97706"),
    ]
    for i, (name, val, color) in enumerate(rows1):
        bx = x0 + 45 + i * 160
        bh = val / 0.9 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 110, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 6), f"{val:.3f}",
                  fill="white", font=f_val)
        draw.text((bx - 10, base_y + 10), name, fill="#111", font=f_label)

    # Panel 2: old mean
    x0 = 800
    draw.text((x0, 120), "② 第 7 天“旧记忆”的平均强度（诚实代价）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.4, "0.4"), (0.8, "0.8")):
        y = base_y - frac / 0.9 * chart_h
        draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 38, y - 9), label, fill="#666", font=f_val)
    rows2 = [
        ("新鲜优先(新)", data["priority"]["old_mean"], "#7b2ff7"),
        ("不优先", data["no_priority"]["old_mean"], "#9ecbff"),
        ("不复习", data["none"]["old_mean"], "#d97706"),
    ]
    for i, (name, val, color) in enumerate(rows2):
        bx = x0 + 45 + i * 160
        bh = val / 0.9 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 110, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 6), f"{val:.3f}",
                  fill="white", font=f_val)
        draw.text((bx - 10, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 610),
              "怎么看：新鲜记忆（编码 2 小时、还不到常规到期阈值）在 6 小时窗口内被"
              "提前练一次，第 7 天强度 0.799 vs 0.783；",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "代价是旧记忆少练一点（0.772 vs 0.818）——名额有限，先巩固刚发生的。",
              fill="#555", font=f_note)
    draw.text((42, 720),
              "实现：practice_due 新增 fresh_priority（默认开）——6 小时内的记忆按"
              "0.65 阈值提前进队并豁免间隔护栏；已接入 MCP。",
              fill="#555", font=f_note)
    draw.text((42, 780),
              "回归：202 测试全过，88/200/10k 零差异（基准里没有 6 小时内的新记忆）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round81_fresh_window.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
