"""Round-35 chart: analogical plan reuse comparison."""

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
        ("mem0官方", 0.9375, "#1a7f37"),
        ("cognitive", 0.1875, "#b91c1c"),
        ("腾讯Agent", 0.125, "#d97706"),
    ]
    ordered = [
        ("Mnemosis", 1.00, "#7b2ff7"),
        ("mem0官方", 0.25, "#1a7f37"),
        ("cognitive", 0.0, "#b91c1c"),
        ("腾讯Agent", 0.0, "#d97706"),
    ]
    accuracy = [
        ("Mnemosis", 0.75, "#7b2ff7"),
        ("mem0官方", 0.75, "#1a7f37"),
        ("cognitive", 0.0, "#b91c1c"),
        ("腾讯Agent", 0.0, "#d97706"),
    ]
    W, H = 1560, 840
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 28), "第 35 轮：类比计划复用（参考别人的旧计划）",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "4 个场景：大壮想去京都旅行，参考阿丽是怎么准备的；琳琳想办派对，"
              "参照小波；强强想搬家，模仿琳琳；小雨想学养花，按照朵朵。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① 参考步骤找回（16 步里找回几步）", coverage),
        (1, "② 步骤顺序正确（4 题里几题按时序）", ordered),
        (2, "③ 千问作答（4 题对几题）", accuracy),
    ]
    panel_w = (W - 140) // 3
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
        bar_w = 72
        step = (panel_w - 20) // len(rows)
        for i, (name, val, color) in enumerate(rows):
            bx = x0 + 12 + i * step
            bh = max(val, 0.02) * chart_h
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
            draw.text((bx + 16, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
            draw.text((bx - 14, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：左边比“参考对象（阿丽/小波/琳琳/朵朵）的旧步骤有没有找回来”，"
              "中间比“顺序对不对”，右边比“千问能不能照抄成计划”。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "Mnemosis：16/16 找回、4/4 按时序——新增“类比计划”标记"
              "（参考/参照/模仿/按照）和参考人提升；mem0 步骤能找回但顺序只对 1/4；"
              "腾讯、cognitive 基本找不到参考步骤。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "千问作答都 3/4（Mnemosis 与 mem0）：有一题“模仿琳琳搬家”模型看到的是"
              "琳琳的步骤却答 unknown（类比迁移没做出来，检索其实 4/4 有序）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round35_plan_reuse.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
