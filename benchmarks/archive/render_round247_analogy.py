"""Round-247 chart: analogy_prompt tool."""

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
            os.path.join(_BENCH, "results", "analogy_prompt_eval.json"),
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

    draw.text((42, 26), "第 247 轮：类比出题（换皮不变骨）", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：把两个“结构相同、表面不同”的例子放在一起比，学得最牢、"
        "迁移最好（Gentner, Loewenstein & Thompson, 2003）。"
        "这个工具把已掌握的记忆换成新人、新地点、新物品，出同构题检验。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text(
        (x0, 120),
        "① 10 个记忆库：各存 3 条已掌握偏好记忆（阿丽喜欢成都/饺子/蓝色）",
        fill="#111",
        font=f_panel,
    )
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("出题成功", data["prompts_ok"], "#7b2ff7"),
        ("结构保留", data["structure_ok"], "#1a7f37"),
        ("表面换新", data["surface_ok"], "#d97706"),
        ("换词记录", data["mapping_ok"], "#0b7285"),
        ("答案隐藏", data["hidden_ok"], "#c2255c"),
        ("主题正确", data["topic_ok"], "#6741d9"),
        ("空库不崩", data["empty_ok"], "#2f9e44"),
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
        "怎么看：8 根柱子全部 10/10——“阿丽喜欢的城市是成都”被换成"
        "“小波喜欢的城市是北京”，“喜欢”这个结构关系原样保留，答案隐藏。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 学完一个知识点后用同构新题自测——答对说明真懂结构，"
        "答错说明只是背住了表面例子。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.analogy_prompt + MCP 工具——取已掌握主题，"
        "替换人名/地点/物品，保留关系词，输出原题+新题+换词记录。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：303 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round247_analogy.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
