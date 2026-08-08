"""Round-30 chart: conflict resolution at 10k scale."""

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
    small = [
        ("Mnemosis加权", 1.00, "#7b2ff7"),
        ("Mnemosis基线", 0.625, "#b0b0b0"),
        ("mem0官方", 0.625, "#1a7f37"),
        ("腾讯Agent", 0.375, "#d97706"),
        ("cognitive", 0.125, "#b91c1c"),
    ]
    large = [
        ("加权·前5", 1.00, "#7b2ff7"),
        ("加权·第1", 1.00, "#7b2ff7"),
        ("基线·前5", 0.875, "#b0b0b0"),
        ("基线·第1", 0.625, "#b0b0b0"),
    ]
    W, H = 1560, 830
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 28), "第 30 轮：冲突消解在 10k 规模下的稳定性",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "8 个冲突场景（同一人两条相反记忆，胜者被证实更多次），"
              "小规模与约 8,700 条噪声规模各跑一遍。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① 小规模：证据胜者排第 1", small),
        (1, "② 10k 规模（证据加权 vs 基线）", large),
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
        bar_w = 104
        step = (panel_w - 20) // len(rows)
        for i, (name, val, color) in enumerate(rows):
            bx = x0 + 14 + i * step
            bh = val * chart_h
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
            draw.text((bx + 26, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
            draw.text((bx - 12, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：左边是上一轮的五个项目小规模对比（真实安装）；"
              "右边是同一批场景埋进 8,685 条噪声后的表现。"
              "证据加权在小规模和 10k 下都是 8/8 胜者第一，基线只有 5/8。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "这轮修的两个 10k 暴露问题：①保护原来只在 top-10 窗口内生效，"
              "被同模式噪声埋到后面就救不回，改为基础分证据加成（全局生效）；",
              fill="#555", font=f_note)
    draw.text((42, 690),
              "②弱证据旧记忆只减一点分仍留在前 5，模型会看到矛盾拒答，"
              "改为按比例压降（胜者证据≥2倍时）退出默认上下文。",
              fill="#555", font=f_note)
    draw.text((42, 730),
              "千问作答抽样（10k，4 题）：证据开/关都 4/4；"
              "标准回归 88/200/10k 全部零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round30_conflict_10k.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
