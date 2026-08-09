# -*- coding: utf-8 -*-
"""Render the official-package comparison table as a Chinese PNG.

Falls back to Pillow (available in the codex runtime) when headless Edge is
not usable.
"""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont


_BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
_RESULTS = os.path.join(_BENCH_DIR, "results", "official_packages_compare.json")
_OUT = os.path.normpath(
    os.path.join(_BENCH_DIR, "..", "..", "outputs", "charts",
                 "iteration_real_compare_table_zh.png")
)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\msjh.ttc",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main() -> int:
    data = json.load(open(_RESULTS, encoding="utf-8"))
    unified_path = os.path.join(_BENCH_DIR, "results", "unified_compare.json")
    unified = {}
    if os.path.exists(unified_path):
        unified = json.load(open(unified_path, encoding="utf-8"))["table"]

    def pct(v):
        return f"{v:.0%}"

    rows = []
    if "mem0_official" in data:
        d = data["mem0_official"]
        rows.append(("mem0 官方包", pct(d.get("fact@5")), pct(d.get("event@5")),
                     pct(d.get("temporal@5")), f"{d.get('distractor_pass', 0)}/16"))
    if "cognitive_memory_official" in data:
        d = data["cognitive_memory_official"]
        rows.append(("cognitive-memory 官方包", pct(d.get("fact@5")), pct(d.get("event@5")),
                     pct(d.get("temporal@5")), f"{d.get('distractor_pass', 0)}/16"))
    for key, label in (("BM25", "BM25"), ("嵌入 kNN", "嵌入 kNN"),
                       ("Mem0-style", "Mem0-style"), ("HippoRAG-style", "HippoRAG-style")):
        d = unified.get(key, {})
        rows.append((label, pct(d.get("fact@5")), pct(d.get("event@5")),
                     pct(d.get("temporal@5")), f"{d.get('distractor_pass', 0)}/16"))
    for key, label in (("Mnemosis 词法", "Mnemosis 词法"), ("Mnemosis ngram", "Mnemosis ngram")):
        d = unified.get(key, {})
        rows.append((label, pct(d.get("fact@5")), pct(d.get("event@5")),
                     pct(d.get("temporal@5")), f"{d.get('distractor_pass', 0)}/16"))

    W, H = 1100, 210 + len(rows) * 62
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(26)
    f_sub = _font(17)
    f_head = _font(20)
    f_row = _font(20)

    draw.text((40, 25), "真实能力对比表：GitHub 项目 vs Mnemosis（同一 88 题）",
              fill="#111", font=f_title)
    draw.text((40, 66), "“记住事实”= 问‘喜欢什么颜色’能不能答对；“记住事件”= 那天发生了什么；"
                        "“之后发生了什么”= 去了植物园之后干了啥；“没聊过不乱说”= 没提过的话题会不会硬编",
              fill="#555", font=f_sub)

    headers = ["系统", "记住事实", "记住事件", "之后发生了什么", "没聊过不乱说"]
    col_x = [40, 330, 500, 680, 880]
    y = 130
    draw.line([(30, y), (W - 30, y)], fill="#999", width=2)
    for hx, htxt in zip(col_x, headers):
        draw.text((hx, y + 6), htxt, fill="#111", font=f_head)
    y += 50
    draw.line([(30, y), (W - 30, y)], fill="#999", width=2)

    for row in rows:
        y += 62
        name = row[0]
        is_mn = name.startswith("Mnemosis")
        name_color = "#1a7f37" if is_mn else "#222"
        draw.text((col_x[0], y), name, fill=name_color, font=f_row)
        for j, val in enumerate(row[1:], start=1):
            if val.endswith("/16"):
                good = val.startswith("16")
            else:
                good = val.startswith("100%")
            color = "#1a7f37" if good else "#c0392b"
            draw.text((col_x[j], y), val, fill=color, font=f_row)
        draw.line([(30, y + 32), (W - 30, y + 32)], fill="#e5e5e5", width=1)

    os.makedirs(os.path.dirname(_OUT), exist_ok=True)
    img.save(_OUT)
    print("written", _OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
