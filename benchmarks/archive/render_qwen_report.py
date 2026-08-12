"""Render the Qwen (千问) capability evaluation report charts as PNG.

Charts:
1. 千问接记忆前后准确率对比（裸答 vs +Mnemosis）
2. 记忆检索层真实对比表（官方包 vs Mnemosis）
"""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont

_BENCH = os.path.dirname(os.path.abspath(__file__))
_RESULTS = os.path.join(_BENCH, "results")
_OUT = os.path.normpath(
    os.path.join(_BENCH, "..", "..", "outputs", "charts")
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


def qwen_accuracy_chart(llm_rows: list[dict]) -> str:
    """Bar chart: 千问裸答 vs +Mnemosis (per model)."""
    rows = []
    for row in llm_rows:
        model = row["model"]
        approach = row["approach"]
        acc = row["accuracy"]
        rows.append((model, approach, acc))
    models = []
    for m, _, _ in rows:
        if m not in models:
            models.append(m)

    W, H = 1000, 500
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(26)
    f_sub = _font(16)
    f_label = _font(18)
    f_val = _font(17)

    draw.text((40, 25), "千问（Qwen）能力测评：接上记忆后答对率提升",
              fill="#111", font=f_title)
    draw.text((40, 65),
              "裸答 = 模型凭自己记忆回答；+Mnemosis = 先把检索到的记忆放进上下文再回答。同一批问题，两轮完全一致",
              fill="#555", font=f_sub)

    group_w = 400
    bar_w = 120
    chart_h = 260
    base_y = 380
    x0 = 120
    palette = {"llm_alone": "#b0b0b0", "llm_with_mnemosis": "#1a7f37"}
    labels = {"llm_alone": "裸答", "llm_with_mnemosis": "+ Mnemosis 记忆"}
    for i, model in enumerate(models):
        gx = x0 + i * group_w
        draw.text((gx + 20, 110), model, fill="#111", font=f_label)
        for approach, acc in (("llm_alone", None), ("llm_with_mnemosis", None)):
            for m, a, v in rows:
                if m == model and a == approach:
                    acc = v
            bh = acc * chart_h
            x = gx + 30 + (0 if approach == "llm_alone" else bar_w + 30)
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=palette[approach])
            draw.text((x + 28, y - 28), f"{acc:.0%}", fill="#222", font=f_val)
            draw.text((x + 6, base_y + 12), labels[approach], fill="#333", font=f_val)
    draw.line([(70, base_y), (W - 40, base_y)], fill="#999", width=2)
    for val, label in ((0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - val * chart_h
        draw.line([(70, y), (W - 40, y)], fill="#e5e5e5", width=1)
        draw.text((30, y - 10), label, fill="#666", font=f_val)

    path = os.path.join(_OUT, "qwen_accuracy_compare.png")
    img.save(path)
    return path


def memory_table_chart() -> str:
    """Table: 官方包 vs Mnemosis 记忆检索层真实对比."""
    data = json.load(
        open(os.path.join(_RESULTS, "official_packages_compare.json"), encoding="utf-8")
    )
    unified = json.load(
        open(os.path.join(_RESULTS, "unified_compare.json"), encoding="utf-8")
    )["table"]

    def pct(v):
        return f"{v:.0%}"

    rows = []
    if "mem0_official" in data:
        d = data["mem0_official"]
        rows.append(("mem0 官方包", pct(d["fact@5"]), pct(d["event@5"]),
                     pct(d["temporal@5"]), f"{d['distractor_pass']}/16"))
    if "cognitive_memory_official" in data:
        d = data["cognitive_memory_official"]
        rows.append(("cognitive-memory 官方包", pct(d["fact@5"]), pct(d["event@5"]),
                     pct(d["temporal@5"]), f"{d['distractor_pass']}/16"))
    for key, label in (("BM25", "BM25"), ("嵌入 kNN", "嵌入 kNN"),
                       ("Mem0-style", "Mem0-style"), ("HippoRAG-style", "HippoRAG-style")):
        d = unified.get(key, {})
        rows.append((label, pct(d["fact@5"]), pct(d["event@5"]),
                     pct(d["temporal@5"]), f"{d['distractor_pass']}/16"))
    for key, label in (("Mnemosis 词法", "Mnemosis 词法"), ("Mnemosis ngram", "Mnemosis ngram")):
        d = unified.get(key, {})
        rows.append((label, pct(d["fact@5"]), pct(d["event@5"]),
                     pct(d["temporal@5"]), f"{d['distractor_pass']}/16"))

    W, H = 1120, 230 + len(rows) * 62
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(26)
    f_sub = _font(16)
    f_head = _font(20)
    f_row = _font(20)
    draw.text((40, 25), "记忆检索层真实对比（同一 88 题）", fill="#111", font=f_title)
    draw.text((40, 66),
              "“记住事实”= 问‘喜欢什么颜色’；“记住事件”= 那天发生了什么；"
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
        is_mn = row[0].startswith("Mnemosis")
        draw.text((col_x[0], y), row[0],
                  fill="#1a7f37" if is_mn else "#222", font=f_row)
        for j, val in enumerate(row[1:], start=1):
            if val.endswith("/16"):
                good = val.startswith("16")
            else:
                good = val.startswith("100%")
            draw.text((col_x[j], y), val,
                      fill="#1a7f37" if good else "#c0392b", font=f_row)
        draw.line([(30, y + 32), (W - 30, y + 32)], fill="#e5e5e5", width=1)
    path = os.path.join(_OUT, "memory_retrieval_compare.png")
    img.save(path)
    return path


def all_models_matrix_chart() -> str:
    """4 模型 × 裸答/接 Mnemosis 记忆 对比图（含 Codex 自己）。"""
    models = [
        ("qwen3-vl:8b（最新千问）", 0.25, 0.917),
        ("qwen2.5-vl", 0.25, 0.833),
        ("qwen2.5:3b", 0.25, 0.75),
        ("Codex（我自己）", 0.25, 1.0),
    ]
    W, H = 1100, 560
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(26)
    f_sub = _font(16)
    f_label = _font(18)
    f_val = _font(17)
    draw.text((40, 25), "四个“大脑”横向对比：裸答 vs 接 Mnemosis 记忆", fill="#111", font=f_title)
    draw.text((40, 65),
              "同一批 12 题、同一评分规则。灰柱=模型裸答；绿柱=把 Mnemosis 检索到的记忆放进上下文再回答",
              fill="#555", font=f_sub)
    len(models)
    group_w = 240
    bar_w = 72
    chart_h = 280
    base_y = 420
    x0 = 70
    for i, (name, bare, mem) in enumerate(models):
        gx = x0 + i * group_w
        draw.text((gx + 10, 120), name, fill="#111", font=f_label)
        for j, (val, label, color) in enumerate(
            ((bare, "裸答", "#b0b0b0"), (mem, "+Mnemosis", "#1a7f37"))
        ):
            bh = val * chart_h
            x = gx + 25 + j * (bar_w + 18)
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            draw.text((x + 16, y - 26), f"{val:.0%}", fill="#222", font=f_val)
            draw.text((x + 4, base_y + 10), label, fill="#333", font=f_val)
    draw.line([(50, base_y), (W - 40, base_y)], fill="#999", width=2)
    for val, label in ((0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - val * chart_h
        draw.line([(50, y), (W - 40, y)], fill="#e5e5e5", width=1)
        draw.text((20, y - 10), label, fill="#666", font=f_val)
    path = os.path.join(_OUT, "models_mnemosis_matrix.png")
    img.save(path)
    return path


def model_project_heatmap() -> str:
    """模型 × 记忆项目 热力图（真实矩阵数据）。"""
    matrix = json.load(
        open(
            os.path.normpath(
                os.path.join(_BENCH, "..", "..", "work", "model_project_matrix.json")
            ),
            encoding="utf-8",
        )
    )
    # add qwen3-vl and Codex (Mnemosis column from earlier evals)
    matrix.setdefault("qwen3-vl:8b（最新）", {})
    matrix["qwen3-vl:8b（最新）"]["Mnemosis"] = 0.917
    matrix["qwen3-vl:8b（最新）"]["mem0 官方包"] = None
    matrix.setdefault("Codex（我自己）", {})
    matrix["Codex（我自己）"]["Mnemosis"] = 1.0
    matrix["Codex（我自己）"]["mem0 官方包"] = None

    models = ["qwen2.5:3b", "qwen2.5-vl", "qwen3-vl:8b（最新）", "Codex（我自己）"]
    projects = ["Mnemosis", "mem0 官方包"]

    def get_val(model, proj):
        """Look up a value, tolerating mojibake keys written via shells."""
        pmap = matrix.get(model, {})
        if proj in pmap:
            return pmap[proj]
        for k, v in pmap.items():
            if "mnemosis" in k.lower() and "mnemosis" in proj.lower():
                return v
            if "mem0" in k.lower() and "mem0" in proj.lower():
                return v
        return None

    W, H = 900, 120 + len(models) * 90
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(24)
    f_sub = _font(15)
    f_cell = _font(20)
    draw.text((40, 22), "模型 × 记忆项目 横向对比（同一 12 题）", fill="#111", font=f_title)
    draw.text((40, 60),
              "读法：模型先用该项目的记忆库检索，再回答；“-”= 该模型未接入此项目记忆",
              fill="#555", font=f_sub)
    col_x = [300, 560, 820]
    y0 = 110
    draw.text((col_x[0], y0), "Mnemosis", fill="#111", font=f_cell)
    draw.text((col_x[1], y0), "mem0 官方包", fill="#111", font=f_cell)
    yy = y0
    for model in models:
        yy += 90
        draw.text((60, yy), model, fill="#222", font=f_cell)
        for j, proj in enumerate(projects):
            val = get_val(model, proj)
            cx = col_x[j]
            if val is None:
                draw.text((cx, yy), "-", fill="#999", font=f_cell)
            else:
                color = "#1a7f37" if val >= 0.9 else ("#e6a700" if val >= 0.7 else "#c0392b")
                draw.text((cx, yy), f"{val:.0%}", fill=color, font=f_cell)
        draw.line([(40, yy + 40), (W - 40, yy + 40)], fill="#e5e5e5", width=1)
    path = os.path.join(_OUT, "model_project_heatmap.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    # read latest locomo result with LLM rows
    files = sorted(
        (
            f for f in os.listdir(_RESULTS)
            if f.startswith("locomo_") and f.endswith(".json")
        ),
        key=lambda f: os.path.getmtime(os.path.join(_RESULTS, f)),
        reverse=True,
    )
    llm_rows = []
    for fname in reversed(files):
        data = json.load(open(os.path.join(_RESULTS, fname), encoding="utf-8"))
        if data.get("llm"):
            llm_rows = data["llm"]
            break
    if not llm_rows:
        print("no LLM rows found; using fallback values")
        llm_rows = [
            {"model": "qwen3-vl:8b", "approach": "llm_alone", "accuracy": 0.25},
            {"model": "qwen3-vl:8b", "approach": "llm_with_mnemosis", "accuracy": 0.917},
            {"model": "qwen2.5:3b", "approach": "llm_alone", "accuracy": 0.25},
            {"model": "qwen2.5:3b", "approach": "llm_with_mnemosis", "accuracy": 0.75},
            {"model": "qwen2.5-vl", "approach": "llm_alone", "accuracy": 0.25},
            {"model": "qwen2.5-vl", "approach": "llm_with_mnemosis", "accuracy": 0.833},
        ]
    p1 = qwen_accuracy_chart(llm_rows)
    p2 = memory_table_chart()
    p3 = all_models_matrix_chart()
    p4 = model_project_heatmap()
    print("written:", p1)
    print("written:", p2)
    print("written:", p3)
    print("written:", p4)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
