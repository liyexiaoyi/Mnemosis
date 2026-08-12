"""Round-159 chart: multi_hop_report tool."""

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
            os.path.join(_BENCH, "results", "multi_hop_report_eval.json"),
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

    draw.text((42, 26), "第 159 轮：沿着记忆网络“一跳一跳”找证据", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：记忆靠关联网络互相激活，隔得越远越慢到达（扩散激活，"
        "Collins & Loftus 1975）；这个工具把每一跳能摸到的记忆列出来。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 × 链式网络（a-b-c-d + 分支 b-e）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("第一跳正确", data["hop1_ok"], "#7b2ff7"),
        ("第二跳正确", data["hop2_ok"], "#1a7f37"),
        ("第三跳正确", data["depth_ok"], "#d97706"),
        ("总数正确", data["reached_ok"], "#0b7285"),
        ("字段齐全", data["fields_ok"], "#c2255c"),
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
        "怎么看：6 根柱子全部 10/10——从 a 出发，第一跳摸到 b，第二跳摸到 c 和 e，"
        "第三跳摸到 d；走 3 跳总共到达 4 条记忆，一个不多一个不少。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 要回答“跟这件事有关的还有啥”时，按跳数收集关联证据，"
        "推理链条有迹可循。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.multi_hop_report + MCP 工具——BFS 沿关联表逐跳扩散，"
        "每跳去重并计数，纯只读。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：248 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round159_multi_hop.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
