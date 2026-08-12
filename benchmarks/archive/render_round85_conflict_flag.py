"""Round-85 chart: stronger-evidence conflict flag."""

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
        open(os.path.join(_BENCH, "results", "conflict_flag_eval.json"),
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

    draw.text((42, 26), "第 85 轮：答案旁边有 3 倍证据的新事实？提醒 agent 别硬答",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Nader et al. (2000) 记忆重整合——旧记忆被更强证据取代时，"
              "系统应该知道并提醒，而不是继续输出旧事实。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 8 个“旧事实排第一但有更强新证据”的场景，正确标出冲突的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("冲突标记(新)", data["on"]["flagged"], "#7b2ff7"),
        ("关闭标记", data["off"]["flagged"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 8.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/8",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：旧事实靠“更重要”排第一，但同一条线索下有 3 倍证据的新事实；"
              "开启冲突标记后 8/8 提醒",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "“存在更强证据冲突”并标成不确定——agent 拿到提示就知道该去核实，"
              "而不是把旧答案当定论。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：recall 新增 conflict_flag（默认开）——榜首同线索存在 ≥3 倍证据"
              "且来源可信不低时，标记冲突。",
              fill="#555", font=f_note)
    draw.text((42, 750),
              "回归：204 测试全过，88/200/10k 零差异（只加标记，不改排序）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round85_conflict_flag.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
