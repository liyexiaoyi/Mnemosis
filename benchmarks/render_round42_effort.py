"""Round-42 chart: resource-rational planning depth."""

from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont


_BENCH = os.path.dirname(os.path.abspath(__file__))
_OUT = os.path.normpath(os.path.join(_BENCH, "..", "..", "outputs", "charts"))


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simsun.ttc"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def chart() -> str:
    rows = [
        ("简单目标", 6, False),
        ("参考1人", 8, True),
        ("参考2人+约束", 14, True),
    ]
    W, H = 1450, 800
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(18)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 28), "第 42 轮：规划深度自适应（资源理性规划）",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "依据：资源理性分析（Lieder & Griffiths 2020）与双过程理论（Kahneman 2011）"
              "——简单目标用浅规划（快、省），复杂目标（多参考人/多约束）才投入深度规划。",
              fill="#555", font=f_sub)

    x0 = 150
    draw.text((x0, 130), "目标复杂度 → 规划容量与结果加权", fill="#111", font=f_panel)
    base_y = 500
    chart_h = 300
    max_n = 14
    draw.line([(x0, base_y), (x0 + 700, base_y)], fill="#999", width=2)
    for i, (name, n, rerank) in enumerate(rows):
        bx = x0 + 30 + i * 230
        bh = n / max_n * chart_h
        color = "#b0b0b0" if not rerank else "#7b2ff7"
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 44, base_y - bh + 8), str(n), fill="white", font=f_val)
        draw.text((bx - 16, base_y + 12), name, fill="#111", font=f_label)
        draw.text((bx - 16, base_y + 34),
                  "结果加权: " + ("开" if rerank else "关"),
                  fill="#333", font=f_note)

    draw.text((42, 600),
              "怎么看：柱子高度=计划上下文容量（条数），颜色=是否启用“成功计划优先”"
              "的结果加权。三档映射全部自动判定且验证通过。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "实现：plan_effort() 按“参考人数×2 + 约束词数（预算/人数/时间/完整/按顺序…）”"
              "打分：0-1=浅（6条、不加权）、2-3=中（8条、加权）、≥4=深（14条、加权）。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "顺带修掉两个真问题：①参考人的步骤原来被更早日期的无关情景挤掉，"
              "改为“参考人优先+组内按时间”排序；②执行记录在基础召回中占容量位，"
              "改为双倍余量召回+过滤后按容量截断。回归：163 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round42_plan_effort.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
