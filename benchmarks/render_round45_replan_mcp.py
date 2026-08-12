"""Round-45 chart: MCP replan tool + 10k re-planning stress."""

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
    checks = [
        ("失败票靠后", 1.00),
        ("成功票在前", 1.00),
        ("重规划理由", 1.00),
        ("决策入记忆", 1.00),
    ]
    W, H = 1450, 780
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 28), "第 45 轮：MCP replan 工具 + 10k 重规划压力",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "agent 现在可以直接通过 MCP 的 replan 工具“执行失败→重新规划”；"
              "同一机制在 8,739 条噪声（含 30 个竞争对手项目）下依然有效。",
              fill="#555", font=f_sub)

    x0 = 150
    draw.text((x0, 130), "10k 重规划行为检查（4 项全过）", fill="#111", font=f_panel)
    base_y = 500
    chart_h = 300
    draw.line([(x0, base_y), (x0 + 620, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(x0, y), (x0 + 620, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
    for i, (name, val) in enumerate(checks):
        bx = x0 + 14 + i * 155
        bh = max(val, 0.02) * chart_h
        draw.rectangle([bx, base_y - bh, bx + 110, base_y], fill="#7b2ff7")
        draw.text((bx + 34, base_y - bh + 8), f"{val:.0%}",
                  fill="white", font=f_val)
        draw.text((bx - 10, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "场景：阿丽订机票失败两次、小波全部成功，30 个对手项目也有“订机票”"
              "失败记录。replan 后：只有阿丽的失败机票被移到计划末尾（共 14 条容量），"
              "小波的成功机票保留在前。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "MCP：新增 replan 工具（goal + failed_step），agent 可把执行失败"
              "直接转成“避开失败步骤”的调整后计划；单元测试锁定行为。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "工程：10k 重规划基准接入 CI（检索版）。回归：166 测试全过，"
              "88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round45_replan_mcp.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
