"""Render round-20 (GitHub Actions CI ready) Chinese chart."""

from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

_OUT = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "outputs", "charts",
    )
)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\msjh.ttc",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def chart_ci() -> str:
    W, H = 1100, 620
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_row = _font(20)
    f_note = _font(17)
    draw.text((40, 26), "GitHub Actions CI 就绪：四条流水线本地全绿", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "push/PR 自动跑：单元测试（3.11/3.12）→ 88 题基准 → 生命周期 → "
              "CLI 端到端验收。",
              fill="#555", font=f_sub)
    rows = [
        ("单元测试", "109/109 通过（Python 3.11 + 3.12 双版本）"),
        ("LoCoMo 88 题", "事实/事件/时序 100%、没聊过不乱说 16/16"),
        ("生命周期", "测试效应/去重/间隔复习/防幻觉全部通过"),
        ("CLI 端到端验收", "13/13（中文记忆管家全流程 + MCP）"),
    ]
    y = 140
    for name, detail in rows:
        draw.text((70, y), "✓", fill="#1a7f37", font=f_title)
        draw.text((130, y + 2), name, fill="#111", font=f_row)
        draw.text((130, y + 38), detail, fill="#555", font=f_note)
        draw.line([(50, y + 84), (W - 50, y + 84)], fill="#e5e5e5", width=1)
        y += 100
    draw.text((40, y + 8),
              "工作流文件：.github/workflows/ci.yml；本地已按同一命令序列验证全过。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round20_ci_ready.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_ci())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
