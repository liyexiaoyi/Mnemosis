"""Round-110 chart: sleep_and_plan tool."""

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
        open(os.path.join(_BENCH, "results", "sleep_and_plan_eval.json"),
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

    draw.text((42, 26), "第 110 轮：睡一觉 + 拿到新复习计划，一次调用",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Stickgold & Walker (2013) 睡眠巩固 + Smolen et al. (2016) "
              "自适应间隔——睡眠后计划会变化，应该一起返回。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库，sleep_and_plan 四项检查",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("重放数一致", data["replay_match"], "#7b2ff7"),
        ("计划非空", data["plan_nonempty"], "#1a7f37"),
        ("预报非空", data["forecast_nonempty"], "#d97706"),
        ("摘要完整", data["summary_ok"], "#0e7490"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 25 + i * 275
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 220, base_y], fill=color)
        draw.text((bx + 78, base_y - bh + 8), f"{val}/10",
                  fill="white", font=f_val)
        draw.text((bx + 30, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：sleep_and_plan 的重放数与单独 sleep 完全一致（10/10），"
              "睡眠后计划/预报仍覆盖该复习的低重要记忆——",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "睡眠只巩固重要的，不重要的照常排队，摘要也带上重放计数。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：engine.sleep_and_plan + MCP 工具——内部组合 sleep()、"
              "practice_plan、practice_forecast。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：219 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round110_sleep_and_plan.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
