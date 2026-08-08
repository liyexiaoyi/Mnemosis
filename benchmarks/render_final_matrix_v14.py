"""Final matrix v14 chart: 55 dimensions x 4 projects x 3 models."""

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


def _pct(v) -> str:
    return "—" if v is None else f"{v:.0%}"


def chart() -> str:
    matrix = json.load(
        open(os.path.join(_BENCH, "results", "final_matrix_v14.json"),
             encoding="utf-8")
    )
    retr = matrix["retrieval"]
    models = matrix["models"]
    projects = ["mnemosis", "mem0", "tencent", "cognitive"]
    dims = [
        "en12", "zh16", "v2", "conflict", "process", "plan",
        "plan_effort", "replan", "prediction", "unexpected_10k",
        "sleep_replay", "desirable_difficulty", "testing_effect",
        "spacing", "interleaving", "competitor_suppression",
        "context_matching", "generation_effect", "associative_linking",
        "self_reference", "source_monitoring", "mood_congruent",
        "confidence_weighting", "emotion_regulation", "transfer_practice",
        "auto_context", "confidence_flag", "encoding_variability",
        "arousal_priority", "gist_preference", "weak_important_replay",
        "emotional_salience", "practice_plan", "fresh_window",
        "combined_scheduling", "second_look", "conflict_flag",
        "corroboration", "retrieval_combo", "revision_flag",
        "practice_forecast", "report_suggestions", "full_chain",
        "decay_flag", "mcp_search", "overdue_flag",
        "full_eval_regression", "conflicts_tool", "report_difficulty",
        "review_score", "agent_scenario", "memory_status",
        "review_batch", "export_import", "toolchain",
    ]
    dim_labels = {
        "en12": "英文12题",
        "zh16": "中文推理16",
        "v2": "推理v2·4",
        "conflict": "冲突消解8",
        "process": "过程步骤6",
        "plan": "计划选择1",
        "plan_effort": "规划深度",
        "replan": "重规划",
        "prediction": "预测误差",
        "unexpected_10k": "意外事件10k",
        "sleep_replay": "睡眠重放",
        "desirable_difficulty": "期望难度",
        "testing_effect": "测试效应",
        "spacing": "间隔练习",
        "interleaving": "交错练习",
        "competitor_suppression": "竞争压制",
        "context_matching": "情境匹配",
        "generation_effect": "生成效应",
        "associative_linking": "联想建链",
        "self_reference": "自我参照",
        "source_monitoring": "来源监控",
        "mood_congruent": "情绪一致",
        "confidence_weighting": "置信度加权",
        "emotion_regulation": "情绪调节",
        "transfer_practice": "迁移练习",
        "auto_context": "自动情境",
        "confidence_flag": "不确定标记",
        "encoding_variability": "线索轮换",
        "arousal_priority": "唤醒优先",
        "gist_preference": "要点优先",
        "weak_important_replay": "弱重要重放",
        "emotional_salience": "情绪显著",
        "practice_plan": "复习计划",
        "fresh_window": "新鲜窗口",
        "combined_scheduling": "组合调度",
        "second_look": "检索复核",
        "conflict_flag": "冲突标记",
        "corroboration": "多来源印证",
        "retrieval_combo": "检索组合",
        "revision_flag": "修订标记",
        "practice_forecast": "复习预报",
        "report_suggestions": "报告建议",
        "full_chain": "全链路",
        "decay_flag": "快遗忘标记",
        "mcp_search": "MCP检索",
        "overdue_flag": "逾期标记",
        "full_eval_regression": "全测评回归",
        "conflicts_tool": "冲突工具",
        "report_difficulty": "难度曲线",
        "review_score": "复习得分",
        "agent_scenario": "agent场景",
        "memory_status": "记忆状态(新)",
        "review_batch": "批量复习(新)",
        "export_import": "导出导入(新)",
        "toolchain": "工具链(新)",
    }
    retr_keys = {
        "en12": "en12",
        "zh16": "zh16_premises",
        "v2": "v2_premises",
        "conflict": "conflict_top1",
        "process": "process_coverage",
        "plan": "plan_choice",
        "plan_effort": "plan_effort",
        "replan": "replan",
        "prediction": "prediction",
        "unexpected_10k": "unexpected_10k",
        "sleep_replay": "sleep_replay",
        "desirable_difficulty": "desirable_difficulty",
        "testing_effect": "testing_effect",
        "spacing": "spacing",
        "interleaving": "interleaving",
        "competitor_suppression": "competitor_suppression",
        "context_matching": "context_matching",
        "generation_effect": "generation_effect",
        "associative_linking": "associative_linking",
        "self_reference": "self_reference",
        "source_monitoring": "source_monitoring",
        "mood_congruent": "mood_congruent",
        "confidence_weighting": "confidence_weighting",
        "emotion_regulation": "emotion_regulation",
        "transfer_practice": "transfer_practice",
        "auto_context": "auto_context",
        "confidence_flag": "confidence_flag",
        "encoding_variability": "encoding_variability",
        "arousal_priority": "arousal_priority",
        "gist_preference": "gist_preference",
        "weak_important_replay": "weak_important_replay",
        "emotional_salience": "emotional_salience",
        "practice_plan": "practice_plan",
        "fresh_window": "fresh_window",
        "combined_scheduling": "combined_scheduling",
        "second_look": "second_look",
        "conflict_flag": "conflict_flag",
        "corroboration": "corroboration",
        "retrieval_combo": "retrieval_combo",
        "revision_flag": "revision_flag",
        "practice_forecast": "practice_forecast",
        "report_suggestions": "report_suggestions",
        "full_chain": "full_chain",
        "decay_flag": "decay_flag",
        "mcp_search": "mcp_search",
        "overdue_flag": "overdue_flag",
        "full_eval_regression": "full_eval_regression",
        "conflicts_tool": "conflicts_tool",
        "report_difficulty": "report_difficulty",
        "review_score": "review_score",
        "agent_scenario": "agent_scenario",
        "memory_status": "memory_status",
        "review_batch": "review_batch",
        "export_import": "export_import",
        "toolchain": "toolchain",
    }
    project_labels = {
        "mnemosis": "Mnemosis",
        "mem0": "mem0官方",
        "tencent": "腾讯Agent",
        "cognitive": "cognitive",
    }
    model_keys = [
        "qwen3.7-plus(云端)",
        "qwen2.5:3b(本地)",
        "DeepSeek V4 Flash(我)",
    ]

    W, H = 1560, 5050
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(17)
    f_h = _font(18)
    f_txt = _font(15)
    y = 28
    draw.text((42, y), "第 14 期全方位测评：Mnemosis vs GitHub 同类项目（55 维度）",
              fill="#111", font=f_title)
    y += 48
    draw.text((42, y),
              "覆盖第 104-107 轮新增能力（记忆状态/批量复习/导出导入/工具链）；"
              "作答 = 云端千问 / 本地 qwen2.5:3b / DeepSeek V4 Flash（我）。",
              fill="#555", font=f_sub)
    y += 44

    # Section A: retrieval heat table
    draw.text((42, y), "A. 检索能力矩阵（真实流水线，越高越好；新维度=Mnemosis独有能力）",
              fill="#111", font=f_h)
    y += 34
    col_x = [320, 590, 860, 1130, 1400]
    for hx, htext in zip(col_x, ["Mnemosis", "mem0官方", "腾讯Agent",
                                 "cognitive", "满分项目数"]):
        draw.text((hx, y), htext, fill="#333", font=f_h)
    y += 28
    for dim in dims:
        draw.text((42, y), dim_labels[dim], fill="#111", font=f_txt)
        vals = [retr[retr_keys[dim]][p] for p in projects]
        for x, v in zip(col_x[:4], vals):
            color = "#7b2ff7" if v >= 0.95 else (
                "#9ecbff" if v >= 0.6 else "#f2d0d0")
            draw.rectangle([x, y - 2, x + 220, y + 20], fill=color)
            draw.text((x + 8, y), f"{v:.0%}", fill="#111", font=f_txt)
        full = sum(1 for v in vals if v >= 0.95)
        draw.text((1400, y), f"{full}/4", fill="#333", font=f_txt)
        y += 26
    y += 12

    # Section B: model answer averages
    draw.text((42, y), "B. 作答准确率平均（有作答的维度，越前面越好）",
              fill="#111", font=f_h)
    y += 38
    base_y = y + 170
    chart_h = 150
    for mi, mk in enumerate(model_keys):
        m = models[mk]
        group_x = 90 + mi * 470
        draw.text((group_x + 40, y - 6), mk, fill="#111", font=f_h)
        for pi, p in enumerate(projects):
            vals = [m[d][p] for d in dims if m[d][p] is not None]
            avg = sum(vals) / len(vals) if vals else 0.0
            bx = group_x + pi * 110
            bh = avg * chart_h
            colors = ["#7b2ff7", "#1a7f37", "#d97706", "#b91c1c"]
            draw.rectangle([bx, base_y - bh, bx + 80, base_y], fill=colors[pi])
            draw.text((bx + 18, base_y - bh + 4), f"{avg:.0%}",
                      fill="white", font=f_txt)
            draw.text((bx - 14, base_y + 8), project_labels[p],
                      fill="#111", font=f_txt)
    y = base_y + 40

    # Section C: per-dimension answer table
    draw.text((42, y), "C. 分维度作答准确率（格内 = 云端 / 本地 / 我；机制维度无作答=—）",
              fill="#111", font=f_h)
    y += 34
    headers = ["维度", "Mnemosis", "mem0官方", "腾讯Agent", "cognitive"]
    col_x = [42, 320, 590, 860, 1130]
    for hx, htext in zip(col_x, headers):
        draw.text((hx, y), htext, fill="#333", font=f_h)
    y += 28
    for dim in dims:
        draw.text((42, y), dim_labels[dim], fill="#111", font=f_txt)
        for pi, p in enumerate(projects):
            cells = [_pct(models[mk][dim][p]) for mk in model_keys]
            draw.text((col_x[pi + 1], y), " / ".join(cells),
                      fill="#111", font=f_txt)
        y += 26

    draw.text((42, y + 8),
              "读法：A 检索矩阵含 49 个新能力维度（Mnemosis 独有，第三方项目不支持）；"
              "B/C 显示三模型作答——换强模型能缩小差距，但检索短板的项目上限仍低。",
              fill="#555", font=f_sub)
    draw.text((42, y + 42),
              "说明：基础 6 维沿用第 4-13 期真实安装测评；59-107 轮改动已跑统一回归"
              "（en88/zh200/zh10k 及 10k 系列）与一键全测评（45/45）零差异。",
              fill="#555", font=f_sub)

    path = os.path.join(_OUT, "final_full_matrix_v14.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
