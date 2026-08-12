"""Final matrix v2 chart: 10 dimensions x 4 projects x 3 models."""

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
        open(os.path.join(_BENCH, "results", "final_matrix_v3.json"),
             encoding="utf-8")
    )
    retr = matrix["retrieval"]
    models = matrix["models"]
    projects = ["mnemosis", "mem0", "tencent", "cognitive"]
    dims = ["en12", "zh16", "v2", "conflict", "process", "plan",
            "plan_effort", "replan", "prediction", "unexpected_10k",
            "sleep_replay", "desirable_difficulty"]
    retr_keys = {
        "en12": "en12",
        "zh16": "zh16_premises",
        "v2": "v2_premises",
        "conflict": "conflict_top1",
        "process": "process_coverage",
        "plan": "plan_choice",
        "plan_effort": "plan_effort",
        "replan": "replan",
        "prediction": "prediction",
        "unexpected_10k": "unexpected_10k",
        "sleep_replay": "sleep_replay",
        "desirable_difficulty": "desirable_difficulty",
    }
    dim_labels = {
        "en12": "英文12题",
        "zh16": "中文推理16",
        "v2": "推理v2·4",
        "conflict": "冲突消解8",
        "process": "过程步骤6",
        "plan": "计划选择1",
        "plan_effort": "规划深度(新)",
        "replan": "重规划(新)",
        "prediction": "预测误差(新)",
        "unexpected_10k": "意外事件10k(新)",
        "sleep_replay": "睡眠重放(新)",
        "desirable_difficulty": "期望难度(新)",
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

    W, H = 1560, 2000
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(17)
    f_h = _font(18)
    f_txt = _font(15)
    y = 28
    draw.text((42, y), "第 2 期全方位测评：Mnemosis vs GitHub 同类项目（10 维度）",
              fill="#111", font=f_title)
    y += 48
    draw.text((42, y),
              "覆盖第 42-46 轮新增能力（规划深度/重规划/预测误差/意外事件）；"
              "作答 = 云端千问 / 本地 qwen2.5:3b / DeepSeek V4 Flash（我）。",
              fill="#555", font=f_sub)
    y += 44

    # Section A: retrieval heat table
    draw.text((42, y), "A. 检索能力矩阵（真实流水线，越高越好；新维度=Mnemosis独有能力）",
              fill="#111", font=f_h)
    y += 34
    col_x = [320, 590, 860, 1130, 1400]
    for hx, htext in zip(col_x, ["Mnemosis", "mem0官方", "腾讯Agent",
                                 "cognitive", "满分维度"]):
        draw.text((hx, y), htext, fill="#333", font=f_h)
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
        draw.text((1400, y), f"{full}/10", fill="#333", font=f_txt)
        y += 26
    y += 12

    # Section B: model answer averages (dims with answers)
    draw.text((42, y), "B. 作答准确率平均（有作答的维度，越前面越好）",
              fill="#111", font=f_h)
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
    draw.text((42, y), "C. 分维度作答准确率（格内 = 云端 / 本地 / 我）",
              fill="#111", font=f_h)
    y += 34
    headers = ["维度", "Mnemosis", "mem0官方", "腾讯Agent", "cognitive"]
    col_x = [42, 320, 590, 860, 1130]
    for hx, htext in zip(col_x, headers):
        draw.text((hx, y), htext, fill="#333", font=f_h)
    y += 28
    for dim in dims:
        draw.text((42, y), dim_labels[dim], fill="#111", font=f_txt)
        for pi, p in enumerate(projects):
            cells = [_pct(models[mk][dim][p]) for mk in model_keys]
            draw.text((col_x[pi + 1], y), " / ".join(cells),
                      fill="#111", font=f_txt)
        y += 26

    draw.text((42, y + 8),
              "读法：A 检索矩阵含 4 个新能力维度（Mnemosis 独有，第三方项目不支持）；"
              "B/C 显示三模型作答——换强模型能缩小差距，但检索短板的项目上限仍低。",
              fill="#555", font=f_sub)

    path = os.path.join(_OUT, "final_full_matrix_v3.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
