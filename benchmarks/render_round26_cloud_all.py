"""Round-26 chart: all real projects with cloud qwen3.7-plus (same 12 Qs)."""

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
    accuracy = [
        ("Mnemosis", 1.00, "#7b2ff7"),
        ("mem0 官方包", 0.833, "#1a7f37"),
        ("腾讯 Agent", 0.833, "#d97706"),
        ("CAM 官方仓库", 0.667, "#0e7490"),
        ("cognitive-memory", 0.25, "#b91c1c"),
    ]
    retrieval = [
        ("Mnemosis", 1.00, "#7b2ff7"),
        ("mem0 官方包", 0.70, "#1a7f37"),
        ("腾讯 Agent", 0.333, "#d97706"),
        ("CAM 官方仓库", 0.50, "#0e7490"),
        ("cognitive-memory", 0.20, "#b91c1c"),
    ]
    W, H = 1580, 820
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(18)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 28), "第 26 轮：五个真实记忆项目 × 云端 qwen3.7-plus（同一 12 题）",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "作答统一用你部署的最新千问（云端，temperature=0）；检索上下文来自各项目自己的真实流水线。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① 12 题回答准确率（越高越好）", accuracy),
        (1, "② 同一 12 题检索命中@5（越高越好）", retrieval),
    ]
    panel_w = (W - 120) // 2
    chart_h = 330
    base_y = 480
    for p, title, rows in panels:
        x0 = 50 + p * (panel_w + 20)
        draw.text((x0, 130), title, fill="#111", font=f_panel)
        draw.line([(x0, base_y), (x0 + panel_w - 10, base_y)], fill="#999", width=2)
        for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
            y = base_y - frac * chart_h
            draw.line([(x0, y), (x0 + panel_w - 10, y)], fill="#e5e5e5", width=1)
            draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
        bar_w = 92
        step = (panel_w - 20) // len(rows)
        for i, (name, val, color) in enumerate(rows):
            bx = x0 + 16 + i * step
            bh = val * chart_h
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
            draw.text((bx + 26, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
            draw.text((bx - 10, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 585),
              "怎么看：第一栏比“模型能不能答对”，第二栏比“记忆库能不能把答案句找回来”。"
              "Mnemosis 两项都满分；腾讯换上千问后答得好但库找不全；CAM 换上千问后检索比原来好一点，"
              "但仍有两道时序题找不到“后一件事”。",
              fill="#555", font=f_note)
    draw.text((42, 640),
              "CAM 细节：3 道防幻觉题答“Not mentioned.”（语义上是对的拒绝），但按同一套严格规则"
              "“必须答 unknown”记 0 分，与历史口径保持一致。",
              fill="#555", font=f_note)
    draw.text((42, 695),
              "检索@5 口径：Mnemosis=88 题全量中同一批 12 题；mem0/cognitive=各自官方包真实检索；"
              "腾讯=CAM=云端千问抽取/推理后的真实检索。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round26_cloud_all_projects.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
