"""Render round-13 (journey overview + zh 10k) Chinese charts."""

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


MILESTONES = [
    ("第1轮", "REM 睡眠联想/矛盾消解", "88 题四类全满分"),
    ("第2轮", "睡眠巩固 + 模式补全", "10k 时序 85.8% → 97.2%"),
    ("第3轮", "情绪记忆强化", "30天保留率 6.9% vs 1.1%（约6倍）"),
    ("第4轮", "事实更新（顺应）", "旧事实淘汰 20/20、矛盾清零"),
    ("第5轮", "模式分离", "相似记忆差距 0 → 0.08"),
    ("第6轮", "自信校准", "校准误差 0.131 → 0.073"),
    ("第7轮", "校准感知复习", "长对话4周后 100% vs 83%"),
    ("第8轮", "A/B 及时止损", "坏偏好 0.964 → 0.936，默认关"),
    ("第9轮", "中文停用词", "中文关键词 26.5 → 12.5"),
    ("第10轮", "精准事件偏好", "10k 总命中 96.5% → 99.6%"),
    ("第11轮", "中文日期归一", "跨格式日期 1/12 → 12/12"),
    ("第12轮", "中文200会话压测", "69.1% → 99.3%"),
    ("第13轮", "中文10k压测", "50.3% → 98.8%（时序 2.2% → 97.6%）"),
]


def chart_journey() -> str:
    rows = MILESTONES
    W, H = 1250, 120 + len(rows) * 52
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_head = _font(19)
    f_row = _font(18)
    draw.text((40, 24), "Mnemosis 迭代里程碑：12 轮真实测评驱动", fill="#111",
              font=f_title)
    draw.text((40, 66),
              "每一轮都做了：论文 → 机制 → 真实测评 → 中文图表 → 提交 Git。",
              fill="#555", font=f_sub)
    headers = ["轮次", "做了什么", "关键数字（真实测评）"]
    col_x = [40, 210, 520]
    y = 100
    draw.line([(30, y), (W - 30, y)], fill="#999", width=2)
    for hx, htxt in zip(col_x, headers):
        draw.text((hx, y + 6), htxt, fill="#111", font=f_head)
    y += 48
    draw.line([(30, y), (W - 30, y)], fill="#999", width=2)
    for round_name, what, num in rows:
        y += 52
        draw.text((col_x[0], y), round_name, fill="#1a7f37", font=f_row)
        draw.text((col_x[1], y), what, fill="#222", font=f_row)
        draw.text((col_x[2], y), num, fill="#222", font=f_row)
        draw.line([(30, y + 26), (W - 30, y + 26)], fill="#e5e5e5", width=1)
    path = os.path.join(_OUT, "round13_journey.png")
    img.save(path)
    return path


def chart_zh10k() -> str:
    with open(os.path.join(_RESULTS, "zh_locomo_10k.json"), encoding="utf-8") as f:
        d = json.load(f)
    on = d["on"]
    W, H = 1050, 560
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(19)
    f_val = _font(18)
    f_note = _font(17)
    draw.text((40, 26), f"中文 {on['total'][1]} 道题压测：全部保持高分", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "3 个中文角色、上万条事件；开启全部中文优化后的分项命中率。",
              fill="#555", font=f_sub)
    kinds = [
        ("记住事件", on["kind_hit5"]["event"]),
        ("之后发生了什么", on["kind_hit5"]["temporal"]),
        ("总命中", on["total"]),
    ]
    chart_h = 280
    base_y = 400
    bar_w = 160
    x0 = 120
    for i, (name, (hits, n)) in enumerate(kinds):
        x = x0 + i * 300
        val = hits / n
        bh = val * chart_h
        y = base_y - bh
        draw.rectangle([x, y, x + bar_w, base_y], fill="#1a7f37")
        draw.text((x + 44, y - 28), f"{val:.1%}", fill="#222", font=f_val)
        draw.text((x + 6, base_y + 12), name, fill="#333", font=f_label)
    draw.line([(70, base_y), (W - 60, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(70, y), (W - 60, y)], fill="#e5e5e5", width=1)
        draw.text((30, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 450),
              f"没聊过不乱说 {on['kind_hit5']['distractor'][0]}/"
              f"{on['kind_hit5']['distractor'][1]}；关键词数平均 {on['avg_query_tokens']} 个。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round13_zh10k.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_journey())
    if os.path.exists(os.path.join(_RESULTS, "zh_locomo_10k.json")):
        print("written:", chart_zh10k())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
