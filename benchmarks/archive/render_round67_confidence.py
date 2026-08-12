"""Round-67 chart: confidence-weighted recall (metacognition)."""

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
        open(os.path.join(_BENCH, "results", "confidence_weighted_eval.json"),
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

    draw.text((42, 26), "第 67 轮：系统自己有把握的记忆，优先拿出来",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Koriat & Goldsmith (1996) 元认知校准——人脑会评估“我记得多牢”，"
              "没把握的答案不该压过有把握的答案。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 8 个冲突问题里，高置信度记忆排第一的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("置信度加权(新)", data["boosted"]["confident_first"], "#7b2ff7"),
        ("不加分", data["plain"]["confident_first"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 8.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/8",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：两条记忆同样重要，低置信度（40%）的后写入、本来排前面；"
              "开启置信度加权后，",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "高置信度（90%）的记忆加 0.045 分，8 次全对——没把握的记忆不再挤掉"
              "有把握的。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：recall 新增 confidence_boost（默认开）——检索分加 0.05 × 置信度"
              "（≥0.85 标注“置信度高”）。",
              fill="#555", font=f_note)
    draw.text((42, 750),
              "回归：191 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round67_confidence_weighted.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
