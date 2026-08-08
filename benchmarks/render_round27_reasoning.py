"""Round-27 chart: Chinese reasoning comparison across real projects."""

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
    premise = [
        ("Mnemosis", 1.00, "#7b2ff7"),
        ("mem0 官方包", 0.9375, "#1a7f37"),
        ("腾讯 Agent", 0.6875, "#d97706"),
        ("cognitive", 0.50, "#b91c1c"),
    ]
    accuracy = [
        ("Mnemosis", 1.00, "#7b2ff7"),
        ("mem0 官方包", 0.875, "#1a7f37"),
        ("腾讯 Agent", 0.5625, "#d97706"),
        ("cognitive", 0.0625, "#b91c1c"),
    ]
    W, H = 1480, 860
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(18)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 28), "第 27 轮：中文推理（数学/比较/传递）真实项目对比",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "同一 16 道中文推理题，作答统一用云端 qwen3.7-plus；"
              "记忆库用各项目自己的真实检索（记忆=四个项目真实安装）。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① 推理前提找齐率（越高越好）", premise),
        (1, "② 16 题回答准确率（越高越好）", accuracy),
    ]
    panel_w = (W - 120) // 2
    chart_h = 340
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
            bx = x0 + 16 + i * step
            bh = val * chart_h
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
            draw.text((bx + 30, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
            draw.text((bx - 8, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：左边比“推理需要的前提（谁比谁高、价格数量）有没有被找齐”，"
              "右边比“千问拿到这些记忆后能不能答对”。Mnemosis 两项都满分；"
              "腾讯前提找齐 11/16，答对 9/16；cognitive 基本找不到前提。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "补充：Mnemosis 的上下文换 DeepSeek V4 Flash（我）按同一规则作答，也是 16/16。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "口径：前提覆盖=前 5 条记忆里是否包含题目的关键要素（人名+关系词+数字）；"
              "腾讯的抽取会改写句子（如补上当天日期），所以按语义算。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round27_reasoning_compare.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
