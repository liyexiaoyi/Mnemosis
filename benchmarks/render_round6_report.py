"""Render round-6 (confidence calibration) Chinese charts."""

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


def _data() -> dict:
    with open(os.path.join(_RESULTS, "calibration_eval.json"), encoding="utf-8") as f:
        return json.load(f)


def chart_ece() -> str:
    d = _data()
    controlled = d["controlled"]
    real = d["real_locomo"]
    W, H = 1100, 620
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(19)
    f_val = _font(18)
    f_note = _font(17)
    draw.text((40, 26), "自信校准：说“有把握”之前，先看看历史命中率", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "校准误差（ECE）越低越好：系统说的把握和实际答对率越接近。"
              "左=受控场景，右=真实 88 题。",
              fill="#555", font=f_sub)
    groups = [
        ("受控场景", controlled["ece_raw"], controlled["ece_calibrated"]),
        ("真实 88 题", real["ece_raw"], real["ece_calibrated"]),
    ]
    chart_h = 300
    base_y = 420
    bar_w = 150
    for gi, (name, raw, cal) in enumerate(groups):
        gx = 100 + gi * 460
        draw.text((gx + 20, 130), name, fill="#111", font=f_label)
        for j, (val, label, color) in enumerate(
            ((raw, "校准前", "#c0392b"), (cal, "校准后", "#1a7f37"))
        ):
            bh = val / 0.2 * chart_h
            x = gx + 20 + j * 210
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            draw.text((x + 40, y - 28), f"{val:.3f}", fill="#222", font=f_val)
            draw.text((x + 28, base_y + 12), label, fill="#333", font=f_label)
    draw.line([(70, base_y), (W - 70, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.1, "0.1"), (0.2, "0.2")):
        y = base_y - frac / 0.2 * chart_h
        draw.line([(70, y), (W - 70, y)], fill="#e5e5e5", width=1)
        draw.text((30, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 480),
              "受控场景：0.131 → 0.073（降约 44%）；真实 88 题误差本就不大"
              "（0.137），且历史证据还少，变化有限。",
              fill="#111", font=f_note)
    draw.text((40, 520),
              "对应理论：置信度校准（Lichtenstein, Fischhoff & Phillips 1977；Yeung & Summerfield 2012）。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round6_ece_bars.png")
    img.save(path)
    return path


def chart_reliability() -> str:
    d = _data()["controlled"]
    raw = {r["predicted_bucket"]: r for r in d["reliability_raw"]}
    cal = {r["predicted_bucket"]: r for r in d["reliability_calibrated"]}
    W, H = 1100, 700
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(18)
    f_val = _font(16)
    chart_x0, chart_x1 = 120, 1000
    chart_y0, chart_y1 = 140, 560

    def px(x: float) -> int:
        return chart_x0 + int(x * (chart_x1 - chart_x0))

    def py(y: float) -> int:
        return chart_y1 - int(y * (chart_y1 - chart_y0))

    draw.text((40, 26), "可靠性图：说 70% 有把握，是不是真的 70% 答对？", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "点越靠近斜线越准。红色=校准前，绿色=校准后（用每条记忆的历史命中率修正）。",
              fill="#555", font=f_sub)
    draw.line([(chart_x0, chart_y1), (chart_x1, chart_y1)], fill="#999", width=2)
    draw.line([(chart_x0, chart_y0), (chart_x0, chart_y1)], fill="#999", width=2)
    for i in range(6):
        x = px(i * 0.2)
        draw.line([(x, chart_y0), (x, chart_y1)], fill="#e5e5e5", width=1)
        draw.text((x - 12, chart_y1 + 8), f"{i * 0.2:.1f}", fill="#666", font=f_val)
    for i in range(6):
        y = py(i * 0.2)
        draw.line([(chart_x0, y), (chart_x1, y)], fill="#e5e5e5", width=1)
        draw.text((chart_x0 - 42, y - 10), f"{i * 0.2:.1f}", fill="#666", font=f_val)
    # diagonal (perfect calibration)
    draw.line([(px(0), py(0)), (px(1), py(1))], fill="#999", width=2)
    draw.text((px(0.82), py(0.78)), "完美校准线", fill="#777", font=f_label)

    def plot(rows, color, label):
        points = []
        for bucket in sorted(rows):
            r = rows[bucket]
            bucket_start = float(bucket.split("-")[0])
            center = bucket_start + 0.1
            empirical = r["empirical_hit_rate"]
            points.append((center, empirical))
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            draw.line([(px(x1), py(y1)), (px(x2), py(y2))], fill=color, width=4)
        for x, y in points:
            draw.ellipse(
                [px(x) - 7, py(y) - 7, px(x) + 7, py(y) + 7], fill=color
            )
        draw.text((px(0.55), py(0.55 if color == "#c0392b" else 0.42)),
                  label, fill=color, font=f_label)

    plot(raw, "#c0392b", "校准前（红）")
    plot(cal, "#1a7f37", "校准后（绿）")
    draw.text((40, 610),
              "校准后分桶更细、更贴对角线；校准误差 0.131 → 0.073。",
              fill="#111", font=f_label)
    path = os.path.join(_OUT, "round6_reliability.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_ece())
    print("written:", chart_reliability())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
