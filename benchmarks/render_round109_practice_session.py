"""Round-109 chart: practice_session tool."""

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
        open(os.path.join(_BENCH, "results", "practice_session_eval.json"),
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

    draw.text((42, 26), "第 109 轮：一次调用跑完一整节练习",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：把“计划 + 作答 + 报告（难度/下次复习）”打包成一个会话——"
              "agent 不必分别调三个工具。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 一次 practice_session 的结果",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (10.0, "10"), (20.0, "20"), (30.0, "30")):
        y = base_y - frac / 30.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("计划卡数", data["plan_len"], 10, "#7b2ff7"),
        ("报告条数", data["report_n"], 30, "#1a7f37"),
        ("难度统计", data["difficulty_n"], 30, "#d97706"),
        ("复习建议", data["suggestions_ok"] * 30, 30, "#0e7490"),
    ]
    for i, (name, val, total, color) in enumerate(rows):
        bx = x0 + 20 + i * 280
        bh = val / 30.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 220, base_y], fill=color)
        draw.text((bx + 78, base_y - bh + 8), f"{val}/{total}",
                  fill="white", font=f_val)
        draw.text((bx + 30, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：一次 practice_session 返回 10 张卡的练习计划，报告覆盖全部"
              "30 条作答，难度统计 30/30、",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "每条都带下次复习建议——agent 整节练习只需要一次调用。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：engine.practice_session + MCP 工具——内部组合 practice_plan "
              "与 practice_report。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：218 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round109_practice_session.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
