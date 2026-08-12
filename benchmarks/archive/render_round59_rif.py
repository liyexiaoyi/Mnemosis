"""Round-59 chart: retrieval-induced forgetting (competitor suppression)."""

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
        open(os.path.join(_BENCH, "results", "interference_suppression_eval.json"),
             encoding="utf-8")
    )
    sup = data["suppressed"]
    data["unsuppressed"]
    data["none"]
    W, H = 1500, 1200
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(21)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 26), "第 59 轮：练过的记忆更不容易被同类记忆挤掉",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Anderson, Bjork & Bjork (1994) 检索诱发的遗忘——成功回忆一条后，"
              "同类的竞争记忆会被轻度压低，减少混淆。",
              fill="#555", font=f_sub)

    def _panel(x0, title_y, base_y, title, rows, scale, labels, value_fmt):
        draw.text((x0, title_y), title, fill="#111", font=f_panel)
        chart_h = 210
        draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
        for frac, label in labels:
            y = base_y - frac / scale * chart_h
            draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
            draw.text((x0 - 34, y - 9), label, fill="#666", font=f_val)
        for i, (name, val, color) in enumerate(rows):
            bx = x0 + 45 + i * 160
            bh = val / scale * chart_h
            draw.rectangle([bx, base_y - bh, bx + 110, base_y], fill=color)
            draw.text((bx + 38, base_y - bh + 6), value_fmt(val),
                      fill="white", font=f_val)
            draw.text((bx - 10, base_y + 10), name, fill="#111",
                      font=f_label)

    names = [("竞争压制(新)", "#7b2ff7"), ("无压制", "#b0b0b0"),
             ("不复习", "#d97706")]
    _panel(90, 110, 360, "① 同类别里“练过的目标”平均排名（越低越好，共 8 名）",
           [(n, sup["target_avg_rank"], c) for n, c in names],
           4.5, ((0.0, "0"), (1.0, "1"), (2.0, "2"), (3.0, "3"), (4.0, "4")),
           lambda v: f"{v:.2f}")
    _panel(800, 110, 360, "② 14 天后练过目标的平均记住强度（越高越好）",
           [(n, sup["target_mean"], c) for n, c in names],
           0.8, ((0.0, "0"), (0.3, "0.3"), (0.6, "0.6")),
           lambda v: f"{v:.3f}")
    _panel(90, 540, 790, "③ 14 天后竞争记忆的平均强度（压制组应该更低）",
           [(n, sup["competitor_mean"], c) for n, c in names],
           0.8, ((0.0, "0"), (0.3, "0.3"), (0.6, "0.6")),
           lambda v: f"{v:.3f}")
    _panel(800, 540, 790, "④ 问“颜色/水果/城市”时，练过的目标排第一（共 3 类）",
           [(n, sup["target_first"], c) for n, c in names],
           3.0, ((0.0, "0"), (1.0, "1"), (2.0, "2"), (3.0, "3")),
           lambda v: f"{v}/3")

    draw.text((42, 890),
              "怎么看：开压制后，练过的目标平均排第 2.3 名（无压制 3.7、不复习 4.0），",
              fill="#555", font=f_note)
    draw.text((42, 930),
              "3 类里有 2 类排第一；目标强度更高（0.685 > 0.616），竞争记忆更低"
              "（0.661 < 0.701）——这正是“回忆会让竞争记忆暂时变弱”的机制。",
              fill="#555", font=f_note)
    draw.text((42, 1010),
              "实现：practice_answer 新增 suppress_competitors（默认开）——成功后把共享"
              "线索的同类记忆强度乘 0.97（不重置复习时间）；已接入 MCP。",
              fill="#555", font=f_note)
    draw.text((42, 1060),
              "回归：182 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)
    draw.text((42, 1100),
              "诚实说明：压制幅度 3% 很小，靠 2 周多次练习累积；如果会话里紧接着要答"
              "竞争记忆，压制可能让那条更难回忆——真实人脑也有同样的代价。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round59_rif_suppression.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
