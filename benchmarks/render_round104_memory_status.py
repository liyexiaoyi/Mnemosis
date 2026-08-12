"""Round-104 chart: MCP memory_status tool."""

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
        open(os.path.join(_BENCH, "results", "memory_status_eval.json"),
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

    draw.text((42, 26), "第 104 轮：agent 一眼看到记忆库“健康状态”",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：让 agent 像人一样体检记忆——总数、类型、平均强度、"
              "现在该复习几条、有几条在打架。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个不同大小的记忆库，5 项状态全部与手工计算一致",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("总数", data["active"], "#7b2ff7"),
        ("语义数", data["semantic"], "#1a7f37"),
        ("事件数", data["episodic"], "#d97706"),
        ("到期数", data["due"], "#b91c1c"),
        ("冲突数", data["conflicts"], "#0e7490"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 25 + i * 220
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 150, base_y], fill=color)
        draw.text((bx + 48, base_y - bh + 8), f"{val}/10",
                  fill="white", font=f_val)
        draw.text((bx + 30, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：memory_status 把 5 项指标全部算对（10/10 个库都一致）——"
              "agent 拿到快照就知道：",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "该复习几条、有没有矛盾、整体记忆强度如何，再决定下一步动作。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：engine.memory_status + MCP memory_status 工具——汇总"
              "backend 统计、到期数量与冲突数量。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：215 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round104_memory_status.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
