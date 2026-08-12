"""Round-33 chart: Chinese price comparison at 10k (synonym-aware pack)."""

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
        ("普通检索", 1.00, "#b0b0b0"),
        ("推理前提包", 1.00, "#7b2ff7"),
    ]
    accuracy = [
        ("普通检索", 1.00, "#b0b0b0"),
        ("推理前提包", 1.00, "#7b2ff7"),
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

    draw.text((42, 28), "第 33 轮：中文价格比较 · 同义词感知的推理前提包",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "5 个价格比较场景埋进 8,674 条噪声；问题用“昂贵/廉价/更贵”，"
              "记忆里只有数字（花了2500元），没有任何“贵/便宜”字样。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① 两条价格前提都找回（10 条里找回几条）", coverage),
        (1, "② 云端千问作答（5 题对几题）", accuracy),
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
            bh = val * chart_h
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
            draw.text((bx + 28, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
            draw.text((bx - 6, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "本轮机制：①“昂贵/廉价”加入比较词识别和同义词组，"
              "“谁更昂贵”能触发推理前提包；②比较类前提包额外自动拉取"
              "“带数字+单位”的记忆（价格、数量），因为比较最终比的是数字。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "结果：10k 噪声下普通检索和前提包都找回 10/10 条价格前提，"
              "千问双 5/5 答对——Mnemosis 词面召回足够强，前提包负责的是"
              "“昂贵/廉价”这类换说法后依然稳定触发推理通道。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "单元测试锁定：更昂贵/更廉价 → 识别为比较题；"
              "数量记忆在比较题下被拉进前提包。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round33_compare_10k.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
