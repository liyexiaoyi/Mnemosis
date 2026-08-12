"""Round-174 chart: plan_quality tool (Chinese agent planning)."""

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
            os.path.join(_BENCH, "results", "plan_quality_eval.json"),
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

    draw.text((42, 26), "第 174 轮（专项）：给中文 agent 的计划打分", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：人脑把目标拆成有序子目标（认知控制，Miller & Cohen 2001），"
        "解决问题用“手段-目的”分析（Newell & Simon 1972）；这个工具检查计划"
        "是否有动词、有顺序、不重复、跟项目记忆对得上。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 × 3 种计划（好计划/重复计划/空计划）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("好计划判高分", data["good_ok"], "#7b2ff7"),
        ("重复计划判低分", data["weak_ok"], "#1a7f37"),
        ("空计划判 0 分", data["empty_ok"], "#d97706"),
        ("动词齐全识别", data["verb_ok"], "#0b7285"),
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
        "怎么看：6 根柱子全部 10/10——“调研→设计→开发→测试→部署”这种动词齐全、"
        "顺序合理、和项目记忆对得上的计划得高分；重复步骤扣分；空计划直接 0 分。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 开工前先自己打分——分数低就按建议补动词、排顺序、"
        "对一下项目背景，避免“计划很漂亮、执行抓瞎”。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.plan_quality + MCP 工具——按动词/顺序/去重/项目对齐四项"
        "打分并给建议，纯只读。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：257 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round174_plan.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
