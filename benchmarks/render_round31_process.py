"""Round-31 chart: chain-of-thought step retrieval comparison."""

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
        ("Mnemosis步骤", 1.00, "#7b2ff7"),
        ("Mnemosis普通", 1.00, "#b0b0b0"),
        ("mem0官方", 0.615, "#1a7f37"),
        ("cognitive", 0.23, "#b91c1c"),
        ("腾讯Agent", 0.15, "#d97706"),
    ]
    ordered = [
        ("Mnemosis步骤", 1.00, "#7b2ff7"),
        ("Mnemosis普通", 0.167, "#b0b0b0"),
        ("mem0官方", 0.167, "#1a7f37"),
        ("cognitive", 0.0, "#b91c1c"),
        ("腾讯Agent", 0.0, "#d97706"),
    ]
    W, H = 1580, 830
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 28), "第 31 轮：思维链步骤检索（“怎么做/怎么准备”）",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "6 个带日期步骤的过程场景（准备旅行、搬家、学做菜…共 26 步）。"
              "依据：思维链（Wei et al. 2022）、心智时间旅行（Tulving 1985）、"
              "事件图式（Gilboa & Marlatte 2017）。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① 步骤找齐率（26 步里找到几步）", coverage),
        (1, "② 步骤顺序正确（6 题里几题按时序排列）", ordered),
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
        bar_w = 92
        step = (panel_w - 20) // len(rows)
        for i, (name, val, color) in enumerate(rows):
            bx = x0 + 14 + i * step
            bh = max(val, 0.02) * chart_h
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
            draw.text((bx + 22, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
            draw.text((bx - 12, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：左边比“每一步有没有找回来”，右边比“顺序对不对”。"
              "Mnemosis 步骤检索两项都是满分；普通检索和 mem0 步骤能找齐但顺序基本不对；"
              "腾讯、cognitive 连步骤都找不全。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "实现：recall_steps() 检测“怎么/如何/为什么/准备”类问题后，"
              "把召回的事件按日期排序交给模型（思维链需要有序步骤）。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "千问作答（6 题）：Mnemosis 5~6/6（模型可从乱序上下文自行排序，有波动）、"
              "mem0 3/6、腾讯 0/6、cognitive 0/6。",
              fill="#555", font=f_note)
    draw.text((42, 740),
              "中文专项优化：同义词扩展（筹备/旅游、迁居、学习 等）。换说法问同样的问题："
              "3/3 步骤找回并按时间排序。新基准已接入 CI（检索版，不调云端）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round31_process_steps.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
