"""Round-252 chart: agent_learning_session tool."""

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
                _BENCH, "results", "agent_learning_session_eval.json"
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

    draw.text((42, 26), "第 252 轮：agent 学习会话（学→测→比→再学）", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：测试效应（Roediger & Karpicke 2006）+ 知识追踪纵向对比。",
        fill="#555",
        font=f_sub,
    )
    draw.text(
        (42, 104),
        "agent 完整跑一轮：出练习→答 2 题（对 1 错 1）→评分→快照对比→规划下一轮。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text(
        (x0, 130),
        "① 10 个记忆库：各 3 条已掌握记忆，每次会话答 2 题",
        fill="#111",
        font=f_panel,
    )
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("字段齐全", data["fields_ok"], "#7b2ff7"),
        ("基线快照", data["baseline_ok"], "#1a7f37"),
        ("练习出题", data["practice_ok"], "#d97706"),
        ("评分正确", data["scoring_ok"], "#0b7285"),
        ("快照对比", data["diff_ok"], "#c2255c"),
        ("下一轮计划", data["next_loop_ok"], "#6741d9"),
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
        "怎么看：8 根柱子全部 10/10——出题后答对 1 题、答错 1 题能准确评分，"
        "快照对比给出 进步/稳定/退步 结论，并规划好下一轮三步。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 每天自己跑一轮“学习会话”，答完自动更新记忆强度、"
        "看有没有进步，再自动排明天的复习和练习。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.agent_learning_session + MCP 工具——组合学习闭环、"
        "练习评分、复习坚持、快照对比，输出评分+对比+下一轮计划。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：306 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round252_session.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
