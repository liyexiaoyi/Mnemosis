"""Round-25 chart: time-cell temporal reasoning A/B (on vs off)."""

from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont


_BENCH = os.path.dirname(os.path.abspath(__file__))
_OUT = os.path.normpath(os.path.join(_BENCH, "..", "..", "outputs", "charts"))


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _bars(draw, x0, y0, rows, max_val, f_label, f_val, f_note):
    """Grouped bars: two per row (off grey, on purple)."""
    chart_h = 180
    bar_w = 56
    row_h = 74
    draw.line([(x0, y0), (x0 + 430, y0)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = y0 - frac * chart_h
        draw.line([(x0, y), (x0 + 430, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
    for i, (name, off, on) in enumerate(rows):
        base_y = y0 - (i * row_h) - 10
        draw.text((x0, base_y + 14), name, fill="#111", font=f_label)
        bx = x0 + 310
        bh_off = off * chart_h
        draw.rectangle([bx, base_y + 26 - bh_off, bx + bar_w, base_y + 26],
                       fill="#b0b0b0")
        draw.text((bx + 12, base_y + 30 - bh_off), f"{off:.0%}",
                  fill="#333", font=f_val)
        bx2 = bx + bar_w + 22
        bh_on = on * chart_h
        draw.rectangle([bx2, base_y + 26 - bh_on, bx2 + bar_w, base_y + 26],
                       fill="#7b2ff7")
        draw.text((bx2 + 12, base_y + 30 - bh_on), f"{on:.0%}",
                  fill="white", font=f_val)


def chart() -> str:
    W, H = 1560, 920
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 26), "第 25 轮：人脑推理论文 → 时序与推理专项优化",
              fill="#111", font=f_title)
    draw.text((42, 76),
              "依据：海马“时间细胞”（Eichenbaum 2014）、前额叶斜坡细胞（PNAS 2024）、"
              "传递推理元分析（NeuroImage 2022）。灰色=关闭机制，紫色=开启机制。",
              fill="#555", font=f_sub)

    draw.text((60, 130), "① 中文 10k 规模（约 1 万条记忆、1026 道题）",
              fill="#111", font=f_panel)
    _bars(
        draw, 70, 470,
        [
            ("时序题：找“后一件事”", 0.952, 1.0),
            ("全部题平均命中", 0.977, 1.0),
        ],
        1.0, f_label, f_val, f_note,
    )
    draw.text((70, 508),
              "万条记忆下，旧方法有 24 道时序题被“同名不同日期”的事件挤掉；"
              "时间细胞锚定后 1026/1026 满分。",
              fill="#555", font=f_note)

    draw.text((880, 130), "② 推理新能力（50 道“之前/二跳/跨人物”难题）",
              fill="#111", font=f_panel)
    _bars(
        draw, 890, 470,
        [
            ("第 1 名就答对", 0.12, 0.64),
            ("前 5 名内有答案", 0.96, 1.0),
        ],
        1.0, f_label, f_val, f_note,
    )
    draw.text((890, 508),
              "开启后能稳定把“之前/二跳/换个人问”的正确答案提到最前面；"
              "旧方法只能碰运气。",
              fill="#555", font=f_note)

    draw.text((60, 640), "③ 英文 88 题 · 零回归", fill="#111", font=f_panel)
    draw.text((60, 678),
              "开/关都是满分：事实 24/24、事件 24/24、时序 24/24、防幻觉 16/16。",
              fill="#555", font=f_note)
    draw.text((880, 640), "④ 中文 200 会话 · 零回归", fill="#111", font=f_panel)
    draw.text((880, 678),
              "开/关完全一致（第 1 名 58%、前 5 名 67%），没有副作用。",
              fill="#555", font=f_note)

    draw.text((42, 800),
              "怎么看：紫色比灰色高 = 新机制带来的真实提升；两边一样高 = 零回归。"
              "标准题本来就满分的保持不变，新增的是“时间顺序推理”能力。",
              fill="#555", font=f_note)
    draw.text((42, 846),
              "顺带优化：召回扩展里一处全表扫描改为集合查询，10k 规模提速约 3 倍，"
              "功能完全不变。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round25_timecell_reasoning.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
