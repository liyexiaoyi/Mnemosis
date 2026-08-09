"""Travel-planning spot-check (round 261): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "8月20日到 8月24日去东京玩，行程：20日浅草，21日涩谷，22日镰仓，23日台场，24日返程。",
        "kind": "episodic",
        "cues": ["东京", "行程"],
    },
    {
        "content": "机票：8月20日 10:30 上海虹桥 T2 飞羽田，航班 MU523；返程 8月24日 18:40 羽田飞虹桥，MU524。",
        "kind": "episodic",
        "cues": ["机票", "MU523"],
    },
    {
        "content": "酒店：8月20-22日住浅草 APA 酒店 402 房；8月22-24日住镰仓王子酒店 815 房。",
        "kind": "episodic",
        "cues": ["酒店", "APA"],
    },
    {
        "content": "护照 2031 年 4 月过期；日本签证单次 15 天，8 月 10 日已出签。",
        "kind": "semantic",
        "cues": ["护照", "签证"],
    },
    {
        "content": "行李清单：护照、充电宝（2万毫安内）、转换插头、常备药、雨伞、薄外套。",
        "kind": "semantic",
        "cues": ["行李", "充电宝"],
    },
    {
        "content": "东京交通：提前买西瓜卡，押金 500 日元，余额充 3000 日元。",
        "kind": "semantic",
        "cues": ["西瓜卡", "交通"],
    },
    {
        "content": "8月21日预约了涩谷天空观景台 18:30 入场，票号 SKY-8841。",
        "kind": "episodic",
        "cues": ["观景台", "SKY-8841"],
    },
    {
        "content": "8月23日预约镰仓大佛 10:00 入场，票号 BUD-2210。",
        "kind": "episodic",
        "cues": ["大佛", "BUD-2210"],
    },
    {
        "content": "8月20日预约了东京国立博物馆 14:00 入场，票号 MUS-3310。",
        "kind": "episodic",
        "cues": ["博物馆", "MUS-3310"],
    },
    {
        "content": "语言备忘：日语的“谢谢”是 ありがとう，问路用 すみません。",
        "kind": "semantic",
        "cues": ["日语", "ありがとう"],
    },
    {
        "content": "旅游保险：安联亚洲计划，保单号 AL-889900，紧急电话 +81-3-1234-5678。",
        "kind": "semantic",
        "cues": ["保险", "AL-889900"],
    },
    {
        "content": "预算：机票两人 5400 元、酒店 4800 元、交通 1500 元、餐饮 3200 元，总预算 18000 元。",
        "kind": "semantic",
        "cues": ["预算", "18000"],
    },
    {
        "content": "天气备选：22 日镰仓预报有雨，改去江之岛水族馆（已确认可现场买票）。",
        "kind": "episodic",
        "cues": ["天气", "江之岛"],
    },
    {
        "content": "8月18日已把行程单发给爸妈，附了航班号和酒店地址。",
        "kind": "episodic",
        "cues": ["2026-08-18", "行程单"],
    },
    {
        "content": "支付：东京多数店支持微信支付宝，但备了 5 万日元现金。",
        "kind": "semantic",
        "cues": ["现金", "支付"],
    },
    {
        "content": "8月19日收到航司通知：MU523 改到 11:00 起飞，航班号不变。",
        "kind": "episodic",
        "cues": ["2026-08-19", "改签"],
    },
    {
        "content": "eSIM 已购买：日本 8 天 20GB，激活码 ESIM-JP-2608。",
        "kind": "semantic",
        "cues": ["eSIM", "ESIM"],
    },
    {
        "content": "到羽田后路线：坐京急线到浅草站，约 40 分钟，620 日元。",
        "kind": "semantic",
        "cues": ["京急线", "羽田"],
    },
    {
        "content": "8月22日镰仓交通：江之电一日券 800 日元，覆盖镰仓到江之岛。",
        "kind": "episodic",
        "cues": ["江之电", "一日券"],
    },
    {
        "content": "餐饮备忘：浅草附近预约了 8月20日 19:00 的烤肉店，2 人位。",
        "kind": "episodic",
        "cues": ["烤肉", "浅草"],
    },
    {
        "content": "购物清单：给妈妈带护手霜，给同事带巧克力，自己看手办。",
        "kind": "semantic",
        "cues": ["购物", "护手霜"],
    },
    {
        "content": "8月21日晚上预约了新宿的居酒屋 20:30，4 人位。",
        "kind": "episodic",
        "cues": ["居酒屋", "新宿"],
    },
    {
        "content": "保险理赔资料：医院收据、航班延误证明都要留好。",
        "kind": "semantic",
        "cues": ["理赔", "收据"],
    },
    {
        "content": "返程提醒：羽田机场退税在 3 楼，现金退税要收手续费。",
        "kind": "semantic",
        "cues": ["退税", "羽田"],
    },
    {
        "content": "8月23日晚上在镰仓吃了荞麦面，人均 1200 日元。",
        "kind": "episodic",
        "cues": ["荞麦面", "镰仓"],
    },
    {
        "content": "行程第 5 天（24 日）上午去筑地市场吃早餐，然后去机场。",
        "kind": "semantic",
        "cues": ["筑地", "早餐"],
    },
]


QUESTIONS = [
    {
        "dim": "行程安排",
        "q": "8月22日原计划去哪里？",
        "answer": "镰仓",
        "terms": ["镰仓"],
    },
    {
        "dim": "机票酒店",
        "q": "去程航班号是多少？几点的？",
        "answer": "MU523，11:00 起飞",
        "terms": ["MU523", "11"],
    },
    {
        "dim": "签证护照",
        "q": "护照什么时候过期？签证是单次还是多次？",
        "answer": "2031 年 4 月，单次 15 天",
        "terms": ["2031", "单次"],
    },
    {
        "dim": "行李清单",
        "q": "行李清单里带了什么充电设备？",
        "answer": "充电宝",
        "terms": ["充电宝"],
    },
    {
        "dim": "当地交通",
        "q": "到羽田后坐什么线去浅草？多少钱？",
        "answer": "京急线，620 日元",
        "terms": ["京急线", "620"],
    },
    {
        "dim": "景点预约",
        "q": "8月21日预约了哪个景点？几点的？",
        "answer": "涩谷天空观景台，18:30",
        "terms": ["观景台", "18:30"],
    },
    {
        "dim": "语言沟通",
        "q": "日语的“谢谢”怎么说？",
        "answer": "ありがとう",
        "terms": ["ありがとう"],
    },
    {
        "dim": "保险急救",
        "q": "旅游保险的紧急电话是多少？",
        "answer": "+81-3-1234-5678",
        "terms": ["1234", "5678"],
    },
    {
        "dim": "费用预算",
        "q": "这次旅行总预算是多少？",
        "answer": "18000 元",
        "terms": ["18000"],
    },
    {
        "dim": "天气备选",
        "q": "22 日镰仓下雨的话，备选去哪？",
        "answer": "江之岛水族馆",
        "terms": ["水族馆"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="出行旅行",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="travel_mem0db",
        out_name="travel_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
