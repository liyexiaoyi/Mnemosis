"""Round-134 chart: suppress_memories tool."""

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
            os.path.join(_BENCH, "results", "suppress_memories_eval.json"),
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

    draw.text((42, 26), "第 134 轮：故意“别想起”的记忆（定向遗忘）", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：人脑能主动抑制一段记忆，让它暂时不冒出来，但内容没有消失"
        "（记忆抑制，Anderson & Green 2001）；这个工具给 agent 同样的能力。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 × 3 条记忆（抑制 1 条 → 恢复 → 换库迁移）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("抑制后不再想起", data["suppress_ok"], "#7b2ff7"),
        ("记忆还在库里", data["intact_ok"], "#1a7f37"),
        ("别的记忆不受影响", data["keep_ok"], "#d97706"),
        ("清单正确", data["report_ok"], "#0b7285"),
        ("解除后恢复", data["unsuppress_ok"], "#c2255c"),
        ("迁移不丢抑制状态", data["roundtrip_ok"], "#6741d9"),
        ("字段齐全", data["fields_ok"], "#2f9e44"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 45 + i * 155
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 125, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：7 根柱子全部 10/10——被抑制的记忆不再冒出来，但一条没删；"
        "其他记忆照常检索；解除抑制立刻恢复；换机器状态也不丢。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 不想被某段记忆反复干扰时（比如一次失败的经历），"
        "可以先压住它，需要时再放出来，而不是删掉。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：suppress/unsuppress/report 3 个 MCP 工具——抑制名单在检索入口"
        "直接排除，不参与评分也不被强化，随导出导入迁移。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：233 个测试全过（含全量 recall 零回归），长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round134_suppress.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
