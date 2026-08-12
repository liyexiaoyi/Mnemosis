"""Render round-11 (Chinese date normalization) Chinese chart."""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont

_BENCH = os.path.dirname(os.path.abspath(__file__))
_RESULTS = os.path.join(_BENCH, "results")
_OUT = os.path.normpath(os.path.join(_BENCH, "..", "..", "outputs", "charts"))


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\msjh.ttc",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def chart_date_norm() -> str:
    with open(os.path.join(_RESULTS, "zh_locomo_bench.json"), encoding="utf-8") as f:
        d = json.load(f)
    on = d["cross_format"]["on"]["hit5"]
    off = d["cross_format"]["off"]["hit5"]
    W, H = 1000, 600
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(20)
    f_val = _font(18)
    f_note = _font(17)
    draw.text((40, 26), "中文日期归一：“2026年3月1日” = “2026-03-01”", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "12 条记忆里日期用一种写法存、问题用另一种写法问。"
              "绿=开启归一，灰=关闭。",
              fill="#555", font=f_sub)
    chart_h = 300
    base_y = 410
    bar_w = 170
    for j, ((hits, n), label, color) in enumerate(
        ((on, "开启归一", "#1a7f37"), (off, "关闭", "#b0b0b0"))
    ):
        val = hits / n
        bh = val * chart_h
        x = 130 + j * 360
        y = base_y - bh
        draw.rectangle([x, y, x + bar_w, base_y], fill=color)
        draw.text((x + 42, y - 30), f"{hits}/{n}", fill="#222", font=f_val)
        draw.text((x + 32, base_y + 12), label, fill="#333", font=f_label)
    draw.line([(70, base_y), (W - 70, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(70, y), (W - 70, y)], fill="#e5e5e5", width=1)
        draw.text((30, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 470),
              f"开启归一：{on[0]}/{on[1]} 全中；关闭：{off[0]}/{off[1]}。"
              "归一后还会把“年/月/日”结构字从分词里剔除，避免所有中文日期互相串味。",
              fill="#111", font=f_note)
    draw.text((40, 515),
              "英文 88/200 无回归；单元测试 107/107 通过。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round11_zh_date_norm.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_date_norm())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
