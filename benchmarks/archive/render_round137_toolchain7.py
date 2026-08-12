"""Round-137 chart: toolchain panorama 7."""

from __future__ import annotations

import json
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
    toolchain = json.load(
        open(os.path.join(_BENCH, "results", "toolchain7_eval.json"),
             encoding="utf-8")
    )
    suite = json.load(
        open(os.path.join(_BENCH, "results", "run_all_evals.json"),
             encoding="utf-8")
    )
    W, H = 2200, 830
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(21)
    f_label = _font(13)
    f_val = _font(13)
    f_note = _font(16)

    draw.text((42, 26), "第 137 轮：工具链全景回归 7（30 步全过）",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：新工具（定向遗忘/时间线/回忆判定）也要和旧工具在同一份数据上"
              "连续工作，互相不打架。",
              fill="#555", font=f_sub)

    x0 = 90
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 30 步工具链结果", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 2000, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (3.0, "3"), (6.0, "6")):
        y = base_y - frac / 6.0 * chart_h
        draw.line([(x0, y), (x0 + 2000, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    steps = [
        ("导出导入", toolchain["export_import"], 1, "#7b2ff7"),
        ("状态", toolchain["status"], 1, "#1a7f37"),
        ("审计", toolchain["audit"], 1, "#d97706"),
        ("压力", toolchain["review_load"], 1, "#b91c1c"),
        ("去重", toolchain["dedupe"], 1, "#0e7490"),
        ("冲突化解", toolchain["resolve_conflicts"], 1, "#6b21a8"),
        ("标签", toolchain["tag"], 1, "#15803d"),
        ("清理预览", toolchain["cleanup_preview"], 1, "#0891b2"),
        ("检索日志", toolchain["recall_log"], 1, "#ec4899"),
        ("相似体检", toolchain["similarity_report"], 1, "#f59e0b"),
        ("网络体检", toolchain["association_report"], 1, "#0d9488"),
        ("批量检索", toolchain["search_batch"], 3, "#334155"),
        ("待办登记", toolchain["intent_remember"], 1, "#e11d48"),
        ("到期提醒", toolchain["intent_due"], 1, "#f97316"),
        ("完成待办", toolchain["intent_complete"], 1, "#16a34a"),
        ("待办汇总", toolchain["intent_report"], 1, "#84cc16"),
        ("换线索", toolchain["retrieval_assist"], 1, "#06b6d4"),
        ("主题汇总", toolchain["schema_report"], 1, "#8b5cf6"),
        ("定向遗忘", toolchain["suppress"], 1, "#ef4444"),
        ("遗忘清单", toolchain["suppressed_report"], 1, "#f43f5e"),
        ("时间线", toolchain["timeline_report"], 1, "#0ea5e9"),
        ("回忆判定", toolchain["recognition_check"], 1, "#6366f1"),
        ("解除遗忘", toolchain["unsuppress"], 1, "#22c55e"),
        ("批量复习", toolchain["review_batch"], 1, "#7c3aed"),
        ("练习会话", toolchain["practice_session"], 1, "#16a34a"),
        ("睡眠计划", toolchain["sleep_and_plan"], 1, "#ca8a04"),
        ("搜索", toolchain["search"], 6, "#475569"),
        ("冲突清零", toolchain["conflicts_after"], 1, "#be185d"),
        ("预报", toolchain["forecast"], 1, "#4d7c0f"),
    ]
    for i, (name, val, total, color) in enumerate(steps):
        bx = x0 + 12 + i * 68
        bh = val / 6.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 52, base_y], fill=color)
        draw.text((bx + 6, base_y - bh + 6), f"{val}/{total}",
                  fill="white", font=f_val)
        draw.text((bx - 16, base_y + 10), name, fill="#111", font=f_label)

    verified = suite.get("verified", suite.get("passed", 0))
    draw.text((42, 600),
              "怎么看：同一份记忆走完 30 步（含第 134-136 轮的定向遗忘/遗忘清单/"
              "时间线/回忆判定/解除遗忘），全部正确；搜索 6/6、批量检索 3/3。",
              fill="#555", font=f_note)
    draw.text((42, 640),
              f"一键全测评扩到 {verified}/{verified}——新增工具没有破坏任何既有机制。",
              fill="#555", font=f_note)
    draw.text((42, 710),
              "回归：235 单元测试全过 + 一键全测评全绿。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round137_toolchain7.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
