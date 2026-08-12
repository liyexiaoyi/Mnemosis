"""Render round-3 (amygdala emotional consolidation) Chinese charts."""

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


def _emotion_data() -> dict:
    with open(
        os.path.join(_RESULTS, "emotion_consolidation.json"), encoding="utf-8"
    ) as handle:
        data = json.load(handle)
    runs = data["runs"]
    first = runs[0]
    return {
        "retention": (first["retention_30d"]["emotional"],
                      first["retention_30d"]["neutral"]),
        "delta_retention": first["retention_30d"]["delta"],
        "confidence": (first["confidence"]["emotional"],
                       first["confidence"]["neutral"]),
        "storage": (first["storage_strength"]["emotional"],
                    first["storage_strength"]["neutral"]),
        "links": (first["avg_internal_link_weight"]["emotional"],
                  first["avg_internal_link_weight"]["neutral"]),
        "runs": len(runs),
    }


def chart_emotion_retention() -> str:
    d = _emotion_data()
    W, H = 1080, 600
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(20)
    f_val = _font(18)
    f_note = _font(18)
    draw.text((40, 26), "情绪记忆 vs 中性记忆：30 天后的保留率", fill="#111", font=f_title)
    draw.text((40, 72),
              "同样重复 2 次、同样 60 天前发生；睡眠巩固后过 30 天再测。绿=带情绪的，灰=中性。",
              fill="#555", font=f_sub)
    emo, neu = d["retention"]
    chart_h = 300
    base_y = 400
    bar_w = 150
    for i, (val, label, color) in enumerate(
        ((emo, "情绪事件", "#c0392b"), (neu, "中性事件", "#b0b0b0"))
    ):
        bh = val / 0.1 * chart_h
        x = 180 + i * 320
        y = base_y - bh
        draw.rectangle([x, y, x + bar_w, base_y], fill=color)
        draw.text((x + 42, y - 30), f"{val:.1%}", fill="#222", font=f_val)
        draw.text((x + 28, base_y + 12), label, fill="#333", font=f_label)
    draw.line([(100, base_y), (W - 60, base_y)], fill="#999", width=2)
    for v, label in ((0.0, "0%"), (0.05, "5%"), (0.1, "10%")):
        y = base_y - v / 0.1 * chart_h
        draw.line([(100, y), (W - 60, y)], fill="#e5e5e5", width=1)
        draw.text((50, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 470),
              f"保留率：情绪 {emo:.1%} vs 中性 {neu:.1%}，高了 {d['delta_retention']:.1%}（约 6 倍）。",
              fill="#c0392b", font=f_note)
    draw.text((40, 510),
              "对应脑科学：杏仁核在情绪事件编码时把记忆“钉”得更牢（McGaugh 2004；Krenz 等 2025）。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round3_emotion_retention.png")
    img.save(path)
    return path


def chart_emotion_links() -> str:
    d = _emotion_data()
    W, H = 1080, 600
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(20)
    f_val = _font(18)
    f_note = _font(18)
    draw.text((40, 26), "情绪记忆“黏”得更紧：链接强度与存储强度", fill="#111", font=f_title)
    draw.text((40, 72),
              "同一件事的两个情绪片段，内部关联更强；存储强度也更高。",
              fill="#555", font=f_sub)
    groups = [
        ("内部关联强度", d["links"], 1.5, "1.5"),
        ("存储强度", d["storage"], 1.5, "1.5"),
        ("置信度", d["confidence"], 1.0, "100%"),
    ]
    chart_h = 280
    base_y = 430
    bar_w = 120
    group_w = 300
    for i, (name, (emo, neu), maxv, maxlabel) in enumerate(groups):
        gx = 80 + i * group_w
        draw.text((gx + 20, 120), name, fill="#111", font=f_label)
        for j, (val, label, color) in enumerate(
            ((emo, "情绪", "#c0392b"), (neu, "中性", "#b0b0b0"))
        ):
            bh = val / maxv * chart_h
            x = gx + 20 + j * (bar_w + 30)
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            draw.text((x + 30, y - 28), f"{val:.2f}", fill="#222", font=f_val)
            draw.text((x + 28, base_y + 12), label, fill="#333", font=f_label)
    draw.line([(60, base_y), (W - 60, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.5, "一半"), (1.0, "满")):
        y = base_y - frac * chart_h
        draw.line([(60, y), (W - 60, y)], fill="#e5e5e5", width=1)
        draw.text((20, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 480),
              "情绪事件的内部链接 1.2 vs 中性 1.0；存储强度 1.05 vs 1.0；置信度 0.93 vs 0.90。",
              fill="#c0392b", font=f_note)
    draw.text((40, 520),
              "对应脑科学：杏仁核-海马耦合让情绪事件彼此关联更紧，一个线索就能唤起整个情绪片段。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round3_emotion_links.png")
    img.save(path)
    return path


def chart_emotion_regression() -> str:
    """第 3 轮回归总览：88 题仍满分、测试全过。"""
    W, H = 1000, 520
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(18)
    f_label = _font(20)
    f_val = _font(20)
    draw.text((40, 26), "第 3 轮回归检查：新机制没有伤到旧能力", fill="#111", font=f_title)
    draw.text((40, 72),
              "加了情绪巩固后，标准 88 题仍然全部满分，90 个单元测试全部通过。",
              fill="#555", font=f_sub)
    categories = [
        ("记住事实", 1.0, 24),
        ("记住事件", 1.0, 24),
        ("之后发生了什么", 1.0, 24),
        ("没聊过不乱说", 1.0, 16),
    ]
    chart_h = 260
    base_y = 380
    bar_w = 130
    x0 = 130
    for i, (name, val, n) in enumerate(categories):
        x = x0 + i * 200
        bh = val * chart_h
        y = base_y - bh
        draw.rectangle([x, y, x + bar_w, base_y], fill="#1a7f37")
        draw.text((x + 40, y - 28), f"{val:.0%}", fill="#222", font=f_val)
        draw.text((x + 2, base_y + 12), f"{name}（{n}题）", fill="#333", font=f_label)
    draw.line([(80, base_y), (W - 60, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(80, y), (W - 60, y)], fill="#e5e5e5", width=1)
        draw.text((30, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 450),
              "测试：90/90 通过（新增 3 个情绪巩固测试）；官方包对比数据沿用第 2 轮（mem0 0.705 / "
              "cognitive 0.205 / Mnemosis 0.818）。",
              fill="#555", font=f_sub)
    path = os.path.join(_OUT, "round3_emotion_regression.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    for fn in (chart_emotion_retention, chart_emotion_links, chart_emotion_regression):
        print("written:", fn())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
