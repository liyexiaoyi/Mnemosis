"""Round-29 chart: evidence-weighted conflict resolution comparison."""

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
    top1 = [
        ("Mnemosis加权", 1.00, "#7b2ff7"),
        ("Mnemosis基线", 0.625, "#b0b0b0"),
        ("mem0官方", 0.625, "#1a7f37"),
        ("腾讯Agent", 0.375, "#d97706"),
        ("cognitive", 0.125, "#b91c1c"),
    ]
    accuracy = [
        ("Mnemosis加权", 1.00, "#7b2ff7"),
        ("Mnemosis基线", 1.00, "#b0b0b0"),
        ("mem0官方", 1.00, "#1a7f37"),
        ("腾讯Agent", 0.375, "#d97706"),
        ("cognitive", 0.125, "#b91c1c"),
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

    draw.text((42, 28), "第 29 轮：记忆冲突消解 · 证据加权对比",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "同一 8 个“同一人两条相反记忆”场景（比如两种不同的‘最喜欢的颜色’），"
              "被证实更多次的那条是胜者。依据：记忆强度随确认次数增长（Anderson 1974；"
              "McClelland et al. 1995）。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① 证据胜者排第 1（检索，确定）", top1),
        (1, "② 云端千问作答准确率（最新一轮）", accuracy),
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
        bar_w = 88
        step = (panel_w - 20) // len(rows)
        for i, (name, val, color) in enumerate(rows):
            bx = x0 + 14 + i * step
            bh = val * chart_h
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
            draw.text((bx + 24, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
            draw.text((bx - 16, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：左边比“被证实更多的那条记忆是不是排第一”（这是系统的活，结果确定），"
              "右边比“千问看到检索结果后能不能答对”。Mnemosis 的证据加权把 5/8 提到 8/8；"
              "腾讯和 cognitive 连胜者都找不回来。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "实现：同模式竞争时，证据最多的一条受保护并小幅上浮；若胜者证据≥2倍，"
              "弱证据旧记忆被压出默认上下文，避免模型看到矛盾后拒绝作答（信念更新）。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "千问作答有多轮波动：Mnemosis 证据开 87.5%~100%、关 75%~100%（两轮），"
              "图中取最新一轮。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round29_conflict_evidence.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
