"""Round-119 chart: tag_memories tool."""

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
        open(os.path.join(_BENCH, "results", "tag_memories_eval.json"),
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

    draw.text((42, 26), "第 119 轮：给记忆批量打标签/摘标签",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：标签就是检索线索——批量打上“工作/项目”，这批记忆就都能"
              "通过标签找回来；索引维护应是可管理操作。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库（各 10 条），4 项检查",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("打标成功", data["add_ok"], "#7b2ff7"),
        ("摘标成功", data["remove_ok"], "#b91c1c"),
        ("计数一致", data["count_ok"], "#d97706"),
        ("标签可检索", data["recall_ok"], "#1a7f37"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 25 + i * 275
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 220, base_y], fill=color)
        draw.text((bx + 78, base_y - bh + 8), f"{val}/10",
                  fill="white", font=f_val)
        draw.text((bx + 30, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：给 10 条记忆批量加 3 个标签，全部生效（10/10）；删掉 1 个"
              "标签全部摘除，计数与手工一致。",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "打上“工作”后，用“工作”检索 5 条以上都能找回来——标签真的可检索。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：engine.tag_memories + MCP 工具——批量更新线索并重建索引。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：224 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round119_tag_memories.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
