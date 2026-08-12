"""Render round-8 (gist/verbatim kind-preference A/B) Chinese charts."""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont

_BENCH = os.path.dirname(os.path.abspath(__file__))
_RESULTS = os.path.join(_BENCH, "results")
_OUT = os.path.normpath(os.path.join(_BENCH, "..", "..", "outputs", "charts"))


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\msjh.ttc",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _stats(path: str, kind: str, field: str) -> float:
    data = json.load(open(os.path.join(_RESULTS, path), encoding="utf-8"))
    s = data["retrieval"]["keyword"]["stats"][kind]
    return s[field] / s["n"]


def chart_ab() -> str:
    W, H = 1150, 640
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(19)
    f_val = _font(18)
    f_note = _font(17)
    draw.text((40, 26), "第 8 轮 A/B 对照：要点/逐字偏好为什么会“默认关”", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "200 会话（440 题）：绿=默认关（原样），红=开启要点/逐字偏好。"
              "开启后“之后发生了什么”变差了，所以默认关。",
              fill="#555", font=f_sub)
    def total_hit5(path: str) -> float:
        data = json.load(open(os.path.join(_RESULTS, path), encoding="utf-8"))
        s = data["retrieval"]["keyword"]["stats"]
        n = sum(v["n"] for v in s.values())
        return sum(v["hit5"] for v in s.values()) / n

    off_total = total_hit5("round8_200_default.json")
    on_total = total_hit5("round8_200_on.json")
    off_temporal = _stats("round8_200_default.json", "temporal", "hit5")
    on_temporal = _stats("round8_200_on.json", "temporal", "hit5")
    rows = [
        ("总命中@5", off_total, on_total),
        ("之后发生了什么@5", off_temporal, on_temporal),
    ]
    chart_h = 280
    base_y = 410
    bar_w = 150
    for gi, (name, off, on) in enumerate(rows):
        gx = 70 + gi * 500
        draw.text((gx + 10, 100), name, fill="#111", font=f_label)
        for j, (val, label, color) in enumerate(
            ((off, "默认关", "#1a7f37"), (on, "开启", "#c0392b"))
        ):
            bh = val * chart_h
            x = gx + 20 + j * 220
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            draw.text((x + 40, y - 28), f"{val:.1%}", fill="#222", font=f_val)
            draw.text((x + 28, base_y + 12), label, fill="#333", font=f_label)
    draw.line([(50, base_y), (W - 50, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(50, y), (W - 50, y)], fill="#e5e5e5", width=1)
        draw.text((20, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 470),
              "开启后总命中从 96.4% 掉到 93.6%，时序从 100% 掉到 97.0%——"
              "均匀给所有情节记忆加分，反而把正确答案挤出了前五。",
              fill="#111", font=f_note)
    draw.text((40, 510),
              "机制保留在代码里（可配置、有单元测试），默认关闭；88 题两档都满分。",
              fill="#555", font=f_note)
    draw.text((40, 548),
              "这轮的意义：真实 A/B 抓出了一个“听起来合理、跑起来有害”的设计，及时止损。",
              fill="#e6a700", font=f_note)
    path = os.path.join(_OUT, "round8_ab_control.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_ab())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
