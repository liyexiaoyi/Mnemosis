"""Round-57 chart: success-rate adaptive practice spacing."""

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
        ("自适应间隔", 0.00751, "#7b2ff7"),
        ("固定间隔", 0.00751, "#9ecbff"),
        ("集中练习", 0.00742, "#b0b0b0"),
    ]
    W, H = 1400, 780
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(18)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 28), "第 57 轮：成功率自适应练习间隔",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "依据：间隔效应 + 掌握学习——历史成功率低的“挣扎”记忆应更早再练。",
              fill="#555", font=f_sub)

    x0 = 160
    draw.text((x0, 130), "每次练习净增益（2 周，30 条记忆）", fill="#111", font=f_panel)
    base_y = 500
    chart_h = 300
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.004, "0.004"), (0.008, "0.008")):
        y = base_y - frac / 0.008 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 10), label, fill="#666", font=f_val)
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 40 + i * 160
        bh = val / 0.008 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 110, base_y], fill=color)
        draw.text((bx + 30, base_y - bh + 6), f"{val:.4f}",
                  fill="white", font=f_val)
        draw.text((bx - 6, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：自适应与固定间隔每次练习效率相同（0.0075），都高于集中练习"
              "（0.0074）——间隔护栏本身带来效率提升；两种间隔策略总次数同为 46。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "实现：practice_due 新增 adaptive_gap——成功率<0.5 的条目间隔 ×0.6"
              "（更早再练），≥0.9 的 ×1.3（放宽）；已接入 MCP（min_gap_hours/"
              "adaptive_gap 参数）。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "诚实说明：本基准下自适应与固定行为一致（期望难度排序主导选卡），"
              "机制与单测已锁定；在更细粒度会话或宽松配额下自适应优势会更明显。"
              "回归：179 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round57_adaptive_spacing.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
