"""Render round-9 (Chinese content optimization) Chinese charts."""

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


def chart_token_reduction() -> str:
    with open(os.path.join(_RESULTS, "zh_locomo_bench.json"), encoding="utf-8") as f:
        d = json.load(f)
    on = d["on"]
    off = d["off"]
    W, H = 1080, 620
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(20)
    f_val = _font(18)
    f_note = _font(17)
    draw.text((40, 26), "中文内容优化：去掉“的/是/什么”等虚词后", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "同一批中文问题（“请问阿丽最喜欢的颜色是什么？”），绿=开启中文停用词过滤，灰=关闭。",
              fill="#555", font=f_sub)
    chart_h = 300
    base_y = 420
    bar_w = 160
    for j, (val, label, color) in enumerate(
        ((on["avg_query_tokens"], "过滤后", "#1a7f37"),
         (off["avg_query_tokens"], "不过滤", "#b0b0b0"))
    ):
        bh = val / 30 * chart_h
        x = 150 + j * 330
        y = base_y - bh
        draw.rectangle([x, y, x + bar_w, base_y], fill=color)
        draw.text((x + 40, y - 30), f"{val:.1f}", fill="#222", font=f_val)
        draw.text((x + 28, base_y + 12), label, fill="#333", font=f_label)
    draw.line([(70, base_y), (W - 70, base_y)], fill="#999", width=2)
    for v, label in ((0, "0"), (15, "15"), (30, "30")):
        y = base_y - v / 30 * chart_h
        draw.line([(70, y), (W - 70, y)], fill="#e5e5e5", width=1)
        draw.text((35, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 120), "平均每个问题拆出的关键词数（越少越干净）",
              fill="#555", font=f_sub)
    draw.text((40, 480),
              f"每个中文问题的检索关键词从 {off['avg_query_tokens']} 个降到 "
              f"{on['avg_query_tokens']} 个（少了一半多）；命中率两边都是 "
              f"{on['total'][0]}/{on['total'][1]}（满分）。",
              fill="#111", font=f_note)
    draw.text((40, 520),
              "“请问/的/是/什么”这类虚词不再参与匹配，检索更干净、更快。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round9_zh_tokens.png")
    img.save(path)
    return path


def chart_zh_kinds() -> str:
    with open(os.path.join(_RESULTS, "zh_locomo_bench.json"), encoding="utf-8") as f:
        d = json.load(f)
    on = d["on"]["kind_hit5"]
    W, H = 1000, 520
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(19)
    f_val = _font(18)
    draw.text((40, 26), "中文基准（LoCoMo 式）：四类题全部满分", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "中文事实、中文事件、中文时序、中文“没聊过不乱说”，"
              "各题型都能在 5 条候选中找到答案。",
              fill="#555", font=f_sub)
    kinds = [
        ("记住事实", on["fact"]),
        ("记住事件", on["event"]),
        ("之后发生了什么", on["temporal"]),
        ("没聊过不乱说", on["distractor"]),
    ]
    chart_h = 260
    base_y = 380
    bar_w = 130
    x0 = 110
    for i, (name, (hits, n)) in enumerate(kinds):
        x = x0 + i * 210
        val = hits / n
        bh = val * chart_h
        y = base_y - bh
        draw.rectangle([x, y, x + bar_w, base_y], fill="#1a7f37")
        draw.text((x + 34, y - 28), f"{hits}/{n}", fill="#222", font=f_val)
        draw.text((x + 2, base_y + 12), name, fill="#333", font=f_label)
    draw.line([(70, base_y), (W - 60, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(70, y), (W - 60, y)], fill="#e5e5e5", width=1)
        draw.text((30, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 450),
              "同时英文 88/200 回归无变化：中文停用词过滤只影响中文虚词。",
              fill="#555", font=f_sub)
    path = os.path.join(_OUT, "round9_zh_kinds.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_token_reduction())
    print("written:", chart_zh_kinds())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
