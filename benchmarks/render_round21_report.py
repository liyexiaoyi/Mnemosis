"""Render round-21 (importance-first review, 200-session zh long dialogue)."""

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


def chart() -> str:
    W, H = 1150, 640
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(19)
    f_val = _font(18)
    f_note = _font(17)
    draw.text((40, 26), "重要性优先的复习：中文 200 会话长对话 4 周后", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "198 条事件 + 事实更新；每天只能复习 6 条时，先复习重要的。"
              "命中@5（12 道题）。",
              fill="#555", font=f_sub)
    rows = [
        ("刚聊完（基线）", 8 / 12, "#2f80ed"),
        ("4周后·旧调度", 4 / 12, "#c0392b"),
        ("4周后·重要性优先", 6 / 12, "#1a7f37"),
        ("4周后·不复习", 5 / 12, "#b0b0b0"),
    ]
    chart_h = 300
    base_y = 420
    bar_w = 170
    for i, (name, val, color) in enumerate(rows):
        x = 70 + i * 260
        bh = val * chart_h
        y = base_y - bh
        draw.rectangle([x, y, x + bar_w, base_y], fill=color)
        draw.text((x + 52, y - 30), f"{val:.0%}", fill="#222", font=f_val)
        draw.text((x - 6, base_y + 12), name, fill="#333", font=f_label)
    draw.line([(50, base_y), (W - 50, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(50, y), (W - 50, y)], fill="#e5e5e5", width=1)
        draw.text((20, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 480),
              "旧调度复习后 33% → 重要性优先 50%，并超过不复习的 42%。",
              fill="#111", font=f_note)
    draw.text((40, 520),
              "对应理论：Rasch & Born (2013)——巩固/复习优先处理重要内容。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round21_importance_review.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
