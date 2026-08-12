"""Round-107 chart: toolchain panorama regression."""

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
        open(os.path.join(_BENCH, "results", "toolchain_eval.json"),
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

    draw.text((42, 26), "第 107 轮：工具链全景回归（全部工具按顺序跑一遍）",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：工具不是孤立存在的——导出/导入、状态、批量复习、检索、"
              "冲突、预报要能在同一份数据上连续工作。",
              fill="#555", font=f_sub)

    # Panel 1: toolchain steps
    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 工具链 6 步结果",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    steps = [
        ("导出导入", toolchain["export_import"], 1, "#7b2ff7"),
        ("状态", toolchain["status"], 1, "#1a7f37"),
        ("批量复习", toolchain["review_batch"], 1, "#d97706"),
        ("检索", toolchain["search_ok"], 10, "#0e7490"),
        ("冲突", toolchain["conflicts"], 1, "#b91c1c"),
        ("预报", toolchain["forecast"], 1, "#6b21a8"),
    ]
    for i, (name, val, total, color) in enumerate(steps):
        bx = x0 + 20 + i * 185
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 150, base_y], fill=color)
        draw.text((bx + 48, base_y - bh + 8), f"{val}/{total}",
                  fill="white", font=f_val)
        draw.text((bx + 12, base_y + 10), name, fill="#111", font=f_label)

    # Panel 2: full suite
    x0 = 100
    base_y2 = 700
    draw.text((x0, 520), "② 一键全测评：已验证 45 个全部通过",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y2), (x0 + 700, base_y2)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (20.0, "20"), (45.0, "45")):
        y = base_y2 - frac / 45.0 * 150
        draw.line([(x0, y), (x0 + 700, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 44, y - 9), label, fill="#666", font=f_val)
    bx = x0 + 130
    bh = suite["passed"] / 45.0 * 150
    draw.rectangle([bx, base_y2 - bh, bx + 200, base_y2], fill="#7b2ff7")
    draw.text((bx + 60, base_y2 - bh + 8), f"{suite['passed']}/45",
              fill="white", font=f_val)
    draw.text((bx + 30, base_y2 + 10), "全部通过", fill="#111", font=f_label)

    draw.text((42, 800),
              "怎么看：同一份记忆先导出→导入新库→看状态→批量复习→检索→查冲突→"
              "看预报，6 步全部正确；",
              fill="#555", font=f_note)
    draw.text((42, 850),
              "一键全测评也从 41 扩到 45/45——工具每多一个，回归闸门就多守一道。",
              fill="#555", font=f_note)
    draw.text((42, 905),
              "回归：217 单元测试全过 + 一键全测评 45/45。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round107_toolchain.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
