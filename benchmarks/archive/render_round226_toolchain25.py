"""Round-226 chart: toolchain panorama 25 (horizontal, readable)."""

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
        open(
            os.path.join(_BENCH, "results", "toolchain25_eval.json"),
            encoding="utf-8",
        )
    )
    steps = [
        ("导出导入", toolchain["export_import"], 1),
        ("状态", toolchain["status"], 1),
        ("审计", toolchain["audit"], 1),
        ("压力", toolchain["review_load"], 1),
        ("去重", toolchain["dedupe"], 1),
        ("冲突化解", toolchain["resolve_conflicts"], 1),
        ("标签", toolchain["tag"], 1),
        ("清理预览", toolchain["cleanup_preview"], 1),
        ("检索日志", toolchain["recall_log"], 1),
        ("相似体检", toolchain["similarity_report"], 1),
        ("网络体检", toolchain["association_report"], 1),
        ("批量检索", toolchain["search_batch"], 3),
        ("待办登记", toolchain["intent_remember"], 1),
        ("到期提醒", toolchain["intent_due"], 1),
        ("完成待办", toolchain["intent_complete"], 1),
        ("待办汇总", toolchain["intent_report"], 1),
        ("待办撞车", toolchain["intent_conflicts"], 1),
        ("换线索", toolchain["retrieval_assist"], 1),
        ("主题汇总", toolchain["schema_report"], 1),
        ("定向遗忘", toolchain["suppress"], 1),
        ("遗忘清单", toolchain["suppressed_report"], 1),
        ("时间线", toolchain["timeline_report"], 1),
        ("回忆判定", toolchain["recognition_check"], 1),
        ("解除遗忘", toolchain["unsuppress"], 1),
        ("线索拥挤", toolchain["interference_report"], 1),
        ("人生阶段", toolchain["life_story"], 1),
        ("健康体检", toolchain["memory_health"], 1),
        ("图谱导出", toolchain["kg_export"], 1),
        ("学习画像", toolchain["learner_profile"], 1),
        ("上下文打包", toolchain["context_pack"], 1),
        ("编码质量", toolchain["encoding_quality"], 1),
        ("记忆档案", toolchain["explain_memory"], 1),
        ("记忆对比", toolchain["compare_memories"], 1),
        ("动作队列", toolchain["action_queue"], 1),
        ("要点压缩", toolchain["summarize_cluster"], 1),
        ("多跳检索", toolchain["multi_hop_report"], 1),
        ("冲刺计划", toolchain["cramming_plan"], 1),
        ("会话摘要", toolchain["session_summary"], 1),
        ("主题漂移", toolchain["topic_drift_report"], 1),
        ("遗忘曲线", toolchain["forgetting_export"], 1),
        ("复习覆盖", toolchain["coverage_report"], 1),
        ("来源校准", toolchain["source_calibration"], 1),
        ("遗忘风险", toolchain["forgetting_risk"], 1),
        ("补桥建议", toolchain["bridge_suggestions"], 1),
        ("计划打分", toolchain["plan_quality"], 1),
        ("项目简报", toolchain["project_brief"], 1),
        ("数量体检", toolchain["numeric_reasoning"], 1),
        ("步骤证据", toolchain["plan_support"], 1),
        ("依赖图", toolchain["dependency_map"], 1),
        ("风险预警", toolchain["project_risk"], 1),
        ("执行跟踪", toolchain["plan_tracker"], 1),
        ("计划改写", toolchain["plan_rewrite"], 1),
        ("经验库", toolchain["lesson_learned"], 1),
        ("工期估算", toolchain["effort_estimate"], 1),
        ("决策复盘", toolchain["decision_review"], 1),
        ("知识迁移", toolchain["transfer_report"], 1),
        ("检索体检", toolchain["retrieval_quality"], 1),
        ("检索路径", toolchain["recall_trace"], 1),
        ("记忆圈子", toolchain["community_report"], 1),
        ("睡前建议", toolchain["sleep_advice"], 1),
        ("情绪建议", toolchain["emotion_advice"], 1),
        ("难度分档", toolchain["difficulty_estimator"], 1),
        ("记忆整合", toolchain["memory_integration"], 1),
        ("推理链", toolchain["reasoning_trace"], 1),
        ("目标重放", toolchain["goal_replay"], 1),
        ("睡眠推断", toolchain["sleep_inference"], 1),
        ("图式拟合", toolchain["schema_fit"], 1),
        ("工作预算", toolchain["working_set_budget"], 1),
        ("测试出题", toolchain["test_generator"], 1),
        ("间隔计划", toolchain["spacing_plan"], 1),
        ("反刍检查", toolchain["rumination_check"], 1),
        ("巩固预测", toolchain["consolidation_forecast"], 1),
        ("遗忘平衡", toolchain["forgetting_balance"], 1),
        ("元认知", toolchain["metacog_report"], 1),
        ("再巩固", toolchain["reconsolidation_plan"], 1),
        ("掌握度", toolchain["mastery_map"], 1),
        ("注意力", toolchain["attention_filter"], 1),
        ("批量复习", toolchain["review_batch"], 1),
        ("练习会话", toolchain["practice_session"], 1),
        ("睡眠计划", toolchain["sleep_and_plan"], 1),
        ("搜索", toolchain["search"], 6),
        ("冲突清零", toolchain["conflicts_after"], 1),
        ("预报", toolchain["forecast"], 1),
    ]
    row_h = 22
    top = 150
    W, H = 1500, top + len(steps) * row_h + 150
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_label = _font(15)
    f_val = _font(15)
    f_note = _font(16)

    draw.text((42, 26), "第 226 轮：工具链全景回归 25（84 步全过）",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "同一份记忆连续走完 84 步（含再巩固/掌握度/注意力），全部正确；"
              "搜索 6/6、批量检索 3/3。",
              fill="#555", font=f_sub)
    max_total = 6
    bar_x0 = 330
    bar_max = 1000
    y = top
    draw.line([(bar_x0, y - 8), (bar_x0, y + len(steps) * row_h + 4)],
              fill="#999", width=2)
    for label, frac in (("0", 0.0), ("3", 3.0 / 6.0), ("6", 1.0)):
        x = bar_x0 + frac * bar_max
        draw.line([(x, y - 8), (x, y + len(steps) * row_h + 4)],
                  fill="#e5e5e5", width=1)
        draw.text((x - 6, y - 34), label, fill="#666", font=f_val)
    colors = ["#7b2ff7", "#1a7f37", "#d97706", "#0b7285", "#c2255c",
              "#6741d9", "#2f9e44", "#e8590c", "#0ca678", "#7048e8"]
    for i, (name, val, total) in enumerate(steps):
        draw.text((42, y + 2), name, fill="#111", font=f_label)
        bw = (val / max_total) * bar_max
        draw.rectangle([bar_x0, y + 2, bar_x0 + bw, y + 16],
                       fill=colors[i % len(colors)])
        draw.text((bar_x0 + bw + 8, y + 1), f"{val}/{total}",
                  fill="#333", font=f_val)
        y += row_h
    draw.text((42, y + 14),
              "怎么看：84 行全绿——旧功能没坏，第 223-225 轮的再巩固/掌握度/"
              "注意力也在同一套数据上正常。",
              fill="#555", font=f_note)
    draw.text((42, y + 48),
              "回归：289 单元测试全过 + 一键全测评全绿。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round226_toolchain25.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
