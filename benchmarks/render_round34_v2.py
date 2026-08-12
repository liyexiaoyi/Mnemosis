"""Round-34 chart: reasoning v2 extra questions across real projects."""

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
    coverage = [
        ("Mnemosis", 1.00, "#7b2ff7"),
        ("mem0官方", 0.625, "#1a7f37"),
        ("腾讯Agent", 0.125, "#d97706"),
        ("cognitive", 0.0, "#b91c1c"),
    ]
    accuracy = [
        ("Mnemosis", 1.00, "#7b2ff7"),
        ("mem0官方", 0.50, "#1a7f37"),
        ("腾讯Agent", 0.50, "#d97706"),
        ("cognitive", 0.0, "#b91c1c"),
    ]
    W, H = 1480, 820
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(18)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 28), "第 34 轮：推理 v2 新增题 · 全项目真实对比",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "4 道新题：哪个更昂贵 / 哪个更廉价 / 两次“一共花了多少钱”。"
              "作答统一用云端 qwen3.7-plus，记忆库用各项目自己的真实检索。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① 两条价格前提都找回（8 条里找回几条）", coverage),
        (1, "② 4 题回答准确率（越高越好）", accuracy),
    ]
    panel_w = (W - 120) // 2
    chart_h = 330
    base_y = 500
    for p, title, rows in panels:
        x0 = 50 + p * (panel_w + 20)
        draw.text((x0, 130), title, fill="#111", font=f_panel)
        draw.line([(x0, base_y), (x0 + panel_w - 10, base_y)], fill="#999", width=2)
        for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
            y = base_y - frac * chart_h
            draw.line([(x0, y), (x0 + panel_w - 10, y)], fill="#e5e5e5", width=1)
            draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
        bar_w = 110
        step = (panel_w - 20) // len(rows)
        for i, (name, val, color) in enumerate(rows):
            bx = x0 + 20 + i * step
            bh = max(val, 0.02) * chart_h
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
            draw.text((bx + 28, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
            draw.text((bx - 6, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：Mnemosis 双模式都 4/4 满分；mem0 答对 2/4；"
              "腾讯 2/4；cognitive 0/4。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "这 4 题特意用“昂贵/廉价/一共”这类换说法，验证第 33 轮的同义词感知前提包："
              "换说法后 Mnemosis 依然稳定触发推理通道，其他项目没有这层能力。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "补充：Mnemosis 的上下文换 DeepSeek V4 Flash（我）按同一规则作答也是 4/4"
              "（小波 / 小波 / 5500元 / 230元）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round34_reasoning_v2.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
