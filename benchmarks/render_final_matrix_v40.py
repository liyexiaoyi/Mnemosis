"""Final matrix v40 chart: 159 dimensions x 4 projects x 3 models."""

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
    return "N/A" if v is None else f"{v:.0%}"


def chart() -> str:
    matrix = json.load(
        open(os.path.join(_BENCH, "results", "final_matrix_v40.json"),
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
        "practice_session", "sleep_and_plan", "memory_audit",
        "toolchain2", "dedupe", "resolve_conflicts", "review_load",
        "toolchain3", "tag_memories", "recall_log", "cleanup_preview",
        "toolchain4", "similarity_report", "association_report",
        "search_batch", "toolchain5", "intent_register",
        "retrieval_assist", "schema_report", "toolchain6",
        "suppress_memories", "timeline_report", "recognition_check",
        "toolchain7", "interference_report", "life_story",
        "intent_conflicts", "toolchain8", "memory_health",
        "kg_export", "learner_profile", "toolchain9",
        "context_pack", "encoding_quality", "explain_memory",
        "toolchain10", "compare_memories", "action_queue",
        "summarize_cluster", "toolchain11", "multi_hop_report",
        "cramming_plan", "session_summary", "toolchain12",
        "topic_drift_report", "forgetting_export", "coverage_report",
        "toolchain13", "source_calibration", "forgetting_risk",
        "bridge_suggestions", "toolchain14", "plan_quality",
        "project_brief", "numeric_reasoning", "plan_support",
        "toolchain15", "dependency_map", "project_risk",
        "plan_tracker", "toolchain16", "plan_rewrite",
        "lesson_learned", "effort_estimate", "toolchain17",
        "decision_review", "transfer_report", "retrieval_quality",
        "toolchain18", "recall_trace", "community_report",
        "sleep_advice", "toolchain19", "emotion_advice",
        "difficulty_estimator", "memory_integration", "toolchain20",
        "reasoning_trace", "goal_replay", "toolchain21",
        "sleep_inference", "schema_fit", "working_set_budget",
        "toolchain22", "test_generator", "spacing_plan",
        "rumination_check", "toolchain23",
        "consolidation_forecast", "forgetting_balance",
        "metacog_report", "toolchain24",
        "reconsolidation_plan", "mastery_map", "attention_filter",
        "toolchain25", "analogy_bridge", "next_interval",
        "nightly_routine", "toolchain26", "cue_diversity",
        "weekly_review", "transfer_prompt", "toolchain27",
    ]
    dim_labels = {
        "en12": "英文12问",
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
        "context_matching": "情景匹配",
        "generation_effect": "生成效应",
        "associative_linking": "联想建链",
        "self_reference": "自我参照",
        "source_monitoring": "来源监控",
        "mood_congruent": "情绪一致",
        "confidence_weighting": "置信度加权",
        "emotion_regulation": "情绪调节",
        "transfer_practice": "迁移练习",
        "auto_context": "自动情景",
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
        "memory_status": "记忆状态",
        "review_batch": "批量复习",
        "export_import": "导出导入",
        "toolchain": "工具链",
        "practice_session": "练习会话",
        "sleep_and_plan": "睡眠计划",
        "memory_audit": "记忆审计",
        "toolchain2": "工具链2",
        "dedupe": "去重",
        "resolve_conflicts": "冲突化解",
        "review_load": "压力指数",
        "toolchain3": "工具链3",
        "tag_memories": "标签管理(新)",
        "recall_log": "检索日志(新)",
        "cleanup_preview": "清理预览(新)",
        "toolchain4": "工具链4(新)",
        "similarity_report": "相似体检(新)",
        "association_report": "网络体检(新)",
        "search_batch": "批量检索(新)",
        "toolchain5": "工具链5(新)",
        "intent_register": "待办登记(新)",
        "retrieval_assist": "换线索(新)",
        "schema_report": "主题汇总(新)",
        "toolchain6": "工具链6(新)",
        "suppress_memories": "定向遗忘(新)",
        "timeline_report": "时间线(新)",
        "recognition_check": "回忆判定(新)",
        "toolchain7": "工具链7(新)",
        "interference_report": "线索拥挤(新)",
        "life_story": "人生阶段(新)",
        "intent_conflicts": "待办撞车(新)",
        "toolchain8": "工具链8(新)",
        "memory_health": "健康体检(新)",
        "kg_export": "图谱导出(新)",
        "learner_profile": "学习画像(新)",
        "toolchain9": "工具链9(新)",
        "context_pack": "上下文打包(新)",
        "encoding_quality": "编码质量(新)",
        "explain_memory": "记忆档案(新)",
        "toolchain10": "工具链10(新)",
        "compare_memories": "记忆对比(新)",
        "action_queue": "动作队列(新)",
        "summarize_cluster": "要点压缩(新)",
        "toolchain11": "工具链11(新)",
        "multi_hop_report": "多跳检索(新)",
        "cramming_plan": "冲刺计划(新)",
        "session_summary": "会话摘要(新)",
        "toolchain12": "工具链12(新)",
        "topic_drift_report": "主题漂移(新)",
        "forgetting_export": "遗忘曲线(新)",
        "coverage_report": "复习覆盖(新)",
        "toolchain13": "工具链13(新)",
        "source_calibration": "来源校准(新)",
        "forgetting_risk": "遗忘风险(新)",
        "bridge_suggestions": "补桥建议(新)",
        "toolchain14": "工具链14(新)",
        "plan_quality": "计划打分(新)",
        "project_brief": "项目简报(新)",
        "numeric_reasoning": "数量体检(新)",
        "plan_support": "步骤证据(新)",
        "toolchain15": "工具链15(新)",
        "dependency_map": "依赖图(新)",
        "project_risk": "风险预警(新)",
        "plan_tracker": "执行跟踪(新)",
        "toolchain16": "工具链16(新)",
        "plan_rewrite": "计划改写(新)",
        "lesson_learned": "经验库(新)",
        "effort_estimate": "工期估算(新)",
        "toolchain17": "工具链17(新)",
        "decision_review": "决策复盘(新)",
        "transfer_report": "知识迁移(新)",
        "retrieval_quality": "检索体检(新)",
        "toolchain18": "工具链18(新)",
        "recall_trace": "检索路径(新)",
        "community_report": "记忆圈子(新)",
        "sleep_advice": "睡前建议(新)",
        "toolchain19": "工具链19(新)",
        "emotion_advice": "情绪建议(新)",
        "difficulty_estimator": "难度分档(新)",
        "memory_integration": "记忆整合(新)",
        "toolchain20": "工具链20(新)",
        "reasoning_trace": "推理链(新)",
        "goal_replay": "目标重放(新)",
        "toolchain21": "工具链21(新)",
        "sleep_inference": "睡眠推断(新)",
        "schema_fit": "图式拟合(新)",
        "working_set_budget": "工作预算(新)",
        "toolchain22": "工具链22(新)",
        "test_generator": "测试出题(新)",
        "spacing_plan": "间隔计划(新)",
        "rumination_check": "反刍检查(新)",
        "toolchain23": "工具链23(新)",
        "consolidation_forecast": "巩固预测(新)",
        "forgetting_balance": "遗忘平衡(新)",
        "metacog_report": "元认知(新)",
        "toolchain24": "工具链24(新)",
        "reconsolidation_plan": "再巩固(新)",
        "mastery_map": "掌握度(新)",
        "attention_filter": "注意力(新)",
        "toolchain25": "工具链25(新)",
        "analogy_bridge": "类比(新)",
        "next_interval": "间隔校准(新)",
        "nightly_routine": "夜间流程(新)",
        "toolchain26": "工具链26(新)",
        "cue_diversity": "线索(新)",
        "weekly_review": "周报(新)",
        "transfer_prompt": "迁移出题(新)",
        "toolchain27": "工具链27(新)",
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
        "practice_session": "practice_session",
        "sleep_and_plan": "sleep_and_plan",
        "memory_audit": "memory_audit",
        "toolchain2": "toolchain2",
        "dedupe": "dedupe",
        "resolve_conflicts": "resolve_conflicts",
        "review_load": "review_load",
        "toolchain3": "toolchain3",
        "tag_memories": "tag_memories",
        "recall_log": "recall_log",
        "cleanup_preview": "cleanup_preview",
        "toolchain4": "toolchain4",
        "similarity_report": "similarity_report",
        "association_report": "association_report",
        "search_batch": "search_batch",
        "toolchain5": "toolchain5",
        "intent_register": "intent_register",
        "retrieval_assist": "retrieval_assist",
        "schema_report": "schema_report",
        "toolchain6": "toolchain6",
        "suppress_memories": "suppress_memories",
        "timeline_report": "timeline_report",
        "recognition_check": "recognition_check",
        "toolchain7": "toolchain7",
        "interference_report": "interference_report",
        "life_story": "life_story",
        "intent_conflicts": "intent_conflicts",
        "toolchain8": "toolchain8",
        "memory_health": "memory_health",
        "kg_export": "kg_export",
        "learner_profile": "learner_profile",
        "toolchain9": "toolchain9",
        "context_pack": "context_pack",
        "encoding_quality": "encoding_quality",
        "explain_memory": "explain_memory",
        "toolchain10": "toolchain10",
        "compare_memories": "compare_memories",
        "action_queue": "action_queue",
        "summarize_cluster": "summarize_cluster",
        "toolchain11": "toolchain11",
        "multi_hop_report": "multi_hop_report",
        "cramming_plan": "cramming_plan",
        "session_summary": "session_summary",
        "toolchain12": "toolchain12",
        "topic_drift_report": "topic_drift_report",
        "forgetting_export": "forgetting_export",
        "coverage_report": "coverage_report",
        "toolchain13": "toolchain13",
        "source_calibration": "source_calibration",
        "forgetting_risk": "forgetting_risk",
        "bridge_suggestions": "bridge_suggestions",
        "toolchain14": "toolchain14",
        "plan_quality": "plan_quality",
        "project_brief": "project_brief",
        "numeric_reasoning": "numeric_reasoning",
        "plan_support": "plan_support",
        "toolchain15": "toolchain15",
        "dependency_map": "dependency_map",
        "project_risk": "project_risk",
        "plan_tracker": "plan_tracker",
        "toolchain16": "toolchain16",
        "plan_rewrite": "plan_rewrite",
        "lesson_learned": "lesson_learned",
        "effort_estimate": "effort_estimate",
        "toolchain17": "toolchain17",
        "decision_review": "decision_review",
        "transfer_report": "transfer_report",
        "retrieval_quality": "retrieval_quality",
        "toolchain18": "toolchain18",
        "recall_trace": "recall_trace",
        "community_report": "community_report",
        "sleep_advice": "sleep_advice",
        "toolchain19": "toolchain19",
        "emotion_advice": "emotion_advice",
        "difficulty_estimator": "difficulty_estimator",
        "memory_integration": "memory_integration",
        "toolchain20": "toolchain20",
        "reasoning_trace": "reasoning_trace",
        "goal_replay": "goal_replay",
        "toolchain21": "toolchain21",
        "sleep_inference": "sleep_inference",
        "schema_fit": "schema_fit",
        "working_set_budget": "working_set_budget",
        "toolchain22": "toolchain22",
        "test_generator": "test_generator",
        "spacing_plan": "spacing_plan",
        "rumination_check": "rumination_check",
        "toolchain23": "toolchain23",
        "consolidation_forecast": "consolidation_forecast",
        "forgetting_balance": "forgetting_balance",
        "metacog_report": "metacog_report",
        "toolchain24": "toolchain24",
        "reconsolidation_plan": "reconsolidation_plan",
        "mastery_map": "mastery_map",
        "attention_filter": "attention_filter",
        "toolchain25": "toolchain25",
        "analogy_bridge": "analogy_bridge",
        "next_interval": "next_interval",
        "nightly_routine": "nightly_routine",
        "toolchain26": "toolchain26",
        "cue_diversity": "cue_diversity",
        "weekly_review": "weekly_review",
        "transfer_prompt": "transfer_prompt",
        "toolchain27": "toolchain27",
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

    W, H = 1560, 14750
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(17)
    f_h = _font(18)
    f_txt = _font(16)
    y = 28
    draw.text((42, y), "第 40 期全方位测评：Mnemosis vs GitHub 同类项目（159 维度）",
              fill="#111", font=f_title)
    y += 48
    draw.text((42, y),
              "覆盖第 233-236 轮新增能力（线索/周报/迁移出题/工具链27）；"
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
        y += 28
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
    draw.text((42, y), "C. 分维度作答准确率（格内 = 云端 / 本地 / 我；机制维度无作答 N/A）",
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
        y += 28

    draw.text((42, y + 8),
              "读法：A 检索矩阵的机制维度为 Mnemosis 独有能力，第三方项目不支持；"
              "B/C 显示三模型作答——换强模型能缩小差距，但检索短板的项目上限仍低。",
              fill="#555", font=f_sub)
    draw.text((42, y + 42),
              "说明：基础维度沿用第 4-39 期真实安装测评；59-236 轮改动已跑统一回归"
              "（en88/zh200/zh10k 及 10k 系列）与一键全测评（145/145）零差异。",
              fill="#555", font=f_sub)

    path = os.path.join(_OUT, "final_full_matrix_v40.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
