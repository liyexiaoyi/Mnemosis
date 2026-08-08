"""Round-50 chart: MCP sleep_replay + 10k post-replay stability."""

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
        ("重放前第一", 1.00),
        ("意外重放", 1.00),
        ("经验固化", 1.00),
        ("重放后第一", 1.00),
        ("摘要可检索", 1.00),
        ("预测走摘要", 1.00),
    ]
    W, H = 1500, 780
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_label = _font(16)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 28), "第 50 轮：MCP sleep_replay + 10k 重放后稳定性",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "8,862 条记忆：1 条意外失败 + 30 条普通失败。睡眠重放后，"
              "意外记录依然排第一，步骤经验固化为摘要，预测走摘要（5/6）。",
              fill="#555", font=f_sub)

    x0 = 130
    base_y = 500
    chart_h = 300
    draw.line([(x0, base_y), (x0 + 780, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(x0, y), (x0 + 780, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
    for i, (name, val) in enumerate(checks):
        bx = x0 + 14 + i * 128
        bh = max(val, 0.02) * chart_h
        draw.rectangle([bx, base_y - bh, bx + 96, base_y], fill="#7b2ff7")
        draw.text((bx + 24, base_y - bh + 8), f"{val:.0%}",
                  fill="white", font=f_val)
        draw.text((bx - 14, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：重放前后“哪个步骤出现过意外失败”都稳定排第一；"
              "MCP 新增 sleep_replay 工具，agent 可显式“睡一觉”巩固经验。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "顺带修掉一个真回归：固化摘要（证据多）会拿证据加成压过警报记录本身，"
              "把摘要重要性降到 0.5 后，摘要仍可被“成功率”查询找到，但不再抢警报第一。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "工程：睡眠重放 10k 基准接入 CI。回归：171 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round50_sleep_mcp.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
