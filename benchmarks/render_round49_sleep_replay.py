"""Round-49 chart: sleep replay / consolidation."""

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
    checks = [
        ("意外重放", 2),
        ("经验固化", 3),
        ("预测走摘要", 1),
        ("千问答对", 1),
    ]
    W, H = 1400, 840
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(18)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 28), "第 49 轮：睡眠重放与经验巩固",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "依据：海马重放（1994）与睡眠巩固（2013）——睡眠时优先重放意外事件，"
              "把步骤经验固化成语义摘要。",
              fill="#555", font=f_sub)

    x0 = 130
    base_y = 540
    chart_h = 280
    draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.5, "2"), (1.0, "4")):
        y = base_y - frac * chart_h
        draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 30, y - 10), label, fill="#666", font=f_val)
    for i, (name, val) in enumerate(checks):
        bx = x0 + 14 + i * 140
        scale = {"意外重放": 1.0, "经验固化": 1.0, "预测走摘要": 0.5,
                 "千问答对": 0.5}[name]
        bh = max(val, 0.1) * scale * chart_h / 2
        draw.rectangle([bx, base_y - bh, bx + 100, base_y], fill="#7b2ff7")
        draw.text((bx + 30, base_y - bh + 8), str(val), fill="white", font=f_val)
        draw.text((bx - 12, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 620),
              "场景：订机票 5 成功+1 意外失败、买相机 3 成功、打包箱子 2 成功+1 意外失败"
              "（两次失败都打破了 100% 成功历史）。sleep_replay() 后：",
              fill="#555", font=f_note)
    draw.text((42, 670),
              "① 两条意外记录被重放（检索成功计数+1，更易浮出）；"
              "② 三个步骤的经验固化为“历史成功率”语义摘要；"
              "③ predict_step 改走摘要（5/6）；④ 千问答对 5/6。",
              fill="#555", font=f_note)
    draw.text((42, 720),
              "回归：170 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round49_sleep_replay.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
