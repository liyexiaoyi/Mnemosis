"""Round-177 chart: plan_support tool (plan-memory loop)."""

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
            os.path.join(_BENCH, "results", "plan_support_eval.json"),
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

    draw.text((42, 26), "第 177 轮（专项）：执行计划时自动带出相关记忆", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：工作记忆执行任务时会不断从长时记忆调取相关信息"
        "（Baddeley & Hitch 1974）；这个工具给计划的每一步检索支持证据。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 × 2 步计划（调研需求/部署上线）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("每步都带证据", data["steps_ok"], "#7b2ff7"),
        ("第一步带需求文档", data["step1_ok"], "#1a7f37"),
        ("第二步带上线清单", data["step2_ok"], "#d97706"),
        ("支持数正确", data["total_ok"], "#0b7285"),
        ("按相关度排序", data["order_ok"], "#c2255c"),
        ("字段齐全", data["fields_ok"], "#6741d9"),
        ("MCP通路正常", data["mcp_ok"], "#2f9e44"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 45 + i * 155
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 125, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：7 根柱子全部 10/10——“调研需求”自动带出需求文档，“部署上线”"
        "自动带出上线清单，两步都有证据、按相关度排好序。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 每执行一步先把相关记忆调出来，边做边看依据，"
        "不用等做完才发现漏了背景。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.plan_support + MCP 工具——逐步骤走完整检索，"
        "返回支持证据与分数，纯只读。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：260 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round177_support.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
