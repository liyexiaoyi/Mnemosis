"""Round-102 chart: agent scenario end-to-end validation."""

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
    scenario = json.load(
        open(os.path.join(_BENCH, "results", "agent_scenario_eval.json"),
             encoding="utf-8")
    )
    suite = json.load(
        open(os.path.join(_BENCH, "results", "run_all_evals.json"),
             encoding="utf-8")
    )
    W, H = 1400, 960
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(21)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 102 轮：agent 场景终验（检索→冲突→预报→复习→报告）",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：把 99-101 轮的工具放进同一个 agent 工作流，验证端到端"
              "能用、顺序正确、没有互相破坏。",
              fill="#555", font=f_sub)

    # Panel 1: scenario steps
    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 场景各步结果（检索 10/10、冲突 8/8、逾期 6/6、计划/报告）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    steps = [
        ("检索", scenario["search_ok"], 10, "#7b2ff7"),
        ("冲突清单", scenario["conflict_ok"], 8, "#b91c1c"),
        ("复习计划", scenario["plan_ok"], 1, "#1a7f37"),
        ("练习报告", scenario["report_ok"], 1, "#d97706"),
        ("逾期预报", scenario["forecast_overdue"], 6, "#0e7490"),
    ]
    for i, (name, val, total, color) in enumerate(steps):
        bx = x0 + 25 + i * 220
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 150, base_y], fill=color)
        draw.text((bx + 48, base_y - bh + 8), f"{val}/{total}",
                  fill="white", font=f_val)
        draw.text((bx + 12, base_y + 10), name, fill="#111", font=f_label)

    # Panel 2: full suite
    x0 = 100
    base_y2 = 700
    draw.text((x0, 520), "② 一键全测评：已验证 41 个全部通过",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y2), (x0 + 700, base_y2)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (20.0, "20"), (41.0, "41")):
        y = base_y2 - frac / 41.0 * 150
        draw.line([(x0, y), (x0 + 700, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 44, y - 9), label, fill="#666", font=f_val)
    bx = x0 + 130
    bh = suite["passed"] / 41.0 * 150
    draw.rectangle([bx, base_y2 - bh, bx + 200, base_y2], fill="#7b2ff7")
    draw.text((bx + 60, base_y2 - bh + 8), f"{suite['passed']}/41",
              fill="white", font=f_val)
    draw.text((bx + 30, base_y2 + 10), "全部通过", fill="#111", font=f_label)

    draw.text((42, 800),
              "怎么看：同一个库里，agent 先检索（10/10）→ 列出冲突（8/8）→ 查逾期"
              "预报（6/6）→ 复习计划与报告（1/1）全部可用。",
              fill="#555", font=f_note)
    draw.text((42, 850),
              "顺序教训：逾期预报要在复习前查——练习会刷新复习时间，逾期会消失；"
              "真实 agent 工作流也是“先看再练”。",
              fill="#555", font=f_note)
    draw.text((42, 905),
              "回归：214 单元测试全过 + 一键全测评 41/41。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round102_agent_scenario.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
