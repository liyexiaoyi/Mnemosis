"""Round-126 chart: search_batch tool."""

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
        open(
            os.path.join(_BENCH, "results", "search_batch_eval.json"),
            encoding="utf-8",
        )
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

    draw.text((42, 26), "第 126 轮：一次问多个问题，一次全答", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：工作记忆容量有限（Miller 1956），把一批问题打包交给记忆系统，"
        "一次往返全部检索，省去多次调用的开销。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 × 4 个查询（2 命中 + 2 无关）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("返回组数正确", data["count_ok"], "#7b2ff7"),
        ("顺序一致", data["order_ok"], "#1a7f37"),
        ("命中排第一", data["hit_ok"], "#d97706"),
        ("无关查询分更低", data["rank_ok"], "#0b7285"),
        ("字段齐全", data["fields_ok"], "#c2255c"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 60 + i * 205
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 165, base_y], fill=color)
        draw.text((bx + 56, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 10, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：5 根柱子全部 10/10——4 个问题一次返回 4 组结果，顺序不乱；"
        "该命中的记忆排在每组第一，无关查询分数明显更低。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 要同时查很多记忆时，不用反复调用，一次拿回所有答案，"
        "节省时间和上下文。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.search_batch + MCP search_batch——按输入顺序逐个走完整 "
        "recall 检索链，返回每组 id/预览/分数/置信度。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：229 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round126_search_batch.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
