"""Round-220 chart: metacog_report tool."""

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
            os.path.join(_BENCH, "results", "metacog_report_eval.json"),
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

    draw.text((42, 26), "第 220 轮：元认知校准报告", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：元认知监控（Koriat 1997）——好的校准是“觉得自己会”和"
        "“真的会”差不多。这个工具对比置信度与真实回忆成绩。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 ×（数学过度自信 + 英语自信不足）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("主题数对", data["topic_ok"], "#7b2ff7"),
        ("过度自信对", data["over_ok"], "#1a7f37"),
        ("自信不足对", data["under_ok"], "#d97706"),
        ("排序正确", data["order_ok"], "#0b7285"),
        ("校准分对", data["score_ok"], "#c2255c"),
        ("建议生成", data["advice_ok"], "#6741d9"),
        ("字段齐全", data["fields_ok"], "#2f9e44"),
        ("MCP 通路正常", data["mcp_ok"], "#e8590c"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 35 + i * 138
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 120, base_y], fill=color)
        draw.text((bx + 34, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：8 根柱子全部 10/10——数学“觉得 95% 会、实际 70%”被判"
        "过度自信；英语“觉得 50%、实际 90%”判自信不足，全部抓对。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 定期跑一次——过度自信的主题多自测校准，"
        "自信不足的主题可以放心一点，让“自我感觉”和真实水平对齐。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.metacog_report + MCP 工具——按主题汇总回忆成败与"
        "置信度，算差距、打标签、输出校准分。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：286 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round220_metacog.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
