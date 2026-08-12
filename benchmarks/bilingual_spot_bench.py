"""Bilingual + repeated-number spot-check (round 263): mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "产品 Nova 当前版本 v2.1，主打移动端；Nova Pro 是桌面版，当前 v1.4。",
        "kind": "semantic",
        "cues": ["Nova", "版本"],
    },
    {
        "content": "Nova v2.2 计划 8 月 30 日发布，发布窗口 8 月 28 日-9 月 2 日。",
        "kind": "episodic",
        "cues": ["Nova", "v2.2", "发布窗口"],
    },
    {
        "content": "Nova Pro v1.5 计划 9 月 15 日发布，发布窗口 9 月 12 日-9 月 18 日。",
        "kind": "episodic",
        "cues": ["Nova Pro", "发布窗口"],
    },
    {
        "content": "任务 A 的 UI 冻结是 8 月 15 日；任务 B 的文案定稿也是 8 月 15 日。",
        "kind": "semantic",
        "cues": ["任务A", "8月15日"],
    },
    {
        "content": "8月转化率 3.2%，比 7 月高 0.4 个百分点；9 月目标 3.5%。",
        "kind": "semantic",
        "cues": ["转化率"],
    },
    {
        "content": "客单价：Nova 内购 128 元，Nova Pro 买断 128 元，但有效期不同。",
        "kind": "semantic",
        "cues": ["客单价", "128"],
    },
    {
        "content": "客户王磊（上海）合同 8 月到期，客户 Wang Li（海外）合同 12 月到期。",
        "kind": "semantic",
        "cues": ["王磊", "Wang Li"],
    },
    {
        "content": "7月20日产品周会纪要：Nova 2.1 的用户反馈标签改版，Nova Pro 暂不动。",
        "kind": "episodic",
        "cues": ["2026-07-20", "周会"],
    },
    {
        "content": "账号：测试环境 admin/test123，生产只读账号 reader/prod456。",
        "kind": "semantic",
        "cues": ["账号", "admin"],
    },
    {
        "content": "术语表：onboarding 译为“新手引导”，checkout 译为“结算”，不要用“支付页”。",
        "kind": "semantic",
        "cues": ["术语", "onboarding"],
    },
    {
        "content": "排期依赖：Nova v2.2 依赖支付 SDK 1.9，SDK 计划 8 月 10 日交付。",
        "kind": "semantic",
        "cues": ["依赖", "SDK"],
    },
    {
        "content": "8月1日灰度：Nova v2.2 先放 5% 用户，观察 3 天再放量。",
        "kind": "episodic",
        "cues": ["2026-08-01", "灰度"],
    },
    {
        "content": "客户王磊的续费折扣是 8 折；Wang Li 的续费折扣是 9 折。",
        "kind": "semantic",
        "cues": ["王磊", "折扣"],
    },
    {
        "content": "8月5日 QA 报告：Nova v2.2 有 3 个 P1 bug，其中登录闪退必须在 8 月 12 日前修。",
        "kind": "episodic",
        "cues": ["2026-08-05", "P1"],
    },
    {
        "content": "8月8日客服反馈：Nova 2.1 的推送文案有歧义，已改一版，8 月 9 日上线。",
        "kind": "episodic",
        "cues": ["2026-08-08", "推送"],
    },
    {
        "content": "翻译排期：onboarding 文案 8 月 18 日交中文稿，8 月 25 日交日文稿。",
        "kind": "semantic",
        "cues": ["翻译", "onboarding"],
    },
    {
        "content": "7月活跃用户：Nova 86 万，Nova Pro 12 万；8 月目标 Nova 100 万。",
        "kind": "semantic",
        "cues": ["活跃", "86"],
    },
    {
        "content": "8月10日 SDK 1.9 提前交付，Nova v2.2 联调提前到 8 月 14 日。",
        "kind": "episodic",
        "cues": ["2026-08-10", "SDK"],
    },
    {
        "content": "合同条款：王磊合同含 30 天试用；Wang Li 合同含 60 天试用。",
        "kind": "semantic",
        "cues": ["合同", "试用"],
    },
    {
        "content": "8月12日修完登录闪退，QA 复测通过，8 月 13 日合入 v2.2 分支。",
        "kind": "episodic",
        "cues": ["2026-08-12", "闪退"],
    },
    {
        "content": "8月15日任务 A UI 冻结完成；任务 B 文案定稿也完成，未延误。",
        "kind": "episodic",
        "cues": ["2026-08-15", "冻结"],
    },
    {
        "content": "8月16日灰度放量到 20%，次日回滚到 5%，因为崩溃率 0.3%。",
        "kind": "episodic",
        "cues": ["2026-08-16", "灰度"],
    },
    {
        "content": "8月18日 onboarding 中文稿交付；日文稿因译员请假改到 8 月 26 日。",
        "kind": "episodic",
        "cues": ["2026-08-18", "中文稿"],
    },
    {
        "content": "8月20日决定 Nova v2.2 上线前加 A/B 实验：新引导 vs 旧引导，跑 7 天。",
        "kind": "episodic",
        "cues": ["2026-08-20", "A/B"],
    },
    {
        "content": "8月21日 Wang Li 邮件确认续费，9 月起生效，年付 128 美元。",
        "kind": "episodic",
        "cues": ["2026-08-21", "Wang Li"],
    },
    {
        "content": "8月22日王磊电话确认续费，9 月起生效，年付 1280 元。",
        "kind": "episodic",
        "cues": ["2026-08-22", "王磊"],
    },
]


QUESTIONS = [
    {
        "dim": "版本记录",
        "q": "Nova Pro 当前是什么版本？",
        "answer": "v1.4",
        "terms": ["v1.4"],
    },
    {
        "dim": "截止日期",
        "q": "任务 B 的文案定稿是哪天？",
        "answer": "8 月 15 日",
        "terms": ["15"],
    },
    {
        "dim": "指标数据",
        "q": "8 月转化率是多少？比 7 月高多少？",
        "answer": "3.2%，高 0.4 个百分点",
        "terms": ["3.2", "0.4"],
    },
    {
        "dim": "客户信息",
        "q": "海外客户 Wang Li 的合同什么时候到期？",
        "answer": "12 月",
        "terms": ["12"],
    },
    {
        "dim": "合同条款",
        "q": "王磊的合同含多少天试用？",
        "answer": "30 天",
        "terms": ["30"],
    },
    {
        "dim": "会议纪要",
        "q": "7月20日周会决定 Nova 2.1 改什么？",
        "answer": "用户反馈标签改版",
        "terms": ["反馈标签"],
    },
    {
        "dim": "权限账号",
        "q": "生产环境只读账号的密码是什么？",
        "answer": "prod456",
        "terms": ["prod456"],
    },
    {
        "dim": "翻译术语",
        "q": "checkout 应该译成什么？",
        "answer": "结算",
        "terms": ["结算"],
    },
    {
        "dim": "排期依赖",
        "q": "Nova v2.2 依赖的支付 SDK 是哪个版本？",
        "answer": "1.9",
        "terms": ["1.9"],
    },
    {
        "dim": "发布窗口",
        "q": "Nova v2.2 的发布窗口是哪几天？",
        "answer": "8 月 28 日-9 月 2 日",
        "terms": ["28", "2"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="多语种工作",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="bilingual_mem0db",
        out_name="bilingual_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
