"""Render round-10 (10k scale + Tencent real comparison) Chinese charts."""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont


_BENCH = os.path.dirname(os.path.abspath(__file__))
_RESULTS = os.path.join(_BENCH, "results")
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


def _hit(path: str, kind: str, field: str) -> float:
    d = json.load(open(os.path.join(_RESULTS, path), encoding="utf-8"))
    s = d["retrieval"]["keyword"]["stats"][kind]
    return s[field] / s["n"]


def chart_10k() -> str:
    W, H = 1150, 640
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(19)
    f_val = _font(18)
    f_note = _font(17)
    draw.text((40, 26), "10,000 条记忆：全机制默认开启后的成绩", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "绿=本轮默认配置（含精准事件偏好），灰=关闭精准偏好。"
              "左=事件题，中=时序题，右=总命中。",
              fill="#555", font=f_sub)
    rows = [
        ("事件题", _hit("round10_10k_default.json", "event", "hit5"),
         _hit("round9_10k_precise_off.json", "event", "hit5")),
        ("时序题", _hit("round10_10k_default.json", "temporal", "hit5"),
         _hit("round9_10k_precise_off.json", "temporal", "hit5")),
    ]

    def total5(path: str) -> float:
        d = json.load(open(os.path.join(_RESULTS, path), encoding="utf-8"))
        s = d["retrieval"]["keyword"]["stats"]
        n = sum(v["n"] for v in s.values())
        return sum(v["hit5"] for v in s.values()) / n

    rows.append(("总命中", total5("round10_10k_default.json"),
                 total5("round9_10k_precise_off.json")))
    chart_h = 280
    base_y = 410
    bar_w = 150
    for gi, (name, on, off) in enumerate(rows):
        gx = 55 + gi * 370
        draw.text((gx + 10, 105), name, fill="#111", font=f_label)
        for j, (val, label, color) in enumerate(
            ((on, "默认开启", "#1a7f37"), (off, "关闭", "#b0b0b0"))
        ):
            bh = val * chart_h
            x = gx + 20 + j * 200
            y = base_y - bh
            draw.rectangle([x, y, x + bar_w, base_y], fill=color)
            draw.text((x + 38, y - 28), f"{val:.1%}", fill="#222", font=f_val)
            draw.text((x + 20, base_y + 12), label, fill="#333", font=f_label)
    draw.line([(45, base_y), (W - 45, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(45, y), (W - 45, y)], fill="#e5e5e5", width=1)
        draw.text((15, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 470),
              "总命中 96.5% → 99.6%，事件/时序全部满分——只给“人物+日期都命中”"
              "的情节记忆加分，避免了上一轮一刀切偏好的副作用。",
              fill="#111", font=f_note)
    draw.text((40, 515),
              "对比第 2 轮旧基线（时序 85.8%/90.8%），本轮时序已到 100%。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round10_10k_improve.png")
    img.save(path)
    return path


def chart_tencent() -> str:
    with open(os.path.join(_RESULTS, "tencent_official.json"), encoding="utf-8") as f:
        tencent = json.load(f)
    with open(os.path.join(_RESULTS, "cam_official.json"), encoding="utf-8") as f:
        cam = json.load(f)
    rows = [
        ("Mnemosis + qwen2.5:3b", 0.75, "#1a7f37"),
        ("mem0 官方包 + qwen2.5:3b", 0.75, "#2f80ed"),
        ("CAM 官方仓库（端到端）", cam["accuracy"], "#7b2ff7"),
        ("TencentDB Agent Memory", tencent["accuracy"], "#0b5fff"),
        ("cognitive-memory + qwen2.5:3b", 0.25, "#c0392b"),
    ]
    W, H = 1350, 620
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(28)
    f_sub = _font(17)
    f_label = _font(18)
    f_val = _font(17)
    f_note = _font(17)
    draw.text((40, 26), "腾讯项目正式入榜：同一 12 题、同规则、本地模型", fill="#111",
              font=f_title)
    draw.text((40, 72),
              "TencentDB Agent Memory 官方仓库已在本机真实跑通全流程"
              "（Node 服务 + SQLite/BM25 + Ollama 抽取与作答）。",
              fill="#555", font=f_sub)
    chart_h = 300
    base_y = 420
    bar_w = 170
    x0 = 90
    for i, (name, val, color) in enumerate(rows):
        x = x0 + i * 250
        bh = val * chart_h
        y = base_y - bh
        draw.rectangle([x, y, x + bar_w, base_y], fill=color)
        draw.text((x + 58, y - 30), f"{val:.0%}", fill="#222", font=f_val)
        label = name.replace(" + qwen2.5:3b", "")
        draw.text((x - 8, base_y + 12), label, fill="#333", font=f_label)
    draw.line([(60, base_y), (W - 60, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = base_y - frac * chart_h
        draw.line([(60, y), (W - 60, y)], fill="#e5e5e5", width=1)
        draw.text((25, y - 10), label, fill="#666", font=f_val)
    draw.text((40, 480),
              f"腾讯真实跑分 {tencent['accuracy']:.0%}、检索命中 {tencent['retrieval_hit5']:.0%}："
              "它的 L1 抽取用本地 3B 模型会把内容转述/编造（日期错位、凭空加细节），"
              "导致精确事实答不出——官方文档推荐用 GPT-4o 级别模型。",
              fill="#0b5fff", font=f_note)
    draw.text((40, 530),
              "说明：这轮是“同一本地小模型”下的公平对比；换强模型腾讯分会更高，"
              "但本机只能用本地模型，结果如实记录。",
              fill="#555", font=f_note)
    path = os.path.join(_OUT, "round10_tencent_compare.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart_10k())
    print("written:", chart_tencent())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
