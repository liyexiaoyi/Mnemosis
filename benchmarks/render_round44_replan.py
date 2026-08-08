"""Round-44 chart: re-planning after failed steps."""

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
        ("失败票靠后", 1.00),
        ("成功票在前", 1.00),
        ("重规划理由", 1.00),
        ("决策入记忆", 1.00),
        ("千问避开", 1.00),
    ]
    W, H = 1450, 780
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 28), "第 44 轮：规划失败后的重规划/纠错",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "依据：前扣带回冲突监控与认知控制（Botvinick et al. 2001）、"
              "错误相关负波 ERN——执行失败后重新规划，并把决策记入记忆。",
              fill="#555", font=f_sub)

    x0 = 130
    draw.text((x0, 130), "重规划行为检查（5 项全过）", fill="#111", font=f_panel)
    base_y = 500
    chart_h = 300
    draw.line([(x0, base_y), (x0 + 620, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(x0, y), (x0 + 620, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
    for i, (name, val) in enumerate(checks):
        bx = x0 + 14 + i * 124
        bh = max(val, 0.02) * chart_h
        draw.rectangle([bx, base_y - bh, bx + 84, base_y], fill="#7b2ff7")
        draw.text((bx + 24, base_y - bh + 8), f"{val:.0%}",
                  fill="white", font=f_val)
        draw.text((bx - 8, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "场景：阿丽订机票失败两次、小波全部成功。replan(目标, 订机票) 后："
              "只把阿丽的失败机票移到计划末尾（普通结果加权只降级不避开），"
              "小波成功的机票保留在前，并写入“重新规划：避开失败步骤”的记忆。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "顺带修掉一个设计缺陷：最初 replan 会连“成功过的订机票”也避开，"
              "改为先查执行记录定位“失败的那个人”，只避开其步骤。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "千问看到重规划后的计划，也主动避开了阿丽的失败机票。"
              "回归：165 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round44_replan.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
