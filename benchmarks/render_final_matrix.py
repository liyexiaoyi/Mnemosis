"""Final comprehensive matrix chart (projects x dimensions x models)."""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont


_BENCH = os.path.dirname(os.path.abspath(__file__))
_OUT = os.path.normpath(os.path.join(_BENCH, "..", "..", "outputs", "charts"))


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simsun.ttc"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _pct(v) -> str:
    return "—" if v is None else f"{v:.0%}"


def chart() -> str:
    matrix = json.load(
        open(os.path.join(_BENCH, "results", "final_matrix.json"),
             encoding="utf-8")
    )
    retr = matrix["retrieval"]
    models = matrix["models"]
    projects = ["mnemosis", "mem0", "tencent", "cognitive"]
    retr_keys = {
        "en12": "en12",
        "zh16": "zh16_premises",
        "v2": "v2_premises",
        "conflict": "conflict_top1",
        "process": "process_coverage",
        "plan": "plan_choice",
    }
    dims = ["en12", "zh16", "v2", "conflict", "process", "plan"]
    dim_labels = {
        "en12": "英文12题",
        "zh16": "中文推理16",
        "v2": "推理v2·4",
        "conflict": "冲突消解8",
        "process": "过程步骤6",
        "plan": "计划选择1",
    }
    project_labels = {
        "mnemosis": "Mnemosis",
        "mem0": "mem0官方",
        "tencent": "腾讯Agent",
        "cognitive": "cognitive",
    }
    model_keys = [
        "qwen3.7-plus(云端)",
        "qwen2.5:3b(本地)",
        "DeepSeek V4 Flash(我)",
    ]

    W, H = 1560, 1500
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(17)
    f_h = _font(18)
    f_txt = _font(15)
    y = 28
    draw.text((42, y), "Mnemosis vs GitHub 同类项目 · 全方位多角度最终测评",
              fill="#111", font=f_title)
    y += 48
    draw.text((42, y),
              "检索侧 = 各项目真实流水线（确定性）；作答侧 = 云端千问 / 本地 qwen2.5:3b / "
              "DeepSeek V4 Flash（我）。", fill="#555", font=f_sub)
    y += 44

    # Section A: retrieval heat table
    draw.text((42, y), "A. 检索能力矩阵（真实检索，越高越好）", fill="#111", font=f_h)
    y += 34
    col_x = [330, 600, 870, 1140, 1410]
    draw.text((330, y), "Mnemosis", fill="#333", font=f_h)
    draw.text((600, y), "mem0官方", fill="#333", font=f_h)
    draw.text((870, y), "腾讯Agent", fill="#333", font=f_h)
    draw.text((1140, y), "cognitive", fill="#333", font=f_h)
    draw.text((1410, y), "满分维度", fill="#333", font=f_h)
    y += 28
    for dim in dims:
        draw.text((42, y), dim_labels[dim], fill="#111", font=f_txt)
        vals = [retr[retr_keys[dim]][p] for p in projects]
        for x, v in zip(col_x[:4], vals):
            color = "#7b2ff7" if v >= 0.95 else (
                "#9ecbff" if v >= 0.6 else "#f2d0d0")
            draw.rectangle([x, y - 2, x + 220, y + 20], fill=color)
            draw.text((x + 8, y), f"{v:.0%}", fill="#111", font=f_txt)
        full = sum(1 for v in vals if v >= 0.95)
        draw.text((1410, y), f"{full}/6", fill="#333", font=f_txt)
        y += 26
    y += 12

    # Section B: model answer averages
    draw.text((42, y), "B. 作答准确率平均（6 维度，越前面越好）", fill="#111", font=f_h)
    y += 38
    base_y = y + 170
    chart_h = 150
    for mi, mk in enumerate(model_keys):
        m = models[mk]
        group_x = 90 + mi * 470
        draw.text((group_x + 40, y - 6), mk, fill="#111", font=f_h)
        for pi, p in enumerate(projects):
            vals = [m[d][p] for d in dims if m[d][p] is not None]
            avg = sum(vals) / len(vals) if vals else 0.0
            bx = group_x + pi * 110
            bh = avg * chart_h
            colors = ["#7b2ff7", "#1a7f37", "#d97706", "#b91c1c"]
            draw.rectangle([bx, base_y - bh, bx + 80, base_y], fill=colors[pi])
            draw.text((bx + 18, base_y - bh + 4), f"{avg:.0%}",
                      fill="white", font=f_txt)
            draw.text((bx - 14, base_y + 8), project_labels[p],
                      fill="#111", font=f_txt)
    y = base_y + 40

    # Section C: per-dimension answer table
    draw.text((42, y), "C. 分维度作答准确率（格内 = 云端 / 本地 / 我）", fill="#111", font=f_h)
    y += 34
    headers = ["维度", "Mnemosis", "mem0官方", "腾讯Agent", "cognitive"]
    col_x = [42, 330, 600, 870, 1140]
    for hx, htext in zip(col_x, headers):
        draw.text((hx, y), htext, fill="#333", font=f_h)
    y += 28
    for dim in dims:
        draw.text((42, y), dim_labels[dim], fill="#111", font=f_txt)
        for pi, p in enumerate(projects):
            cells = []
            for mk in model_keys:
                v = models[mk][dim][p]
                cells.append(_pct(v))
            draw.text((col_x[pi + 1], y), " / ".join(cells),
                      fill="#111", font=f_txt)
        y += 26

    draw.text((42, y + 8),
              "读法：检索矩阵看系统能力（Mnemosis 6/6 维度满分）；B 看三模型平均作答；"
              "C 看每个维度三个模型的差距——换更强模型（千问）差距缩小，但检索短板的项目"
              "（腾讯/认知）上限仍低。", fill="#555", font=f_sub)

    path = os.path.join(_OUT, "final_full_matrix.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
