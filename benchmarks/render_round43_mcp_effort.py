"""Round-43 chart: MCP plan effort parameter + CI coverage."""

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
    rows = [
        ("low（浅）", False),
        ("high（深）", True),
    ]
    W, H = 1300, 720
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(18)
    f_note = _font(16)

    draw.text((42, 28), "第 43 轮：MCP plan 工具开放规划深度档位",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "agent 现在可以通过 MCP 的 plan 工具指定 effort=low/medium/high；"
              "不指定时自动判定（第 42 轮）。",
              fill="#555", font=f_sub)

    x0 = 200
    draw.text((x0, 130), "指定档位后的行为（单元测试锁定）", fill="#111", font=f_panel)
    for i, (name, rerank) in enumerate(rows):
        bx = x0 + 40 + i * 380
        color = "#b0b0b0" if not rerank else "#7b2ff7"
        draw.rectangle([bx, 280, bx + 240, 360], fill=color)
        draw.text((bx + 20, 300), "effort=" + name, fill="white", font=f_panel)
        draw.text((bx + 20, 470),
                  "结果加权: " + ("开" if rerank else "关"),
                  fill="#111", font=f_label)

    draw.text((42, 540),
              "验证：MCP 传 effort=low → 浅规划、不加结果加权；effort=high → 深规划、"
              "结果加权开启（单元测试 13/13 通过）。",
              fill="#555", font=f_note)
    draw.text((42, 590),
              "工程：规划深度基准（plan_effort_bench，检索版）已接入 GitHub Actions CI。",
              fill="#555", font=f_note)
    draw.text((42, 640),
              "回归：164 测试全过，英文 88 满分、中文 200 不变、中文 10k 1026/1026 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round43_mcp_effort.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
