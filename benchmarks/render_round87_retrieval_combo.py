"""Round-87 chart: retrieval-side combination validation."""

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
        open(os.path.join(_BENCH, "results", "retrieval_combo_eval.json"),
             encoding="utf-8")
    )
    W, H = 1450, 940
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(21)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 26), "第 87 轮：检索机制全开，30 题混合集 30/30",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：把 84-86 轮与既有检索机制（要点/情绪/情境/印证等）放在同一个"
              "记忆库里验证叠加——组合不能互相打架。",
              fill="#555", font=f_sub)

    # Panel 1: total
    x0 = 100
    base_y = 340
    chart_h = 190
    draw.text((x0, 120), "① 30 题混合集答对总数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 500, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (10.0, "10"), (20.0, "20"), (30.0, "30")):
        y = base_y - frac / 30.0 * chart_h
        draw.line([(x0, y), (x0 + 500, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    for i, (lbl, key, color) in enumerate(
        (("组合全开", "combined", "#7b2ff7"), ("基线全关", "baseline", "#b0b0b0"))
    ):
        bx = x0 + 80 + i * 200
        bh = data[key]["total"] / 30.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 140, base_y], fill=color)
        draw.text((bx + 44, base_y - bh + 8), f"{data[key]['total']}/30",
                  fill="white", font=f_val)
        draw.text((bx + 4, base_y + 10), lbl, fill="#111", font=f_label)

    # Panel 2: by kind
    x0 = 90
    base_y = 680
    chart_h = 200
    draw.text((x0, 460), "② 分类型答对（印证/要点/情绪/情境/复核/普通）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1280, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6")):
        y = base_y - frac / 6.0 * chart_h
        draw.line([(x0, y), (x0 + 1280, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    kinds = [
        ("印证", "corroboration", 6),
        ("要点", "gist", 4),
        ("情绪", "emotional", 4),
        ("情境", "context", 4),
        ("复核", "second_look", 6),
        ("普通", "plain", 6),
    ]
    for gi, (name, key, n) in enumerate(kinds):
        gx = x0 + gi * 215
        c_val = data["combined"]["by_kind"][key]
        b_val = data["baseline"]["by_kind"][key]
        for i, (val, color) in enumerate(
            ((c_val, "#7b2ff7"), (b_val, "#b0b0b0"))
        ):
            bx = gx + 35 + i * 80
            bh = val / 6.0 * chart_h
            draw.rectangle([bx, base_y - bh, bx + 60, base_y], fill=color)
            draw.text((bx + 12, base_y - bh + 6), f"{val}",
                      fill="white", font=f_val)
        draw.text((gx + 55, base_y + 10), name, fill="#333", font=f_label)

    draw.text((42, 800),
              "怎么看：组合全开 30/30，基线全关只有 7/30（普通题 6 题 + 情境蒙对 1 题）；"
              "每个机制子类组合都赢。",
              fill="#555", font=f_note)
    draw.text((42, 850),
              "结论：检索侧机制可以安全叠加——它们作用在排序/标记上，不像练习侧强化"
              "会互相抢名额（对比第 82 轮的调度组合结论）。",
              fill="#555", font=f_note)
    draw.text((42, 905),
              "回归：205 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round87_retrieval_combo.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
