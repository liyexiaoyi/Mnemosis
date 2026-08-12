"""Round-39 chart: outcome-aware plan choice at 10k."""

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
    on = [
        ("成功计划第一", 1.00),
        ("参考步骤找回", 1.00),
        ("千问选对小波", 1.00),
    ]
    off = [
        ("成功计划第一", 0.00),
        ("参考步骤找回", 1.00),
        ("千问选对小波", 1.00),
    ]
    W, H = 1500, 800
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 28), "第 39 轮：成功计划优先 · 10k 项目历史压力验证",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "8,738 条记忆：阿丽订机票失败两次、小波全部成功，另加 30 个竞争对手项目"
              "同样有“订机票/买相机”记录。问“参考谁的计划更好”。",
              fill="#555", font=f_sub)

    panels = [
        (0, "① 结果加权开", on),
        (1, "② 结果加权关", off),
    ]
    panel_w = (W - 120) // 2
    chart_h = 320
    base_y = 500
    for p, title, rows in panels:
        x0 = 50 + p * (panel_w + 20)
        draw.text((x0, 130), title, fill="#111", font=f_panel)
        draw.line([(x0, base_y), (x0 + panel_w - 10, base_y)], fill="#999", width=2)
        for frac, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
            y = base_y - frac * chart_h
            draw.line([(x0, y), (x0 + panel_w - 10, y)], fill="#e5e5e5", width=1)
            draw.text((x0 - 34, y - 10), label, fill="#666", font=f_val)
        bar_w = 100
        step = (panel_w - 20) // len(rows)
        for i, (name, val) in enumerate(rows):
            bx = x0 + 16 + i * step
            bh = max(val, 0.02) * chart_h
            color = "#7b2ff7" if p == 0 else "#b0b0b0"
            draw.rectangle([bx, base_y - bh, bx + bar_w, base_y], fill=color)
            draw.text((bx + 24, base_y - bh + 8), f"{val:.0%}",
                      fill="white", font=f_val)
            draw.text((bx - 14, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 600),
              "怎么看：开=结果加权，关=只按时间。差别在“成功计划第一”（1/1 vs 0/1）："
              "开启时被证实成功的小波计划排最前，关闭时按时间排、失败的阿丽在前；"
              "参考步骤找回和千问判断两边都满分。",
              fill="#555", font=f_note)
    draw.text((42, 650),
              "10k 暴露并修掉两个真问题：①参考人名正则太贪婪，“参考阿丽和小波”只抓到阿丽；"
              "②参考步骤被短噪声挤出 top-12，参考提升救不回——新增“情景记忆通道”"
              "第二轮定向检索（按参考人物+主题词），把步骤找回来再参与结果加权。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "MCP plan 工具已继承结果加权重排（集成测试通过）。"
              "回归：159 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round39_plan_10k.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
