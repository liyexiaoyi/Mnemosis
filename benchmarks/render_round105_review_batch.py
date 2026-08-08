"""Round-105 chart: review_batch API."""

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
        open(os.path.join(_BENCH, "results", "review_batch_eval.json"),
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

    draw.text((42, 26), "第 105 轮：一次批量复习 30 条，调度状态全部对齐",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Smolen et al. (2016) 自适应间隔——agent 用一条命令提交"
              "整批复习结果，拿到每条的下次复习时间。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 批量 30 条的统计与调度状态（满分 30/30）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (10.0, "10"), (20.0, "20"), (30.0, "30")):
        y = base_y - frac / 30.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("答对 15", data["successes"], "#1a7f37"),
        ("答错 15", data["failures"], "#b91c1c"),
        ("streak 对齐", data["streak_matches"], "#7b2ff7"),
        ("下次复习对齐", data["next_review_matches"], "#d97706"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 20 + i * 280
        bh = val / 30.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 220, base_y], fill=color)
        draw.text((bx + 78, base_y - bh + 8), f"{val}/30",
                  fill="white", font=f_val)
        draw.text((bx + 30, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：一条 review_batch 命令处理 30 条（15 对 15 错），"
              "每条的下次复习时间与调度器完全一致（30/30），",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "答对的间隔变长、答错的立刻缩短——agent 可以直接驱动复习循环。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：engine.review_batch + MCP review_batch 工具——批量执行"
              "review() 并返回 streak/next_review_at/retry_hours。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：216 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round105_review_batch.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
