"""Round-74 chart: encoding variability (rotating practice cues)."""

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
        open(os.path.join(_BENCH, "results", "encoding_variability_eval.json"),
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

    draw.text((42, 26), "第 74 轮：练习时换着线索问，换一种问法也答得上来",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Martin (1968) 编码变异性——同一条记忆用不同线索练过，"
              "以后无论从哪个角度问都能想起来。",
              fill="#555", font=f_sub)

    # Panel 1: final test via cue C
    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 30 次最终测验（用练习时最没练到的线索 C 提问）答对次数",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (10.0, "10"), (20.0, "20"), (30.0, "30")):
        y = base_y - frac / 30.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("换线索练(新)", data["varied"]["final_successes"], "#7b2ff7"),
        ("固定线索练", data["fixed"]["final_successes"], "#9ecbff"),
        ("不复习", data["none"]["final_successes"], "#d97706"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 45 + i * 160
        bh = val / 30.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 110, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 6), f"{val}/30",
                  fill="white", font=f_val)
        draw.text((bx - 10, base_y + 10), name, fill="#111", font=f_label)

    # Panel 2: cue C rehearsed count
    x0 = 760
    draw.text((x0, 120), "② 练习期间，线索 C 被显示过的记忆条数（共 30 条）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (10.0, "10"), (20.0, "20"), (30.0, "30")):
        y = base_y - frac / 30.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows2 = [
        ("换线索练(新)", data["varied"]["cue_c_shown"], "#7b2ff7"),
        ("固定线索练", data["fixed"]["cue_c_shown"], "#9ecbff"),
    ]
    for i, (name, val, color) in enumerate(rows2):
        bx = x0 + 85 + i * 190
        bh = val / 30.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/30",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：每条记忆有 3 条线索，固定练习永远只显示前两条（线索 C 从未练过）；"
              "轮换练习让 18/30 条练到线索 C。",
              fill="#555", font=f_note)
    draw.text((42, 640),
              "最终用线索 C 提问：轮换组答对 20/30，固定组 17/30，不复习 10/30——"
              "换着线索练，换一种问法也稳。",
              fill="#555", font=f_note)
    draw.text((42, 710),
              "实现：practice_due 新增 vary_cues（默认开）——多线索记忆按复习次数"
              "轮换显示两条线索窗口；已接入 MCP。",
              fill="#555", font=f_note)
    draw.text((42, 760),
              "回归：196 测试全过，88/200/10k 零差异（只改给 agent 看的提示词文本）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round74_encoding_variability.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
