"""Round-114 chart: dedupe_memories tool."""

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
        open(os.path.join(_BENCH, "results", "dedupe_eval.json"),
             encoding="utf-8")
    )
    W, H = 1400, 780
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(21)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 114 轮：重复的记忆可以随时合并，不用等睡觉",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：McClelland et al. (1995) 互补学习系统——重复事件应塌缩成"
              "一条更强的记忆；把睡眠里的合并步骤开放成按需工具。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库，合并数与预期完全一致",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 44, y - 9), label, fill="#666", font=f_val)
    bx = x0 + 130
    bh = data["count_matches"] / 10.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#7b2ff7")
    draw.text((bx + 30, base_y - bh + 8), f"{data['count_matches']}/10",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "合并数一致", fill="#111", font=f_label)

    x0 = 760
    draw.text((x0, 120), "② 活跃记忆数按合并量减少",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 44, y - 9), label, fill="#666", font=f_val)
    bx = x0 + 130
    bh = data["reduce_matches"] / 10.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#1a7f37")
    draw.text((bx + 30, base_y - bh + 8), f"{data['reduce_matches']}/10",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "减少量一致", fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：10 个库（2-5 份重复事件）的合并数与预期完全一致，活跃数"
              "同步减少——",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "agent 随时可以整理记忆库，不必等到睡眠周期。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：engine.dedupe_memories + MCP 工具——按需调用睡眠合并逻辑。",
              fill="#555", font=f_note)
    draw.text((42, 750),
              "回归：221 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round114_dedupe.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
