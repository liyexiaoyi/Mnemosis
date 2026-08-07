"""Cloud-model (qwen3.7-plus + DeepSeek V4 Flash) x project comparison chart."""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont


_BENCH = os.path.dirname(os.path.abspath(__file__))
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


def _dsv4_scores() -> dict[str, float]:
    answers = json.load(
        open(os.path.join(_WORK, "codex_project_answers.json"), encoding="utf-8")
    )
    from compare_with_models import score_answer
    from locomo_bench import generate_dataset

    dataset = generate_dataset(seed=42, sessions=24, events_per_session=5)
    by_q = {q["q"]: q for q in dataset["questions"]}
    out = {}
    for project, rows in answers.items():
        answered = [(q, a) for q, a in rows.items() if a]
        hits = sum(
            1
            for q, a in answered
            if score_answer(a, by_q.get(q, {}).get("answer", "")) >= 1.0
        )
        out[project] = round(hits / len(answered), 3)
    return out


def chart() -> str:
    matrix = json.load(
        open(os.path.join(_WORK, "model_project_matrix_cloud.json"), encoding="utf-8")
    )
    dsv4 = _dsv4_scores()
    project_label = {
        "mnemosis": "Mnemosis",
        "mem0": "mem0 官方包",
        "cognitive": "cognitive-memory",
    }
    projects = ["mnemosis", "mem0", "cognitive"]
    W, H = 1250, 640
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(19)
    f_val = _font(17)
    f_note = _font(16)
    draw.text((40, 26), "云端模型 × 记忆项目：同一 12 题（不再用本地小模型）",
              fill="#111", font=f_title)
    draw.text((40, 72),
              "qwen3.7-plus = 你部署的最新版千问（DashScope 云端）；"
              "DeepSeek V4 Flash = 我。检索上下文来自各项目真实检索。",
              fill="#555", font=f_sub)
    # legend on top
    draw.rectangle([60, 104, 90, 126], fill="#7b2ff7")
    draw.text((98, 100), "qwen3.7-plus（最新千问）", fill="#111", font=f_sub)
    draw.rectangle([330, 104, 360, 126], fill="#1a7f37")
    draw.text((368, 100), "DeepSeek V4 Flash（我）", fill="#111", font=f_sub)
    chart_h = 300
    base_y = 430
    bar_w = 150
    group_w = 360
    for i, project in enumerate(projects):
        gx = 70 + i * group_w
        qwen = matrix.get(project, {}).get("qwen3.7-plus", {}).get("accuracy", 0.0)
        me = dsv4.get(project, 0.0)
        for j, (val, label, color) in enumerate(
            ((qwen, "qwen3.7-plus", "#7b2ff7"), (me, "DeepSeek V4 Flash（我）", "#1a7f37"))
        ):
            bh = val * chart_h
            x = gx + 20 + j * 180
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            draw.text((x + 42, y + 10), f"{val:.0%}", fill="white", font=f_val)
        draw.text((gx + 40, base_y + 14), project_label[project],
                  fill="#111", font=f_label)
    draw.line([(50, base_y), (W - 50, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(50, y), (W - 50, y)], fill="#e5e5e5", width=1)
        draw.text((20, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 500),
              "读法：横轴三组 = 三个记忆项目；每组两根柱 = 两个模型"
              "（紫=qwen3.7-plus，绿=DeepSeek V4 Flash）。答案都由模型说出，同一打分规则。",
              fill="#555", font=f_note)
    draw.text((40, 545),
              "说明：检索上下文由各项目真实检索生成（本地检索不涉及模型）；"
              "CAM/腾讯端到端用云端模型复测列入下一步。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "cloud_model_x_project.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
