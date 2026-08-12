"""Account-management spot-check (round 299): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日注册网盘账号。",
        "kind": "episodic",
        "cues": ["2026-01-10", "账号"],
    },
    {
        "content": "2026年1月20日改密码：邮箱验证。",
        "kind": "episodic",
        "cues": ["2026-01-20", "改密码"],
    },
    {
        "content": "2026年2月1日开通两步验证。",
        "kind": "episodic",
        "cues": ["2026-02-01", "两步验证"],
    },
    {
        "content": "2026年2月15日绑定手机号。",
        "kind": "episodic",
        "cues": ["2026-02-15", "绑定"],
    },
    {
        "content": "2026年3月1日预约 3 月 10 日账号申诉。",
        "kind": "episodic",
        "cues": ["2026-03-01", "申诉"],
    },
    {
        "content": "2026年3月10日申诉成功。",
        "kind": "episodic",
        "cues": ["2026-03-10", "申诉"],
    },
    {
        "content": "2026年4月1日买会员：年费 128 元。",
        "kind": "episodic",
        "cues": ["2026-04-01", "会员"],
    },
    {
        "content": "2026年4月15日会员到期：2027 年 4 月 15 日。",
        "kind": "semantic",
        "cues": ["会员到期"],
    },
    {
        "content": "2026年5月1日同步照片。",
        "kind": "episodic",
        "cues": ["2026-05-01", "同步"],
    },
    {
        "content": "2026年5月20日收到提醒：5 月 30 日存储空间不足。",
        "kind": "episodic",
        "cues": ["2026-05-20", "空间"],
    },
    {
        "content": "2026年5月30日清理相册。",
        "kind": "episodic",
        "cues": ["2026-05-30", "清理"],
    },
    {
        "content": "2026年6月1日换头像。",
        "kind": "episodic",
        "cues": ["2026-06-01", "头像"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日账号迁移。",
        "kind": "episodic",
        "cues": ["2026-06-15", "迁移"],
    },
    {
        "content": "2026年6月25日迁移完成。",
        "kind": "episodic",
        "cues": ["2026-06-25", "迁移"],
    },
    {
        "content": "2026年7月1日开通家庭共享。",
        "kind": "episodic",
        "cues": ["2026-07-01", "家庭共享"],
    },
    {
        "content": "2026年7月15日收到通知：7 月 25 日版本更新。",
        "kind": "episodic",
        "cues": ["2026-07-15", "更新"],
    },
    {
        "content": "2026年7月25日更新完成。",
        "kind": "episodic",
        "cues": ["2026-07-25", "更新"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日换绑邮箱。",
        "kind": "episodic",
        "cues": ["2026-08-01", "换绑"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日会员续费。",
        "kind": "episodic",
        "cues": ["2026-08-05", "续费"],
    },
    {
        "content": "客服邮箱 support@example.com。",
        "kind": "semantic",
        "cues": ["客服", "邮箱"],
    },
]


QUESTIONS = [
    {
        "dim": "账号安全",
        "q": "开了什么安全设置？",
        "answer": "两步验证、绑定手机",
        "terms": ["两步"],
    },
    {
        "dim": "会员信息",
        "q": "会员多少钱？什么时候到期？",
        "answer": "128元，2027年4月15日",
        "terms": ["128", "2027"],
    },
    {
        "dim": "未来安排",
        "q": "下次换绑邮箱是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "申诉记录",
        "q": "账号申诉什么时候成功的？",
        "answer": "3月10日",
        "terms": ["10"],
    },
    {
        "dim": "迁移记录",
        "q": "账号迁移什么时候完成的？",
        "answer": "6月25日",
        "terms": ["25"],
    },
    {
        "dim": "空间提醒",
        "q": "什么时候提醒存储空间不足？",
        "answer": "5月30日",
        "terms": ["30"],
    },
    {
        "dim": "家庭共享",
        "q": "开通了什么功能？",
        "answer": "家庭共享",
        "terms": ["家庭共享"],
    },
    {
        "dim": "客服邮箱",
        "q": "客服邮箱多少？",
        "answer": "support@example.com",
        "terms": ["support"],
    },
    {
        "dim": "续费提醒",
        "q": "会员什么时候续费？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "版本更新",
        "q": "版本更新什么时候？",
        "answer": "7月25日",
        "terms": ["25"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="账号管理",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="account_mem0db",
        out_name="account_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
