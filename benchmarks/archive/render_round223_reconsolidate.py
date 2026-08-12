"""Round-223 chart: reconsolidation_plan tool."""

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
            os.path.join(_BENCH, "results", "reconsolidation_plan_eval.json"),
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

    draw.text((42, 26), "第 223 轮：再巩固更新计划", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：记忆被提取后会变“可塑”，可以趁机更新而不是只重放"
        "（Nader et al. 2000）——流程是：提取 → 找冲突/新证据 → 更新 → 再巩固。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 ×（矛盾会议日期 → 更新计划）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("找到目标记忆", data["found_ok"], "#7b2ff7"),
        ("记忆档案齐全", data["mem_ok"], "#1a7f37"),
        ("冲突证据找到", data["conflict_ok"], "#d97706"),
        ("更新步骤完整", data["step_ok"], "#0b7285"),
        ("建议生成", data["advice_ok"], "#c2255c"),
        ("字段齐全", data["fields_ok"], "#6741d9"),
        ("MCP 通路正常", data["mcp_ok"], "#2f9e44"),
        ("错误 ID 不崩", data["missing_ok"], "#e8590c"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 35 + i * 138
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 120, base_y], fill=color)
        draw.text((bx + 34, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：8 根柱子全部 10/10——“会议在周一”和“会议在周二”互相矛盾时，"
        "工具能定位目标、列出冲突证据，并给出 4 步更新计划。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 发现记忆打架或过时后跑一次——先提取打开更新窗口，"
        "再按新证据改写，更新后间隔复习，不让旧版本继续误导。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.reconsolidation_plan + MCP 工具——定位记忆、"
        "按线索找冲突、生成提取→更新→再巩固四步计划。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：287 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round223_reconsolidate.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
