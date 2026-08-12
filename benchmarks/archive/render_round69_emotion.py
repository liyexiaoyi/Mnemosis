"""Round-69 chart: emotion regulation (processed memories stop staying hot)."""

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
        open(os.path.join(_BENCH, "results", "emotion_regulation_eval.json"),
             encoding="utf-8")
    )
    W, H = 1450, 920
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 26), "第 69 轮：反复回忆处理后，情绪记忆不再“永远保鲜”",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Gross (2002) 情绪调节——反复回忆并处理一段情绪记忆后，"
              "它的情绪强度会消退（类似恐惧消退），遗忘速度回到普通水平。",
              fill="#555", font=f_sub)

    rows = [
        ("处理过(新)", data["regulated"]["mean_retrievability"],
         data["regulated"]["retained"], "#7b2ff7"),
        ("情绪但没处理", data["unprocessed"]["mean_retrievability"],
         data["unprocessed"]["retained"], "#d97706"),
        ("普通记忆", data["neutral"]["mean_retrievability"],
         data["neutral"]["retained"], "#b0b0b0"),
    ]

    # Panel 1: mean retrievability
    x0 = 90
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 30 天后的平均记住强度（越高越好）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.2, "0.2"), (0.4, "0.4")):
        y = base_y - frac / 0.45 * chart_h
        draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 38, y - 9), label, fill="#666", font=f_val)
    for i, (name, val, _, color) in enumerate(rows):
        bx = x0 + 55 + i * 170
        bh = val / 0.45 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 120, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 6), f"{val:.3f}",
                  fill="white", font=f_val)
        draw.text((bx - 18, base_y + 10), name, fill="#111", font=f_label)

    # Panel 2: retained
    x0 = 800
    draw.text((x0, 120), "② 30 天后还记住多少条（共 30 条）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (10.0, "10"), (20.0, "20"), (30.0, "30")):
        y = base_y - frac / 30.0 * chart_h
        draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    for i, (name, _, val, color) in enumerate(rows):
        bx = x0 + 55 + i * 170
        bh = val / 30.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 120, base_y], fill=color)
        draw.text((bx + 38, base_y - bh + 6), f"{val}/30",
                  fill="white", font=f_val)
        draw.text((bx - 18, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 610),
              "怎么看：处理组连续 6 天完整回忆（30/30 达到 3 次以上成功），之后遗忘速度"
              "回到普通水平；30 天后仍记住 30/30、",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "强度 0.374。没处理的情绪记忆虽然衰减慢（0.0012/小时 vs 普通 0.002），"
              "但从不复习，30 天后 0 条达标（0.241）。",
              fill="#555", font=f_note)
    draw.text((42, 720),
              "实现：遗忘曲线新增情绪调节——情绪记忆连续成功回忆 3 次后，衰减速度"
              "从 0.6 倍恢复为普通速度（不再永远保鲜）。",
              fill="#555", font=f_note)
    draw.text((42, 780),
              "诚实说明：本轮先试了“多线索冗余加分”，发现会让全库集体加分、破坏排序"
              "（同义 10k 从 9/9 掉到 0/9），已回退不发布，改为本机制。",
              fill="#555", font=f_note)
    draw.text((42, 840),
              "回归：192 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round69_emotion_regulation.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
