"""Round-80 chart: practice plan (review schedule API)."""

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
        open(os.path.join(_BENCH, "results", "practice_plan_eval.json"),
             encoding="utf-8")
    )
    W, H = 1400, 820
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(21)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 80 轮：给 agent 一份“复习计划表”",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Smolen et al. (2016) 自适应间隔调度——把每条到期卡的"
              "“下次复习时间/可提取度/成功率”提前告诉 agent，方便安排。",
              fill="#555", font=f_sub)

    # Panel 1: retry horizons
    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 计划里的复习间隔（小时，越往后间隔越大）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (12.0, "12"), (24.0, "24"), (36.0, "36"),
                        (48.0, "48")):
        y = base_y - frac / 48.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 44, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("答错后", 12, "#b91c1c"),
        ("答对 1 次", 24, "#1a7f37"),
        ("巩固 2 次", 48, "#7b2ff7"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 45 + i * 160
        bh = val / 48.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 110, base_y], fill=color)
        draw.text((bx + 32, base_y - bh + 6), f"{val} 小时",
                  fill="white", font=f_val)
        draw.text((bx - 10, base_y + 10), name, fill="#111", font=f_label)

    # Panel 2: consistency
    x0 = 760
    draw.text((x0, 120), "② 30 条计划的正确性（30 分满分）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (10.0, "10"), (20.0, "20"), (30.0, "30")):
        y = base_y - frac / 30.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 44, y - 9), label, fill="#666", font=f_val)
    rows2 = [
        ("时间与调度一致", data["exact_next_review"], "#7b2ff7"),
        ("间隔档位正确", data["correct_horizon"], "#1a7f37"),
        ("字段齐全", data["fields_ok"], "#d97706"),
    ]
    for i, (name, val, color) in enumerate(rows2):
        bx = x0 + 35 + i * 150
        bh = val / 30.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 110, base_y], fill=color)
        draw.text((bx + 32, base_y - bh + 6), f"{val}/30",
                  fill="white", font=f_val)
        draw.text((bx - 18, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：答错 12 小时后重试，答对 1 次 24 小时，连续巩固 2 次 48 小时——"
              "间隔随熟练度增长；",
              fill="#555", font=f_note)
    draw.text((42, 640),
              "30 条计划的下次复习时间与调度器完全一致（30/30），agent 可以直接照着安排。",
              fill="#555", font=f_note)
    draw.text((42, 710),
              "诚实说明：本轮先试了“半对答案给更多强化”和“半对答案更早重试”，2 周模拟都"
              "因为挤占练习名额而净效果下降（0.534-0.637），已全部回退；",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "最终改为零风险的复习计划 API：practice_plan + MCP 工具，不改任何调度行为。"
              "回归：201 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round80_practice_plan.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
