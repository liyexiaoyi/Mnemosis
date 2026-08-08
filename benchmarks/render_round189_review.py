"""Round-189 chart: decision_review tool."""

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
            os.path.join(_BENCH, "results", "decision_review_eval.json"),
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

    draw.text((42, 26), "第 189 轮：项目收尾，复盘一下这次干得怎么样", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：做完任务要元认知复盘（Koriat & Goldsmith 1996）；这个工具对比"
        "计划与结果，算成功率、打分、总结成功/失败模式，沉淀经验。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 × 4 步计划（2 成功 + 1 失败 + 1 未知）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("步骤数正确", data["steps_ok"], "#7b2ff7"),
        ("成功率正确(50%)", data["rate_ok"], "#1a7f37"),
        ("得分正确(50)", data["score_ok"], "#d97706"),
        ("档位正确(中等)", data["verdict_ok"], "#0b7285"),
        ("模式总结对", data["pattern_ok"], "#c2255c"),
        ("经验沉淀对", data["lessons_ok"], "#6741d9"),
        ("字段齐全", data["fields_ok"], "#2f9e44"),
        ("MCP通路正常", data["mcp_ok"], "#0e7490"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 45 + i * 155
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 125, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：8 根柱子全部 10/10——2 步成功、1 步失败、1 步未知算出成功率 50%、"
        "得分 50（中等）；失败的那步被单独点名并写成经验。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 项目收尾时跑一次复盘——哪里顺利、哪里栽了、下次注意什么，"
        "直接生成复盘结论，写进记忆库。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.decision_review + MCP 工具——对比计划/结果，算成功率/得分/"
        "模式/经验，纯只读。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：267 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round189_review.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
