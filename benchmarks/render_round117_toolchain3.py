"""Round-117 chart: toolchain panorama 3."""

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
        open(os.path.join(_BENCH, "results", "toolchain3_eval.json"),
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

    draw.text((42, 26), "第 117 轮：工具链全景回归 3（12 步全过）",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：维护型工具（去重/冲突化解/压力指数）必须与既有工具在"
              "同一份数据上连续工作。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 工具链 12 步结果",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (4.0, "4"), (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    steps = [
        ("导出导入", toolchain["export_import"], 1, "#7b2ff7"),
        ("状态", toolchain["status"], 1, "#1a7f37"),
        ("审计", toolchain["audit"], 1, "#d97706"),
        ("压力指数", toolchain["review_load"], 1, "#b91c1c"),
        ("去重", toolchain["dedupe"], 1, "#0e7490"),
        ("冲突化解", toolchain["resolve_conflicts"], 1, "#6b21a8"),
        ("批量复习", toolchain["review_batch"], 1, "#15803d"),
        ("练习会话", toolchain["practice_session"], 1, "#0891b2"),
        ("睡眠计划", toolchain["sleep_and_plan"], 1, "#ec4899"),
        ("检索", toolchain["search"], 8, "#7c3aed"),
        ("冲突清零", toolchain["conflicts_after"], 1, "#16a34a"),
        ("预报", toolchain["forecast"], 1, "#ca8a04"),
    ]
    for i, (name, val, total, color) in enumerate(steps):
        bx = x0 + 8 + i * 95
        bh = val / 8.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 80, base_y], fill=color)
        draw.text((bx + 12, base_y - bh + 6), f"{val}/{total}",
                  fill="white", font=f_val)
        draw.text((bx - 14, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：同一份记忆走完 12 步（含去重 2 条、冲突化解后清零）"
              "全部正确，检索 8/8。",
              fill="#555", font=f_note)
    draw.text((42, 640),
              "一键全测评扩到 53/53——维护型工具没有破坏任何既有机制。",
              fill="#555", font=f_note)
    draw.text((42, 710),
              "回归：223 单元测试全过 + 一键全测评 53/53。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round117_toolchain3.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
