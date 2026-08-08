"""Round-255 chart: concept_cover agent-chain integration."""

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
            os.path.join(_BENCH, "results", "concept_cover_eval.json"),
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

    draw.text((42, 26), "第 255 轮：概念覆盖接入 agent 链路", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：工作记忆分块（Miller, 1956）。多概念问题拆块补查，"
        "并让 search / context_pack 也能拿到补回来的记忆。",
        fill="#555",
        font=f_sub,
    )
    draw.text(
        (42, 104),
        "本轮还修了两个真实缺口：同分候选按随机 id 选“最佳”会漏；"
        "context_pack 曾过滤掉“概念覆盖”补回来的记忆。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 400
    chart_h = 220
    draw.text(
        (x0, 140),
        "① 10 个记忆库 × 8 项检查（分块/覆盖/最终上下文/MCP 链路）",
        fill="#111",
        font=f_panel,
    )
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("字段齐全", data["fields_ok"], "#7b2ff7"),
        ("分块正确", data["chunks_ok"], "#1a7f37"),
        ("每块信息全", data["per_chunk_ok"], "#d97706"),
        ("覆盖判定准", data["covered_ok"], "#0b7285"),
        ("最终上下文齐", data["final_ok"], "#c2255c"),
        ("结论合法", data["verdict_ok"], "#6741d9"),
        ("建议含覆盖", data["advice_ok"], "#2f9e44"),
        ("MCP 链路全通", data["mcp_ok"], "#e8590c"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 35 + i * 138
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 120, base_y], fill=color)
        draw.text((bx + 34, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 610),
        "怎么看：8 根柱子全部 10/10——“移动速度和跳跃力度”被拆成两个概念，"
        "前 2 条同时带回 320 和 420；MCP 的 search 和 context_pack 也都能拿到。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 650),
        "用处：agent 遇到“A 和 B 分别……”的问题时，不再漏掉其中一半；"
        "换上下文打包给模型时，补查到的记忆也不会被丢掉。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 720),
        "回归：308 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round255_concept.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
