"""Detailed multi-dimensional cross-comparison chart (real data only)."""

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


def _kind_acc(details: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    by_kind: dict[str, list[int]] = {}
    for d in details:
        by_kind.setdefault(d["kind"], []).append(1 if d["score"] >= 1.0 else 0)
    for kind, vals in by_kind.items():
        out[kind] = round(sum(vals) / len(vals), 3)
    return out


def _codex_kind_acc() -> dict[str, dict[str, dict[str, float]]]:
    answers = json.load(
        open(os.path.join(_WORK, "codex_project_answers.json"), encoding="utf-8")
    )
    from compare_with_models import score_answer
    from locomo_bench import generate_dataset

    dataset = generate_dataset(seed=42, sessions=24, events_per_session=5)
    by_q = {q["q"]: q for q in dataset["questions"]}
    out: dict[str, dict[str, float]] = {}
    for project, rows in answers.items():
        by_kind: dict[str, list[int]] = {}
        for q, answer in rows.items():
            if not answer:
                continue
            kind = by_q.get(q, {}).get("kind", "fact")
            score = score_answer(answer, by_q.get(q, {}).get("answer", ""))
            by_kind.setdefault(kind, []).append(1 if score >= 1.0 else 0)
        out[project] = {
            kind: round(sum(v) / len(v), 3) for kind, v in by_kind.items()
        }
    return out


def _fmt(v) -> str:
    return "—" if v is None else f"{v:.0%}"


def build_rows() -> list[tuple]:
    matrix = json.load(
        open(os.path.join(_WORK, "model_project_matrix.json"), encoding="utf-8")
    )
    codex_kind = _codex_kind_acc()
    official = json.load(
        open(os.path.join(_RESULTS, "official_packages_compare.json"), encoding="utf-8")
    )
    project_retrieval = {
        "mnemosis": official["mnemosis_keyword"]["total_hit5"],
        "mem0": official["mem0_official"]["total_hit5"],
        "cognitive": official["cognitive_memory_official"]["total_hit5"],
    }
    project_label = {
        "mnemosis": "Mnemosis",
        "mem0": "mem0 官方包",
        "cognitive": "cognitive-memory",
    }
    rows: list[tuple] = []
    for project, models in matrix.items():
        label = project_label[project]
        for model, row in models.items():
            kind = _kind_acc(row.get("details", []))
            rows.append(
                (
                    f"{model} × {label}",
                    row["accuracy"],
                    kind.get("fact"),
                    kind.get("event"),
                    kind.get("temporal"),
                    kind.get("distractor"),
                    row.get("avg_seconds"),
                    project_retrieval[project],
                )
            )
    for project in ("mnemosis", "mem0", "cognitive"):
        kind = codex_kind.get(project, {})
        total = round(
            sum(v for v in kind.values()) / max(1, len(kind)), 3
        )
        rows.append(
            (
                f"DeepSeek V4 Flash（我） × {project_label[project]}",
                total,
                kind.get("fact"),
                kind.get("event"),
                kind.get("temporal"),
                kind.get("distractor"),
                None,
                project_retrieval[project],
            )
        )
    cam = json.load(open(os.path.join(_RESULTS, "cam_official.json"), encoding="utf-8"))
    cam_kind = _kind_acc(cam.get("details", []))
    rows.append(
        (
            "CAM 官方仓库（端到端）",
            cam["accuracy"],
            cam_kind.get("fact"),
            cam_kind.get("event"),
            cam_kind.get("temporal"),
            cam_kind.get("distractor"),
            None,
            cam["retrieval_hit5"],
        )
    )
    tencent = json.load(
        open(os.path.join(_RESULTS, "tencent_official.json"), encoding="utf-8")
    )
    t_kind = _kind_acc(tencent.get("details", []))
    rows.append(
        (
            "TencentDB Agent Memory（本地服务）",
            tencent["accuracy"],
            t_kind.get("fact"),
            t_kind.get("event"),
            t_kind.get("temporal"),
            t_kind.get("distractor"),
            None,
            tencent["retrieval_hit5"],
        )
    )
    return rows


def chart_cross_table() -> str:
    rows = build_rows()
    W, H = 1650, 150 + len(rows) * 44
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(17)
    f_head = _font(18)
    f_row = _font(17)
    f_small = _font(14)
    draw.text((40, 24), "模型 × 记忆项目 × 多维度：真实交叉对比（同一 12 题）",
              fill="#111", font=f_title)
    draw.text((40, 70),
              "数据全部来自本机真实运行：4 个模型（含最新千问 qwen3-vl:8b 和我 DeepSeek V4 Flash）× "
              "3 个记忆项目 + CAM/腾讯端到端。",
              fill="#555", font=f_sub)
    draw.text((40, 96),
              "绿≥90%、黄 70-89%、红<70%；耗时=每题平均秒数；项目检索@5=该记忆系统在 88 题上的真实检索命中。",
              fill="#777", font=f_small)
    headers = ["系统", "总准确率", "记住事实", "记住事件", "之后发生了什么",
               "没聊过不乱说", "耗时(秒/题)", "项目检索@5"]
    col_x = [40, 430, 560, 700, 860, 1030, 1210, 1420]
    y = 130
    draw.line([(30, y), (W - 30, y)], fill="#999", width=2)
    for hx, htxt in zip(col_x, headers):
        draw.text((hx, y + 6), htxt, fill="#111", font=f_head)
    y += 46
    draw.line([(30, y), (W - 30, y)], fill="#999", width=2)
    for row in rows:
        y += 44
        name, acc, fact, event, temporal, distractor, seconds, retrieval = row
        short_name = name if len(name) <= 26 else name[:26] + "…"
        draw.text((col_x[0], y), short_name, fill="#111", font=f_row)
        for j, val in enumerate((acc, fact, event, temporal, distractor)):
            if val is None:
                draw.text((col_x[j + 1], y), "—", fill="#999", font=f_row)
            else:
                color = "#1a7f37" if val >= 0.9 else (
                    "#e6a700" if val >= 0.7 else "#c0392b")
                draw.text((col_x[j + 1], y), _fmt(val), fill=color, font=f_row)
        draw.text((col_x[6], y),
                  "—" if seconds is None else f"{seconds:.1f}",
                  fill="#555", font=f_row)
        if retrieval is None:
            draw.text((col_x[7], y), "—", fill="#999", font=f_row)
        else:
            rcolor = "#1a7f37" if retrieval >= 0.8 else (
                "#e6a700" if retrieval >= 0.5 else "#c0392b")
            draw.text((col_x[7], y), _fmt(retrieval), fill=rcolor, font=f_row)
        draw.line([(30, y + 22), (W - 30, y + 22)], fill="#e5e5e5", width=1)
    path = os.path.join(_OUT, "cross_compare_detailed.png")
    img.save(path)
    return path


def chart_project_retrieval() -> str:
    official = json.load(
        open(os.path.join(_RESULTS, "official_packages_compare.json"), encoding="utf-8")
    )
    cam = json.load(open(os.path.join(_RESULTS, "cam_official.json"), encoding="utf-8"))
    tencent = json.load(
        open(os.path.join(_RESULTS, "tencent_official.json"), encoding="utf-8")
    )
    projects = [
        ("Mnemosis", official["mnemosis_keyword"], "#1a7f37"),
        ("mem0 官方包", official["mem0_official"], "#2f80ed"),
        ("CAM 官方仓库", {"fact@5": None, "event@5": None,
                          "temporal@5": None, "distractor_pass": None,
                          "retrieval": cam["retrieval_hit5"]}, "#7b2ff7"),
        ("TencentDB Agent Memory", {"fact@5": None, "event@5": None,
                                    "temporal@5": None, "distractor_pass": None,
                                    "retrieval": tencent["retrieval_hit5"]}, "#0b5fff"),
        ("cognitive-memory", official["cognitive_memory_official"], "#c0392b"),
    ]
    W, H = 1350, 620
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(17)
    f_val = _font(15)
    draw.text((40, 24), "记忆项目检索能力：同一 88 题（真实安装运行）", fill="#111",
              font=f_title)
    draw.text((40, 70),
              "CAM/腾讯无检索分项（它们是端到端），用 12 题检索命中@5 代替。",
              fill="#555", font=f_sub)
    metrics = [
        ("事实", "fact@5"),
        ("事件", "event@5"),
        ("时序", "temporal@5"),
        ("不乱说", "distractor_pass"),
    ]
    group_w = 250
    bar_w = 52
    chart_h = 300
    base_y = 440
    for gi, (name, d, color) in enumerate(projects):
        gx = 55 + gi * group_w
        draw.text((gx + 5, 110), name, fill="#111", font=f_label)
        for mi, (mlabel, key) in enumerate(metrics):
            val = d.get(key)
            if val is None:
                continue
            if key == "distractor_pass":
                val = val / 16.0
            bh = val * chart_h
            x = gx + 8 + mi * 58
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            if gi == 0:
                draw.text((x - 2, base_y + 12), mlabel, fill="#333", font=f_val)
        if d.get("retrieval") is not None:
            val = d["retrieval"]
            bh = val * chart_h
            x = gx + 8 + 4 * 58
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            if gi == 0:
                draw.text((x - 6, base_y + 12), "检索", fill="#333", font=f_val)
    draw.line([(45, base_y), (W - 45, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        yy = base_y - frac * chart_h
        draw.line([(45, yy), (W - 45, yy)], fill="#e5e5e5", width=1)
        draw.text((15, yy - 10), label, fill="#666", font=f_val)
    draw.text((40, 500),
              "Mnemosis 四项全满、时序 100%、不乱说 16/16；mem0 时序 58%、不乱说 0/16；"
              "CAM/腾讯检索命中低（本地 3B 抽取失真）。",
              fill="#555", font=f_sub)
    path = os.path.join(_OUT, "cross_project_retrieval.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_cross_table())
    print("written:", chart_project_retrieval())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
