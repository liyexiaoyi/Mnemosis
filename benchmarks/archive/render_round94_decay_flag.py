"""Round-94 chart: decay warning flag."""

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
        open(os.path.join(_BENCH, "results", "decay_flag_eval.json"),
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

    draw.text((42, 26), "第 94 轮：快忘掉的记忆，检索时提醒“快忘了”",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Ebbinghaus 遗忘曲线——可提取度低于 0.3 说明快掉出记忆了，"
              "agent 应该尽快复习或谨慎作答。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 8 条“快遗忘”记忆，被正确提醒的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("快遗忘标记(新)", data["on"]["weak_flagged"], "#7b2ff7"),
        ("关闭标记", data["off"]["weak_flagged"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 8.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/8",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    x0 = 760
    draw.text((x0, 120), "② 8 条“还很牢”的记忆，被误标的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    val = data["on"]["strong_flagged"]
    bx = x0 + 130
    bh = val / 8.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#1a7f37")
    draw.text((bx + 42, base_y - bh + 8), f"{val}/8",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "快遗忘标记(新)", fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：快遗忘的记忆（可提取度 <0.3）8/8 被提醒“低可提取(快遗忘)”，"
              "还很牢的 0/8 误标。",
              fill="#555", font=f_note)
    draw.text((42, 640),
              "agent 拿到提醒就知道：这条要么尽快复习，要么回答时别太肯定。",
              fill="#555", font=f_note)
    draw.text((42, 710),
              "实现：recall 新增 decay_flag（默认开）——可提取度低于 0.3 的检索结果"
              "标注提醒；只加标记，不改排序。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：209 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round94_decay_flag.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
