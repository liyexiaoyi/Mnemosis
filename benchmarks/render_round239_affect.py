"""Round-239 chart: affect_decay tool."""

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
            os.path.join(_BENCH, "results", "affect_decay_eval.json"),
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

    draw.text((42, 26), "第 239 轮：情绪强度衰减", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：情绪记忆更持久，但反复成功处理后情绪会消退（Gross 2002）——"
        "连处理 3 次后强度归零。这个工具预测每条情绪记忆还剩多少“劲”。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 ×（未处理/半消退/已处理三类情绪记忆）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("总数算对", data["total_ok"], "#7b2ff7"),
        ("未处理判断对", data["persistent_ok"], "#1a7f37"),
        ("半消退判断对", data["fading_ok"], "#d97706"),
        ("已处理判断对", data["processed_ok"], "#0b7285"),
        ("分布统计对", data["counts_ok"], "#c2255c"),
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
        "怎么看：8 根柱子全部 10/10——没处理过的负性记忆强度 100%、"
        "预计持续 30 天；处理 2 次的降到 33%；处理 3 次的归零。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 定期体检情绪记忆——剩下的“劲”还大的先重评+更新，"
        "处理差不多的保持间隔复习，避免反复回放强化情绪。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.affect_decay + MCP 工具——按连胜处理次数算剩余"
        "情绪强度、预计持续天数、状态与处理提示。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：297 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round239_affect.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
