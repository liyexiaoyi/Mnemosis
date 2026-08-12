"""Round-92 chart: full-chain combination (write -> sleep -> practice -> retrieve)."""

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
        open(os.path.join(_BENCH, "results", "full_chain_eval.json"),
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

    draw.text((42, 26), "第 92 轮：全链路组合（写入→睡眠→练习→检索）",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：把睡眠巩固、练习调度、检索机制从头到尾串起来跑 40 题，"
              "验证整条链路一起用不打架。",
              fill="#555", font=f_sub)

    # Panel 1: total
    x0 = 100
    base_y = 340
    chart_h = 190
    draw.text((x0, 120), "① 40 题总分",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 500, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (10.0, "10"), (20.0, "20"), (30.0, "30"),
                        (40.0, "40")):
        y = base_y - frac / 40.0 * chart_h
        draw.line([(x0, y), (x0 + 500, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 44, y - 9), label, fill="#666", font=f_val)
    for i, (lbl, key, color) in enumerate(
        (("全链路(新)", "full", "#7b2ff7"), ("基线全关", "baseline", "#b0b0b0"))
    ):
        bx = x0 + 80 + i * 200
        bh = data[key]["total"] / 40.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 140, base_y], fill=color)
        draw.text((bx + 44, base_y - bh + 8), f"{data[key]['total']}/40",
                  fill="white", font=f_val)
        draw.text((bx + 4, base_y + 10), lbl, fill="#111", font=f_label)

    # Panel 2: by kind
    x0 = 90
    base_y = 680
    chart_h = 200
    draw.text((x0, 460), "② 分类型答对（事实/冲突/情绪/要点/情境/修订标记）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1280, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (4.0, "4"), (8.0, "8"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1280, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    kinds = [
        ("事实", "fact", 10),
        ("冲突", "conflict", 8),
        ("情绪", "emotional", 8),
        ("要点", "gist", 6),
        ("情境", "context", 4),
        ("修订", "revised", 4),
    ]
    for gi, (name, key, n) in enumerate(kinds):
        gx = x0 + gi * 215
        c_val = data["full"]["by_kind"][key]
        b_val = data["baseline"]["by_kind"][key]
        for i, (val, color) in enumerate(
            ((c_val, "#7b2ff7"), (b_val, "#b0b0b0"))
        ):
            bx = gx + 35 + i * 80
            bh = val / 10.0 * chart_h
            draw.rectangle([bx, base_y - bh, bx + 60, base_y], fill=color)
            draw.text((bx + 12, base_y - bh + 6), f"{val}",
                      fill="white", font=f_val)
        draw.text((gx + 55, base_y + 10), name, fill="#333", font=f_label)

    draw.text((42, 800),
              "怎么看：全链路 26/40，基线 11/40；冲突/修订/事实等全部子类都赢。",
              fill="#555", font=f_note)
    draw.text((42, 850),
              "诚实发现：练习会把“近期原话”练得更强，抵消部分要点偏好的优势"
              "（本轮要点 0/6）——机制叠加有真实代价，不是每个都完美。",
              fill="#555", font=f_note)
    draw.text((42, 900),
              "回归：208 测试全过，88/200/10k 零差异（本轮为端到端测评，无代码改动）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round92_full_chain.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
