"""Round-253 chart: game-dev spot-check comparison (new domain/dimensions)."""

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

    W, H = 1600, 1280
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(17)
    f_h = _font(19)
    f_label = _font(15)
    f_val = _font(14)

    draw.text(
        (42, 26),
        "第 253 轮抽查：本机游戏制作记忆对比（全新维度）",
        fill="#111",
        font=f_title,
    )
    draw.text(
        (42, 72),
        "内容：一个中文 Godot 项目的 18 条开发记忆（版本/路径/数值/节点树/信号/资源/"
        "时间线/报错/决策/更新）；3 个真实安装项目，同一个库、同一套题。",
        fill="#555",
        font=f_sub,
    )

    # Panel A: retrieval hit@4 per dimension
    y = 130
    draw.text((42, y), "A. 检索命中（前 4 条里有没有答案；每题 1 分）", fill="#111", font=f_h)
    y += 40
    base_y = y + 190
    chart_h = 170
    group_w = 150
    bar_w = 42
    for i, dim in enumerate(dims):
        gx = 70 + i * group_w
        draw.text((gx, base_y + 10), dim, fill="#111", font=f_label)
        for pi, project in enumerate(projects):
            score = data["retrieval"][project]["per_dim"].get(dim, 0.0)
            bx = gx + pi * 48
            bh = score * chart_h
            draw.rectangle(
                [bx, base_y - bh, bx + bar_w, base_y], fill=colors[project]
            )
            if score > 0:
                draw.text((bx + 6, base_y - bh + 4), f"{score:.0%}", fill="white", font=f_val)
    # legend
    for pi, project in enumerate(projects):
        lx = 860 + pi * 180
        draw.rectangle([lx, y - 18, lx + 24, y - 2], fill=colors[project])
        draw.text((lx + 30, y - 20), project_labels[project], fill="#111", font=f_label)
    draw.text(
        (42, base_y + 42),
        "怎么看：mem0 官方这次 10 项全中；Mnemosis 差在“数值参数”（320/420 分散在两条记忆，"
        "前 4 条只带回了一条）；cognitive-memory 只中 3 项。",
        fill="#555",
        font=f_sub,
    )

    # Panel B: model answer accuracy
    y = base_y + 100
    draw.text(
        (42, y),
        "B. 拿到自己检索的前 4 条后作答（云端千问 / 本地 qwen2.5:3b / DeepSeek V4 Flash）",
        fill="#111",
        font=f_h,
    )
    y += 44
    model_keys = [
        ("云端千问", "accuracy_cloud"),
        ("本地qwen", "accuracy_local"),
        ("DeepSeek我", "accuracy_codex"),
    ]
    group_w2 = 500
    for mi, (model_label, key) in enumerate(model_keys):
        gx = 70 + mi * group_w2
        draw.text((gx + 80, y - 8), model_label, fill="#111", font=f_h)
        for pi, project in enumerate(projects):
            score = data[key][project]["total"] / 10.0
            bx = gx + pi * 150
            bh = score * 150
            draw.rectangle([bx, y + 170 - bh, bx + 120, y + 170], fill=colors[project])
            draw.text((bx + 34, y + 170 - bh + 4), f"{score:.0%}", fill="white", font=f_val)
            draw.text((bx + 2, y + 178), project_labels[project], fill="#111", font=f_label)
    y += 250
    totals = {
        project: f"{data['retrieval'][project]['total']}/10"
        for project in projects
    }
    draw.text(
        (42, y),
        "总结：检索命中 Mnemosis 9/10、mem0 10/10、cognitive 3/10；"
        "三模型作答基本跟随检索——记忆系统先决定上限，模型只决定发挥。",
        fill="#555",
        font=f_sub,
    )
    draw.text(
        (42, y + 40),
        "方法：同一 18 条记忆分别真实写入三个官方包；每题取各自前 4 条给模型作答；"
        "答案按关键词客观判分，找不到必须答“不知道”。",
        fill="#555",
        font=f_sub,
    )

    path = os.path.join(_OUT, "round253_gamedev.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
