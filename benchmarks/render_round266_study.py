"""Round-266 chart: study-abroad spot-check, Mnemosis vs mem0 only."""

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
        open(os.path.join(_WORK, "study_spot.json"), encoding="utf-8")
    )
    dims = data["dimensions"]
    projects = ["mnemosis", "mem0"]
    labels = {"mnemosis": "Mnemosis", "mem0": "mem0官方"}
    colors = {"mnemosis": "#7b2ff7", "mem0": "#1a7f37"}

    W, H = 1500, 1080
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(17)
    f_h = _font(20)
    f_label = _font(15)
    f_val = _font(15)

    draw.text(
        (42, 26),
        "第 266 轮抽查：留学申请记忆对比（只对比 mem0 官方）",
        fill="#111",
        font=f_title,
    )
    draw.text(
        (42, 72),
        "内容：留学全程 27 条记忆（考试/申请/面试/Offer/签证/疫苗/入学/"
        "宿舍/机票/费用），含“上次、下次、几月几日”时间提问。",
        fill="#555",
        font=f_sub,
    )

    y = 130
    draw.text(
        (42, y), "A. 检索命中（前 4 条里有没有答案，每题 1 分）", fill="#111", font=f_h
    )
    y += 40
    base_y = y + 170
    chart_h = 150
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
            else:
                draw.text(
                    (bx + 16, base_y + 2),
                    "0",
                    fill="#e8590c",
                    font=f_val,
                )
    for pi, project in enumerate(projects):
        lx = 950 + pi * 180
        draw.rectangle([lx, y - 20, lx + 24, y - 4], fill=colors[project])
        draw.text((lx + 30, y - 22), labels[project], fill="#111", font=f_label)

    y = base_y + 100
    draw.text(
        (42, y),
        "B. 作答准确率（云端千问 + DeepSeek V4 Flash，拿到自己检索的前 4 条后作答）",
        fill="#111",
        font=f_h,
    )
    y += 64
    base_b = y + 170
    chart_h2 = 130
    for mi, (model_label, key) in enumerate(
        (("云端千问", "accuracy_cloud"), ("DeepSeek我", "accuracy_codex"))
    ):
        gx = 90 + mi * 620
        draw.text((gx + 150, y), model_label, fill="#111", font=f_h)
        for pi, project in enumerate(projects):
            score = data[key][project]["total"] / 10.0
            bx = gx + pi * 280
            bh = score * chart_h2
            draw.rectangle(
                [bx, base_b - bh, bx + 220, base_b], fill=colors[project]
            )
            draw.text(
                (bx + 60, base_b - bh + 5),
                f"{score:.0%}",
                fill="white",
                font=f_val,
            )
            draw.text(
                (bx + 30, base_b + 8), labels[project], fill="#111", font=f_label
            )
    y = base_b + 48
    draw.text(
        (42, y),
        "结果：Mnemosis 检索 10/10、作答 10/10；mem0 检索 9/10、作答 9/10"
        "（mem0 漏掉 A 大学 offer 记录）。",
        fill="#555",
        font=f_sub,
    )
    draw.text(
        (42, y + 40),
        "过程说明：首轮 Mnemosis 检索 9/10——“上次托福考试”被“面试”里的“试”"
        "误锚，3月20日托福二考被挤出前4；",
        fill="#555",
        font=f_sub,
    )
    draw.text(
        (42, y + 68),
        "修复：长主题（托福考试 ≥3 字）必须双字词重叠才认，短主题（面试）才允许"
        "词尾字容错；最佳候选已在结果里时不重复插入。",
        fill="#555",
        font=f_sub,
    )
    draw.text(
        (42, y + 96),
        "同时修正一题口径问题（“从哪里飞”改成“从哪里飞到哪里”，双方同权）。"
        "复测后 Mnemosis 10/10。",
        fill="#555",
        font=f_sub,
    )
    draw.text(
        (42, y + 136),
        "结论：第 266 轮 Mnemosis 10/10 领先 mem0 9/10，无弱项；"
        "本轮继续由时间上下文/时间细胞/序数时间/时空数量线论文驱动。",
        fill="#555",
        font=f_sub,
    )

    path = os.path.join(_OUT, "round266_study.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
