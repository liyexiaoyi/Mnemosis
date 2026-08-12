"""Render round-7 (long dialogue + review loop) Chinese charts."""

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


def chart_long_dialogue() -> str:
    with open(os.path.join(_RESULTS, "long_dialogue_eval.json"), encoding="utf-8") as f:
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
    draw.text((40, 26), "LoCoMo 式长对话：36 条记忆 + 4 周后的复习闭环", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "对话里发生过事实更新；绿柱=命中@5（5 条候选里有正确答案），灰柱=命中@1（第一个就对）。",
              fill="#555", font=f_sub)
    groups = [
        ("刚聊完（基线）", aware["baseline"]["accuracy5"],
         aware["baseline"]["accuracy1"]),
        ("4 周后·有复习", aware["after_4weeks"]["accuracy5"],
         aware["after_4weeks"]["accuracy1"]),
        ("4 周后·不复习", no_review["after_4weeks_no_review"]["accuracy5"],
         no_review["after_4weeks_no_review"]["accuracy1"]),
    ]
    chart_h = 300
    base_y = 430
    bar_w = 110
    group_w = 330
    for gi, (name, acc5, acc1) in enumerate(groups):
        gx = 60 + gi * group_w
        draw.text((gx + 10, 120), name, fill="#111", font=f_label)
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
    draw.line([(50, base_y), (W - 50, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(50, y), (W - 50, y)], fill="#e5e5e5", width=1)
        draw.text((20, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 480),
              "结论：有复习，4 周后仍然 100% 找得到答案；不复习，命中@5 掉到 83%、"
              "命中@1 掉到 33%。",
              fill="#111", font=f_note)
    draw.text((40, 520),
              "事实更新验证：对话中间 Alice 喜欢颜色变了，系统正确记住新值（旧值被“顺应”掉）。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round7_long_dialogue.png")
    img.save(path)
    return path


def chart_review_aware() -> str:
    W, H = 1050, 600
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(19)
    f_val = _font(18)
    f_note = _font(17)
    draw.text((40, 26), "校准感知复习：没把握却答对了，下次复习来得更早", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "两条记忆都是“成功复习一次”。红=历史命中率低（没把握），绿=历史命中率高（有把握）。",
              fill="#555", font=f_sub)
    groups = [
        ("复习连击数", (0.5, "#c0392b"), (1.0, "#1a7f37"), "次数"),
        ("下次复习间隔", (16.97, "#c0392b"), (24.0, "#1a7f37"), "小时"),
    ]
    chart_h = 280
    base_y = 410
    bar_w = 150
    for gi, (name, (low, lc), (high, hc), unit) in enumerate(groups):
        gx = 60 + gi * 480
        draw.text((gx + 10, 120), name, fill="#111", font=f_label)
        maxv = 24.0 if unit == "小时" else 1.0
        for j, (val, label, color) in enumerate(
            ((low, "没把握答对", lc), (high, "有把握答对", hc))
        ):
            bh = val / maxv * chart_h
            x = gx + 20 + j * 210
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            draw.text((x + 40, y - 28), f"{val:.1f}{unit}", fill="#222", font=f_val)
            draw.text((x + 2, base_y + 12), label, fill="#333", font=f_label)
    draw.line([(50, base_y), (W - 50, base_y)], fill="#999", width=2)
    draw.text((40, 470),
              "没把握但答对的记忆：复习连击只算一半，间隔从 24 小时缩到约 17 小时——"
              "这正是“值得练习的困难”（desirable difficulty）的调度落地。",
              fill="#111", font=f_note)
    draw.text((40, 520),
              "对应理论：Bjork & Kroll (2015) 期望难度；Koriat & Goldsmith (1996) 元认知监控。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round7_review_aware.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_long_dialogue())
    print("written:", chart_review_aware())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
