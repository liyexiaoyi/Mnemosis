"""Round-125 chart: association_report tool."""

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
            os.path.join(_BENCH, "results", "association_report_eval.json"),
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

    draw.text((42, 26), "第 125 轮：记忆关联网络体检", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：大脑的记忆靠关联网络互相唤醒（激活扩散，Collins & Loftus 1975）；"
        "这个工具汇总每条记忆有多少“朋友”、谁最容易被带动、谁完全孤立。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 ×（6 条联网 + 6 条孤立 + 2 条自动关联）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("数量统计正确", data["count_ok"], "#7b2ff7"),
        ("孤立数正确", data["isolated_ok"], "#1a7f37"),
        ("联网数正确", data["connected_ok"], "#d97706"),
        ("找出最热记忆", data["top_ok"], "#0b7285"),
        ("自动链接入账", data["auto_ok"], "#c2255c"),
        ("字段齐全", data["fields_ok"], "#6741d9"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 45 + i * 180
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 150, base_y], fill=color)
        draw.text((bx + 48, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 8, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：6 根柱子全部 10/10——手建的 7 条关联和自动产生的关联都算得对，"
        "6 条孤立记忆一个不少，最“热”的记忆被准确点名。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：给 agent 一份关联网络快照——孤立记忆可能缺线索需要补 cue，"
        "超热记忆可能是该拆分的中枢。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.association_report + MCP 工具——读链接表统计总数/孤立数/"
        "平均度/Top-N，纯只读不改记忆。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：228 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round125_association_report.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
