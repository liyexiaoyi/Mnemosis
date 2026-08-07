"""Render round-4 (constructivist assimilation/accommodation) Chinese charts."""

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


def chart_accommodation() -> str:
    with open(
        os.path.join(_RESULTS, "accommodation_eval.json"), encoding="utf-8"
    ) as handle:
        d = json.load(handle)
    lopsided = d["lopsided_evidence"]
    balanced = d["balanced_control"]
    trials = d["trials"]
    W, H = 1180, 620
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(19)
    f_val = _font(18)
    f_note = _font(17)
    draw.text((40, 26), "事实更新专项：旧知识被新证据“顺应”掉", fill="#111", font=f_title)
    draw.text((40, 72),
              f"每组 {trials} 对事实。左=新证据明显更多（4:1），右=两边证据一样多（对照组）。",
              fill="#555", font=f_sub)
    groups = [
        ("新证据碾压（4:1）", [
            ("旧事实被淘汰", lopsided["stale_retired"], "#1a7f37"),
            ("新事实保住", lopsided["new_kept"], "#1a7f37"),
            ("新事实能答对", lopsided["new_top1_recall"], "#1a7f37"),
            ("剩余矛盾", lopsided["conflicts_after_sum"], "#c0392b"),
        ]),
        ("证据一样多（对照组）", [
            ("旧事实被淘汰", balanced["stale_retired"], "#c0392b"),
            ("新事实能答对", balanced["new_top1_recall"], "#1a7f37"),
            ("剩余矛盾", balanced["conflicts_after_sum"], "#e6a700"),
        ]),
    ]
    chart_h = 280
    base_y = 430
    bar_w = 100
    group_w = 500
    for gi, (name, rows) in enumerate(groups):
        gx = 70 + gi * group_w
        draw.text((gx + 10, 92), name, fill="#111", font=f_label)
        for ri, (label, val, color) in enumerate(rows):
            frac = val / trials
            bh = frac * chart_h
            x = gx + 10 + ri * 118
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            draw.text((x + 28, y - 34), f"{val}/{trials}", fill="#222", font=f_val)
            draw.text((x - 6, base_y + 10), label, fill="#333", font=f_label)
    draw.line([(60, base_y), (W - 60, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(60, y), (W - 60, y)], fill="#e5e5e5", width=1)
        draw.text((25, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 480),
              "结论：证据明显占优时，系统会“顺应”——淘汰旧事实、留下新事实、矛盾归零；"
              "证据持平时不强行站队，把矛盾留给使用者判断。",
              fill="#111", font=f_note)
    draw.text((40, 520),
              "对应理论：皮亚杰建构主义“同化-顺应”（CAM，Li 等，NeurIPS 2025）。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round4_accommodation.png")
    img.save(path)
    return path


def chart_regression() -> str:
    W, H = 1000, 520
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(18)
    f_label = _font(20)
    f_val = _font(20)
    draw.text((40, 26), "第 4 轮回归检查：新机制没有伤到旧能力", fill="#111", font=f_title)
    draw.text((40, 72),
              "加了“同化-顺应”后，标准 88 题仍然全部满分，93 个单元测试全部通过。",
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
              "测试：93/93 通过（新增 3 个同化-顺应测试）；生命周期、情绪巩固等旧能力全部保持。",
              fill="#555", font=f_sub)
    path = os.path.join(_OUT, "round4_regression.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_accommodation())
    print("written:", chart_regression())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
