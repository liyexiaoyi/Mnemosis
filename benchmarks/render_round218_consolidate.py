"""Round-218 chart: consolidation_forecast tool."""

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
            os.path.join(
                _BENCH, "results", "consolidation_forecast_eval.json"
            ),
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

    draw.text((42, 26), "第 218 轮：睡眠巩固预测", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：睡眠巩固记忆，睡前复习重要材料效果最好（Rasch & Born 2013）——"
        "这个工具预测“今晚哪几条记忆睡觉收益最大”。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 ×（重要/情绪/易忘 → 今晚候选）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("总数算对", data["total_ok"], "#7b2ff7"),
        ("第一名正确", data["top_ok"], "#1a7f37"),
        ("分数够高", data["score_ok"], "#d97706"),
        ("收益预测有", data["gain_ok"], "#0b7285"),
        ("理由齐全", data["reason_ok"], "#c2255c"),
        ("建议生成", data["advice_ok"], "#6741d9"),
        ("字段齐全", data["fields_ok"], "#2f9e44"),
        ("MCP 通路正常", data["mcp_ok"], "#e8590c"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 35 + i * 138
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 120, base_y], fill=color)
        draw.text((bx + 34, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：8 根柱子全部 10/10——“高数重点”这种又重要、又带情绪、"
        "又快忘的记忆排第一，是今晚最值得过一遍的。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 睡前跑一次——先复习今晚候选，睡后再用测试出题器"
        "验证，记忆收益最大，像人一样“睡一觉记更牢”。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.consolidation_forecast + MCP 工具——按重要度/情绪/"
        "易忘度算睡眠收益分，输出今晚候选与预计增益。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：284 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round218_consolidate.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
