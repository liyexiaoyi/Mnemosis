"""Round-65 chart: source monitoring (trust-weighted conflict resolution)."""

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
        open(os.path.join(_BENCH, "results", "source_monitoring_eval.json"),
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

    draw.text((42, 26), "第 65 轮：同样的问题，优先相信可信来源的记忆",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Johnson, Hashtroudi & Lindsay (1993) 来源监控——人脑会分辨"
              "记忆“从哪来的”，低可信来源（听说/猜测）不该压过高可信来源（亲眼所见）。",
              fill="#555", font=f_sub)

    # Panel 1: winner-first hits
    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 8 个冲突问题里，高可信来源的记忆排第一的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("来源监控(新)", data["boosted"]["winner_first"], "#7b2ff7"),
        ("不加分", data["plain"]["winner_first"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 8.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/8",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    # Panel 2: trust bonus illustration
    x0 = 760
    draw.text((x0, 120), "② 来源可信度带来的检索加分（越高越好）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.02, "0.02"), (0.04, "0.04"),
                        (0.06, "0.06")):
        y = base_y - frac / 0.07 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 46, y - 9), label, fill="#666", font=f_val)
    rows2 = [
        ("可信 100%", 0.06, "#7b2ff7"),
        ("可信 40%", 0.024, "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows2):
        bx = x0 + 70 + i * 190
        bh = val / 0.07 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 34, base_y - bh + 8), f"{val:.3f}",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：低可信的记忆故意后写入（平时后写的会排在前面），没有来源监控时"
              "8 次全错；",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "开启后按来源可信度加分（可信 100% 加 0.06，40% 只加 0.024），"
              "8 次全对——高可信来源赢回位置。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：recall 新增 source_trust_boost（默认开）——检索分加"
              "0.06 × 来源可信度，高可信条目标注“来源可信(高)”。",
              fill="#555", font=f_note)
    draw.text((42, 750),
              "回归：189 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round65_source_monitoring.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
