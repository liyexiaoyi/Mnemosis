"""Adult-vaccination spot-check (round 307): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日打流感疫苗。",
        "kind": "episodic",
        "cues": ["2026-01-10", "流感"],
    },
    {
        "content": "2026年1月20日预约 2 月 1 日乙肝疫苗。",
        "kind": "episodic",
        "cues": ["2026-01-20", "乙肝"],
    },
    {
        "content": "2026年2月1日打乙肝疫苗第三针。",
        "kind": "episodic",
        "cues": ["2026-02-01", "乙肝"],
    },
    {
        "content": "2026年3月1日预约 3 月 15 日带状疱疹疫苗。",
        "kind": "episodic",
        "cues": ["2026-03-01", "带状疱疹"],
    },
    {
        "content": "2026年3月15日打带状疱疹疫苗第一针。",
        "kind": "episodic",
        "cues": ["2026-03-15", "带状疱疹"],
    },
    {
        "content": "2026年4月1日预约 4 月 15 日第二针。",
        "kind": "episodic",
        "cues": ["2026-04-01", "带状疱疹"],
    },
    {
        "content": "2026年4月15日打第二针。",
        "kind": "episodic",
        "cues": ["2026-04-15", "带状疱疹"],
    },
    {
        "content": "2026年5月1日预约 5 月 10 日破伤风疫苗。",
        "kind": "episodic",
        "cues": ["2026-05-01", "破伤风"],
    },
    {
        "content": "2026年5月10日打破伤风疫苗。",
        "kind": "episodic",
        "cues": ["2026-05-10", "破伤风"],
    },
    {
        "content": "2026年6月1日预约 6 月 15 日 HPV 疫苗。",
        "kind": "episodic",
        "cues": ["2026-06-01", "HPV"],
    },
    {
        "content": "2026年6月15日打 HPV 第一针。",
        "kind": "episodic",
        "cues": ["2026-06-15", "HPV"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日 HPV 第二针。",
        "kind": "episodic",
        "cues": ["2026-07-01", "HPV"],
    },
    {
        "content": "2026年7月15日打 HPV 第二针。",
        "kind": "episodic",
        "cues": ["2026-07-15", "HPV"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日 HPV 第三针。",
        "kind": "episodic",
        "cues": ["2026-08-01", "HPV"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日流感疫苗预约。",
        "kind": "episodic",
        "cues": ["2026-08-05", "流感"],
    },
    {
        "content": "接种点电话 400-444-5555。",
        "kind": "semantic",
        "cues": ["接种点", "电话"],
    },
    {
        "content": "疫苗本放家里。",
        "kind": "semantic",
        "cues": ["疫苗本"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日社区义诊。",
        "kind": "episodic",
        "cues": ["2026-08-08", "义诊"],
    },
]


QUESTIONS = [
    {
        "dim": "流感疫苗",
        "q": "流感疫苗什么时候打的？",
        "answer": "1月10日",
        "terms": ["10"],
    },
    {
        "dim": "乙肝疫苗",
        "q": "乙肝疫苗什么时候打的？",
        "answer": "2月1日",
        "terms": ["1"],
    },
    {
        "dim": "HPV进度",
        "q": "HPV疫苗上次打的是第几针？",
        "answer": "第二针",
        "terms": ["第二针"],
    },
    {
        "dim": "未来安排",
        "q": "下次 HPV 第三针是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "带状疱疹",
        "q": "带状疱疹疫苗什么时候打的第一针？",
        "answer": "3月15日",
        "terms": ["15"],
    },
    {
        "dim": "破伤风",
        "q": "破伤风疫苗什么时候打的？",
        "answer": "5月10日",
        "terms": ["10"],
    },
    {
        "dim": "接种点",
        "q": "接种点电话多少？",
        "answer": "400-444-5555",
        "terms": ["5555"],
    },
    {
        "dim": "疫苗本",
        "q": "疫苗本放哪？",
        "answer": "家里",
        "terms": ["家里"],
    },
    {
        "dim": "流感预约",
        "q": "流感疫苗什么时候预约？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "社区义诊",
        "q": "社区义诊什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="成人疫苗",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="vaccine_mem0db",
        out_name="vaccine_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
