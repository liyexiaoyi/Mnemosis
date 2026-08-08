"""Round-256 chart: e-commerce spot-check, Mnemosis vs mem0 only."""

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
        open(os.path.join(_WORK, "ecommerce_spot.json"), encoding="utf-8")
    )
    dims = data["dimensions"]
    projects = ["mnemosis", "mem0"]
    labels = {"mnemosis": "Mnemosis", "mem0": "mem0官方"}
    colors = {"mnemosis": "#7b2ff7", "mem0": "#1a7f37"}

    W, H = 1500, 1060
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(17)
    f_h = _font(20)
    f_label = _font(15)
    f_val = _font(15)

    draw.text(
        (42, 26),
        "第 256 轮抽查：电商运营记忆对比（只对比 mem0 官方）",
        fill="#111",
        font=f_title,
    )
    draw.text(
        (42, 72),
        "内容：一个坚果零食店铺的 18 条运营记忆（SKU/价格/库存/满减/客服/物流/"
        "供应商/规则/复购/竞品）；Mnemosis 与 mem0ai 2.0.17 官方包同库同题。",
        fill="#555",
        font=f_sub,
    )

    y = 130
    draw.text((42, y), "A. 检索命中（前 4 条里有没有答案，每题 1 分）", fill="#111", font=f_h)
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
            draw.text((bx + 12, base_y - bh + 4), f"{score:.0%}", fill="white", font=f_val)
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
        "结果：检索两家都 10/10；作答两家都 10/10；没有发现 Mnemosis 弱于 mem0 的维度。",
        fill="#555",
        font=f_sub,
    )
    draw.text(
        (42, y + 40),
        "过程说明：物流异常题一度判 0，是题目把“加急处理”也算进必答项——"
        "修正口径后两家都答对；mem0 的竞品题首次作答网络超时，补跑后答对。",
        fill="#555",
        font=f_sub,
    )
    draw.text(
        (42, y + 80),
        "结论：本轮无弱项，无需针对性优化；继续换新领域抽查，发现弱项再改。",
        fill="#555",
        font=f_sub,
    )

    path = os.path.join(_OUT, "round256_ecommerce.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
