"""Round-121 chart: cleanup_preview tool."""

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
        open(os.path.join(_BENCH, "results", "cleanup_preview_eval.json"),
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

    draw.text((42, 26), "第 121 轮：清理记忆前先预览，不删任何东西",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：睡眠修剪会回收“不重要+没访问+很旧”的事件记忆；把这份名单"
              "先给 agent 看，确认后再动手。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库，3 项检查",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("候选数正确", data["count_ok"], "#7b2ff7"),
        ("未删除任何条", data["intact_ok"], "#1a7f37"),
        ("字段齐全", data["fields_ok"], "#d97706"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 60 + i * 340
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 260, base_y], fill=color)
        draw.text((bx + 96, base_y - bh + 8), f"{val}/10",
                  fill="white", font=f_val)
        draw.text((bx + 20, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：预览正好列出 3 条“该回收”的旧琐碎事件，重要/访问过/"
              "语义记忆都不在名单里，",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "预览后活跃数一条没少——先看再删，删除权仍留给 agent。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：engine.cleanup_preview + MCP 工具——复用睡眠修剪规则，"
              "只返回候选不删除。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：226 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round121_cleanup_preview.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
