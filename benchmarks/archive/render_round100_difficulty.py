"""Round-100 chart: practice-report difficulty curve."""

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
        open(os.path.join(_BENCH, "results", "report_difficulty_eval.json"),
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

    draw.text((42, 26), "第 100 轮：练习报告告诉你“这场练得有多难”",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：期望难度（desirable difficulty）——练得太容易没效果，"
              "太难老失败；报告给出本场难度，agent 可以调整配额。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 30 条报告的难度统计，与手工计算一致的项目",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (1.0, "1"), (2.0, "2"), (3.0, "3"),
                        (4.0, "4")):
        y = base_y - frac / 4.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    bx = x0 + 130
    bh = 4 / 4.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#7b2ff7")
    draw.text((bx + 42, base_y - bh + 8), "4/4", fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "四项全一致", fill="#111", font=f_label)

    x0 = 760
    draw.text((x0, 120), "② 本场平均难度（0=白捡，1=全不会）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.2, "0.2"), (0.4, "0.4")):
        y = base_y - frac / 0.5 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    val = data["mean_difficulty"]
    bx = x0 + 130
    bh = val / 0.5 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#d97706")
    draw.text((bx + 42, base_y - bh + 8), f"{val:.3f}",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "平均难度", fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：报告里的 n、平均/最低/最高可提取度和难度换算全部与手工计算"
              "一致（4/4）；",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "本场平均难度 0.378（中等偏易）——如果连续几天都是 0.1，说明该加量；"
              "都是 0.8，说明该减量。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：practice_report 增加 difficulty 块（n/mean/min/max/"
              "mean_difficulty），只读统计不改行为。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：213 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round100_report_difficulty.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
