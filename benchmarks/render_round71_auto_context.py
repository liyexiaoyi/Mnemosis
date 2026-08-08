"""Round-71 chart: auto-context tagging (context-dependent recall)."""

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
        open(os.path.join(_BENCH, "results", "auto_context_eval.json"),
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

    draw.text((42, 26), "第 71 轮：写记忆时自动记下“在哪儿发生的”",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Godden & Baddeley (1975) 情境依赖记忆——自动从内容里提取"
              "“在会议室/在餐厅/在图书馆”，不用手动打标签。",
              fill="#555", font=f_sub)

    # Panel 1: location hits
    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 3 个“刚才讨论的方案”问题里，答对地点的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (1.0, "1"), (2.0, "2"), (3.0, "3")):
        y = base_y - frac / 3.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("自动打标(新)", data["auto"]["location_hits"], "#7b2ff7"),
        ("不打标", data["no_auto"]["location_hits"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 3.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/3",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    # Panel 2: tagged count
    x0 = 760
    draw.text((x0, 120), "② 12 条记忆里自动带上情境标签的条数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (6.0, "6"), (12.0, "12")):
        y = base_y - frac / 12.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows2 = [
        ("自动打标(新)", data["auto"]["tagged"], "#7b2ff7"),
        ("不打标", data["no_auto"]["tagged"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows2):
        bx = x0 + 70 + i * 190
        bh = val / 12.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/12",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：问句里没有地点词（“刚才讨论的方案”），只能靠“当前在会议室”"
              "分辨；自动打标后 3/3 答对，",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "不打标只能蒙对 1/3。日期（在2026年…）、口头语（在这里）不会被误认成地点。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：remember 新增 auto_context（默认开）——识别“在会议室里/去机场/"
              "到餐厅”等短语并写入记忆的情境字段，配合第 60 轮的情境匹配使用。",
              fill="#555", font=f_note)
    draw.text((42, 750),
              "回归：194 测试全过，88/200/10k 零差异（写入侧自动打标，不改检索排序）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round71_auto_context.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
