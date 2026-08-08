"""Round-62 chart: elaborative co-retrieval linking."""

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
        open(os.path.join(_BENCH, "results", "elaborative_linking_eval.json"),
             encoding="utf-8")
    )
    W, H = 1400, 800
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 62 轮：一起想起过的记忆，以后互相“带得动”",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Craik & Tulving (1975) 精加工编码 + Collins & Loftus (1975)"
              "扩散激活——同一次检索中一起出现的记忆会结成联想，想起一个就带出另一个。",
              fill="#555", font=f_sub)

    # Panel 1: linked hits
    x0 = 110
    base_y = 400
    chart_h = 230
    draw.text((x0, 120), "① 10 次“只给 A 的线索”检索里，带出关联记忆 B 的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("同现建链(新)", data["linked"]["linked_hits"], "#7b2ff7"),
        ("不建链", data["unlinked"]["linked_hits"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/10",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    # Panel 2: avg rank
    x0 = 770
    draw.text((x0, 120), "② 带出时平均排第几名（越低越好）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (1.0, "1"), (2.0, "2")):
        y = base_y - frac / 2.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 38, y - 9), label, fill="#666", font=f_val)
    rank = data["linked"]["avg_rank"]
    bx = x0 + 130
    bh = rank / 2.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#7b2ff7")
    draw.text((bx + 44, base_y - bh + 8), f"{rank:.1f}",
              fill="white", font=f_val)
    draw.text((bx - 18, base_y + 12), "同现建链(新)", fill="#111", font=f_label)
    draw.text((x0 + 330, base_y + 12), "不建链：带不出来",
              fill="#666", font=f_label)

    draw.text((42, 600),
              "怎么看：两条记忆只要在同一次检索里一起出现过，就自动结成联想；"
              "之后只给其中一条的线索，另一条也能被带出来（10/10，平均第 2 名）。"
              "不建链时 0/10。",
              fill="#555", font=f_note)
    draw.text((42, 660),
              "实现：recall 新增 elaborate_links（默认开）——一次检索中共同命中的"
              "记忆互相加 0.05 链接权重（封顶 1.0，避免图过密）；由扩散激活机制在"
              "后续检索中使用。",
              fill="#555", font=f_note)
    draw.text((42, 720),
              "回归：187 测试全过；统一回归 16 项（en88/zh200/zh10k 及 10k 系列）"
              "全部达标。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round62_elaborative_linking.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
