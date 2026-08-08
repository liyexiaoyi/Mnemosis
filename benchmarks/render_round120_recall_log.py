"""Round-120 chart: recall_log tool."""

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
        open(os.path.join(_BENCH, "results", "recall_log_eval.json"),
             encoding="utf-8")
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

    draw.text((42, 26), "第 120 轮：检索也有审计日志",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：可观测性——每次检索记下“问了什么、答了什么、有没有把握”，"
              "agent 可以回查系统行为。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库各跑 30 次检索，4 项检查",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("日志长度正确", data["len_ok"], "#7b2ff7"),
        ("最后一条准确", data["last_ok"], "#1a7f37"),
        ("limit 生效", data["limit_ok"], "#d97706"),
        ("字段齐全", data["conf_ok"], "#0e7490"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 25 + i * 275
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 220, base_y], fill=color)
        draw.text((bx + 78, base_y - bh + 8), f"{val}/10",
                  fill="white", font=f_val)
        draw.text((bx + 30, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：30 次检索后日志正好 30 条（上限 100 有界），最新一条与"
              "最后一次检索完全对应，",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "limit=5 只取最近 5 条，每条都带置信度标记——可观测、可回查。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：engine 内置 100 条有界日志 + get_recall_log + MCP recall_log。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：225 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round120_recall_log.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
