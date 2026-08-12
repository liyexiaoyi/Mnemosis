"""Round-37 chart: MCP cloud integration + 10k outcome evidence."""

from __future__ import annotations

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
    mcp_items = [
        ("按序", 1.00),
        ("完整", 1.00),
        ("写计划", 1.00),
        ("记录", 1.00),
        ("复盘", 1.00),
        ("缺口", 1.00),
    ]
    evidence = [
        ("证据开·第1", 1.00, "#7b2ff7"),
        ("证据关·第1", 0.0, "#b0b0b0"),
        ("证据开·前5", 1.00, "#7b2ff7"),
        ("证据关·前5", 1.00, "#b0b0b0"),
    ]
    W, H = 1560, 830
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 28), "第 37 轮：MCP 云端集成 + 10k 项目历史证据压力",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "左边：agent 通过 MCP 工具（plan/record_outcome/recall/check）"
              "跑完整项目闭环，云端千问作答；右边：20 个项目历史里问"
              "“哪个项目订机票失败”，证据加权开/关对比。",
              fill="#555", font=f_sub)

    # panel 1: MCP six items (checkmark bars)
    x0 = 70
    draw.text((x0, 130), "① MCP 工具闭环（6 项，全过=100%）", fill="#111", font=f_panel)
    base_y = 500
    chart_h = 300
    draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
    for i, (name, val) in enumerate(mcp_items):
        bx = x0 + 12 + i * 92
        bh = val * chart_h
        draw.rectangle([bx, base_y - bh, bx + 60, base_y], fill="#7b2ff7")
        draw.text((bx + 10, base_y - bh + 8), f"{val:.0%}",
                  fill="white", font=f_val)
        draw.text((bx - 6, base_y + 12), name, fill="#111", font=f_label)

    # panel 2: evidence A/B
    x1 = 640
    draw.text((x1, 130), "② 10k 项目历史：证据开/关（3 题）", fill="#111", font=f_panel)
    draw.line([(x1, base_y), (x1 + 480, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(x1, y), (x1 + 480, y)], fill="#e5e5e5", width=1)
        draw.text((x1 - 34, y - 10), label, fill="#666", font=f_val)
    for i, (name, val, color) in enumerate(evidence):
        bx = x1 + 14 + i * 118
        bh = max(val, 0.02) * chart_h
        draw.rectangle([bx, base_y - bh, bx + 84, base_y], fill=color)
        draw.text((bx + 24, base_y - bh + 8), f"{val:.0%}",
                  fill="white", font=f_val)
        draw.text((bx - 12, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "MCP 闭环 6/6：计划按时间找回、旧步骤完整、千问写出的计划覆盖全部步骤、"
              "失败结果记录成功、复盘答出“订机票”、没见过的问题答 unknown。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "10k 压力：被证实两次的失败记录（evidence=2）在 8,693 条记忆里排第一 3/3；"
              "关闭证据后同样的记录排第一 0/3（只靠插入顺序，前 5 里能找到但排名乱）。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "工程：10k 证据压力基准已接入 CI（检索版）。回归 156 测试全过，"
              "88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round37_mcp_evidence.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
