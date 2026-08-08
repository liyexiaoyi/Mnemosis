"""Round-254 chart: concept-coverage retrieval retest (before/after)."""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont


_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
_OUT = os.path.normpath(os.path.join(_BENCH, "..", "..", "outputs", "charts"))


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simsun.ttc"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def chart() -> str:
    data = json.load(
        open(os.path.join(_WORK, "gamedev_spot.json"), encoding="utf-8")
    )
    dims = data["dimensions"]
    projects = ["mnemosis", "mem0", "cognitive"]
    project_labels = {
        "mnemosis": "Mnemosis",
        "mem0": "mem0官方",
        "cognitive": "cognitive",
    }
    colors = {"mnemosis": "#7b2ff7", "mem0": "#1a7f37", "cognitive": "#e8590c"}

    W, H = 1600, 1120
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(17)
    f_h = _font(19)
    f_label = _font(15)
    f_val = _font(15)

    draw.text(
        (42, 26),
        "第 254 轮：概念覆盖检索复测（同一套游戏制作抽查）",
        fill="#111",
        font=f_title,
    )
    draw.text(
        (42, 72),
        "机制：检测“A 和 B 分别……”这类多概念问题，按概念分块补查，"
        "保证每个概念的记忆都进前 4 条。",
        fill="#555",
        font=f_sub,
    )

    # Panel A: Mnemosis per-dim before/after
    y = 120
    draw.text(
        (42, y),
        "A. Mnemosis 检索命中：修复前（第253轮）vs 修复后（本轮）",
        fill="#111",
        font=f_h,
    )
    y += 38
    before = {
        "版本记忆": 1, "路径命名": 1, "数值参数": 0, "场景结构": 1,
        "信号连接": 1, "资源细节": 1, "开发时间线": 1, "报错修复": 1,
        "决策原因": 1, "更新内容": 1,
    }
    after = data["retrieval"]["mnemosis"]["per_dim"]
    base_y = y + 170
    chart_h = 150
    group_w = 150
    for i, dim in enumerate(dims):
        gx = 70 + i * group_w
        draw.text((gx, base_y + 10), dim, fill="#111", font=f_label)
        for pi, (label, values, color) in enumerate(
            (
                ("前", before, "#adb5bd"),
                ("后", after, "#7b2ff7"),
            )
        ):
            bx = gx + pi * 70
            value = values.get(dim, 0.0)
            bh = value * chart_h
            draw.rectangle([bx, base_y - bh, bx + 56, base_y], fill=color)
            if value > 0:
                draw.text((bx + 18, base_y - bh + 5), str(value), fill="white", font=f_val)
    draw.text((350, y - 8), "灰=修复前  紫=修复后", fill="#555", font=f_label)
    draw.text(
        (42, base_y + 42),
        "变化：只有“数值参数”从 0 变 1（320 和 420 两条都找回来了），"
        "其他 9 维不受影响；总分 9 → 10。",
        fill="#555",
        font=f_sub,
    )

    # Panel B: final totals + model accuracy
    y = base_y + 100
    draw.text(
        (42, y),
        "B. 最终对比（检索总分 + 三个模型作答）",
        fill="#111",
        font=f_h,
    )
    y += 42
    group_w2 = 500
    for mi, (label, key) in enumerate(
        (
            ("检索命中", "retrieval"),
            ("作答(云端)", "accuracy_cloud"),
            ("作答(本地)", "accuracy_local"),
        )
    ):
        gx = 70 + mi * group_w2
        draw.text((gx + 80, y - 10), label, fill="#111", font=f_h)
        for pi, project in enumerate(projects):
            total = data[key][project]["total"]
            score = total / 10.0
            bx = gx + pi * 150
            bh = score * 140
            draw.rectangle([bx, y + 150 - bh, bx + 120, y + 150], fill=colors[project])
            draw.text((bx + 30, y + 150 - bh + 5), f"{total}/10", fill="white", font=f_val)
            draw.text((bx + 2, y + 158), project_labels[project], fill="#111", font=f_label)
    y += 210
    draw.text(
        (42, y),
        "结果：Mnemosis 修复后检索 10/10、三模型作答 10/10，与 mem0 官方持平；"
        "cognitive-memory 仍 3/10。",
        fill="#555",
        font=f_sub,
    )
    draw.text(
        (42, y + 40),
        "回归：307 个单元测试全过，一键全测评全绿；其他 9 维检索结果与修复前一致，"
        "说明增强是“补漏”而不是“换题”。",
        fill="#555",
        font=f_sub,
    )

    path = os.path.join(_OUT, "round254_concept.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
