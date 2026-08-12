"""Round-51 chart: desirable-difficulty review scheduling."""

from __future__ import annotations

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
    rows = [
        ("期望难度", 0.446, 0.500, "#7b2ff7"),
        ("最遗忘优先", 0.411, 0.457, "#b0b0b0"),
        ("不复习", 0.0, 0.144, "#d9c9c9"),
    ]
    W, H = 1500, 820
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(18)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 28), "第 51 轮：期望难度驱动的复习调度",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "依据：期望难度（Bjork & Bjork 2011）——复习应挑“有难度但能成功”的"
              "记忆（可提取度中等），而不是最遗忘的（多半失败）或最轻松的。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① 复习成功率（越高越好）", "rate"),
        (1, "② 4 周后平均可提取度（越高越好）", "mean"),
    ]
    panel_w = (W - 120) // 2
    chart_h = 300
    base_y = 500
    for p, title, key in panels:
        x0 = 50 + p * (panel_w + 20)
        draw.text((x0, 130), title, fill="#111", font=f_panel)
        draw.line([(x0, base_y), (x0 + panel_w - 10, base_y)], fill="#999", width=2)
        for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
            y = base_y - frac * chart_h
            draw.line([(x0, y), (x0 + panel_w - 10, y)], fill="#e5e5e5", width=1)
            draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
        bar_w = 120
        step = (panel_w - 20) // len(rows)
        for i, (name, rate, mean, color) in enumerate(rows):
            val = rate if key == "rate" else mean
            bx = x0 + 16 + i * step
            bh = max(val, 0.02) * chart_h
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
            draw.text((bx + 30, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
            draw.text((bx - 8, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：左图比复习“成功率高不高”（期望难度 44.6% vs 最遗忘优先 41.1%），"
              "右图比 4 周后记忆还剩多强（0.500 vs 0.457；不复习只有 0.144）。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "实现：due_items 新增 desirable_difficulty 参数——到期项里优先挑"
              "“可提取度最接近 0.45”的（有难度但成功率高），替换“最遗忘优先”；"
              "复习成功仍按努力度（1-可提取度）放大强化。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "4 周模拟（60 条记忆、每日 6 条、随机成功）三策略对比全绿。"
              "回归：172 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round51_desirable.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
