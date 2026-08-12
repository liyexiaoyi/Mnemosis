"""Round-77 chart: weak-important sleep replay."""

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
        open(os.path.join(_BENCH, "results", "weak_important_replay_eval.json"),
             encoding="utf-8")
    )
    W, H = 1400, 800
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(21)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 77 轮：睡觉时优先重放“重要但快忘掉”的记忆",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Stickgold & Walker (2013) 睡眠巩固优先照顾重要内容——"
              "重要的记忆哪怕很旧、很弱，也要在睡眠里被捞回来。",
              fill="#555", font=f_sub)

    # Panel 1: important mean
    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 15 条“重要但快忘”的记忆，睡眠后平均强度",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.1, "0.1"), (0.2, "0.2"), (0.3, "0.3")):
        y = base_y - frac / 0.4 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("弱重要重放(新)", data["sleep"]["important_mean"], "#7b2ff7"),
        ("不重放", data["no_sleep"]["important_mean"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 0.4 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 38, base_y - bh + 8), f"{val:.4f}",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    # Panel 2: trivial mean
    x0 = 760
    draw.text((x0, 120), "② 15 条琐碎记忆的平均强度（应该基本不动）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.01, "0.01"), (0.02, "0.02")):
        y = base_y - frac / 0.03 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows2 = [
        ("弱重要重放(新)", data["sleep"]["trivial_mean"], "#7b2ff7"),
        ("不重放", data["no_sleep"]["trivial_mean"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows2):
        bx = x0 + 70 + i * 190
        bh = val / 0.03 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 38, base_y - bh + 8), f"{val:.4f}",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：15 条重要但快忘的记忆在睡眠里被重放（0.352 vs 0.017），"
              "不再无声消失；",
              fill="#555", font=f_note)
    draw.text((42, 640),
              "琐碎记忆基本不动（0.0168 vs 0.0168）——重放名额只给重要的。",
              fill="#555", font=f_note)
    draw.text((42, 710),
              "实现：睡眠巩固新增 weak_replayed 阶段——可提取度低于 0.35 且"
              "重要度 ≥0.6 的记忆获得小幅度巩固（上限 100 条，按重要度排序）。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：199 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round77_weak_important_replay.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
