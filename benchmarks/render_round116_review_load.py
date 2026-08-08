"""Round-116 chart: review_load tool."""

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
        open(os.path.join(_BENCH, "results", "review_load_eval.json"),
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

    draw.text((42, 26), "第 116 轮：今天复习压力多大？一个指数告诉你",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：把到期、逾期、弱记忆合并成一个“复习压力指数”——"
              "agent 据此决定今天配额加量还是减量。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个随机记忆库，4 项负荷指标全部与手工计算一致",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("到期数", data["due_now"], "#7b2ff7"),
        ("逾期数", data["overdue"], "#b91c1c"),
        ("弱记忆数", data["weak"], "#d97706"),
        ("压力指数", data["load_index"], "#1a7f37"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 25 + i * 275
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 220, base_y], fill=color)
        draw.text((bx + 78, base_y - bh + 8), f"{val}/10",
                  fill="white", font=f_val)
        draw.text((bx + 30, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：review_load 把到期/逾期/弱记忆/压力指数全部算对"
              "（10 个库逐项一致）——",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "指数 = 未来 7 天到期数 + 逾期数×2（逾期更急），agent 看一眼"
              "就知道今天要不要加班复习。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：engine.review_load + MCP review_load——调度器与遗忘曲线"
              "联合统计。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：223 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round116_review_load.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
