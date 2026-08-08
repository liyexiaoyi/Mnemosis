"""Round-64 chart: self-reference effect."""

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
        open(os.path.join(_BENCH, "results", "self_reference_eval.json"),
             encoding="utf-8")
    )
    W, H = 1400, 780
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 64 轮：和“我”有关的记忆，更容易被想起来",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Rogers, Kuiper & Kirker (1977) 自我参照效应——信息和自己相关时"
              "加工更深，回忆更容易。",
              fill="#555", font=f_sub)

    # Panel 1: self-first hits
    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 6 个“我喜欢的…”问题里，自我记忆排第一的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6")):
        y = base_y - frac / 6.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("自我参照(新)", data["boosted"]["self_first"], "#7b2ff7"),
        ("不加分", data["plain"]["self_first"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 6.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/6",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    # Panel 2: avg rank
    x0 = 760
    draw.text((x0, 120), "② 自我记忆平均排第几名（越低越好）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (1.0, "1"), (2.0, "2")):
        y = base_y - frac / 2.5 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    rows2 = [
        ("自我参照(新)", data["boosted"]["avg_rank"], "#7b2ff7"),
        ("不加分", data["plain"]["avg_rank"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows2):
        bx = x0 + 70 + i * 190
        bh = val / 2.5 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 44, base_y - bh + 8), f"{val:.2f}",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：别的记忆明明更重要（重要度 0.8 vs 0.5），不带自我加分时只有 1/6"
              "答对、平均排第 2.3 名；",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "问句里带“我/自己”时，系统给自我相关的记忆 +0.05 分，变成 6/6 排第一"
              "（平均第 1.0 名）。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：recall 新增 self_reference_boost（默认开）——查询含“我/自己”且"
              "记忆内容/线索也含自我标记时加 0.05，原因标注“自我参照”。",
              fill="#555", font=f_note)
    draw.text((42, 750),
              "回归：188 测试全过，88/200/10k 零差异（此轮只加了查询侧小加分）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round64_self_reference.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
