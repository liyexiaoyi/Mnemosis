"""Round-101 chart: review-score priority (importance x forgetting)."""

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
        open(os.path.join(_BENCH, "results", "review_score_eval.json"),
             encoding="utf-8")
    )
    W, H = 1400, 800
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(21)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 101 轮：复习顺序按“重要 × 快忘”排，而不是只看重要",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：重要性×遗忘程度才是真正的“复习需求”（重要性加权复习；"
              "Bjork 期望难度）——重要但快忘的排前面。",
              fill="#555", font=f_sub)

    # Panel 1: retained
    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 天后记住的条数（共 30 条）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (10.0, "10"), (20.0, "20"), (30.0, "30")):
        y = base_y - frac / 30.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("复习得分(新)", data["score"]["retained"], "#7b2ff7"),
        ("只看重要度", data["default"]["retained"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 30.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/30",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    # Panel 2: weighted retained
    x0 = 760
    draw.text((x0, 120), "② 按重要度加权的保留分（保住重要内容才算赢）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10"),
                        (15.0, "15"), (19.0, "19")):
        y = base_y - frac / 19.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 44, y - 9), label, fill="#666", font=f_val)
    rows2 = [
        ("复习得分(新)", data["score"]["importance_weighted_retained"],
         "#7b2ff7"),
        ("只看重要度", data["default"]["importance_weighted_retained"],
         "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows2):
        bx = x0 + 70 + i * 190
        bh = val / 19.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val:.1f}",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：重要但快忘的记忆按“重要×遗忘程度”排前面后，10 天保留 30/30"
              "（默认 25/30），",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "重要度加权保留 19.0 vs 16.0——同样多的练习次数，保住了更重要的内容。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：practice_due 新增 review_score_priority（默认关，按需开）——"
              "排序键改为 重要度×(1-可提取度)。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：214 测试全过；默认关，既有测评与 88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round101_review_score.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
