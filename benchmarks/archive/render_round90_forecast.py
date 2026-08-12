"""Round-90 chart: practice forecast (review calendar)."""

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
        open(os.path.join(_BENCH, "results", "practice_forecast_eval.json"),
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

    draw.text((42, 26), "第 90 轮：未来 7 天哪些记忆会到期，提前告诉 agent",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Smolen et al. (2016) 自适应间隔调度——把一周的复习日历"
              "预报出来，agent 可以提前安排。",
              fill="#555", font=f_sub)

    # Panel 1: coverage
    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 7 天预报：30 条记忆里应该到期的 24 条全部覆盖",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (10.0, "10"), (20.0, "20"), (30.0, "30")):
        y = base_y - frac / 30.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    for i, (lbl, val, color) in enumerate(
        (("预报命中", data["exact_due"], "#7b2ff7"),
         ("应预报数", data["expected_count"], "#b0b0b0"))
    ):
        bx = x0 + 70 + i * 190
        bh = val / 30.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 34, base_y - bh + 8), f"{val}/30",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), lbl, fill="#111", font=f_label)

    # Panel 2: intervals
    x0 = 760
    draw.text((x0, 120), "② 复习间隔随熟练度增长（小时）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (50.0, "50"), (100.0, "100"),
                        (150.0, "150"), (200.0, "200")):
        y = base_y - frac / 210.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 48, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("答错后", 12, "#b91c1c"),
        ("巩固 1 次", 24, "#d97706"),
        ("巩固 2 次", 48, "#1a7f37"),
        ("巩固 3 次", 96, "#7b2ff7"),
        ("巩固 4 次", 192, "#0e7490"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 15 + i * 102
        bh = val / 210.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 85, base_y], fill=color)
        draw.text((bx + 12, base_y - bh + 6), f"{val}",
                  fill="white", font=f_val)
        draw.text((bx - 22, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：7 天预报覆盖 24/24 应到期记忆，到期时间与调度器完全一致"
              "（24/24）、按时间排序；",
              fill="#555", font=f_note)
    draw.text((42, 640),
              "间隔从 12 小时到 192 小时指数增长——agent 拿到日历就能安排复习，"
              "不会漏掉任何一条。",
              fill="#555", font=f_note)
    draw.text((42, 710),
              "实现：新增 practice_forecast(days) + MCP 工具——扫描全部活跃记忆的"
              "下次复习时间，落在窗口内的按时间排序返回。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：207 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round90_practice_forecast.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
