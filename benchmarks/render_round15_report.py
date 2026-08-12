"""Render round-15 (Chinese long dialogue) Chinese chart."""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont

_BENCH = os.path.dirname(os.path.abspath(__file__))
_RESULTS = os.path.join(_BENCH, "results")
_OUT = os.path.normpath(os.path.join(_BENCH, "..", "..", "outputs", "charts"))


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\msjh.ttc",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def chart_zh_long() -> str:
    with open(
        os.path.join(_RESULTS, "zh_long_dialogue_eval.json"), encoding="utf-8"
    ) as f:
        d = json.load(f)
    aware = d["results"]["aware"]
    no_review = d["no_review"]
    W, H = 1150, 640
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(19)
    f_val = _font(18)
    f_note = _font(17)
    draw.text((40, 26), "中文长对话：36 条记忆 + 事实更新 + 4 周复习闭环", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "对话里有中英文两种日期写法，中间还改过一次事实。"
              "绿柱=命中@5，灰柱=命中@1。",
              fill="#555", font=f_sub)
    groups = [
        ("刚聊完", aware["baseline"]["accuracy5"],
         aware["baseline"]["accuracy1"]),
        ("4周后·有复习", aware["after_4weeks"]["accuracy5"],
         aware["after_4weeks"]["accuracy1"]),
        ("4周后·不复习", no_review["accuracy5"], no_review["accuracy1"]),
    ]
    chart_h = 300
    base_y = 430
    bar_w = 110
    group_w = 330
    for gi, (name, acc5, acc1) in enumerate(groups):
        gx = 55 + gi * group_w
        draw.text((gx + 10, 96), name, fill="#111", font=f_label)
        for j, (val, label, color) in enumerate(
            ((acc5, "命中@5", "#1a7f37"), (acc1, "命中@1", "#b0b0b0"))
        ):
            bh = val * chart_h
            x = gx + 20 + j * 140
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            draw.text((x + 28, y + 10), f"{val:.0%}", fill="white", font=f_val)
            if gi == 0:
                draw.text((x + 6, base_y + 12), label, fill="#333", font=f_label)
    draw.line([(45, base_y), (W - 45, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(45, y), (W - 45, y)], fill="#e5e5e5", width=1)
        draw.text((15, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 480),
              "有复习：4 周后仍 100% 找得到答案；不复习：命中@5 掉到 75%、"
              "命中@1 掉到 50%。",
              fill="#111", font=f_note)
    draw.text((40, 520),
              "事实更新验证：阿丽喜欢的颜色改成靛蓝色后，系统记住新值（旧值被“顺应”掉）。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round15_zh_long_dialogue.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_zh_long())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
