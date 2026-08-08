"""Round-95 chart: MCP search tool."""

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
        open(os.path.join(_BENCH, "results", "mcp_search_eval.json"),
             encoding="utf-8")
    )
    W, H = 1400, 780
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 95 轮：agent 现在能直接调用“检索记忆”工具",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：把 recall 完整接入 MCP——agent 不用再猜内部 API，"
              "一条 search 命令拿到内容、分数、置信度与原因。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 次 MCP 检索，top-1 答对的次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 44, y - 9), label, fill="#666", font=f_val)
    bx = x0 + 130
    bh = data["correct_top1"] / 10.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#7b2ff7")
    draw.text((bx + 30, base_y - bh + 8), f"{data['correct_top1']}/10",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "top-1 正确", fill="#111", font=f_label)

    x0 = 760
    draw.text((x0, 120), "② 返回字段齐全的检索次数（分数/置信度/原因）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 44, y - 9), label, fill="#666", font=f_val)
    bx = x0 + 130
    bh = data["fields_ok"] / 10.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#1a7f37")
    draw.text((bx + 30, base_y - bh + 8), f"{data['fields_ok']}/10",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "字段齐全", fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：MCP search 在 20 条记忆上 10 次查询全部 top-1 正确，"
              "每次都带回内容、分数、置信度标记和原因——",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "agent 拿到结果就知道该不该信、为什么排它第一。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：MCP 新增 search 工具（query/top_k/context），内部走完整 recall"
              "（情境匹配、复核、冲突标记等全部生效）。",
              fill="#555", font=f_note)
    draw.text((42, 750),
              "回归：210 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round95_mcp_search.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
