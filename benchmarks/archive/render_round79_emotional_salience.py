"""Round-79 chart: emotional salience in retrieval."""

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
        open(os.path.join(_BENCH, "results", "emotional_salience_eval.json"),
             encoding="utf-8")
    )
    W, H = 1400, 800
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 79 轮：同样匹配时，情绪记忆排在前面",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Kensinger (2009) 情绪增强记忆——情绪内容在记忆里更突出，"
              "同等匹配时应该先被想起来。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 8 个“提到这件事”的检索里，情绪记忆排第一的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("情绪显著(新)", data["boosted"]["emotional_first"], "#7b2ff7"),
        ("不加分", data["plain"]["emotional_first"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 8.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/8",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：中性记忆故意更重要（0.7 vs 0.5），不加分时它 8/8 赢；"
              "开启情绪显著后情绪记忆 +0.05，8/8 翻盘。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "诚实说明：先试过“成功回忆情绪记忆强化 ×1.1”，2 周模拟里强化让"
              "记忆更快脱离练习队列、练习次数变少，净效果反而下降（0.594 vs 0.616），"
              "已回退；本机制只影响排序，不动强度。",
              fill="#555", font=f_note)
    draw.text((42, 720),
              "实现：recall 新增 emotional_salience_boost（默认开）——情绪记忆"
              "检索 +0.05，标注“情绪显著”。",
              fill="#555", font=f_note)
    draw.text((42, 770),
              "回归：199 测试全过，88/200/10k 零差异（基准里没有情绪记忆）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round79_emotional_salience.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
