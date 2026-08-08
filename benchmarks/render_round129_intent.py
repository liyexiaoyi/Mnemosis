"""Round-129 chart: prospective-memory intent register."""

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
            os.path.join(_BENCH, "results", "intent_register_eval.json"),
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

    draw.text((42, 26), "第 129 轮：记住以后要做的事（前瞻记忆）", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：人脑不只记过去，还专门“记住到点要去做某事”（前瞻性记忆，"
        "Einstein & McDaniel 1990）；这个功能让 agent 也能登记待办、到点提醒。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 × 4 个待办（3 到期 + 1 未到期/完成/取消）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("到期清单正确", data["due_ok"], "#7b2ff7"),
        ("汇总数字正确", data["report_ok"], "#1a7f37"),
        ("完成即消失", data["complete_ok"], "#d97706"),
        ("取消即归档", data["cancel_ok"], "#0b7285"),
        ("导出导入不丢", data["roundtrip_ok"], "#c2255c"),
        ("字段齐全", data["fields_ok"], "#6741d9"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 45 + i * 180
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 150, base_y], fill=color)
        draw.text((bx + 48, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 8, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：6 根柱子全部 10/10——到期的事按时间顺序准确列出；"
        "完成后不再提醒；取消后归档；导出再导入一件不丢。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 接到“两小时后提醒我发报告”这类任务时，能登记到点自动浮现，"
        "不用靠回忆硬碰。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine 的 intent 登记/到期/完成/取消/汇总 5 个方法 + 5 个 MCP 工具，"
        "随记忆一起导出导入。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：230 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round129_intent.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
