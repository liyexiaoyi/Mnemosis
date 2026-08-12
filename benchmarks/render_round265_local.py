"""Round-265 local-model chart: same retrieval, local answer models."""

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
        open(os.path.join(_WORK, "job_spot.json"), encoding="utf-8")
    )
    dims = data["dimensions"]
    projects = ["mnemosis", "mem0"]
    labels = {"mnemosis": "Mnemosis", "mem0": "mem0官方"}
    colors = {"mnemosis": "#7b2ff7", "mem0": "#1a7f37"}
    models = [
        ("云端千问", "accuracy_cloud"),
        ("DeepSeek我", "accuracy_codex"),
        ("本地qwen2.5:3b", "accuracy_local_qwen2.5_3b"),
        ("本地gemma3:12b", "accuracy_local_gemma3_12b"),
    ]

    W, H = 1500, 1220
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(17)
    f_h = _font(20)
    f_label = _font(15)
    f_val = _font(15)

    draw.text(
        (42, 26),
        "第 265 轮复测：本地小模型作答对比（检索不变，只对比 mem0 官方）",
        fill="#111",
        font=f_title,
    )
    draw.text(
        (42, 72),
        "方式：Mnemosis 与 mem0 各自真实检索同一份 26 条求职记忆，"
        "换成本地小模型读各自前 4 条作答，同题同规则打分。",
        fill="#555",
        font=f_sub,
    )

    y = 130
    draw.text(
        (42, y), "A. 检索命中（前 4 条里有没有答案，每题 1 分）", fill="#111", font=f_h
    )
    y += 40
    base_y = y + 150
    chart_h = 130
    group_w = 135
    bar_w = 48
    for i, dim in enumerate(dims):
        gx = 70 + i * group_w
        draw.text((gx, base_y + 10), dim, fill="#111", font=f_label)
        for pi, project in enumerate(projects):
            score = data["retrieval"][project]["per_dim"].get(dim, 0.0)
            bx = gx + pi * 62
            bh = score * chart_h
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=colors[project])
            if score > 0:
                draw.text(
                    (bx + 12, base_y - bh + 4),
                    f"{score:.0%}",
                    fill="white",
                    font=f_val,
                )
    for pi, project in enumerate(projects):
        lx = 950 + pi * 180
        draw.rectangle([lx, y - 20, lx + 24, y - 4], fill=colors[project])
        draw.text((lx + 30, y - 22), labels[project], fill="#111", font=f_label)

    y = base_y + 80
    draw.text(
        (42, y),
        "B. 作答准确率（4 个模型 × 2 个项目，都是 10 题）",
        fill="#111",
        font=f_h,
    )
    y += 60
    base_b = y + 170
    chart_h2 = 130
    group_w2 = 340
    for mi, (model_label, key) in enumerate(models):
        gx = 60 + mi * group_w2
        draw.text((gx, y), model_label, fill="#111", font=f_h)
        for pi, project in enumerate(projects):
            score = data[key][project]["total"] / 10.0
            bx = gx + pi * 150
            bh = score * chart_h2
            draw.rectangle(
                [bx, base_b - bh, bx + 120, base_b], fill=colors[project]
            )
            draw.text(
                (bx + 26, base_b - bh + 5),
                f"{score:.0%}",
                fill="white",
                font=f_val,
            )
            draw.text(
                (bx + 16, base_b + 8), labels[project], fill="#111", font=f_label
            )
    y = base_b + 48
    draw.text(
        (42, y),
        "结果：本地小模型两边都是 9/10，且都只错同一题“上次面试是哪一天？”"
        "——3 次重试全部再错，属于小模型",
        fill="#555",
        font=f_sub,
    )
    draw.text(
        (42, y + 40),
        "的时序推理缺陷（正确记录明明排在检索第 1，小模型仍答成 4月18日"
        "或 7月30日），Mnemosis 相对 mem0 没有弱项。",
        fill="#555",
        font=f_sub,
    )
    draw.text(
        (42, y + 80),
        "对比：云端千问与 DeepSeek（我）两边都 10/10；本地模型在“上次/下次”"
        "这类方向题上能力不足，是模型层问题，不是记忆检索问题。",
        fill="#555",
        font=f_sub,
    )
    draw.text(
        (42, y + 120),
        "结论：第 265 轮本地复测 Mnemosis 9/10 vs mem0 9/10，打平；"
        "检索层 10/10 无损。",
        fill="#555",
        font=f_sub,
    )

    path = os.path.join(_OUT, "round265_local.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
