"""Round-82 chart: combined scheduling validation."""

from __future__ import annotations

import json
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
    data = json.load(
        open(os.path.join(_BENCH, "results", "combined_scheduling_eval.json"),
             encoding="utf-8")
    )
    W, H = 1450, 900
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(21)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 26), "第 82 轮：调度机制组合验证（唤醒+交错+轮换一起开）",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：前面各轮机制同属练习调度，需要验证叠加不冲突；组合采用稳健子集"
              "（唤醒优先+交错+线索轮换），新鲜窗口按需单独开。",
              fill="#555", font=f_sub)

    # Panel 1: group means
    x0 = 90
    base_y = 420
    chart_h = 230
    draw.text((x0, 120), "① 三组记忆第 7 天平均强度（组合 vs 基线）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1130, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.4, "0.4"), (0.8, "0.8")):
        y = base_y - frac / 0.95 * chart_h
        draw.line([(x0, y), (x0 + 1130, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 38, y - 9), label, fill="#666", font=f_val)
    groups = [
        ("唤醒记忆", "arousal_mean"),
        ("新鲜记忆", "fresh_mean"),
        ("中性记忆", "neutral_mean"),
    ]
    for gi, (name, key) in enumerate(groups):
        gx = x0 + gi * 380
        vals = [
            ("组合", data["combined"][key], "#7b2ff7"),
            ("基线", data["baseline"][key], "#b0b0b0"),
        ]
        for i, (lbl, val, color) in enumerate(vals):
            bx = gx + 55 + i * 130
            bh = val / 0.95 * chart_h
            draw.rectangle([bx, base_y - bh, bx + 100, base_y], fill=color)
            draw.text((bx + 30, base_y - bh + 6), f"{val:.3f}",
                      fill="white", font=f_val)
            draw.text((bx - 8, base_y + 10), lbl, fill="#111", font=f_label)
        draw.text((gx + 95, base_y + 42), name, fill="#333", font=f_label)

    # Panel 2: retained
    x0 = 90
    base_y2 = 760
    draw.text((x0, 610), "② 30 条记忆里第 7 天还记住的条数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y2), (x0 + 700, base_y2)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (10.0, "10"), (20.0, "20"), (30.0, "30")):
        y = base_y2 - frac / 30.0 * 150
        draw.line([(x0, y), (x0 + 700, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    for i, (lbl, key, color) in enumerate(
        (("组合", "combined", "#7b2ff7"), ("基线", "baseline", "#b0b0b0"))
    ):
        bx = x0 + 100 + i * 260
        bh = data[key]["retained"] / 30.0 * 150
        draw.rectangle([bx, base_y2 - bh, bx + 160, base_y2], fill=color)
        draw.text((bx + 58, base_y2 - bh + 8), f"{data[key]['retained']}/30",
                  fill="white", font=f_val)
        draw.text((bx + 42, base_y2 + 10), lbl, fill="#111", font=f_label)

    draw.text((42, 880),
              "怎么看：组合把唤醒记忆提到 0.919（基线 0.740），总保留 30/30（基线 28）；"
              "新鲜/中性组付出诚实代价。",
              fill="#555", font=f_note)
    draw.text((42, 920),
              "重要发现：把“新鲜优先”也一起开时，新鲜组反而下降（0.766 < 0.818）——"
              "新鲜条还没练熟就提前占名额，得不偿失；",
              fill="#555", font=f_note)
    draw.text((42, 960),
              "因此 fresh_priority 默认改为关（按需开启），本轮同时给两种额外优先"
              "加了每轮上限（≤ 一半名额），防止单组垄断。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round82_combined_scheduling.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
