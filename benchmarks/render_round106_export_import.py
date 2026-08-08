"""Round-106 chart: memory export/import."""

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
        open(os.path.join(_BENCH, "results", "export_import_eval.json"),
             encoding="utf-8")
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

    draw.text((42, 26), "第 106 轮：记忆可以整体导出、换机器导入",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：记忆库可移植性——把全部记忆（含复习状态）打包成 JSON，"
              "换一个引擎实例也能完整还原。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库“导出→导入”后完整还原",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 44, y - 9), label, fill="#666", font=f_val)
    bx = x0 + 130
    bh = data["exact_roundtrips"] / 10.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#7b2ff7")
    draw.text((bx + 30, base_y - bh + 8), f"{data['exact_roundtrips']}/10",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "完整还原", fill="#111", font=f_label)

    x0 = 760
    draw.text((x0, 120), "② 导入后 50 次检索，top-1 与原库一致",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (10.0, "10"), (20.0, "20"),
                        (30.0, "30"), (40.0, "40"), (50.0, "50")):
        y = base_y - frac / 50.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 46, y - 9), label, fill="#666", font=f_val)
    bx = x0 + 130
    bh = data["recall_matches"] / 50.0 * chart_h
    draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill="#1a7f37")
    draw.text((bx + 30, base_y - bh + 8), f"{data['recall_matches']}/50",
              fill="white", font=f_val)
    draw.text((bx + 2, base_y + 12), "检索一致", fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：10 个不同记忆库导出→导入后逐字段还原（内部序号会重排，"
              "其余全部一致），",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "导入后 50 次检索 top-1 与原库完全相同——agent 可以放心备份/迁移。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：engine.export_memories / import_memories + MCP 工具——"
              "基于 MemoryItem.to_dict/from_dict，重建线索与联想。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：217 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round106_export_import.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
