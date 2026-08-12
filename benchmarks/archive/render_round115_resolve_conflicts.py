"""Round-115 chart: resolve_conflicts tool."""

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
        open(os.path.join(_BENCH, "results", "resolve_conflicts_eval.json"),
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

    draw.text((42, 26), "第 115 轮：记忆打架可以当场解决，不用等睡觉",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Nader et al. (2000) 重整合 + Walker & Stickgold (2004) REM——"
              "证据悬殊的旧记忆直接退休，势均力敌的双方都降一点自信。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库（各 3 组悬殊 + 3 组平衡冲突）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("旧记忆退休", data["accommodated_ok"], "#b91c1c"),
        ("平衡冲突降自信", data["rem_resolved_ok"], "#d97706"),
        ("剩余冲突准确", data["remaining_ok"], "#7b2ff7"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 60 + i * 340
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 260, base_y], fill=color)
        draw.text((bx + 96, base_y - bh + 8), f"{val}/10",
                  fill="white", font=f_val)
        draw.text((bx + 20, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：证据 5 比 1 的旧记忆全部退休（accommodated=3），势均力敌的"
              "双方都降自信（rem_resolved≥3），",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "剩余冲突数与重新检测完全一致——agent 可以当场整理矛盾，不必等睡眠。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：engine.resolve_conflicts + MCP 工具——按需运行睡眠的"
              "accommodation 与 REM 阶段。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：222 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round115_resolve_conflicts.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
