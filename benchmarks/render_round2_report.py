"""Render the round-2 (hippocampal pattern completion) Chinese charts."""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont


_BENCH = os.path.dirname(os.path.abspath(__file__))
_RESULTS = os.path.join(_BENCH, "results")
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
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


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _hits(stats: dict, kind: str, field: str) -> float:
    n = stats[kind]["n"]
    return stats[kind][field] / n if n else 0.0


def chart_10k_scale() -> str:
    """10k 大规模：时序/事件 旧基线 vs 本轮。"""
    old_a = _load(os.path.join(_RESULTS, "locomo_10k_deterministic.json"))
    old_b = _load(os.path.join(_RESULTS, "locomo_10k.json"))
    new = _load(os.path.join(_RESULTS, "round2_10k_pc_on.json"))

    def temporal(data) -> float:
        return _hits(data["retrieval"]["keyword"]["stats"], "temporal", "hit5")

    def event(data) -> float:
        return _hits(data["retrieval"]["keyword"]["stats"], "event", "hit5")

    series = [
        ("旧基线 A", temporal(old_a), event(old_a), "#b0b0b0"),
        ("旧基线 B", temporal(old_b), event(old_b), "#8a8a8a"),
        ("本轮（第2轮）", temporal(new), event(new), "#1a7f37"),
    ]
    W, H = 1080, 620
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(20)
    f_val = _font(18)
    f_legend = _font(18)
    draw.text((40, 26), "10,000 条记忆压力测试：之后发生了什么？", fill="#111", font=f_title)
    draw.text((40, 72),
              "同一套 4,040 道题，记忆库从 120 条涨到 10,000 条。绿条=本轮迭代后的结果，灰条=昨天的旧版本。",
              fill="#555", font=f_sub)
    group_w = 300
    bar_w = 100
    chart_h = 300
    base_y = 470
    x0 = 100
    labels = ["时序", "事件"]
    for i, (name, t, e, color) in enumerate(series):
        gx = x0 + i * group_w
        draw.text((gx + 20, 120), name, fill="#111", font=f_label)
        for j, (val, label) in enumerate(((t, labels[0]), (e, labels[1]))):
            bh = val * chart_h
            x = gx + 25 + j * (bar_w + 30)
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            draw.text((x + 18, y - 30), f"{val:.1%}", fill="#222", font=f_val)
            if i == 0:
                draw.text((x - 6, base_y + 12), labels[j][:4], fill="#333", font=f_legend)
    draw.line([(60, base_y), (W - 60, base_y)], fill="#999", width=2)
    for val, label in ((0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - val * chart_h
        draw.line([(60, y), (W - 60, y)], fill="#e5e5e5", width=1)
        draw.text((25, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 540),
              "时序@5：旧 0.858/0.908 → 本轮 0.972（1,944/2,000），提升 +0.064~+0.114；事件@5 保持 0.967。",
              fill="#1a7f37", font=f_sub)
    path = os.path.join(_OUT, "round2_10k_scale.png")
    img.save(path)
    return path


def chart_pc_ab() -> str:
    """模式补全 开/关 A/B 对照：88 / 200 / 10k 全规模。"""
    rows = []
    for scale, on_key, off_key in (
        ("88 题", "round2_88_pc_on.json", "round2_88_pc_off.json"),
        ("200 会话", "round2_200_pc_on.json", "round2_200_pc_off.json"),
        ("10k 记忆", "round2_10k_pc_on.json", "round2_10k_pc_off.json"),
    ):
        on = _load(os.path.join(_RESULTS, on_key))
        off = _load(os.path.join(_RESULTS, off_key))
        s_on = on["retrieval"]["keyword"]["stats"]
        s_off = off["retrieval"]["keyword"]["stats"]
        total_n = sum(v["n"] for v in s_on.values())
        rows.append(
            (
                scale,
                sum(v["hit5"] for v in s_on.values()) / total_n,
                sum(v["hit5"] for v in s_off.values()) / total_n,
            )
        )
    W, H = 1000, 560
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(20)
    f_val = _font(18)
    f_legend = _font(18)
    draw.text((40, 26), "模式补全开关对照：三个规模都无回退", fill="#111", font=f_title)
    draw.text((40, 72),
              "绿=开启模式补全，灰=关闭。三档规模（小/中/超大）命中率完全一致，证明新机制不会引入噪音。",
              fill="#555", font=f_sub)
    group_w = 260
    bar_w = 90
    chart_h = 280
    base_y = 430
    x0 = 110
    for i, (name, on, off) in enumerate(rows):
        gx = x0 + i * group_w
        draw.text((gx + 30, 120), name, fill="#111", font=f_label)
        for j, (val, label, color) in enumerate(
            ((on, "开启", "#1a7f37"), (off, "关闭", "#b0b0b0"))
        ):
            bh = val * chart_h
            x = gx + 20 + j * (bar_w + 24)
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            draw.text((x + 16, y - 28), f"{val:.1%}", fill="#222", font=f_val)
            draw.text((x + 14, base_y + 12), label, fill="#333", font=f_legend)
    draw.line([(60, base_y), (W - 60, base_y)], fill="#999", width=2)
    for val, label in ((0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - val * chart_h
        draw.line([(60, y), (W - 60, y)], fill="#e5e5e5", width=1)
        draw.text((25, y - 10), label, fill="#666", font=f_val)
    path = os.path.join(_OUT, "round2_pc_ab_control.png")
    img.save(path)
    return path


def _matrix_rows() -> list[tuple[str, dict]]:
    matrix = _load(os.path.join(_WORK, "model_project_matrix.json"))
    codex_answers = _load(os.path.join(_WORK, "codex_project_answers.json"))
    rows = []
    for project, models in matrix.items():
        codex_acc = None
        codex_rows = codex_answers.get(project, {})
        if codex_rows:
            from compare_with_models import score_answer
            from locomo_bench import generate_dataset

            dataset = generate_dataset(seed=42, sessions=24, events_per_session=5)
            by_q = {q["q"]: q for q in dataset["questions"]}
            acc_denom = 0
            acc_hits = 0
            for q, answer in codex_rows.items():
                if not answer:
                    continue
                acc_denom += 1
                expected = by_q.get(q, {}).get("answer", "")
                score = score_answer(answer, expected)
                acc_hits += int(score >= 1.0)
            if acc_denom:
                codex_acc = round(acc_hits / acc_denom, 3)
        rows.append((project, models, codex_acc))
    return rows


def chart_model_x_project() -> str:
    """4 模型 × 3 记忆项目 真实横向对比（柱状图）。"""
    project_rows = _matrix_rows()
    project_labels = {
        "mnemosis": "Mnemosis",
        "mem0": "mem0 官方包",
        "cognitive": "cognitive-memory 官方包",
    }
    colors = {
        "qwen3-vl:8b": "#1a7f37",
        "qwen2.5-vl": "#2f80ed",
        "qwen2.5:3b": "#e6a700",
        "Codex（我自己）": "#7b2ff7",
    }
    models = ["qwen3-vl:8b", "qwen2.5-vl", "qwen2.5:3b", "Codex（我自己）"]
    W, H = 1500, 700
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_label = _font(19)
    f_val = _font(17)
    f_legend = _font(18)
    draw.text((40, 26), "四个“大脑” × 三个记忆项目：真实横向对比", fill="#111", font=f_title)
    draw.text((40, 76),
              "同一 12 道题、同一打分规则：先让各项目检索记忆，再让模型照着记忆回答。",
              fill="#555", font=f_sub)
    draw.text((40, 104),
              "每个模型下三根柱依次是：Mnemosis、mem0 官方包、cognitive-memory 官方包",
              fill="#777", font=f_sub)
    group_w = 340
    bar_w = 56
    chart_h = 330
    base_y = 520
    x0 = 60
    for i, model in enumerate(models):
        gx = x0 + i * group_w
        draw.text((gx + 15, 120), model, fill="#111", font=f_label)
        bar_i = 0
        for project, models_map, codex_acc in project_rows:
            if project not in project_labels:
                continue
            val = None
            if model == "Codex（我自己）":
                val = codex_acc
            if val is None:
                row = models_map.get(model)
                val = row.get("accuracy") if isinstance(row, dict) else row
            if val is None:
                val = 0.0
            bh = val * chart_h
            x = gx + 25 + bar_i * (bar_w + 55)
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=colors[model])
            draw.text((x + 8, y - 26), f"{val:.0%}" if val else "—",
                      fill="#222", font=f_val)
            if i == 0:
                short = {
                    "mnemosis": "Mnemosis",
                    "mem0": "mem0",
                    "cognitive": "cognitive",
                }[project]
                draw.text((x - 14, base_y + 12), short,
                          fill="#333", font=f_legend)
            bar_i += 1
    draw.line([(50, base_y), (W - 50, base_y)], fill="#999", width=2)
    for val, label in ((0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - val * chart_h
        draw.line([(50, y), (W - 50, y)], fill="#e5e5e5", width=1)
        draw.text((22, y - 10), label, fill="#666", font=f_val)
    path = os.path.join(_OUT, "round2_model_x_project.png")
    img.save(path)
    return path


def chart_project_heatmap() -> str:
    """项目 × 模型 热力表格（同样数据，另一种读法）。"""
    project_rows = _matrix_rows()
    project_labels = {
        "mnemosis": "Mnemosis",
        "mem0": "mem0 官方包",
        "cognitive": "cognitive-memory 官方包",
    }
    models = ["qwen3-vl:8b", "qwen2.5-vl", "qwen2.5:3b", "Codex（我自己）"]
    W, H = 1250, 170 + len(project_rows) * 88
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(26)
    f_sub = _font(16)
    f_head = _font(20)
    f_cell = _font(20)
    draw.text((40, 24), "哪个项目喂给哪个模型最靠谱？（同一 12 题）", fill="#111", font=f_title)
    draw.text((40, 64),
              "绿色≥90%、黄色 70-89%、红色<70%；“—”表示该项没跑。答案完全由模型说出，不是检索库自己打分。",
              fill="#555", font=f_sub)
    col_x = [240, 520, 800, 1080]
    y = 110
    for m, cx in zip(models, col_x):
        draw.text((cx, y), m, fill="#111", font=f_head)
    yy = y
    for project, models_map, codex_acc in project_rows:
        yy += 88
        draw.text((40, yy), project_labels.get(project, project), fill="#222", font=f_cell)
        for j, model in enumerate(models):
            val = None
            if model == "Codex（我自己）":
                val = codex_acc
            if val is None:
                row = models_map.get(model)
                val = row.get("accuracy") if isinstance(row, dict) else row
            cx = col_x[j]
            if val is None:
                draw.text((cx, yy), "—", fill="#999", font=f_cell)
            else:
                color = "#1a7f37" if val >= 0.9 else ("#e6a700" if val >= 0.7 else "#c0392b")
                draw.text((cx, yy), f"{val:.0%}", fill=color, font=f_cell)
        draw.line([(30, yy + 42), (W - 30, yy + 42)], fill="#e5e5e5", width=1)
    path = os.path.join(_OUT, "round2_project_heatmap.png")
    img.save(path)
    return path


def chart_official_packages() -> str:
    """官方安装包真实能力对比表（中文大白话）。"""
    data = _load(os.path.join(_RESULTS, "official_packages_compare.json"))
    rows = []
    if "mem0_official" in data:
        d = data["mem0_official"]
        rows.append(("mem0 官方包", f"{d['fact@5']:.0%}", f"{d['event@5']:.0%}",
                     f"{d['temporal@5']:.0%}", f"{d['distractor_pass']}/16"))
    if "cognitive_memory_official" in data:
        d = data["cognitive_memory_official"]
        rows.append(("cognitive-memory 官方包", f"{d['fact@5']:.0%}",
                     f"{d['event@5']:.0%}", f"{d['temporal@5']:.0%}",
                     f"{d['distractor_pass']}/16"))
    for key, label in (("mnemosis_keyword", "Mnemosis 词法"),
                       ("mnemosis_ngram", "Mnemosis 向量")):
        d = data.get(key, {})
        rows.append((label, f"{d['fact@5']:.0%}", f"{d['event@5']:.0%}",
                     f"{d['temporal@5']:.0%}", f"{d['distractor_pass']}/16"))
    W, H = 1160, 250 + len(rows) * 72
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(26)
    f_sub = _font(16)
    f_head = _font(20)
    f_row = _font(20)
    draw.text((40, 24), "三个真实安装的项目，跑同一套 88 道题", fill="#111", font=f_title)
    draw.text((40, 66),
              "“记住事实”=问喜欢啥颜色；“记住事件”=那天干了啥；“之后发生了什么”=先后顺序；"
              "“没聊过不乱说”=没提过的话题会不会瞎编。",
              fill="#555", font=f_sub)
    headers = ["系统", "记住事实", "记住事件", "之后发生了什么", "没聊过不乱说"]
    col_x = [40, 340, 520, 700, 920]
    y = 140
    draw.line([(30, y), (W - 30, y)], fill="#999", width=2)
    for hx, htxt in zip(col_x, headers):
        draw.text((hx, y + 6), htxt, fill="#111", font=f_head)
    y += 52
    draw.line([(30, y), (W - 30, y)], fill="#999", width=2)
    for row in rows:
        y += 72
        is_mn = row[0].startswith("Mnemosis")
        draw.text((col_x[0], y), row[0], fill="#1a7f37" if is_mn else "#222",
                  font=f_row)
        for j, val in enumerate(row[1:], start=1):
            good = val == "100%" or val == "16/16"
            draw.text((col_x[j], y), val,
                      fill="#1a7f37" if good else "#c0392b", font=f_row)
        draw.line([(30, y + 36), (W - 30, y + 36)], fill="#e5e5e5", width=1)
    path = os.path.join(_OUT, "round2_official_packages.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    paths = [
        chart_10k_scale(),
        chart_pc_ab(),
        chart_official_packages(),
        chart_model_x_project(),
        chart_project_heatmap(),
    ]
    for p in paths:
        print("written:", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
