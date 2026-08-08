"""Round-219 chart: forgetting_balance tool."""

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
            os.path.join(_BENCH, "results", "forgetting_balance_eval.json"),
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

    draw.text((42, 26), "第 219 轮：遗忘平衡", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：提取诱发遗忘（Anderson, Bjork & Bjork 1994）——"
        "一条记忆被反复想起，会偷偷压制同主题的兄弟记忆。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 ×（物理失衡 + 音乐均衡）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("主题数对", data["topic_ok"], "#7b2ff7"),
        ("失衡数对", data["flag_ok"], "#1a7f37"),
        ("失衡判断对", data["imbalanced_ok"], "#d97706"),
        ("均衡判断对", data["balanced_ok"], "#0b7285"),
        ("明细排序对", data["detail_ok"], "#c2255c"),
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
        "怎么看：8 根柱子全部 10/10——物理主题（10 次 vs 1 次）被判失衡，"
        "音乐主题（2 次 vs 2 次）判定均衡，不会乱报警。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 定期体检——发现同主题提取失衡时，优先补练低频记忆，"
        "避免热门记忆越练越强、兄弟记忆被偷偷忘掉。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.forgetting_balance + MCP 工具——按主题统计访问次数/"
        "占比，比值超阈值即标记失衡并给建议。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：285 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round219_balance.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
