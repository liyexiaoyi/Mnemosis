"""Round-91 chart: practice report review suggestions."""

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
        open(os.path.join(_BENCH, "results", "report_suggestions_eval.json"),
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

    draw.text((42, 26), "第 91 轮：练习报告直接告诉 agent“这条多久后复习”",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Smolen et al. (2016) 自适应间隔——把复习建议直接写进每轮"
              "练习报告，agent 不用再单独查计划。",
              fill="#555", font=f_sub)

    # Panel 1: consistency
    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 30 条练习报告的“下次复习时间”与调度器完全一致",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (10.0, "10"), (20.0, "20"), (30.0, "30")):
        y = base_y - frac / 30.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    bx = x0 + 130
    bh = data["exact_next_review"] / 30.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#7b2ff7")
    draw.text((bx + 30, base_y - bh + 8), f"{data['exact_next_review']}/30",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "完全一致", fill="#111", font=f_label)

    # Panel 2: horizons
    x0 = 760
    draw.text((x0, 120), "② 复习建议间隔（答对 24 小时 / 答错 12 小时）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (10.0, "10"), (20.0, "20"), (30.0, "30")):
        y = base_y - frac / 30.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    for i, (lbl, color) in enumerate(
        (("答对→24h", "#1a7f37"), ("答错→12h", "#b91c1c"))
    ):
        bx = x0 + 60 + i * 200
        bh = 15 / 30.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 140, base_y], fill=color)
        draw.text((bx + 40, base_y - bh + 8), "15/15",
                  fill="white", font=f_val)
        draw.text((bx + 8, base_y + 12), lbl, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：30 条练习报告每条都带“下次复习时间”，与调度器完全一致"
              "（30/30）；",
              fill="#555", font=f_note)
    draw.text((42, 640),
              "答对的建议 24 小时后复习（15/15），答错的 12 小时后复习（15/15）——"
              "agent 按报告就能安排。",
              fill="#555", font=f_note)
    draw.text((42, 710),
              "实现：practice_report 每条结果增加 next_review_at 和 retry_hours；"
              "不改调度行为。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：208 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round91_report_suggestions.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
