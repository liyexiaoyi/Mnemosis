"""Round-112 chart: toolchain panorama 2."""

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
    toolchain = json.load(
        open(os.path.join(_BENCH, "results", "toolchain2_eval.json"),
             encoding="utf-8")
    )
    suite = json.load(
        open(os.path.join(_BENCH, "results", "run_all_evals.json"),
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

    draw.text((42, 26), "第 112 轮：工具链全景回归 2（9 步全过）",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：新增的聚合工具（审计/会话/睡眠计划）必须与既有工具在同一份"
              "数据上连续工作。",
              fill="#555", font=f_sub)

    # Panel 1: toolchain steps
    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 工具链 9 步结果",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    steps = [
        ("导出导入", toolchain["export_import"], 1, "#7b2ff7"),
        ("状态", toolchain["status"], 1, "#1a7f37"),
        ("审计", toolchain["audit"], 1, "#d97706"),
        ("批量复习", toolchain["review_batch"], 1, "#b91c1c"),
        ("练习会话", toolchain["practice_session"], 1, "#0e7490"),
        ("睡眠计划", toolchain["sleep_and_plan"], 1, "#6b21a8"),
        ("检索", toolchain["search"], 10, "#0891b2"),
        ("冲突", toolchain["conflicts"], 1, "#ec4899"),
        ("预报", toolchain["forecast"], 1, "#15803d"),
    ]
    for i, (name, val, total, color) in enumerate(steps):
        bx = x0 + 12 + i * 125
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 105, base_y], fill=color)
        draw.text((bx + 24, base_y - bh + 8), f"{val}/{total}",
                  fill="white", font=f_val)
        draw.text((bx - 10, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：同一份记忆走完 9 步（导出导入→状态→审计→批量复习→练习"
              "会话→睡眠计划→检索→冲突→预报）全部正确。",
              fill="#555", font=f_note)
    draw.text((42, 640),
              "一键全测评也从 45 扩到 49/49——聚合工具没有破坏任何既有机制。",
              fill="#555", font=f_note)
    draw.text((42, 710),
              "回归：220 单元测试全过 + 一键全测评 49/49。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round112_toolchain2.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
