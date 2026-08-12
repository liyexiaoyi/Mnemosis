"""Round-145 chart: kg_export tool."""

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
            os.path.join(_BENCH, "results", "kg_export_eval.json"),
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

    draw.text((42, 26), "第 145 轮：把记忆网络导出成知识图谱", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：相关记忆在脑里像一张语义网（分层语义网络，Collins & Quillian 1969）；"
        "这个工具把“记忆-记忆”的连线导出成标准节点+边，方便外部画图和分析。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 ×（1 中心 + 5 邻居 + 2 孤立）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("节点数正确", data["node_ok"], "#7b2ff7"),
        ("连线数正确", data["edge_ok"], "#1a7f37"),
        ("连线不重复", data["dedup_ok"], "#d97706"),
        ("字段齐全", data["fields_ok"], "#0b7285"),
        ("计数自洽", data["count_ok"], "#c2255c"),
        ("MCP通路正常", data["mcp_ok"], "#6741d9"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 45 + i * 180
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 150, base_y], fill=color)
        draw.text((bx + 48, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 8, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：6 根柱子全部 10/10——8 个节点、5 条连线一个不多一个不少；"
        "双向连线去重成一条，孤立记忆作为节点保留但无连线。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：把记忆网络交给外部可视化工具画图，或做图分析（找中心、找桥），"
        "agent 和用户都能一眼看懂记忆关系。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.kg_export + MCP 工具——读取关联表，双向去重为无向边，"
        "节点带标签和类型，纯只读。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：240 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round145_kg.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
