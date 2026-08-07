"""Render round-12 (Chinese scale + LLM grounding) Chinese charts."""

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


def chart_zh_scale() -> str:
    with open(os.path.join(_RESULTS, "zh_locomo_bench.json"), encoding="utf-8") as f:
        d = json.load(f)
    on = d["on"]
    off = d["off"]
    W, H = 1150, 640
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(19)
    f_val = _font(18)
    f_note = _font(17)
    draw.text((40, 26), "中文 200 会话压测：停用词过滤的价值藏不住了", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "3 个中文角色、198 条事件、411 道题。绿=开启中文停用词过滤，灰=关闭。",
              fill="#555", font=f_sub)
    rows = [
        ("总命中", on["total"][0] / on["total"][1],
         off["total"][0] / off["total"][1]),
        ("记住事件", on["kind_hit5"]["event"][0] / on["kind_hit5"]["event"][1],
         off["kind_hit5"]["event"][0] / off["kind_hit5"]["event"][1]),
        ("之后发生了什么", on["kind_hit5"]["temporal"][0] / on["kind_hit5"]["temporal"][1],
         off["kind_hit5"]["temporal"][0] / off["kind_hit5"]["temporal"][1]),
    ]
    chart_h = 280
    base_y = 410
    bar_w = 150
    for gi, (name, onv, offv) in enumerate(rows):
        gx = 45 + gi * 380
        draw.text((gx + 10, 105), name, fill="#111", font=f_label)
        for j, (val, label, color) in enumerate(
            ((onv, "过滤后", "#1a7f37"), (offv, "不过滤", "#b0b0b0"))
        ):
            bh = val * chart_h
            x = gx + 20 + j * 200
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            draw.text((x + 38, y - 28), f"{val:.1%}", fill="#222", font=f_val)
            draw.text((x + 20, base_y + 12), label, fill="#333", font=f_label)
    draw.line([(40, base_y), (W - 40, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(40, y), (W - 40, y)], fill="#e5e5e5", width=1)
        draw.text((12, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 470),
              "总命中 69.1% → 99.3%；“之后发生了什么”47.7% → 98.5%。"
              "规模一大，虚词串味就变成致命噪音，过滤后全部回归。",
              fill="#111", font=f_note)
    draw.text((40, 515),
              "跨格式日期也保持 12/12（上一轮归一），英文 88/200 无回归。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round12_zh_scale.png")
    img.save(path)
    return path


def chart_zh_llm() -> str:
    with open(os.path.join(_RESULTS, "zh_locomo_bench.json"), encoding="utf-8") as f:
        d = json.load(f)
    llm = d["llm_zh"]
    W, H = 1000, 560
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(20)
    f_val = _font(18)
    f_note = _font(17)
    draw.text((40, 26), "中文问答：千问模型 裸答 vs 接 Mnemosis 记忆", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "同一 12 道中文题（事实/事件/时序/没聊过不乱说），模型是 qwen2.5:3b。",
              fill="#555", font=f_sub)
    chart_h = 300
    base_y = 410
    bar_w = 170
    for j, (cond, label, color) in enumerate(
        (("bare", "裸答", "#b0b0b0"), ("with_mnemosis", "+Mnemosis 记忆", "#1a7f37"))
    ):
        val = llm[cond]["accuracy"]
        bh = val * chart_h
        x = 110 + j * 380
        y = base_y - bh
        draw.rectangle([x, y, x + bar_w, base_y], fill=color)
        draw.text((x + 46, y - 30), f"{val:.0%}", fill="#222", font=f_val)
        draw.text((x + 8, base_y + 12), label, fill="#333", font=f_label)
    draw.line([(60, base_y), (W - 60, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(60, y), (W - 60, y)], fill="#e5e5e5", width=1)
        draw.text((25, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 470),
              f"裸答 25% → 接记忆 83%：中文内容先检索再回答，提升 58 个百分点。",
              fill="#111", font=f_note)
    draw.text((40, 515),
              "和英文矩阵结论一致：Mnemosis 给模型的中文上下文同样有效。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round12_zh_llm.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_zh_scale())
    print("written:", chart_zh_llm())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
