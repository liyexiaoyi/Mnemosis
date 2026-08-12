"""Round-72 chart: recall confidence flag (metacognitive hedging)."""

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
        open(os.path.join(_BENCH, "results", "confidence_flag_eval.json"),
             encoding="utf-8")
    )
    W, H = 1400, 780
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 72 轮：检索结果自带“我有把握/我不确定”标记",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Koriat & Goldsmith (1996) 元认知监控——系统知道自己记不牢时"
              "要告诉 agent：答案模糊时别硬答。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 6 个“答案明确”的问题，被正确标成有把握的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6")):
        y = base_y - frac / 6.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    bx = x0 + 110
    bh = 6 / 6.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#7b2ff7")
    draw.text((bx + 42, base_y - bh + 8), "6/6", fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "明确答案", fill="#111", font=f_label)

    x0 = 760
    draw.text((x0, 120), "② 6 个“答案模糊”的问题，被正确标成不确定的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6")):
        y = base_y - frac / 6.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    ambiguous = data["ambiguous"]["confident_flags"]
    bx = x0 + 110
    bh = (6 - ambiguous) / 6.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#d97706")
    draw.text((bx + 42, base_y - bh + 8), f"{6 - ambiguous}/6",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "模糊答案", fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：明确答案（第一名分差 ≥0.03、分数 ≥0.45）标记“有把握”6/6；"
              "完全平局的模糊答案 6/6 标记“不确定”，",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "并注明“低置信(与次选差距小)”——agent 拿到这个标记就知道该说"
              "“我不太确定”而不是硬编答案。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：RecallResult 新增 confident 字段；recall 自动计算第一名绝对分与"
              "和次选的差距，给 top-1 打标。",
              fill="#555", font=f_note)
    draw.text((42, 750),
              "回归：195 测试全过，88/200/10k 零差异（只加标记，不改排序）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round72_confidence_flag.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
