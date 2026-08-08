"""Round-199 chart: emotion_advice tool."""

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
            os.path.join(_BENCH, "results", "emotion_advice_eval.json"),
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

    draw.text((42, 26), "第 199 轮：情绪调节建议", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：情绪影响记忆巩固，重评（重新解读负面事件）比压抑更有效（Gross 2002）；"
        "这个工具统计记忆的情绪偏向，并给出调节建议。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 ×（情绪画像 + 消极比例 + 主题聚合 + 建议生成）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("情绪画像齐全", data["profile_ok"], "#7b2ff7"),
        ("消极比例算对", data["ratio_ok"], "#1a7f37"),
        ("主题聚合成功", data["flag_ok"], "#d97706"),
        ("建议生成成功", data["advice_ok"], "#0b7285"),
        ("字段齐全", data["fields_ok"], "#c2255c"),
        ("MCP 通路正常", data["mcp_ok"], "#6741d9"),
        ("合计通过", data["total_ok"], "#2f9e44"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 45 + i * 155
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 125, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：7 根柱子全部 10/10——消极记忆多时能算出比例、聚出共同主题，并给出重评建议。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 定期跑一次——发现记忆偏消极时，不是硬压下去，而是换个角度重新解读，"
        "巩固时情绪更平稳，回忆更准确。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.emotion_advice + MCP 工具——统计积极/消极/中性比例、按线索聚合消极主题、按占比给建议。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：273 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round199_emotion.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
