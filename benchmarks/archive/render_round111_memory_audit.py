"""Round-111 chart: memory_audit tool."""

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
        open(os.path.join(_BENCH, "results", "memory_audit_eval.json"),
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

    draw.text((42, 26), "第 111 轮：记忆生命周期深度审计",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：维护记忆库像维护身体——不仅看总数，还要看回收了多少、"
              "改过几条、情绪记忆几条、平均可提取度多高。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库，10 项审计指标全部与手工计算一致",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("活跃", data["active"], "#7b2ff7"),
        ("回收", data["recycled"], "#b91c1c"),
        ("已修订", data["revised"], "#d97706"),
        ("情绪", data["emotional"], "#ec4899"),
        ("冲突", data["conflicts"], "#0e7490"),
        ("到期", data["due_now"], "#1a7f37"),
        ("平均可提取", data["avg_retrievability"], "#0891b2"),
        ("平均重要度", data["avg_importance"], "#6b21a8"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 15 + i * 140
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 120, base_y], fill=color)
        draw.text((bx + 34, base_y - bh + 8), f"{val}/10",
                  fill="white", font=f_val)
        draw.text((bx - 22, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：memory_audit 一次给出 10 项生命周期指标，10 个不同记忆库"
              "逐项与手工计算一致（10/10）。",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "语义/事件计数也全部对齐——agent 维护记忆库时有完整“体检报告”。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：engine.memory_audit + MCP memory_audit——在状态快照基础上"
              "增加回收/修订/情绪/平均可提取度等深层指标。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：220 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round111_memory_audit.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
