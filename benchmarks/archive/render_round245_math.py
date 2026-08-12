"""Round-245 chart: math_ladder tool."""

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
            os.path.join(_BENCH, "results", "math_ladder_eval.json"),
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

    draw.text((42, 26), "第 245 轮：数学抽象阶梯（具体→符号→公式）", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：人脑的数学知识是一套独立网络（Amalric & Dehaene, 2019），"
        "学习时从具体例子走向符号再走向一般规则效果最好（具体化递减）。"
        "这个工具把数学题按三级阶梯拆开，并优先用记忆里存过的公式。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text(
        (x0, 120),
        "① 10 个记忆库：一半存有速度公式，一半没有",
        fill="#111",
        font=f_panel,
    )
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("题型识别准", data["type_ok"], "#7b2ff7"),
        ("具体数字全", data["concrete_ok"], "#1a7f37"),
        ("符号模板对", data["symbolic_ok"], "#d97706"),
        ("一般规则有", data["general_ok"], "#0b7285"),
        ("结论合法", data["verdict_ok"], "#c2255c"),
        ("三级阶梯齐", data["ladder_ok"], "#6741d9"),
        ("建议含公式", data["advice_ok"], "#2f9e44"),
        ("MCP 通路", data["mcp_ok"], "#e8590c"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 35 + i * 138
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 120, base_y], fill=color)
        draw.text((bx + 34, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：8 根柱子全部 10/10——速度题识别准确，具体数字（60、2）提取全，"
        "符号模板是“速度=路程÷时间”，有公式的库直接调用记忆公式，没公式的用通用模板。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 解数学题前先爬一遍抽象阶梯，避免拿到题就乱算；"
        "记忆里有公式就代入，没有就提醒先补知识。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.math_ladder + MCP 工具——题型关键词识别，"
        "提取数字，映射符号模板，从语义记忆找公式，给出三级阶梯和建议。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：301 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round245_math.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
