"""Round-46 chart: prediction-error driven memory updates."""

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
    checks = [
        ("预测先1.0", 1.00),
        ("意外后0.83", 0.83),
        ("意外高重要", 0.90),
        ("意外有标记", 1.00),
        ("预期低重要", 0.75),
        ("千问识别", 1.00),
    ]
    W, H = 1500, 780
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(16)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 28), "第 46 轮：预测误差驱动的记忆更新",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "依据：多巴胺预测误差（Schultz et al. 1997）与 Rescorla-Wagner 学习规则"
              "——与预期不符的结果（意外失败）获得更高重要性并打上“意外”标记。",
              fill="#555", font=f_sub)

    x0 = 120
    draw.text((x0, 130), "订机票：5 次成功后出现意外失败", fill="#111", font=f_panel)
    base_y = 500
    chart_h = 300
    draw.line([(x0, base_y), (x0 + 760, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(x0, y), (x0 + 760, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
    for i, (name, val) in enumerate(checks):
        bx = x0 + 14 + i * 126
        bh = max(val, 0.02) * chart_h
        color = "#7b2ff7" if val >= 0.9 else "#9ecbff"
        draw.rectangle([bx, base_y - bh, bx + 94, base_y], fill=color)
        draw.text((bx + 20, base_y - bh + 8), f"{val:.0%}",
                  fill="white", font=f_val)
        draw.text((bx - 14, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：意外失败前预测成功率 100%，出现失败后更新为 83%（5/6）；"
              "意外失败记录重要性 0.90 并带“意外”标记，而预期成功记录只有 0.75、无标记。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "实现：record_outcome 按“历史成功率 vs 本次结果”计算预测误差，"
              "误差≥0.6 的结果重要性+0.15 并加“意外”线索；新增 predict_step()"
              "让 agent 执行前能问“这一步成功率多少”。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "千问问“哪个步骤出现过意外失败？”能定位到订机票。"
              "回归：168 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round46_prediction_error.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
