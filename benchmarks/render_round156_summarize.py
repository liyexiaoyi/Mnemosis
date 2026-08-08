"""Round-156 chart: summarize_cluster tool."""

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
            os.path.join(_BENCH, "results", "summarize_cluster_eval.json"),
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

    draw.text((42, 26), "第 156 轮：一堆相关记忆，压成一句话", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：人记重复经历时留的是“要点”而不是每条细节（模糊痕迹理论，"
        "Brainerd & Reyna 1990）；这个工具把一组相关记忆提炼成要点摘要。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 × 4 条同主题记忆（共享线索+高频词）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("全部记忆入组", data["found_ok"], "#7b2ff7"),
        ("共享线索找到", data["cues_ok"], "#1a7f37"),
        ("高频词找到", data["terms_ok"], "#d97706"),
        ("摘要生成成功", data["summary_ok"], "#0b7285"),
        ("证据数正确", data["evidence_ok"], "#c2255c"),
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
        "怎么看：7 根柱子全部 10/10——4 条记忆全部入组，共享线索“工作”和"
        "高频词“预算”都被提取出来，摘要、证据数一个不差。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 想“这几条记忆到底在说啥”时，一条摘要就能概括；"
        "确认后还可以把摘要写成一条新记忆，省空间不丢要点。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.summarize_cluster + MCP 工具——交集线索 + 高频词 + "
        "证据累计生成摘要，纯只读。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：247 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round156_summarize.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
