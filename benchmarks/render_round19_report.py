"""Render round-19 (Tencent three-config retest) Chinese chart."""

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


def chart_tencent_configs() -> str:
    W, H = 1250, 640
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(18)
    f_val = _font(17)
    f_note = _font(16)
    draw.text((40, 24), "腾讯项目三种本地配置复测：同一 12 题、同规则", fill="#111",
              font=f_title)
    draw.text((40, 70),
              "腾讯的 L1 抽取依赖 LLM 把对话转成结构化记忆；本地模型下三种配置"
              "都保不住精确事实。",
              fill="#555", font=f_sub)
    rows = [
        ("腾讯+qwen2.5:3b\n（默认提示词）", 0.25, 0.0),
        ("腾讯+qwen2.5:3b\n（保留原文）", 0.25, 0.0),
        ("腾讯+qwen3-vl:8b\n（最新千问）", 0.25, 0.0),
        ("对照：Mnemosis\n+qwen2.5:3b", 0.75, 0.82),
    ]
    chart_h = 280
    base_y = 400
    bar_w = 130
    x0 = 70
    for i, (name, acc, retr) in enumerate(rows):
        gx = x0 + i * 290
        lines = name.split("\n")
        for li, line in enumerate(lines):
            draw.text((gx + 2, 115 + li * 26), line, fill="#111", font=f_label)
        for j, (val, label, color) in enumerate(
            ((acc, "答对", "#1a7f37" if i == 3 else "#c0392b"),
             (retr, "检索@5", "#b0b0b0"))
        ):
            bh = val * chart_h
            x = gx + 15 + j * 150
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            draw.text((x + 36, y - 28), f"{val:.0%}", fill="#222", font=f_val)
            if i == 0:
                draw.text((x + 20, base_y + 12), label, fill="#333", font=f_label)
    draw.line([(50, base_y), (W - 50, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(50, y), (W - 50, y)], fill="#e5e5e5", width=1)
        draw.text((20, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 470),
              "三种配置的抽取结果：属性/日期张冠李戴、凭空加细节，甚至最新的"
              "qwen3-vl 抽取后检索直接为空（思考输出可能破坏了 JSON 解析）。",
              fill="#111", font=f_note)
    draw.text((40, 510),
              "结论：腾讯官方文档推荐 GPT-4o 级别抽取模型；本机只有本地模型，"
              "同基准下它无法与 Mnemosis 竞争——这是项目设计使然，不是模型个别失误。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round19_tencent_configs.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_tencent_configs())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
