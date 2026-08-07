"""Round-24 chart: TencentDB Agent Memory cloud retest (qwen3.7-plus).

Same 12 LoCoMo questions, answer side = qwen3.7-plus (DashScope cloud) for
every project. Retrieval@5 shows each project's own real retrieval pipeline.
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont


_BENCH = os.path.dirname(os.path.abspath(__file__))
_OUT = os.path.normpath(os.path.join(_BENCH, "..", "..", "outputs", "charts"))


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def chart() -> str:
    # answer accuracy with qwen3.7-plus on the same 12 questions
    accuracy = [
        ("Mnemosis", 1.00, "#7b2ff7"),
        ("mem0 官方包", 0.833, "#1a7f37"),
        ("腾讯 Agent", 0.833, "#d97706"),
        ("cognitive-memory", 0.25, "#b91c1c"),
    ]
    # each project's own real retrieval on the same 12 questions
    retrieval = [
        ("Mnemosis", 1.00, "#7b2ff7"),
        ("mem0 官方包", 0.70, "#1a7f37"),
        ("腾讯 Agent", 0.333, "#d97706"),
        ("cognitive-memory", 0.20, "#b91c1c"),
    ]

    W, H = 1520, 760
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 28), "第 24 轮：腾讯 Agent Memory 云端复测（qwen3.7-plus 作答）",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "同一 12 道题，作答全部换成你部署的最新版千问（云端 qwen3.7-plus，temperature=0），"
              "只有检索上下文来自各项目自己的真实记忆库。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① 12 题回答准确率（越高越好）", accuracy),
        (1, "② 同一 12 题检索命中@5（越高越好）", retrieval),
    ]
    panel_w = (W - 120) // 2
    chart_h = 330
    base_y = 470
    for panel_idx, (p, title, rows) in enumerate(panels):
        x0 = 50 + p * (panel_w + 20)
        draw.text((x0, 130), title, fill="#111", font=f_panel)
        # grid
        draw.line([(x0, base_y), (x0 + panel_w - 20, base_y)], fill="#999", width=2)
        for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
            y = base_y - frac * chart_h
            draw.line([(x0, y), (x0 + panel_w - 20, y)], fill="#e5e5e5", width=1)
            draw.text((x0 - 26, y - 10), label, fill="#666", font=f_val)
        bar_w = 88
        step = (panel_w - 10) // len(rows)
        for i, (name, val, color) in enumerate(rows):
            bx = x0 + 12 + i * step
            bh = val * chart_h
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
            draw.text((bx + 28, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
            draw.text((bx - 12, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 560),
              "怎么看这张图：左边比回答对了几题，右边比谁的记忆库能把正确答案找出来。"
              "换上新千问后腾讯从 0.25 升到 0.833，但它自己的抽取流程仍丢掉细节，"
              "两道时序题没找到“后一件事”只能答不知道。",
              fill="#555", font=f_note)
    draw.text((42, 610),
              "检索@5 说明：腾讯=云端千问抽取后的本地库检索；mem0/cognitive=各自官方包的真实检索；"
              "Mnemosis=88 题全量检索中的同一批 12 题。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round24_tencent_cloud.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
