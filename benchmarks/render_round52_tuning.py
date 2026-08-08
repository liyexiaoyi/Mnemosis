"""Round-52 chart: desirable-difficulty tuning (synthetic stress + zh200)."""

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
    stress = [
        ("期望0.3", 0.446, 35, "#7b2ff7"),
        ("期望0.45", 0.446, 33, "#7b2ff7"),
        ("期望0.6", 0.446, 34, "#7b2ff7"),
        ("旧策略", 0.411, 31, "#b0b0b0"),
        ("不复习", 0.0, 0, "#d9c9c9"),
    ]
    zh = [
        ("期望0.3", 7),
        ("期望0.45", 6),
        ("期望0.6", 6),
        ("旧策略", 7),
        ("不复习", 5),
    ]
    W, H = 1560, 830
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(16)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 28), "第 52 轮：期望难度目标调参 + zh200 回归",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "合成压力集（配额紧张）找最优难度目标；中文 200 会话基准验证"
              "4 周后真实命中率是否受影响。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① 合成压力集：复习成功率（左）与保留条数（右）", stress, "stress"),
        (1, "② zh200：4 周后 12 题命中（越高越好）", zh, "zh"),
    ]
    panel_w = (W - 120) // 2
    chart_h = 300
    base_y = 500
    for p, title, rows, kind in panels:
        x0 = 50 + p * (panel_w + 20)
        draw.text((x0, 130), title, fill="#111", font=f_panel)
        draw.line([(x0, base_y), (x0 + panel_w - 10, base_y)], fill="#999", width=2)
        if kind == "stress":
            for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
                y = base_y - frac * chart_h
                draw.line([(x0, y), (x0 + panel_w - 10, y)], fill="#e5e5e5", width=1)
                draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
            bar_w = 66
            step = (panel_w - 20) // len(rows)
            for i, (name, rate, retained, color) in enumerate(rows):
                bx = x0 + 10 + i * step
                bh = max(rate, 0.02) * chart_h
                draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
                draw.text((bx + 14, base_y - bh + 6), f"{rate:.0%}",
                          fill="white", font=f_val)
                # retained as secondary number under label
                draw.text((bx - 18, base_y + 12), name, fill="#111", font=f_label)
                draw.text((bx - 18, base_y + 32), f"保留{retained}",
                          fill="#555", font=f_val)
        else:
            for frac, label in ((0.0, "0"), (4.0, "4"), (8.0, "8")):
                y = base_y - frac / 8.0 * chart_h
                draw.line([(x0, y), (x0 + panel_w - 10, y)], fill="#e5e5e5", width=1)
                draw.text((x0 - 30, y - 10), label, fill="#666", font=f_val)
            bar_w = 90
            step = (panel_w - 20) // len(rows)
            for i, (name, hit) in enumerate(rows):
                bx = x0 + 16 + i * step
                bh = hit / 8.0 * chart_h
                color = "#7b2ff7" if i < 3 else ("#b0b0b0" if i == 3 else "#d9c9c9")
                draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
                draw.text((bx + 30, base_y - bh + 6), str(hit),
                          fill="white", font=f_val)
                draw.text((bx - 8, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：左图在“配额紧张”时，三个期望难度目标都优于旧策略"
              "（成功率 44.6% vs 41.1%，保留 33-35 vs 31），目标 0.3 略优；",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "右图在 zh200（配额不紧张）上各策略命中 6-7/12，旧策略 7、期望 0.3 也是 7，"
              "不复习 5——期望难度无回归，复习仍然有效。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "结论：期望难度在配额紧张时是真实增益；zh200 上中性。"
              "回归：172 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round52_desirable_tuning.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
