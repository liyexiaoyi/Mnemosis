"""Round-36 chart: agent project workflow (plan/record/judge)."""

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
    metrics = [
        ("计划按序检索", 1.00, "#7b2ff7"),
        ("计划覆盖全部步骤", 1.00, "#7b2ff7"),
        ("执行结果召回", 1.00, "#7b2ff7"),
        ("判断正确", 1.00, "#7b2ff7"),
    ]
    mem0 = [
        ("计划按序检索", 0.333, "#1a7f37"),
        ("计划覆盖全部步骤", 0.667, "#1a7f37"),
        ("执行结果召回", 1.00, "#1a7f37"),
        ("判断正确", 1.00, "#1a7f37"),
    ]
    W, H = 1560, 830
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 28), "第 36 轮：Agent 项目制作 · 计划→执行→判断",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "3 个小项目（旅行/生日派对/搬家），云端千问扮演 agent："
              "参考旧计划出步骤 → 记录哪一步失败 → 复盘判断。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① Mnemosis（4 项，每项 3 题）", metrics),
        (1, "② mem0 官方包（同 4 项）", mem0),
    ]
    panel_w = (W - 120) // 2
    chart_h = 330
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
        for i, (name, val, color) in enumerate(rows):
            bx = x0 + 16 + i * step
            bh = max(val, 0.02) * chart_h
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
            draw.text((bx + 28, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
            draw.text((bx - 16, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：四项指标各 3 题——计划步骤是否按时间找回、千问写出的计划是否覆盖"
              "全部步骤、执行失败记录能否召回、复盘判断（unknown/哪个项目）是否正确。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "Mnemosis 四项全满分；mem0 执行结果和判断也满分，但检索上下文不是按时间排序"
              "（1/3），导致千问写出的计划覆盖度（2/3）和顺序（1/3）都打折扣。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "新增 agent 能力：plan_for_goal（目标→旧计划模板）、record_outcome"
              "（结果证据累积）、MCP 工具 plan/reason/record_outcome。"
              "依据：前额叶目标保持、类比迁移、结果监控。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round36_agent_project.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
