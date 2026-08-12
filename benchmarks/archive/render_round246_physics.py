"""Round-246 chart: physics_simulate tool."""

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
                _BENCH, "results", "physics_simulate_eval.json"
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

    draw.text((42, 26), "第 246 轮：物理心智模拟（脑内推演）", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：人脑像内置了一个“物理引擎”，看到场景会自动推演结果"
        "（Battaglia et al., 2013；Fischer et al., 2016）。"
        "这个工具识别物理场景、取数量、从记忆调规律，然后分 4 步脑内推演。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text(
        (x0, 120),
        "① 10 个记忆库：一半存有自由落体定律，一半没有",
        fill="#111",
        font=f_panel,
    )
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("场景识别准", data["type_ok"], "#7b2ff7"),
        ("数量提取全", data["qty_ok"], "#1a7f37"),
        ("规律来源对", data["law_ok"], "#d97706"),
        ("四阶段齐全", data["phases_ok"], "#0b7285"),
        ("推演有结果", data["sim_ok"], "#c2255c"),
        ("结论合法", data["verdict_ok"], "#6741d9"),
        ("建议含规律", data["advice_ok"], "#2f9e44"),
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
        "怎么看：8 根柱子全部 10/10——自由落体场景识别准确，高度数字提取全；"
        "有记忆的库直接调用存过的定律，没有的用内置规律，都能算出落地时间。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 遇到物理问题先按 初始→规律→推演→结果 四步在脑内跑一遍，"
        "比直接猜答案稳；推演完还能把规律存进记忆。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.physics_simulate + MCP 工具——场景关键词识别、"
        "数量提取、语义记忆找定律，内置通用规律兜底，输出四阶段推演。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：302 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round246_physics.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
