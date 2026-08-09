"""Pet & family-life spot-check (round 262): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "家里有两只猫：布丁（英短，3 岁）和奶糖（橘猫，1 岁）。",
        "kind": "semantic",
        "cues": ["布丁", "奶糖", "猫"],
    },
    {
        "content": "喂食：布丁早上 30g、晚上 30g；奶糖早上 20g、晚上 20g，猫粮都是 K9 牌。",
        "kind": "semantic",
        "cues": ["喂食", "K9"],
    },
    {
        "content": "布丁疫苗：2026年3月10日打猫三联，2026年4月5日打狂犬疫苗。",
        "kind": "episodic",
        "cues": ["布丁", "疫苗"],
    },
    {
        "content": "奶糖疫苗：2026年6月20日打猫三联，狂犬疫苗还没打。",
        "kind": "episodic",
        "cues": ["奶糖", "疫苗"],
    },
    {
        "content": "布丁的皮肤药：原来每天 5mg，7 月 1 日起改成每天 10mg，连吃两周。",
        "kind": "episodic",
        "cues": ["布丁", "皮肤药"],
    },
    {
        "content": "7月8日带布丁去安心宠物医院，王医生看的，复诊 7 月 22 日。",
        "kind": "episodic",
        "cues": ["2026-07-08", "宠物医院"],
    },
    {
        "content": "家里规则：不能喂巧克力、葡萄和洋葱；布丁对花生不过敏，奶糖对猫薄荷没反应。",
        "kind": "semantic",
        "cues": ["规则", "巧克力"],
    },
    {
        "content": "7月10日买了猫砂 4 袋（每袋 6L）、猫罐头 12 罐，花了 268 元。",
        "kind": "episodic",
        "cues": ["2026-07-10", "猫砂"],
    },
    {
        "content": "孩子 7 月 15 日放暑假，8 月 20 日开学，夏令营 8 月 1-7 日。",
        "kind": "semantic",
        "cues": ["暑假", "夏令营"],
    },
    {
        "content": "空调 7 月 12 日报修，约了 7 月 14 日上午上门，师傅姓刘。",
        "kind": "episodic",
        "cues": ["2026-07-12", "空调"],
    },
    {
        "content": "7月5日家庭会议决定：每月 15 号大扫除，垃圾分类从 7 月起执行。",
        "kind": "episodic",
        "cues": ["2026-07-05", "大扫除"],
    },
    {
        "content": "中秋节 9 月 25 日回老家，高铁票 7 月 20 日开售。",
        "kind": "semantic",
        "cues": ["中秋", "高铁"],
    },
    {
        "content": "奶糖 7 月 3 日吐过一次，喂了益生菌后好了，医生说观察。",
        "kind": "episodic",
        "cues": ["2026-07-03", "奶糖"],
    },
    {
        "content": "冰箱里常备：鸡蛋、牛奶、酸奶，周末补一次菜。",
        "kind": "semantic",
        "cues": ["冰箱", "鸡蛋"],
    },
    {
        "content": "7月11日孩子游泳课请假一次，8 月课程表发了：周三、周六 10:00。",
        "kind": "episodic",
        "cues": ["2026-07-11", "游泳课"],
    },
    {
        "content": "布丁驱虫：体内 3 个月一次，体外每月一次，上次体外 7 月 1 日。",
        "kind": "semantic",
        "cues": ["驱虫", "布丁"],
    },
    {
        "content": "7月13日超市买的狗粮是给楼下邻居家狗带的，不是自己家的。",
        "kind": "episodic",
        "cues": ["2026-07-13", "狗粮"],
    },
    {
        "content": "家庭电话：物业 400-123-4567，燃气 95007，社区医院 021-5555-8888。",
        "kind": "semantic",
        "cues": ["物业", "电话"],
    },
    {
        "content": "7月9日阳台花盆碎了，买了 3 个新的，薄荷和罗勒各一盆。",
        "kind": "episodic",
        "cues": ["2026-07-09", "花盆"],
    },
    {
        "content": "7月16日预约全家体检，7 月 28 日上午 8:30，空腹去。",
        "kind": "episodic",
        "cues": ["2026-07-16", "体检"],
    },
    {
        "content": "6月房租 4800 元已交；7 月房租 7 月 25 日前交到房东卡里。",
        "kind": "semantic",
        "cues": ["房租"],
    },
    {
        "content": "奶糖 7 月 18 日做了绝育，术后 10 天不能洗澡，7 月 25 日拆线。",
        "kind": "episodic",
        "cues": ["2026-07-18", "绝育"],
    },
    {
        "content": "布丁的项圈是蓝色带铃铛，奶糖的项圈是红色，都是防走丢款。",
        "kind": "semantic",
        "cues": ["项圈", "铃铛"],
    },
    {
        "content": "7月17日收到社区通知：8 月 2 日停水检修，上午 9 点到下午 2 点。",
        "kind": "episodic",
        "cues": ["2026-07-17", "停水"],
    },
]


QUESTIONS = [
    {
        "dim": "宠物档案",
        "q": "家里的橘猫叫什么名字？几岁了？",
        "answer": "奶糖，1 岁",
        "terms": ["奶糖", "1"],
    },
    {
        "dim": "喂食安排",
        "q": "布丁每天早晚各喂多少克猫粮？",
        "answer": "早上 30g，晚上 30g",
        "terms": ["30"],
    },
    {
        "dim": "疫苗记录",
        "q": "奶糖的狂犬疫苗打了吗？",
        "answer": "还没打",
        "terms": ["狂犬", "还没"],
    },
    {
        "dim": "用药剂量",
        "q": "布丁的皮肤药现在每天吃多少？",
        "answer": "10mg",
        "terms": ["10"],
    },
    {
        "dim": "宠物医院",
        "q": "7月8日带哪只猫去了哪家医院？",
        "answer": "布丁，安心宠物医院",
        "terms": ["安心", "宠物医院"],
    },
    {
        "dim": "家庭规则",
        "q": "家里不能喂哪三种食物？",
        "answer": "巧克力、葡萄、洋葱",
        "terms": ["巧克力", "葡萄", "洋葱"],
    },
    {
        "dim": "购物清单",
        "q": "7月10日买了多少袋猫砂？花了多少钱？",
        "answer": "4 袋，268 元",
        "terms": ["4", "268"],
    },
    {
        "dim": "学校活动",
        "q": "孩子夏令营是哪几天？",
        "answer": "8 月 1-7 日",
        "terms": ["1", "7"],
    },
    {
        "dim": "维修预约",
        "q": "空调师傅约在哪天上门？姓什么？",
        "answer": "7 月 14 日上午，刘师傅",
        "terms": ["14", "刘"],
    },
    {
        "dim": "节日安排",
        "q": "中秋节几号回老家？高铁票什么时候开售？",
        "answer": "9 月 25 日，7 月 20 日开售",
        "terms": ["25", "20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="宠物家庭",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="pet_mem0db",
        out_name="pet_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
