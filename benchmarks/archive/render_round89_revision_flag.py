"""Round-89 chart: revision flag (reconsolidation transparency)."""

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
        open(os.path.join(_BENCH, "results", "revision_flag_eval.json"),
             encoding="utf-8")
    )
    W, H = 1400, 820
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(21)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 89 轮：这条记忆改过，告诉 agent “已修订”",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Nader et al. (2000) 记忆重整合——事实被更新后，系统要标注"
              "版本变化，别让 agent 把新版本当成原始记忆。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 8 条“改过版本”的记忆，被正确标注的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("修订标记(新)", data["on"]["revised_flagged"], "#7b2ff7"),
        ("关闭标记", data["off"]["revised_flagged"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 8.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/8",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    x0 = 760
    draw.text((x0, 120), "② 8 条“没改过”的记忆，被误标的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    val = data["on"]["plain_flagged"]
    bx = x0 + 130
    bh = val / 8.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#1a7f37")
    draw.text((bx + 42, base_y - bh + 8), f"{val}/8",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "修订标记(新)", fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：改过版本（1-3 次）的记忆 8/8 被标“已修订(版本n)”，"
              "没改过的 0/8 误标——agent 看到标记就知道这条变过。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "诚实说明：先试了“多实体联合加分”，实测引擎本来就靠多线索重叠"
              "处理这类问题，加分只多 0.002 边际（机制冗余），已回退。",
              fill="#555", font=f_note)
    draw.text((42, 720),
              "实现：recall 新增 revision_flag（默认开）——revision_count>0 的记忆"
              "标注版本号；只加标记，不改排序。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：206 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round89_revision_flag.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
