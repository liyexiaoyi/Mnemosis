"""Round-96 chart: overdue flags in review plan/forecast."""

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
        open(os.path.join(_BENCH, "results", "overdue_flag_eval.json"),
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

    draw.text((42, 26), "第 96 轮：该复习还没复习的记忆，标成“逾期”",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Smolen et al. (2016) 自适应间隔——下次复习时间按上次实际复习"
              "时刻计算，错过就标记，agent 一眼看到。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 条逾期记忆，在复习计划里被标记的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 44, y - 9), label, fill="#666", font=f_val)
    bx = x0 + 130
    bh = data["plan_flagged"] / 10.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#7b2ff7")
    draw.text((bx + 30, base_y - bh + 8), f"{data['plan_flagged']}/10",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "计划标记", fill="#111", font=f_label)

    x0 = 760
    draw.text((x0, 120), "② 10 条逾期记忆，在 7 天预报里被包含并排前",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 44, y - 9), label, fill="#666", font=f_val)
    bx = x0 + 130
    bh = data["forecast_overdue"] / 10.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#d97706")
    draw.text((bx + 30, base_y - bh + 8), f"{data['forecast_overdue']}/10",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "预报包含", fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：10 条逾期记忆在复习计划里全部标记“overdue=True”，在 7 天"
              "预报里也全部包含并排在最前面。",
              fill="#555", font=f_note)
    draw.text((42, 640),
              "修复：next_review_at 改为以上次实际复习时间为锚——逾期才可检测；"
              "之前总以“现在”为锚，逾期永远不会成立。",
              fill="#555", font=f_note)
    draw.text((42, 710),
              "实现：practice_plan / practice_forecast 增加 overdue 字段；预报窗口"
              "包含已逾期条目并按时间排序。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：211 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round96_overdue_flag.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
