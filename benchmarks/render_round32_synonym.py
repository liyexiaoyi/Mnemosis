"""Round-32 chart: Chinese synonym expansion at 10k scale."""

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
    coverage = [
        ("同义词开", 1.00, "#7b2ff7"),
        ("同义词关", 0.889, "#b0b0b0"),
    ]
    ordered = [
        ("同义词开", 1.00, "#7b2ff7"),
        ("同义词关", 0.667, "#b0b0b0"),
    ]
    llm = [
        ("同义词开", 0.667, "#7b2ff7"),
        ("同义词关", 0.333, "#b0b0b0"),
    ]
    W, H = 1560, 840
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(18)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 28), "第 32 轮：中文同义词扩展 · 10k 规模验证",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "3 个带日期步骤的场景埋进 8,679 条噪声；问题用同义词说法"
              "（筹备/旅游/餐厅/礼物/迁居/酒店），记忆用原词（准备/旅行/饭店/礼品/搬家/宾馆）。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① 步骤找回（9 步里找回几步）", coverage),
        (1, "② 顺序正确（3 题里几题按时序）", ordered),
        (2, "③ 千问作答（3 题对几题）", llm),
    ]
    panel_w = (W - 140) // 3
    chart_h = 330
    base_y = 500
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
            bh = max(val, 0.02) * chart_h
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
            draw.text((bx + 22, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
            draw.text((bx - 6, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：紫色=开启同义词扩展，灰色=关闭。差别最大的场景是“迁居/酒店”："
              "记忆里写“搬家服务/宾馆”，与查询字面零字形重叠，关闭时丢 1 步且乱序，"
              "开启后 3/3 找回并按时间排序。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "另外两个场景（筹备/旅游、餐厅/礼物）因为“旅”等共享字形和联想传播，"
              "关闭时也能找回——这是 Mnemosis 原有能力的体现，同义词扩展负责的是"
              "纯近义词链路（零字形重叠）。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "同义词组从 13 组扩到 30 组（餐厅/饭馆/饭店、酒店/宾馆、礼物/礼品、"
              "相机/照相机、做饭/烹饪 等）；recall 增加 zh_synonyms 开关便于 A/B。",
              fill="#555", font=f_note)
    draw.text((42, 740),
              "千问作答：开启 2/3（迁居场景答对），关闭 1/3；阿丽题两轮都答 unknown"
              "（模型拒答，上下文其实有步骤）。冲突 10k 与同义词 10k 基准已接入 CI。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round32_synonym_10k.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
