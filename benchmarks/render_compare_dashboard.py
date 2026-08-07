"""Render the latest multi-model comparison dashboard (Chinese bar charts)."""

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


def _matrix() -> dict:
    with open(os.path.join(_WORK, "model_project_matrix.json"), encoding="utf-8") as f:
        return json.load(f)


def _cam() -> dict:
    with open(os.path.join(_RESULTS, "cam_official.json"), encoding="utf-8") as f:
        return json.load(f)


def _leaderboard_rows() -> list[tuple[str, float, str]]:
    matrix = _matrix()
    project_color = {
        "mnemosis": "#1a7f37",
        "mem0": "#2f80ed",
        "cognitive": "#c0392b",
    }
    rows: list[tuple[str, float, str]] = []
    for project, models in matrix.items():
        color = project_color.get(project, "#888")
        label = {"mnemosis": "Mnemosis", "mem0": "mem0 官方包",
                 "cognitive": "cognitive-memory"}[project]
        for model, row in models.items():
            acc = row["accuracy"] if isinstance(row, dict) else row
            rows.append((f"{model} × {label}", acc, color))
    # Codex (agent) answers
    codex = json.load(
        open(os.path.join(_WORK, "codex_project_answers.json"), encoding="utf-8")
    )
    from locomo_bench import generate_dataset
    from compare_with_models import score_answer

    dataset = generate_dataset(seed=42, sessions=24, events_per_session=5)
    by_q = {q["q"]: q for q in dataset["questions"]}
    for project, color, label in (
        ("mnemosis", "#1a7f37", "Mnemosis"),
        ("mem0", "#2f80ed", "mem0 官方包"),
        ("cognitive", "#c0392b", "cognitive-memory"),
    ):
        answers = codex.get(project, {})
        answered = [(q, a) for q, a in answers.items() if a]
        if not answered:
            continue
        hits = sum(
            1
            for q, a in answered
            if score_answer(a, by_q.get(q, {}).get("answer", "")) >= 1.0
        )
        rows.append(
            (f"Codex（我自己） × {label}", hits / len(answered), color)
        )
    cam = _cam()
    rows.append(
        ("CAM 官方仓库（端到端）", cam["accuracy"], "#7b2ff7")
    )
    rows.sort(key=lambda r: r[1], reverse=True)
    return rows


def chart_leaderboard() -> str:
    rows = _leaderboard_rows()
    W, H = 1400, 120 + len(rows) * 46
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(17)
    f_val = _font(16)
    draw.text((40, 24), "多模型 × 多记忆系统：总排行榜（同一 12 道题）", fill="#111", font=f_title)
    draw.text((40, 66),
              "柱越长越强。同一种颜色=同一个记忆系统；CAM 是官方仓库端到端（本地小模型），其余是模型+检索上下文。",
              fill="#555", font=f_sub)
    bar_x0 = 520
    bar_max_w = 620
    base_y = 120
    row_h = 46
    for i, (label, acc, color) in enumerate(rows):
        y = base_y + i * row_h
        draw.text((40, y + 4), label, fill="#111", font=f_label)
        w = int(bar_max_w * acc)
        draw.rectangle([bar_x0, y + 4, bar_x0 + w, y + 30], fill=color)
        draw.text((bar_x0 + w + 10, y + 4), f"{acc:.0%}", fill="#222", font=f_val)
    draw.line([(bar_x0, base_y + len(rows) * row_h + 6),
               (bar_x0 + bar_max_w + 70, base_y + len(rows) * row_h + 6)],
              fill="#999", width=2)
    path = os.path.join(_OUT, "compare_leaderboard.png")
    img.save(path)
    return path


def _kind_accuracy() -> dict[str, dict[str, dict[str, float]]]:
    """model -> project -> kind -> accuracy (0..1)."""
    matrix = _matrix()
    out: dict[str, dict[str, dict[str, float]]] = {}
    for project, models in matrix.items():
        for model, row in models.items():
            details = row.get("details", [])
            by_kind: dict[str, list[float]] = {}
            for d in details:
                by_kind.setdefault(d["kind"], []).append(
                    1.0 if d["score"] >= 1.0 else 0.0
                )
            out.setdefault(model, {})[project] = {
                k: round(sum(v) / len(v), 2) for k, v in by_kind.items()
            }
    return out


def chart_kinds() -> str:
    data = _kind_accuracy()
    kind_labels = {"fact": "记住事实", "event": "记住事件",
                   "temporal": "之后发生了什么", "distractor": "没聊过不乱说"}
    kind_colors = {"fact": "#1a7f37", "event": "#2f80ed",
                   "temporal": "#e6a700", "distractor": "#c0392b"}
    project_labels = {"mnemosis": "Mnemosis", "mem0": "mem0 官方包",
                      "cognitive": "cognitive-memory"}
    models = ["qwen3-vl:8b", "qwen2.5-vl", "qwen2.5:3b"]
    W, H = 1500, 340 + len(models) * 300
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(18)
    f_val = _font(15)
    draw.text((40, 24), "每个模型接不同记忆系统：分题型对比", fill="#111", font=f_title)
    draw.text((40, 66),
              "每个模型一张面板：横轴是题型，四根柱分别代表接 Mnemosis / mem0 / cognitive-memory。",
              fill="#555", font=f_sub)
    panel_w = 1380
    chart_h = 180
    base_y = 150
    for mi, model in enumerate(models):
        py = 120 + mi * 300
        draw.text((60, py), model, fill="#111", font=f_label)
        proj = data.get(model, {})
        group_w = panel_w / 4
        for ki, (kind, klabel) in enumerate(kind_labels.items()):
            gx = 80 + ki * group_w
            draw.text((gx + 20, py + 30), klabel, fill="#333", font=f_label)
            for pi, (project, pcolor) in enumerate(
                (("mnemosis", "#1a7f37"), ("mem0", "#2f80ed"),
                 ("cognitive", "#c0392b"))
            ):
                val = proj.get(project, {}).get(kind, 0.0)
                bh = val * chart_h
                x = gx + 20 + pi * 88
                y = py + 55 + chart_h - bh
                draw.rectangle([x, y, x + 66, py + 55 + chart_h],
                               fill=pcolor)
                if val > 0:
                    draw.text((x + 10, y - 18), f"{val:.0%}", fill="#222",
                              font=f_val)
            if mi == 0:
                for pi, (project, pcolor) in enumerate(
                    (("mnemosis", "#1a7f37"), ("mem0", "#2f80ed"),
                     ("cognitive", "#c0392b"))
                ):
                    x = 80 + ki * group_w + 20 + pi * 88
                    draw.text((x + 2, py + 55 + chart_h + 8),
                              project_labels[project][:5], fill="#333",
                              font=f_val)
    path = os.path.join(_OUT, "compare_kinds_bars.png")
    img.save(path)
    return path


def chart_official_bars() -> str:
    with open(
        os.path.join(_RESULTS, "official_packages_compare.json"), encoding="utf-8"
    ) as f:
        data = json.load(f)
    rows = [
        ("mem0 官方包", data["mem0_official"], "#2f80ed"),
        ("cognitive-memory", data["cognitive_memory_official"], "#c0392b"),
        ("Mnemosis 词法", data["mnemosis_keyword"], "#1a7f37"),
    ]
    metrics = [
        ("记住事实", "fact@5"),
        ("记住事件", "event@5"),
        ("之后发生了什么", "temporal@5"),
        ("没聊过不乱说", None),
    ]
    W, H = 1350, 620
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(18)
    f_val = _font(16)
    draw.text((40, 24), "三个真实安装的记忆系统：检索能力柱状对比（同一 88 题）", fill="#111",
              font=f_title)
    draw.text((40, 68),
              "注意：“没聊过不乱说”看的是 16 道没提过的话题里，系统会不会瞎编——只有 Mnemosis 全过。",
              fill="#555", font=f_sub)
    group_w = 300
    bar_w = 52
    chart_h = 280
    base_y = 430
    for gi, (name, d, color) in enumerate(rows):
        gx = 70 + gi * group_w
        draw.text((gx + 10, 110), name, fill="#111", font=f_label)
        for mi, (mlabel, key) in enumerate(metrics):
            val = (
                d["distractor_pass"] / 16.0
                if key is None
                else d[key]
            )
            bh = val * chart_h
            x = gx + 15 + mi * 66
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            if mi < 3:
                draw.text((x + 12, y - 26), f"{val:.0%}", fill="#222", font=f_val)
            else:
                draw.text((x + 12, y - 26), f"{d['distractor_pass']}/16",
                          fill="#222", font=f_val)
        if gi == 0:
            for mi, (mlabel, _) in enumerate(metrics):
                x = 70 + 15 + mi * 66
                short = {0: "记住事实", 1: "记住事件",
                         2: "之后发生", 3: "不乱说"}[mi]
                draw.text((x - 4, base_y + 12), short, fill="#333",
                          font=f_label)
    draw.line([(60, base_y), (W - 60, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(60, y), (W - 60, y)], fill="#e5e5e5", width=1)
        draw.text((25, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 500),
              "读法：三根柱越满越强。Mnemosis 在“之后发生了什么”和“没聊过不乱说”上明显领先。",
              fill="#555", font=f_sub)
    path = os.path.join(_OUT, "compare_official_bars.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    for fn in (chart_leaderboard, chart_kinds, chart_official_bars):
        print("written:", fn())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
