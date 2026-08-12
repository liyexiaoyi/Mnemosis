"""Render round-16 (CLI end-to-end) Chinese chart."""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont

_BENCH = os.path.dirname(os.path.abspath(__file__))
_RESULTS = os.path.join(_BENCH, "results")
_OUT = os.path.normpath(os.path.join(_BENCH, "..", "..", "outputs", "charts"))


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\msjh.ttc",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def chart_e2e() -> str:
    with open(os.path.join(_RESULTS, "e2e_cli_workflow.json"), encoding="utf-8") as f:
        d = json.load(f)
    W, H = 1150, 160 + len(d["steps"]) * 48
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_row = _font(18)
    f_val = _font(17)
    draw.text((40, 24), "CLI 端到端验收：记忆管家全流程（中文）", fill="#111",
              font=f_title)
    draw.text((40, 66),
              f"用真实的 `python -m mnemosis` 命令跑完整个生命周期："
              f"{d['passed']}/{d['total']} 步全部通过。",
              fill="#555", font=f_sub)
    y = 100
    draw.line([(30, y), (W - 30, y)], fill="#999", width=2)
    for s in d["steps"]:
        y += 48
        mark = "✓" if s["passed"] else "✗"
        color = "#1a7f37" if s["passed"] else "#c0392b"
        draw.text((40, y), mark, fill=color, font=f_row)
        draw.text((90, y), s["name"], fill="#111", font=f_row)
        draw.line([(30, y + 24), (W - 30, y + 24)], fill="#e5e5e5", width=1)
    draw.text((40, y + 40),
              "覆盖：记住（中文/虚词）→ 回忆（跨格式日期）→ 没聊过不乱说 → "
              "睡眠巩固 → 统计 → 更新事实 → 复习 → 工作集。",
              fill="#555", font=f_val)
    path = os.path.join(_OUT, "round16_e2e_cli.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_e2e())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
