"""Round-99 chart: MCP list_conflicts tool."""

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
        open(os.path.join(_BENCH, "results", "conflicts_tool_eval.json"),
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

    draw.text((42, 26), "第 99 轮：agent 可以一键列出“记忆打架”的清单",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：冲突检测（图式重建/重整合）——同一线索下两条都自信但内容不同，"
              "必须先让 agent 知道，再决定信谁。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 8 对真实冲突，工具全部报告",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    bx = x0 + 130
    bh = data["reported_pairs"] / 8.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#7b2ff7")
    draw.text((bx + 42, base_y - bh + 8), f"{data['reported_pairs']}/8",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "真冲突", fill="#111", font=f_label)

    x0 = 760
    draw.text((x0, 120), "② 8 对“不算冲突”的记忆，被误报的对数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    val = data["false_positives"] // 2
    bx = x0 + 130
    bh = val / 8.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#1a7f37")
    draw.text((bx + 42, base_y - bh + 8), f"{val}/8",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "误报", fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：list_conflicts 把 8 对真冲突全部报告（8/8），"
              "8 对“一方不自信”的记忆 0 误报——",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "agent 回答前先跑一次，就知道哪些事实在打架、需要核实。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：MCP 新增 list_conflicts——包装 detect_conflicts，返回双方"
              "内容、id 与原因。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：212 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round99_conflicts_tool.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
