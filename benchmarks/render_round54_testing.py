"""Round-54 chart: testing effect (retrieval practice vs restudy)."""

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
        ("主动练习", 0.674, "#7b2ff7"),
        ("被动重读", 0.604, "#b0b0b0"),
        ("不练习", 0.292, "#d9c9c9"),
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

    draw.text((42, 28), "第 54 轮：测试效应 · 主动检索练习",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "依据：测试效应（Roediger & Karpicke 2006）——主动回忆 + 反馈比"
              "被动重读更强化记忆。",
              fill="#555", font=f_sub)

    x0 = 180
    draw.text((x0, 130), "2 周后的平均可提取度（30 条记忆）", fill="#111", font=f_panel)
    base_y = 500
    chart_h = 300
    draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 40 + i * 180
        bh = val * chart_h
        draw.rectangle([bx, base_y - bh, bx + 120, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 8), f"{val:.0%}",
                  fill="white", font=f_val)
        draw.text((bx - 6, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：主动练习（先凭线索回忆、再给反馈）2 周后平均可提取度 0.674，"
              "高于被动重读 0.604，远高于不练习 0.292；保留条数都是 30 vs 13。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "实现：practice_due 只给线索不给答案（自测），practice_answer 判分后"
              "成功按努力度强化、失败给小幅反馈强化并重置复习进度；已接入 MCP。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "回归：175 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round54_testing_effect.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
