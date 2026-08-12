"""Round-124 chart: similarity_report tool."""

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
        open(
            os.path.join(_BENCH, "results", "similarity_report_eval.json"),
            encoding="utf-8",
        )
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

    draw.text((42, 26), "第 124 轮：找出容易搞混的记忆对", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：大脑会用“模式分离”把相似经历分开存放，防止记串；"
        "这个工具把内容高度重叠的记忆对列出来给 agent 看。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 × 3 对相似记忆 + 3 对无关记忆", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("相似对数量正确", data["count_ok"], "#7b2ff7"),
        ("找对相似对象", data["correct_ok"], "#1a7f37"),
        ("字段齐全", data["fields_ok"], "#d97706"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 60 + i * 340
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 260, base_y], fill=color)
        draw.text((bx + 96, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx + 20, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：30 对里只报出真正相似的那 3 对，无关记忆一个都不误报；"
        "每条还带两个记忆的编号、相似度和内容预览。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：帮 agent 发现该合并的重复记忆、或需要加深区分的易混记忆，"
        "有点像帮大脑做“别记串了”的体检。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.similarity_report + MCP 工具——按内容分词重叠算相似度，"
        "可调阈值和返回条数，只读不改任何记忆。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：227 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round124_similarity_report.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
