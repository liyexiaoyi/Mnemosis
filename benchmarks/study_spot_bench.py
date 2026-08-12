"""Study-abroad spot-check (round 266): Mnemosis vs mem0 ONLY.

New domain (留学申请) and new dimensions (考试时间线/未来预约/申请结果/
面试内容/签证材料/疫苗记录/入学安排/宿舍入住/机票信息/申请费用).
Continues the paper-driven loop: temporal-context model (Howard &
Kahana 2002), cross-scale time cells (Howard & Eichenbaum 2013),
ordinal-time processing (Gauthier et al. 2020), and the space/time/
number line (Dehaene & Brannon 2011).
"""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日决定申请美国研究生，目标院校 5 所。",
        "kind": "episodic",
        "cues": ["2026-01-10", "目标院校"],
    },
    {
        "content": "2026年1月20日报了托福班：2 月 15 日首考。",
        "kind": "episodic",
        "cues": ["2026-01-20", "托福"],
    },
    {
        "content": "2026年2月15日托福首考：总分 96。",
        "kind": "episodic",
        "cues": ["2026-02-15", "托福"],
    },
    {
        "content": "2026年2月25日报名 3 月 20 日第二次托福。",
        "kind": "episodic",
        "cues": ["2026-02-25", "托福"],
    },
    {
        "content": "2026年3月20日托福二考：总分 104（达标）。",
        "kind": "episodic",
        "cues": ["2026-03-20", "托福"],
    },
    {
        "content": "2026年4月1日找推荐人：导师王老师同意写推荐信。",
        "kind": "episodic",
        "cues": ["2026-04-01", "推荐信"],
    },
    {
        "content": "2026年4月10日考 GRE：总分 322。",
        "kind": "episodic",
        "cues": ["2026-04-10", "GRE"],
    },
    {
        "content": "2026年4月20日写个人陈述初稿，找学长改了 3 遍。",
        "kind": "episodic",
        "cues": ["2026-04-20", "个人陈述"],
    },
    {
        "content": "2026年5月5日递交 A 大学申请：计算机硕士，申请费 90 美元。",
        "kind": "episodic",
        "cues": ["2026-05-05", "A大学"],
    },
    {
        "content": "2026年5月8日递交 B 大学申请。",
        "kind": "episodic",
        "cues": ["2026-05-08", "B大学"],
    },
    {
        "content": "2026年5月15日收到 A 大学面试邀请：5 月 25 日视频面试。",
        "kind": "episodic",
        "cues": ["2026-05-15", "面试"],
    },
    {
        "content": "2026年5月25日 A 大学面试完成：问科研经历。",
        "kind": "episodic",
        "cues": ["2026-05-25", "面试"],
    },
    {
        "content": "2026年6月1日收到 A 大学 offer：奖学金 60%。",
        "kind": "semantic",
        "cues": ["offer", "奖学金"],
    },
    {
        "content": "2026年6月10日签证预约：6 月 20 日面签，带 I-20。",
        "kind": "episodic",
        "cues": ["2026-06-10", "签证"],
    },
    {
        "content": "2026年6月20日面签通过，7 月 10 日出发。",
        "kind": "episodic",
        "cues": ["2026-06-20", "签证"],
    },
    {
        "content": "2026年6月25日收到 B 大学 waitlist 通知。",
        "kind": "episodic",
        "cues": ["2026-06-25", "waitlist"],
    },
    {
        "content": "2026年7月1日买机票：8 月 25 日上海飞洛杉矶。",
        "kind": "episodic",
        "cues": ["2026-07-01", "机票"],
    },
    {
        "content": "2026年7月5日预约体检：7 月 15 日体检。",
        "kind": "episodic",
        "cues": ["2026-07-05", "体检"],
    },
    {
        "content": "2026年7月15日体检完成：疫苗记录缺乙肝。",
        "kind": "episodic",
        "cues": ["2026-07-15", "疫苗"],
    },
    {
        "content": "2026年7月20日补打乙肝疫苗，8 月 5 日拿接种证明。",
        "kind": "episodic",
        "cues": ["2026-07-20", "乙肝"],
    },
    {
        "content": "2026年7月25日收到学校邮件：8 月 30 日新生注册，9 月 1 日开学。",
        "kind": "episodic",
        "cues": ["2026-07-25", "注册"],
    },
    {
        "content": "2026年8月2日定宿舍：8 月 28 日入住。",
        "kind": "episodic",
        "cues": ["2026-08-02", "宿舍"],
    },
    {
        "content": "2026年8月6日预约 8 月 20 日行前说明会。",
        "kind": "episodic",
        "cues": ["2026-08-06", "说明会"],
    },
    {
        "content": "行前说明会是线上会议，链接发在邮箱里。",
        "kind": "semantic",
        "cues": ["说明会", "链接"],
    },
    {
        "content": "行李清单：护照、I-20、疫苗证明、成绩单。",
        "kind": "semantic",
        "cues": ["行李", "I-20"],
    },
    {
        "content": "汇率提醒：开学前换 5000 美元，分批换。",
        "kind": "semantic",
        "cues": ["汇率", "美元"],
    },
    {
        "content": "2026年8月8日预约：8 月 22 日去银行办信用卡。",
        "kind": "episodic",
        "cues": ["2026-08-08", "信用卡"],
    },
]


QUESTIONS = [
    {
        "dim": "考试时间线",
        "q": "上次托福考试是什么时候？考了多少分？",
        "answer": "3月20日，104分",
        "terms": ["104"],
    },
    {
        "dim": "未来预约",
        "q": "下次去银行办信用卡是什么时候？",
        "answer": "8月22日",
        "terms": ["22"],
    },
    {
        "dim": "申请结果",
        "q": "A 大学的申请结果是什么？",
        "answer": "offer，奖学金60%",
        "terms": ["奖学金", "60"],
    },
    {
        "dim": "面试内容",
        "q": "上次面试是什么时候？问了什么？",
        "answer": "5月25日，科研经历",
        "terms": ["科研经历"],
    },
    {
        "dim": "签证材料",
        "q": "面签要带什么？",
        "answer": "I-20",
        "terms": ["I-20"],
    },
    {
        "dim": "疫苗记录",
        "q": "体检发现缺什么疫苗？",
        "answer": "乙肝疫苗",
        "terms": ["乙肝"],
    },
    {
        "dim": "入学安排",
        "q": "什么时候开学？新生注册是什么时候？",
        "answer": "9月1日开学，8月30日注册",
        "terms": ["30", "1"],
    },
    {
        "dim": "宿舍入住",
        "q": "宿舍什么时候能入住？",
        "answer": "8月28日",
        "terms": ["28"],
    },
    {
        "dim": "机票信息",
        "q": "机票是哪天的？从哪里飞到哪里？",
        "answer": "8月25日，上海飞洛杉矶",
        "terms": ["上海", "洛杉矶"],
    },
    {
        "dim": "申请费用",
        "q": "A 大学的申请费是多少？",
        "answer": "90美元",
        "terms": ["90"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="留学申请",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="study_mem0db",
        out_name="study_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
