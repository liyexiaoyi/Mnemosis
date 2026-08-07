"""Render round-17 (zh money/measure normalization) Chinese chart."""

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


def chart_units() -> str:
    W, H = 1050, 580
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_row = _font(20)
    f_note = _font(17)
    draw.text((40, 26), "中文金额/量词归一：中文数字也能被检索到", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "“三百元”和“300元”、“三本”和“3本”，现在都能互相检索。",
              fill="#555", font=f_sub)
    rows = [
        ("记忆：阿丽花了三百元买了笔记本。", "查询：阿丽 300元", "✓"),
        ("记忆：小王买了三本书。", "查询：小王 3本", "✓"),
    ]
    y = 150
    for mem, q, mark in rows:
        draw.text((60, y), mem, fill="#222", font=f_row)
        draw.text((60, y + 40), q, fill="#222", font=f_row)
        draw.text((900, y + 10), mark, fill="#1a7f37", font=f_title)
        draw.line([(40, y + 90), (W - 40, y + 90)], fill="#e5e5e5", width=1)
        y += 120
    draw.text((40, y + 10),
              "实现：分词时把“数字汉字 + 元/块/本/个/台/条/张/件/杯/瓶”"
              "同时转成数字形式（如 300元、3本），两边写法都能命中。",
              fill="#555", font=f_note)
    draw.text((40, y + 55),
              "回归：英文 88 题满分、中文 200 会话 99.3% 保持；测试 109/109。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round17_zh_units.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_units())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
