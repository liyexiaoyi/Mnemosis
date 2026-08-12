"""Round-70 chart: transfer-appropriate practice (kind-focused sessions)."""

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
        open(os.path.join(_BENCH, "results", "transfer_practice_eval.json"),
             encoding="utf-8")
    )
    W, H = 1450, 1100
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(21)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 26), "第 70 轮：按“要考什么”来练习，练得更准",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Morris, Bransford & Franks (1977) 迁移适当加工——练习的形式"
              "和考试越接近，效果越好；知道要考事实就多练事实。",
              fill="#555", font=f_sub)

    # Panel 1: semantic (target) mean
    x0 = 90
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 14 天后“事实类”平均记住强度（考试目标，越高越好）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.3, "0.3"), (0.6, "0.6")):
        y = base_y - frac / 0.75 * chart_h
        draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 38, y - 9), label, fill="#666", font=f_val)
    rows1 = [
        ("聚焦练习(新)", data["matched"]["semantic_mean"], "#7b2ff7"),
        ("混合练习", data["mixed"]["semantic_mean"], "#9ecbff"),
        ("不复习", data["none"]["semantic_mean"], "#d97706"),
    ]
    for i, (name, val, color) in enumerate(rows1):
        bx = x0 + 45 + i * 160
        bh = val / 0.75 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 110, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 6), f"{val:.3f}",
                  fill="white", font=f_val)
        draw.text((bx - 10, base_y + 10), name, fill="#111", font=f_label)

    # Panel 2: episodic mean
    x0 = 800
    draw.text((x0, 120), "② 14 天后“事件类”平均记住强度（诚实代价）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.3, "0.3"), (0.6, "0.6")):
        y = base_y - frac / 0.75 * chart_h
        draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 38, y - 9), label, fill="#666", font=f_val)
    rows2 = [
        ("聚焦练习(新)", data["matched"]["episodic_mean"], "#7b2ff7"),
        ("混合练习", data["mixed"]["episodic_mean"], "#9ecbff"),
        ("不复习", data["none"]["episodic_mean"], "#d97706"),
    ]
    for i, (name, val, color) in enumerate(rows2):
        bx = x0 + 45 + i * 160
        bh = val / 0.75 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 110, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 6), f"{val:.3f}",
                  fill="white", font=f_val)
        draw.text((bx - 10, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 610), "③ 14 天练习次数分配（事实 / 事件）",
              fill="#111", font=f_panel)
    base_y2 = 830
    for i, (name, mode) in enumerate(
        (("聚焦练习(新)", "matched"), ("混合练习", "mixed"))
    ):
        bx = 110 + i * 560
        sem = data[mode]["semantic_reviews"]
        epi = data[mode]["episodic_reviews"]
        total = sem + epi
        sem_h = sem / total * 180
        draw.rectangle(
            [bx, base_y2 - sem_h, bx + 240, base_y2], fill="#7b2ff7"
        )
        draw.rectangle(
            [bx, base_y2 - 180, bx + 240, base_y2 - sem_h], fill="#9ecbff"
        )
        draw.text((bx + 60, base_y2 - sem_h + 6), f"事实 {sem}",
                  fill="white", font=f_val)
        draw.text((bx + 60, base_y2 - 150), f"事件 {epi}",
                  fill="white", font=f_val)
        draw.text((bx + 55, base_y2 + 10), name, fill="#111", font=f_label)

    draw.text((42, 890),
              "怎么看：知道要考事实，就把练习名额优先给事实（27 vs 21 次），事实强度"
              "0.678 > 混合 0.642；",
              fill="#555", font=f_note)
    draw.text((42, 930),
              "代价是事件类少练一点（0.610 < 0.637）——这就是“聚焦”的真实取舍。",
              fill="#555", font=f_note)
    draw.text((42, 1000),
              "实现：practice_due 新增 kind（semantic/episodic）——该类型到期卡优先"
              "占练习名额，已接入 MCP。",
              fill="#555", font=f_note)
    draw.text((42, 1040),
              "回归：193 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round70_transfer_practice.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
