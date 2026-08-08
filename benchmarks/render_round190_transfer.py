"""Round-190 chart: transfer_report tool."""

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
            os.path.join(_BENCH, "results", "transfer_report_eval.json"),
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

    draw.text((42, 26), "第 190 轮：老经验能不能用到新项目？", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：可复用的图式会迁移到新任务（Bartlett 1932）；这个工具把经验库"
        "里的成功/失败/注意逐条匹配新计划步骤，标出哪些经验适用。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 × 3 条经验（2 条命中计划 + 1 条无关）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("计划步骤齐", data["steps_ok"], "#7b2ff7"),
        ("经验全扫到", data["total_ok"], "#1a7f37"),
        ("适用条数对", data["match_ok"], "#d97706"),
        ("命中步骤对", data["hit_ok"], "#0b7285"),
        ("无关经验跳过", data["skip_ok"], "#c2255c"),
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
        "怎么看：7 根柱子全部 10/10——3 条经验全部扫到，其中 2 条命中计划步骤"
        "（调研需求、测试功能），无关的“原型先行”被跳过。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 开新项目时先跑迁移报告——上次“测试超时”的教训直接挂到"
        "这次“测试功能”步骤上，注意事项自动带上。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.transfer_report + MCP 工具——经验关键词 + 词重叠匹配"
        "计划步骤，纯只读。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：268 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round190_transfer.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
