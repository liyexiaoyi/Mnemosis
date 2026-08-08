"""Round-248 chart: review_consistency tool."""

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
            os.path.join(
                _BENCH, "results", "review_consistency_eval.json"
            ),
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

    draw.text((42, 26), "第 248 轮：复习坚持度（有没有按时复习）", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：间隔复习只有“真的按时复习”才有效（Cepeda et al., 2006）；",
        fill="#555",
        font=f_sub,
    )
    draw.text(
        (42, 104),
        "自我调节学习要监控自己的学习行为；工具对比“该复习”和“实际复习”的时间。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text(
        (x0, 130),
        "① 10 个记忆库：各有 1 条按时复习、1 条拖了 18 天、1 条从没复习",
        fill="#111",
        font=f_panel,
    )
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("统计自洽", data["counts_ok"], "#7b2ff7"),
        ("按时识别", data["on_time_ok"], "#1a7f37"),
        ("拖延识别", data["overdue_ok"], "#d97706"),
        ("坚持度对", data["ratio_ok"], "#0b7285"),
        ("结论合法", data["verdict_ok"], "#c2255c"),
        ("建议含复习", data["advice_ok"], "#6741d9"),
        ("未复习计数", data["never_ok"], "#2f9e44"),
        ("MCP 通路", data["mcp_ok"], "#e8590c"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 35 + i * 138
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 120, base_y], fill=color)
        draw.text((bx + 34, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：8 根柱子全部 10/10——按时复习、拖了 18 天、从没复习的"
        "都能正确识别，坚持度 50% 判为“中等”，并建议先清积压。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 定期查一次坚持度，就知道自己是真在学还是光记不复习；"
        "坚持度低时按“最重要+最晚到期”先补。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.review_consistency + MCP 工具——用每次复习时间算"
        "下次应复习时间，超期就算拖延，汇总坚持度、平均拖延天数和建议。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：304 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round248_review.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
