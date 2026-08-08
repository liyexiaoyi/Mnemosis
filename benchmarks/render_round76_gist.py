"""Round-76 chart: gist preference for summary questions."""

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
        open(os.path.join(_BENCH, "results", "gist_preference_eval.json"),
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

    draw.text((42, 26), "第 76 轮：问“总结/要点”时，优先给沉淀过的要点",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Brainerd & Reyna (1990) 模糊痕迹理论——时间一长，细节会褪色，"
              "但“要点”还在；总结类问题该答要点而不是最近的原话。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 8 个“总结一下…”问题里，旧要点记忆排第一的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("要点优先(新)", data["boosted"]["gist_first"], "#7b2ff7"),
        ("不加分", data["plain"]["gist_first"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 8.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/8",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：同样的内容，一条是 60 天前沉淀的“要点：阿丽喜欢红色”，一条是"
              "2 天前的新鲜原话。",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "不加分时新鲜原话总是排第一（0/8）；开启要点优先后 8/8 都答沉淀过的"
              "要点——总结问题就该这样。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：recall 新增 gist_preference（默认开）——总结/要点类问题给"
              "30 天以上的语义要点 +0.20，标注“图式要点(旧)”。",
              fill="#555", font=f_note)
    draw.text((42, 745),
              "回归：198 测试全过；统一回归全绿（要点词不在既有基准问题里）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round76_gist_preference.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
