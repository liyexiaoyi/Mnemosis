"""Home-renovation spot-check (round 264): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "新家 8 月交房，户型 89 平两居，装修预算 12 万，9 月开工。",
        "kind": "semantic",
        "cues": ["交房", "预算"],
    },
    {
        "content": "装修公司 A 报价 11.6 万（半包），公司 B 报价 10.2 万（全包，主材另算）。",
        "kind": "semantic",
        "cues": ["公司A", "公司B", "报价"],
    },
    {
        "content": "7月20日选定公司 B：全包合同 10.2 万，工期 75 天，9 月 5 日开工。",
        "kind": "episodic",
        "cues": ["2026-07-20", "合同"],
    },
    {
        "content": "付款计划：开工付 40%、水电验收付 40%、完工付 20%；8 月 2 日改为 30/40/30。",
        "kind": "semantic",
        "cues": ["付款", "40"],
    },
    {
        "content": "主材清单：地板 95 元/平，瓷砖 68 元/平，乳胶漆 3 桶共 1280 元。",
        "kind": "semantic",
        "cues": ["主材", "地板"],
    },
    {
        "content": "9月5日开工，9 月 20 日水电进场，10 月 10 日瓦工进场。",
        "kind": "episodic",
        "cues": ["2026-09-05", "水电"],
    },
    {
        "content": "9月25日水电验收通过，付第二笔款 3.06 万（30%）。",
        "kind": "episodic",
        "cues": ["2026-09-25", "水电验收"],
    },
    {
        "content": "10月15日瓦工验收：瓷砖空鼓 3 处，要求返工，10 月 18 日重做。",
        "kind": "episodic",
        "cues": ["2026-10-15", "空鼓"],
    },
    {
        "content": "合同保修：隐蔽工程 5 年，整体 2 年，从完工日起算。",
        "kind": "semantic",
        "cues": ["保修", "5年"],
    },
    {
        "content": "8月20日跟楼上邻居打过招呼：装修噪音集中在 9:00-12:00、14:00-18:00。",
        "kind": "episodic",
        "cues": ["2026-08-20", "邻居"],
    },
    {
        "content": "物业规定：装修押金 2000 元，垃圾清运费 300 元，周末禁止大噪音施工。",
        "kind": "semantic",
        "cues": ["物业", "押金"],
    },
    {
        "content": "11月1日预计完工，搬家定在 11 月 15 日，搬家公司已预约。",
        "kind": "semantic",
        "cues": ["完工", "搬家"],
    },
    {
        "content": "7月25日量了尺寸：客厅 24 平、主卧 14 平、次卧 11 平。",
        "kind": "episodic",
        "cues": ["2026-07-25", "尺寸"],
    },
    {
        "content": "8月5日订了家电：冰箱 4599 元、洗衣机 3299 元、空调两台 5600 元。",
        "kind": "episodic",
        "cues": ["2026-08-05", "家电"],
    },
    {
        "content": "9月30日发现合同里没写阳台防水，补签增项 2600 元。",
        "kind": "episodic",
        "cues": ["2026-09-30", "增项"],
    },
    {
        "content": "10月20日油漆进场：乳胶漆颜色选了暖白，儿童房浅蓝。",
        "kind": "episodic",
        "cues": ["2026-10-20", "油漆"],
    },
    {
        "content": "10月25日木工验收通过：柜子 12 个抽屉全部顺滑，铰链是百隆。",
        "kind": "episodic",
        "cues": ["2026-10-25", "木工"],
    },
    {
        "content": "11月3日完工验收：发现 2 处乳胶漆色差，公司 B 承诺 11 月 8 日前修复。",
        "kind": "episodic",
        "cues": ["2026-11-03", "色差"],
    },
    {
        "content": "尾款 20% 共 2.04 万，修复验收通过后 11 月 10 日前付。",
        "kind": "semantic",
        "cues": ["尾款", "2.04"],
    },
    {
        "content": "11月6日物业退装修押金 2000 元，垃圾清运费不退。",
        "kind": "episodic",
        "cues": ["2026-11-06", "押金"],
    },
    {
        "content": "搬家清单：先搬床和沙发，再搬厨房用品，最后书和衣服。",
        "kind": "semantic",
        "cues": ["搬家", "清单"],
    },
    {
        "content": "11月12日开通燃气预约成功，师傅 11 月 14 日上午上门。",
        "kind": "episodic",
        "cues": ["2026-11-12", "燃气"],
    },
    {
        "content": "邻居 11 月 13 日说阳台渗水，物业约 11 月 16 日一起看。",
        "kind": "episodic",
        "cues": ["2026-11-13", "渗水"],
    },
    {
        "content": "11月15日搬家完成，晚上在新家吃了第一顿饭，点了外卖。",
        "kind": "episodic",
        "cues": ["2026-11-15", "搬家"],
    },
    {
        "content": "11月20日发现柜门铰链有一颗松动，联系公司 B 保修。",
        "kind": "episodic",
        "cues": ["2026-11-20", "铰链"],
    },
    {
        "content": "装修总花费：合同 10.2 万 + 增项 2600 + 家电 1.35 万，共 11.81 万。",
        "kind": "semantic",
        "cues": ["总花费", "11.81"],
    },
]


QUESTIONS = [
    {
        "dim": "装修报价",
        "q": "公司 B 的报价是多少？是半包还是全包？",
        "answer": "10.2 万，全包",
        "terms": ["10.2", "全包"],
    },
    {
        "dim": "材料清单",
        "q": "地板多少钱一平？乳胶漆 3 桶多少钱？",
        "answer": "95 元/平，1280 元",
        "terms": ["95", "1280"],
    },
    {
        "dim": "施工进度",
        "q": "瓦工是什么时候进场的？",
        "answer": "10 月 10 日",
        "terms": ["10", "10"],
    },
    {
        "dim": "付款计划",
        "q": "现在的付款比例是什么？",
        "answer": "30/40/30",
        "terms": ["30", "40", "30"],
    },
    {
        "dim": "合同条款",
        "q": "装修合同保修期隐蔽工程几年？",
        "answer": "5 年",
        "terms": ["5"],
    },
    {
        "dim": "验收记录",
        "q": "10月15日瓦工验收发现了什么问题？",
        "answer": "瓷砖空鼓 3 处",
        "terms": ["空鼓", "3"],
    },
    {
        "dim": "保修信息",
        "q": "11月20日发现什么保修问题？",
        "answer": "柜门铰链松动",
        "terms": ["铰链", "松动"],
    },
    {
        "dim": "邻居沟通",
        "q": "装修噪音施工时间是几点到几点？",
        "answer": "9:00-12:00、14:00-18:00",
        "terms": ["9", "18"],
    },
    {
        "dim": "搬家计划",
        "q": "搬家定在哪天？",
        "answer": "11 月 15 日",
        "terms": ["15"],
    },
    {
        "dim": "物业规定",
        "q": "装修押金是多少？垃圾清运费呢？",
        "answer": "押金 2000，清运费 300",
        "terms": ["2000", "300"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="住房装修",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="home_mem0db",
        out_name="home_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
