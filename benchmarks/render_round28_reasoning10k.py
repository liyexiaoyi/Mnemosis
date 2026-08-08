"""Round-28 chart: Chinese reasoning at 10k scale + adaptive pack size."""

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
    coverage = [
        ("普通 top-5", 1.00, "#b0b0b0"),
        ("推理前提包", 1.00, "#7b2ff7"),
    ]
    accuracy = [
        ("普通 top-5", 1.00, "#b0b0b0"),
        ("推理前提包", 1.00, "#7b2ff7"),
    ]
    pack_sizes = [
        ("普通事实题", 6, "#1a7f37"),
        ("两人比较", 8, "#1a7f37"),
        ("三人链", 10, "#1a7f37"),
        ("四人链", 12, "#1a7f37"),
    ]
    W, H = 1560, 900
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(18)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 28 轮：中文推理 · 约 1 万条记忆下的规模压力测试",
              fill="#111", font=f_title)
    draw.text((42, 76),
              "同一 16 道中文推理题，记忆库灌到 9,917 条。依据：前额叶工作记忆"
              "（Miller & Cohen 2001）：前提越多，工作记忆集应越大。",
              fill="#555", font=f_sub)

    # panel 1: coverage
    x0 = 70
    draw.text((x0, 130), "① 16 题推理前提全部找齐（越高越好）", fill="#111", font=f_panel)
    base_y = 470
    chart_h = 300
    draw.line([(x0, base_y), (x0 + 380, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(x0, y), (x0 + 380, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
    for i, (name, val, color) in enumerate(coverage):
        bx = x0 + 30 + i * 160
        bh = val * chart_h
        draw.rectangle([bx, base_y - bh, bx + 100, base_y], fill=color)
        draw.text((bx + 28, base_y - bh + 8), f"{val:.0%}",
                  fill="white", font=f_val)
        draw.text((bx - 4, base_y + 12), name, fill="#111", font=f_label)
    draw.text((x0, 530),
              "普通检索在 1 万条噪声下仍 16/16 找齐；前提包同样 16/16。",
              fill="#555", font=f_note)

    # panel 2: accuracy
    x1 = 620
    draw.text((x1, 130), "② 千问作答（10 题抽样，越高越好）", fill="#111", font=f_panel)
    draw.line([(x1, base_y), (x1 + 380, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(x1, y), (x1 + 380, y)], fill="#e5e5e5", width=1)
        draw.text((x1 - 34, y - 10), label, fill="#666", font=f_val)
    for i, (name, val, color) in enumerate(accuracy):
        bx = x1 + 30 + i * 160
        bh = val * chart_h
        draw.rectangle([bx, base_y - bh, bx + 100, base_y], fill=color)
        draw.text((bx + 28, base_y - bh + 8), f"{val:.0%}",
                  fill="white", font=f_val)
        draw.text((bx - 4, base_y + 12), name, fill="#111", font=f_label)
    draw.text((x1, 530),
              "两种上下文下云端千问都 10/10 满分。",
              fill="#555", font=f_note)

    # panel 3: adaptive pack size
    x2 = 1170
    draw.text((x2, 130), "③ 工作记忆容量自适应（前提包大小）", fill="#111", font=f_panel)
    max_n = 14
    draw.line([(x2, base_y), (x2 + 300, base_y)], fill="#999", width=2)
    for i, (name, n, color) in enumerate(pack_sizes):
        bx = x2 + 10 + i * 78
        bh = n / max_n * chart_h
        draw.rectangle([bx, base_y - bh, bx + 48, base_y], fill=color)
        draw.text((bx + 14, base_y - bh + 6), str(n), fill="white", font=f_val)
        draw.text((bx - 14, base_y + 12), name, fill="#111", font=f_label)
    draw.text((x2, 530),
              "普通题 6 条；两人比较 8；三人链 10；四人链 12。",
              fill="#555", font=f_note)

    draw.text((42, 700),
              "基准 QA 修掉 3 个真实问题：题面前提与记忆不一致（耳机/音箱）、"
              "语义口径漏掉商品词、10k 版漏了 2 条 canonical 前提。"
              "教训：噪声不能制造同人同属性的矛盾事实，否则检索无法判断哪条为真。",
              fill="#555", font=f_note)
    draw.text((42, 748),
              "结论：Mnemosis 的词面召回在 1 万条噪声下依然稳健（16/16、10/10），"
              "前提包 + 自适应容量为更复杂的多跳推理预留了余量。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round28_reasoning_10k.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
