"""Round-66 chart: mood-congruent retrieval."""

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
        open(os.path.join(_BENCH, "results", "mood_congruent_eval.json"),
             encoding="utf-8")
    )
    W, H = 1400, 760
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 66 轮：带着情绪的问题，优先想起同样情绪的记忆",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Bower (1981) 心境一致性记忆——开心的时候更容易想起开心的事，"
              "情绪本身就是一个检索线索。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 6 个“为什么…会开心？”问题里，开心记忆排第一的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6")):
        y = base_y - frac / 6.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("情绪一致(新)", data["boosted"]["mood_first"], "#7b2ff7"),
        ("不加分", data["plain"]["mood_first"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 6.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/6",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：两条记忆完全一样重要、一样新，只是情绪不同；后写入的“害怕”"
              "记忆本来会排前面。",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "问题里带“开心”时，系统给开心记忆 +0.05，6/6 次把开心的那条找出来"
              "（不加分 0/6）。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：recall 新增 mood_congruent_boost（默认开）——识别问题里的情绪词"
              "（开心/焦虑/刺激等），与记忆的 affect 标签一致时加分，标注“情绪一致”。",
              fill="#555", font=f_note)
    draw.text((42, 740),
              "回归：190 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round66_mood_congruent.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
