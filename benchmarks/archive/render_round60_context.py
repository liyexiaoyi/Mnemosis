"""Round-60 chart: fuzzy context-dependent memory recall."""

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
        open(os.path.join(_BENCH, "results", "context_dependent_eval.json"),
             encoding="utf-8")
    )
    W, H = 1450, 860
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 60 轮：记得“在哪儿发生的”更容易被想起来",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Godden & Baddeley (1975) 情境依赖记忆——回到同样的环境/情境，"
              "回忆效果更好；本测评用“正在会议室里开会”匹配“会议室”。",
              fill="#555", font=f_sub)

    # Panel 1: top-1 correct (of 3 queries)
    x0 = 100
    base_y = 380
    chart_h = 220
    draw.text((x0, 120), "① 3 次检索里，正确情境的记忆排第一的次数（越高越好）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 540, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (1.0, "1"), (2.0, "2"), (3.0, "3")):
        y = base_y - frac / 3.0 * chart_h
        draw.line([(x0, y), (x0 + 540, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 34, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("部分情境(新)", data["fuzzy"]["top1_correct"], "#7b2ff7"),
        ("完全一致", data["exact"]["top1_correct"], "#9ecbff"),
        ("情境但无加分", data["no_boost"]["top1_correct"], "#b0b0b0"),
        ("不给情境", data["no_context"]["top1_correct"], "#d97706"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 20 + i * 130
        bh = val / 3.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 105, base_y], fill=color)
        draw.text((bx + 38, base_y - bh + 6), f"{val}/3",
                  fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    # Panel 2: avg best rank (lower = better)
    x0 = 760
    draw.text((x0, 120), "② 正确情境的记忆平均排第几名（越低越好，共 15 条）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 540, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6")):
        y = base_y - frac / 6.0 * chart_h
        draw.line([(x0, y), (x0 + 540, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 34, y - 9), label, fill="#666", font=f_val)
    rows2 = [
        ("部分情境(新)", data["fuzzy"]["avg_best_rank"], "#7b2ff7"),
        ("完全一致", data["exact"]["avg_best_rank"], "#9ecbff"),
        ("情境但无加分", data["no_boost"]["avg_best_rank"], "#b0b0b0"),
        ("不给情境", data["no_context"]["avg_best_rank"], "#d97706"),
    ]
    for i, (name, val, color) in enumerate(rows2):
        bx = x0 + 20 + i * 130
        bh = val / 6.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 105, base_y], fill=color)
        draw.text((bx + 38, base_y - bh + 6), f"{val:.1f}",
                  fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：问法模糊时（只问“采购”，15 条都沾边），当前情境“正在会议室里开会”"
              "能让存在“会议室”里的记忆排第一（3/3）；",
              fill="#555", font=f_note)
    draw.text((42, 640),
              "不利用情境时正确率只有 1/3、平均排第 6 名。完全一致和部分重叠效果相同，"
              "说明系统不再要求情境逐字相同。",
              fill="#555", font=f_note)
    draw.text((42, 710),
              "实现：recall 新增 context_boost（默认开）——按当前情境与存储情境的词语重叠"
              "比例给检索加分（最高 0.15），原因栏标注 context overlap。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：183 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round60_context_dependent.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
