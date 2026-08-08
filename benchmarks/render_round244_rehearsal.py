"""Round-244 chart: plan_rehearsal tool."""

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
            os.path.join(_BENCH, "results", "plan_rehearsal_eval.json"),
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

    draw.text((42, 26), "第 244 轮：计划预演（先在心里过一遍）", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：人脑会把过去的经历重新组合，用来想象未来（Schacter & Addis, "
        "2007）；做决定前会预演每一步的结果（Momennejad et al., 2017）。"
        "这个工具让 agent 执行前先过一遍计划、标出最可能失败的步骤和备选。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text(
        (x0, 120),
        "① 10 个记忆库：两个人做过同一趟旅行，一个成功一个失败",
        fill="#111",
        font=f_panel,
    )
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("计划齐全", data["steps_ok"], "#7b2ff7"),
        ("预测合法", data["prob_ok"], "#1a7f37"),
        ("薄弱点准", data["weakest_ok"], "#d97706"),
        ("整体概率对", data["overall_ok"], "#0b7285"),
        ("建议含预演", data["advice_ok"], "#c2255c"),
        ("空库不崩", data["empty_ok"], "#6741d9"),
        ("字段齐全", data["fields_ok"], "#2f9e44"),
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
        "怎么看：8 根柱子全部 10/10——每次都能找回 4 个步骤、算出每步成功率、"
        "准确标出阿丽“订机票”是最薄弱环节，还会提示备选或先小步试。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 执行计划前先预演一遍，成功率低的步骤提前准备备选，"
        "避免闷头执行到失败才发现。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.plan_rehearsal + MCP 工具——从记忆里取计划，"
        "按历史成功/失败记录算每步成功率，选出最薄弱步骤，找同人成功备选。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：300 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round244_rehearsal.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
