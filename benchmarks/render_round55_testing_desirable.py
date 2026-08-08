"""Round-55 chart: testing effect x desirable difficulty combined."""

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
        ("先练后考", 0.663, "#7b2ff7"),
        ("只练", 0.647, "#9ecbff"),
        ("只读", 0.593, "#b0b0b0"),
        ("不复习", 0.292, "#d9c9c9"),
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

    draw.text((42, 28), "第 55 轮：测试效应 × 期望难度 联合",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "2 周练习（每日 4 条，30 条衰减记忆）：先练后考（期望难度排序自测）"
              "vs 只练 vs 只读 vs 不复习。",
              fill="#555", font=f_sub)

    x0 = 180
    draw.text((x0, 130), "2 周后平均可提取度（越高越好）", fill="#111", font=f_panel)
    base_y = 500
    chart_h = 300
    draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 30 + i * 140
        bh = val * chart_h
        draw.rectangle([bx, base_y - bh, bx + 100, base_y], fill=color)
        draw.text((bx + 30, base_y - bh + 8), f"{val:.0%}",
                  fill="white", font=f_val)
        draw.text((bx - 6, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：期望难度排序的自测（先练后考）最强（0.663），普通练习次之"
              "（0.647），被动重读更弱（0.593），不复习最差（0.292）。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "实现：practice_due 默认按期望难度出卡；新增 practice_report"
              "（一次交一批答案，返回整轮成绩与逐卡反馈），已接入 MCP。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "回归：177 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round55_testing_desirable.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
