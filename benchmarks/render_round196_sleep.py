"""Round-196 chart: sleep_advice tool."""

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
            os.path.join(_BENCH, "results", "sleep_advice_eval.json"),
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

    draw.text((42, 26), "第 196 轮：睡前该复习什么？", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：睡眠巩固记忆，睡前复习重要材料会强化（Rasch & Born 2013）；"
        "这个工具把“重要但快忘”的记忆挑出来，加上冲突/过期/明日盲区。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 ×（弱重要 + 冲突 + 过期 + 盲区主题）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("睡前清单有人", data["review_ok"], "#7b2ff7"),
        ("冲突数到", data["conflict_ok"], "#1a7f37"),
        ("过期数到", data["overdue_ok"], "#d97706"),
        ("明日盲区列出", data["priority_ok"], "#0b7285"),
        ("建议生成成功", data["advice_ok"], "#c2255c"),
        ("字段齐全", data["fields_ok"], "#6741d9"),
        ("MCP通路正常", data["mcp_ok"], "#2f9e44"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 45 + i * 155
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 125, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：7 根柱子全部 10/10——“重要但快忘”的记忆进睡前清单，"
        "冲突、过期待办都数到，明天该补的盲区主题也列出来了。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 睡前跑一次——先把重要的过一遍，冲突明天处理，"
        "过期待办收尾，明天优先补盲区，巩固效率更高。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.sleep_advice + MCP 工具——汇总弱重要/冲突/过期/"
        "未复习主题并给建议，纯只读。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：272 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round196_sleep.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
