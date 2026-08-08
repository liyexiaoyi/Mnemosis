"""Round-38 chart: outcome-aware plan choice."""

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
        ("成功计划排第一（检索）", 1.00, 0.0),
        ("千问选对成功计划", 1.00, 1.00),
    ]
    W, H = 1400, 780
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(18)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 28), "第 38 轮：结果驱动的计划选择（成功计划优先）",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "两个参考计划：阿丽的订机票失败两次，小波的全部成功。"
              "新目标问“参考谁的计划更好”，结果加权开/关对比。",
              fill="#555", font=f_sub)

    x0 = 120
    draw.text((x0, 130), "① 成功计划（小波）的步骤是否排第一（检索，确定）",
              fill="#111", font=f_panel)
    base_y = 500
    chart_h = 300
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
    for i, (name, on_val, off_val) in enumerate(rows[:1]):
        bx = x0 + 40 + i * 250
        for j, (val, color) in enumerate(((on_val, "#7b2ff7"), (off_val, "#b0b0b0"))):
            bxx = bx + j * 110
            bh = max(val, 0.02) * chart_h
            draw.rectangle([bxx, base_y - bh, bxx + 80, base_y], fill=color)
            draw.text((bxx + 18, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
        draw.text((bx - 10, base_y + 12), "结果加权开", fill="#7b2ff7", font=f_label)
        draw.text((bx + 100, base_y + 12), "结果加权关", fill="#666", font=f_label)

    x1 = 780
    draw.text((x1, 130), "② 千问看到执行记录后选对成功计划",
              fill="#111", font=f_panel)
    draw.line([(x1, base_y), (x1 + 420, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(x1, y), (x1 + 420, y)], fill="#e5e5e5", width=1)
        draw.text((x1 - 34, y - 10), label, fill="#666", font=f_val)
    for i, (name, on_val, off_val) in enumerate(rows[1:]):
        bx = x1 + 40 + i * 250
        for j, (val, color) in enumerate(((on_val, "#7b2ff7"), (off_val, "#b0b0b0"))):
            bxx = bx + j * 110
            bh = max(val, 0.02) * chart_h
            draw.rectangle([bxx, base_y - bh, bxx + 80, base_y], fill=color)
            draw.text((bxx + 18, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
        draw.text((bx - 10, base_y + 12), "开", fill="#7b2ff7", font=f_label)
        draw.text((bx + 100, base_y + 12), "关", fill="#666", font=f_label)

    draw.text((42, 600),
              "怎么看：左边是系统的活（确定）——结果加权开时，被证实成功的计划"
              "（小波）排第一，关时按时间排、阿丽在前；右边是模型判断——"
              "只要执行记录在上下文里，千问两种都能选对小波。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "实现：plan_for_goal 新增结果加权重排（效果定律 Thorndike 1911；"
              "结果监控 Smolen 2016）——每个步骤按“成功证据-失败证据”加减分"
              "（封顶 ±0.15），再按“结果分组+时间序”重排；执行记录本身不混进计划。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "回归：158 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round38_plan_choice.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
