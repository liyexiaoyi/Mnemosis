"""Round-56 chart: spacing x practice (per-review gain)."""

from __future__ import annotations

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
    rows = [
        ("间隔练习", 0.00751, "#7b2ff7"),
        ("集中练习", 0.00742, "#9ecbff"),
        ("被动重读", 0.00639, "#b0b0b0"),
        ("不复习", 0.0, "#d9c9c9"),
    ]
    W, H = 1450, 800
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(18)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 28), "第 56 轮：间隔效应 × 练习",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "依据：间隔效应（Cepeda et al. 2006）——分散练习优于集中练习。"
              "指标：每次练习带来的平均可提取度净增益。",
              fill="#555", font=f_sub)

    x0 = 160
    draw.text((x0, 130), "每次练习的净增益（2 周，30 条记忆）", fill="#111", font=f_panel)
    base_y = 500
    chart_h = 300
    draw.line([(x0, base_y), (x0 + 580, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.004, "0.004"), (0.008, "0.008")):
        y = base_y - frac / 0.008 * chart_h
        draw.line([(x0, y), (x0 + 580, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 10), label, fill="#666", font=f_val)
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 30 + i * 140
        bh = val / 0.008 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 100, base_y], fill=color)
        draw.text((bx + 22, base_y - bh + 6), f"{val:.4f}",
                  fill="white", font=f_val)
        draw.text((bx - 6, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：间隔练习每次净增益最高（0.0075），集中练习次之（0.0074），"
              "被动重读更低（0.0064），不复习为 0。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "实现：practice_due 新增 min_gap_hours 间隔护栏（默认 24h），"
              "防止同一记忆被集中反复练习；间隔组单次效率更高。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "回归：178 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round56_spacing.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
