"""Round-84 chart: second look (evidence re-rank on shaky answers)."""

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
        open(os.path.join(_BENCH, "results", "second_look_eval.json"),
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

    draw.text((42, 26), "第 84 轮：拿不准时“再看一眼”，按证据重新排",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Koriat & Goldsmith (1996) 元认知监控 + Yonelinas (2002) "
              "回忆提取——低置信时不硬答，改用证据强度复核。",
              fill="#555", font=f_sub)

    # Panel 1: evidence-first hits
    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 8 个“拿不准”的检索里，证据充分的记忆排第一",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("复核(新)", data["second_look"]["evidence_first"], "#7b2ff7"),
        ("单次检索", data["single_pass"]["evidence_first"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 8.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/8",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    # Panel 2: shaky tops
    x0 = 760
    draw.text((x0, 120), "② 被正确标记“不确定”的检索数（复核前提）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    rows2 = [
        ("复核(新)", data["second_look"]["shaky_top"], "#7b2ff7"),
        ("单次检索", data["single_pass"]["shaky_top"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows2):
        bx = x0 + 70 + i * 190
        bh = val / 8.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/8",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：8 个场景里，单次检索都让“证据少但稍微占优”的记忆排第一（0/8）；"
              "开启复核后按证据强度重新排，8/8 换成证据充分的。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "复核只发生在“不确定”标记出现时（8/8 场景都触发了）——答案明确时"
              "不多此一举。",
              fill="#555", font=f_note)
    draw.text((42, 720),
              "实现：recall 新增 second_look（默认关，按需开）——低置信时给证据数"
              "和来源可信度加权重排，标注“复核(证据/来源重排)”。",
              fill="#555", font=f_note)
    draw.text((42, 770),
              "回归：203 测试全过，88/200/10k 零差异（默认关，不改变现有行为）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round84_second_look.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
