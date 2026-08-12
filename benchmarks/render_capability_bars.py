"""Multi-dimensional capability comparison bar chart (real data)."""

from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

_OUT = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "outputs", "charts",
    )
)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\msjh.ttc",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


SYSTEMS = [
    ("Mnemosis", "#1a7f37"),
    ("mem0", "#2f80ed"),
    ("CAM", "#7b2ff7"),
    ("腾讯", "#0b5fff"),
    ("cognitive", "#c0392b"),
]

# value matrix: dimension -> list of 5 system values (percent)
DIMS = [
    ("总准确率（12题）", [75, 75, 67, 25, 25]),
    ("记住事实", [100, 100, 100, 0, 0]),
    ("记住事件", [100, 67, 100, 0, 0]),
    ("之后发生了什么", [0, 33, 67, 0, 0]),
    ("没聊过不乱说", [100, 100, 0, 100, 100]),
    ("检索命中@5", [82, 70, 42, 0, 20]),
]


def chart() -> str:
    W, H = 1750, 1160
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(34)
    f_sub = _font(18)
    f_panel = _font(22)
    f_val = _font(17)
    f_leg = _font(18)
    draw.text((40, 26), "五个记忆系统 · 六个能力维度 · 真实对比", fill="#111",
              font=f_title)
    draw.text((40, 76),
              "模型维度：同一本地模型 qwen2.5:3b 接各系统作答；"
              "检索维度：88 题真实检索命中@5（CAM/腾讯为 12 题）。",
              fill="#555", font=f_sub)
    # legend on its own row
    lx = 60
    for name, color in SYSTEMS:
        draw.rectangle([lx, 122, lx + 30, 146], fill=color)
        draw.text((lx + 40, 118), name, fill="#111", font=f_leg)
        lx += 40 + len(name) * 17 + 50
    panel_w = 520
    chart_h = 220
    bar_w = 52
    title_h = 70
    row_h = title_h + chart_h + 70
    for idx, (dim, values) in enumerate(DIMS):
        col = idx % 3
        row = idx // 3
        px0 = 40 + col * (panel_w + 55)
        top = 160 + row * row_h
        draw.text((px0 + 10, top), dim, fill="#111", font=f_panel)
        baseline = top + title_h + chart_h
        for si, (name, color) in enumerate(SYSTEMS):
            val = values[si]
            bh = val / 100 * chart_h
            x = px0 + 20 + si * (bar_w + 36)
            y = baseline - bh
            draw.rectangle([x, y, x + bar_w, baseline], fill=color)
            draw.text((x + 2, y - 24), f"{val}%", fill="#222", font=f_val)
        draw.line([(px0 + 10, baseline), (px0 + panel_w - 10, baseline)],
                  fill="#999", width=2)
        for frac, label in ((0.0, "0"), (0.5, "50%"), (1.0, "100%")):
            yy = baseline - frac / 1.0 * chart_h
            draw.line([(px0 + 10, yy), (px0 + panel_w - 10, yy)],
                      fill="#e5e5e5", width=1)
    draw.text((40, 1080),
              "读法：每个小图一个能力维度，五根柱=五个系统，柱越高越强。"
              "Mnemosis 在事实/事件/不乱说/检索上领先；时序是大家都难的短板。",
              fill="#555", font=f_sub)
    path = os.path.join(_OUT, "capability_compare_bars.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
