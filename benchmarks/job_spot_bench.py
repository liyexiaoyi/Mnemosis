"""Job-hunting spot-check (round 265): Mnemosis vs mem0 ONLY.

New domain (求职/就业) and new dimensions (上次/下次时间锚点、薪资福利、
报销明细、入职材料、试用期、制度流程、猎头沟通、培训准备、预约看牙).
Driven by temporal-context model (Howard & Kahana, 2002), cross-scale
time cells (Howard & Eichenbaum, 2013), human ordinal-time processing
(Gauthier et al., 2020) and the space/time/number line (Dehaene &
Brannon, 2011).
"""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年4月10日投了简历到云图科技：后端工程师，简历编号 R-2031。",
        "kind": "episodic",
        "cues": ["2026-04-10", "简历"],
    },
    {
        "content": "2026年4月12日云图科技约一面：4 月 18 日 19:30 视频面试。",
        "kind": "episodic",
        "cues": ["2026-04-12", "一面"],
    },
    {
        "content": "2026年4月18日一面完成：问 Go、Redis、系统设计，说一周内给结果。",
        "kind": "episodic",
        "cues": ["2026-04-18", "一面"],
    },
    {
        "content": "2026年4月25日云图科技通知二面：4 月 30 日线下，带作品。",
        "kind": "episodic",
        "cues": ["2026-04-25", "二面"],
    },
    {
        "content": "2026年4月30日二面完成：技术负责人面，聊了消息队列选型。",
        "kind": "episodic",
        "cues": ["2026-04-30", "二面"],
    },
    {
        "content": "2026年5月6日终面完成：总监问职业规划，薪资谈到 30k。",
        "kind": "episodic",
        "cues": ["2026-05-06", "终面"],
    },
    {
        "content": "2026年5月15日收到 offer：月薪 30k，14 薪，6 月 1 日入职。",
        "kind": "semantic",
        "cues": ["offer", "30k"],
    },
    {
        "content": "2026年5月18日拒绝了星辰互动的 offer：月薪 28k，加班多。",
        "kind": "episodic",
        "cues": ["2026-05-18", "星辰互动"],
    },
    {
        "content": "2026年5月25日入职体检：报告 6 月 1 日前出来。",
        "kind": "episodic",
        "cues": ["2026-05-25", "体检"],
    },
    {
        "content": "2026年6月1日入职云图科技，签劳动合同：试用期 3 个月，8 月 20 日前转正评估。",
        "kind": "episodic",
        "cues": ["2026-06-01", "入职"],
    },
    {
        "content": "2026年6月5日 HR 说工资每月 10 号发，公积金按 12% 缴纳。",
        "kind": "semantic",
        "cues": ["工资", "公积金"],
    },
    {
        "content": "2026年6月10日收到第一笔工资：实发 25983 元（扣税和公积金）。",
        "kind": "episodic",
        "cues": ["2026-06-10", "工资"],
    },
    {
        "content": "入职材料：身份证复印件、学历证明、离职证明、一寸照。",
        "kind": "semantic",
        "cues": ["入职材料"],
    },
    {
        "content": "2026年7月2日申请报销：键盘 899 元、显示器 1599 元，发票已提交。",
        "kind": "episodic",
        "cues": ["2026-07-02", "报销"],
    },
    {
        "content": "2026年7月12日报销到账 2498 元。",
        "kind": "episodic",
        "cues": ["2026-07-12", "报销"],
    },
    {
        "content": "2026年7月18日 HR 通知：7 月 25 日年度团建，可带家属。",
        "kind": "episodic",
        "cues": ["2026-07-18", "团建"],
    },
    {
        "content": "2026年7月20日预约：7 月 28 日补牙，医保卡要带上。",
        "kind": "episodic",
        "cues": ["2026-07-20", "补牙"],
    },
    {
        "content": "2026年7月22日约了猎头：7 月 30 日聊聊新机会。",
        "kind": "episodic",
        "cues": ["2026-07-22", "猎头"],
    },
    {
        "content": "2026年7月30日猎头聊完：推荐两个机会，一家做电商，一家做 AI 工具。",
        "kind": "episodic",
        "cues": ["2026-07-30", "猎头"],
    },
    {
        "content": "2026年8月5日同事小周说 8 月 15 日部门技术分享，主题是分布式锁。",
        "kind": "episodic",
        "cues": ["2026-08-05", "技术分享"],
    },
    {
        "content": "2026年8月6日收到通知：8 月 16 日新人中期沟通会，准备 10 分钟 PPT。",
        "kind": "episodic",
        "cues": ["2026-08-06", "沟通会"],
    },
    {
        "content": "公司报销制度：加班餐 50 元/天，打车 22:00 后可以报销。",
        "kind": "semantic",
        "cues": ["报销制度"],
    },
    {
        "content": "加班申请流程：先跟组长确认，再在 OA 提交，审批后算调休。",
        "kind": "semantic",
        "cues": ["加班", "调休"],
    },
    {
        "content": "试用期薪资按 100% 发放，转正后调薪看 12 月绩效。",
        "kind": "semantic",
        "cues": ["试用期", "薪资"],
    },
    {
        "content": "2026年8月8日收到 8 月 12 日的会议提醒：评审数据库选型，带方案文档。",
        "kind": "episodic",
        "cues": ["2026-08-08", "会议"],
    },
    {
        "content": "2026年8月9日买了工位升降桌 1099 元，发票放报销文件夹。",
        "kind": "episodic",
        "cues": ["2026-08-09", "升降桌"],
    },
]


QUESTIONS = [
    {
        "dim": "求职时间线",
        "q": "上次面试是哪一天？面了什么内容？",
        "answer": "5月6日终面，总监问职业规划",
        "terms": ["职业规划"],
    },
    {
        "dim": "未来安排",
        "q": "下次团建是什么时候？",
        "answer": "7月25日",
        "terms": ["25"],
    },
    {
        "dim": "薪资福利",
        "q": "工资每月几号发？公积金比例是多少？",
        "answer": "每月10号，公积金12%",
        "terms": ["10", "12"],
    },
    {
        "dim": "报销明细",
        "q": "7月2日报销了哪些东西？一共多少钱？",
        "answer": "键盘899、显示器1599，共2498元",
        "terms": ["键盘", "2498"],
    },
    {
        "dim": "入职材料",
        "q": "入职需要带哪些材料？",
        "answer": "身份证复印件、学历证明、离职证明、一寸照",
        "terms": ["学历证明"],
    },
    {
        "dim": "试用期",
        "q": "试用期是几个月？什么时候转正评估？",
        "answer": "3个月，8月20日前",
        "terms": ["20"],
    },
    {
        "dim": "制度流程",
        "q": "加班申请流程是什么？",
        "answer": "先跟组长确认，再在OA提交，审批后算调休",
        "terms": ["调休"],
    },
    {
        "dim": "猎头沟通",
        "q": "上次和猎头聊是什么时候？推荐了什么？",
        "answer": "7月30日，电商和AI工具两个机会",
        "terms": ["AI"],
    },
    {
        "dim": "培训准备",
        "q": "8月16日的沟通会要准备什么？",
        "answer": "10分钟PPT",
        "terms": ["PPT"],
    },
    {
        "dim": "预约看牙",
        "q": "补牙是什么时候？要带什么？",
        "answer": "7月28日，医保卡",
        "terms": ["医保卡"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="就业求职",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="job_mem0db",
        out_name="job_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
