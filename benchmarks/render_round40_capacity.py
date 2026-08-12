"""Round-40 chart: working-memory capacity matching (Miller 1956)."""

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
    auto = [
        ("步骤找回", 1.00),
        ("顺序正确", 1.00),
    ]
    fixed = [
        ("步骤找回", 0.80),
        ("顺序正确", 0.00),
    ]
    W, H = 1450, 800
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(18)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 28), "第 40 轮：工作记忆容量匹配（Miller 1956，7±2）",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "一个 5 步参考计划埋在 8,675 条噪声里。自动容量（按参考人数/复杂度"
              "决定上下文大小）vs 固定只取 4 条。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① 自动容量（默认）", auto),
        (1, "② 固定 4 条（截断）", fixed),
    ]
    panel_w = (W - 120) // 2
    chart_h = 320
    base_y = 500
    for p, title, rows in panels:
        x0 = 50 + p * (panel_w + 20)
        draw.text((x0, 130), title, fill="#111", font=f_panel)
        draw.line([(x0, base_y), (x0 + panel_w - 10, base_y)], fill="#999", width=2)
        for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
            y = base_y - frac * chart_h
            draw.line([(x0, y), (x0 + panel_w - 10, y)], fill="#e5e5e5", width=1)
            draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
        bar_w = 110
        step = (panel_w - 20) // len(rows)
        for i, (name, val) in enumerate(rows):
            bx = x0 + 16 + i * step
            bh = max(val, 0.02) * chart_h
            color = "#7b2ff7" if p == 0 else "#b0b0b0"
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
            draw.text((bx + 24, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
            draw.text((bx - 6, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：自动容量下 5/5 步骤找回且按时间排序；固定 4 条把计划拦腰截断"
              "（4/5、乱序）。差异是确定性的。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "实现：plan_for_goal(top_k=None) 按 Miller 1956 的容量匹配自动决定大小——"
              "基础 8 条，每多一个参考人物 +2（参考阿丽和小波→10），"
              "要求完整/按顺序 +2，封顶 14。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "工程：计划选择、计划容量两个基准接入 CI（检索版）。"
              "回归：161 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round40_capacity.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
