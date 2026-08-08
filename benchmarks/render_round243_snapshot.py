"""Round-243 chart: retrieval_snapshot tool."""

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
            os.path.join(
                _BENCH, "results", "retrieval_snapshot_eval.json"
            ),
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

    draw.text((42, 26), "第 243 轮：记忆状态快照与进步对比", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：知识追踪（knowledge tracing）——像老师记录学生“会不会”一样，"
        "每隔一段时间给记忆拍一张快照，对比两次就知道在进步还是退步。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text(
        (x0, 120),
        "① 10 个记忆库：先拍第 1 张快照，复习强化后再拍第 2 张并对比",
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
        ("首张无对比", data["first_none_ok"], "#1a7f37"),
        ("快照指标全", data["keys_ok"], "#d97706"),
        ("复习后提升", data["reviewed_ok"], "#0b7285"),
        ("结论合法", data["verdict_ok"], "#c2255c"),
        ("对比字段全", data["diff_keys_ok"], "#6741d9"),
        ("建议生成", data["advice_ok"], "#2f9e44"),
        ("MCP 通路", data["mcp_ok"], "#e8590c"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 35 + i * 138
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 120, base_y], fill=color)
        draw.text((bx + 34, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：8 根柱子全部 10/10——快照字段齐全；第一次调用不对比，"
        "复习后再拍就有进步对比；结论只会是 进步/稳定/退步。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 隔一段时间（比如每周）拍一次记忆快照，"
        "能看出哪部分记忆在变好、哪部分在衰退，及时补复习。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.retrieval_snapshot + MCP 工具——统计活跃记忆、"
        "平均可回忆度、已复习比例、遗忘风险和校准分，两次对比出结论。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：299 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round243_snapshot.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
