"""Chinese reasoning at 10k scale (round 28).

Builds ~10k deterministic memories: the 8 main people keep their canonical
premises (height chains, prices, unit prices, cities) buried under hundreds
of same-person facts and same-dimension variants, plus 150 distractor
people. Evaluates the reasoning premise pack on vs off:

  - plain top-5 vs pack (working-memory sized) premise coverage;
  - optional cloud qwen3.7-plus answering on a sampled subset.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from reasoning_zh_bench import QUESTIONS

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

MAIN_PERSONS = ["阿丽", "小波", "小王", "琳琳", "大壮", "强强", "朵朵", "小雨"]
OBJECTS = ["笔记本", "手机", "相机", "音箱", "耳机", "手表", "平板", "钢笔"]
NOISE_OBJECTS = ["钢笔", "手表", "平板", "耳机"]
ADJECTIVES = ["白", "胖", "快", "认真", "热情", "安静", "开朗", "细心",
              "勇敢", "礼貌", "幽默", "整洁"]
LIKES = ["红色", "蓝色", "绿色", "橙色", "紫色", "咖啡", "奶茶", "面条",
         "饺子", "火锅", "米饭", "西瓜", "苹果", "香蕉", "篮球", "足球",
         "游泳", "跑步", "读书", "画画", "唱歌", "弹琴", "爬山", "旅行"]


def _canonical_premises() -> list[str]:
    return [
        "阿丽比小波高。",
        "小波比小王高。",
        "阿丽买相机花了2500元。",
        "小波买手机花了3000元。",
        "阿丽买了3本笔记本花了90元。",
        "小波买了2本笔记本花了40元。",
        "阿丽最喜欢的城市是成都。",
        "小波最喜欢的城市是杭州。",
        "阿丽最喜欢的颜色是琥珀色。",
        "小波最喜欢的食物是饺子。",
        "琳琳比大壮高。",
        "大壮比强强高。",
        "朵朵买音箱花了200元。",
        "小雨买音箱花了600元。",
        "小雨买了5本笔记本花了150元。",
        "强强买了4本笔记本花了80元。",
        "琳琳最喜欢的城市是西安。",
        "大壮最喜欢的城市是北京。",
    ]


def generate_memories(seed: int = 27) -> list[str]:
    rng = random.Random(seed)
    memories: list[str] = []
    extra = [f"人物{i}" for i in range(1, 151)]
    for person in MAIN_PERSONS:
        # 30 same-object price variants with consistent unit prices
        unit = {"阿丽": 30, "小波": 20, "小雨": 30, "强强": 20}.get(person, 25)
        for i in range(30):
            n = rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
            obj = rng.choice(NOISE_OBJECTS)
            memories.append(f"{person}买了{n}个{obj}花了{n * unit}元。")
        # 30 same-person comparative variants (different dimensions)
        for other in rng.sample(extra + MAIN_PERSONS, 30):
            if other == person:
                continue
            adj = rng.choice(ADJECTIVES)
            memories.append(f"{person}比{other}{adj}。")
        # 240 random facts
        for _ in range(240):
            kind = rng.randrange(3)
            if kind == 0:
                # main people's canonical attributes are 颜色/食物/城市;
                # noise must not create contradictory "same person + same
                # attribute" facts, so use only 运动/水果 here.
                memories.append(
                    f"{person}最喜欢的{rng.choice(['运动', '水果'])}"
                    f"是{rng.choice(LIKES)}。"
                )
            elif kind == 1:
                memories.append(
                    f"{person}在2026年{rng.randrange(1, 13)}月{rng.randrange(1, 29)}日"
                    f"买了{rng.choice(NOISE_OBJECTS)}花了{rng.randrange(5, 100) * 10}元。"
                )
            else:
                memories.append(
                    f"{person}喜欢{rng.choice(LIKES)}。"
                )
    for person in extra:
        for _ in range(50):
            kind = rng.randrange(3)
            if kind == 0:
                memories.append(
                    f"{person}最喜欢的{rng.choice(['颜色', '食物'])}"
                    f"是{rng.choice(LIKES)}。"
                )
            elif kind == 1:
                memories.append(
                    f"{person}买了{rng.choice(OBJECTS)}花了{rng.randrange(5, 100) * 10}元。"
                )
            else:
                memories.append(
                    f"{person}比{rng.choice(MAIN_PERSONS + extra)}{rng.choice(ADJECTIVES)}。"
                )
    memories.extend(_canonical_premises())
    return memories


def _premise_keys(premise: str) -> set[str]:
    keys = set(re.findall(r"[阿-龥]+|[0-9]+", premise))
    return keys - {
        "买了", "花了", "笔记本", "最喜欢的", "城市", "是", "买", "花", "了",
        "比", "谁", "元", "个", "本", "的", "和",
        "东西", "钱", "分别", "什么", "更", "最",
    }


def _semantic_hit(blob: str, q: dict) -> bool:
    return all(
        all(k in blob for k in _premise_keys(p))
        for p in q["premises"]
        if _premise_keys(p)
    )


def build_engine(memories: list[str]) -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for content in memories:
        cue = re.split(r"[比最喜欢买]", content, maxsplit=1)[0]
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[cue],
            importance=0.7,
        )
    return engine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-limit", type=int, default=10)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "reasoning_zh_10k_bench.json"),
    )
    args = parser.parse_args()

    memories = generate_memories()
    print("memories:", len(memories), flush=True)
    engine = build_engine(memories)

    plain_rows = []
    pack_rows = []
    plain_hits = pack_hits = 0
    for q in QUESTIONS:
        plain = [r.item.content for r in engine.recall(
            q["q"], top_k=5, reasoning_pack=False
        )]
        pack = [r.item.content for r in engine.recall_reasoning(q["q"])]
        plain_rows.append({"kind": q["kind"], "question": q["q"],
                           "context": plain, "pack_size": len(pack)})
        pack_rows.append({"kind": q["kind"], "question": q["q"],
                          "context": pack})
        plain_hits += int(_semantic_hit("\n".join(plain), q))
        pack_hits += int(_semantic_hit("\n".join(pack), q))

    report = {
        "memories": len(memories),
        "plain5": {"premise_hit": [plain_hits, len(QUESTIONS)],
                   "rows": plain_rows},
        "pack": {"premise_hit": [pack_hits, len(QUESTIONS)],
                 "rows": pack_rows},
        "llm": [],
    }
    print("plain premise hit:", plain_hits, "/", len(QUESTIONS), flush=True)
    print("pack premise hit:", pack_hits, "/", len(QUESTIONS), flush=True)

    if args.llm:
        from cloud_qwen_matrix import cloud_generate
        from reasoning_zh_bench import score_answer

        chosen = QUESTIONS[: args.llm_limit]
        for condition, rows, top_k in (
            ("plain_top5", plain_rows, 5),
            ("pack", pack_rows, None),
        ):
            hits = 0
            details = []
            for i, q in enumerate(chosen):
                row = rows[i]
                context = "\n".join(f"- {c}" for c in row["context"])
                prompt = (
                    "只用下面的记忆上下文回答中文问题；上下文里没有答案就回答'unknown'。"
                    "需要计算时先算清楚再回答。\n\n"
                    f"上下文：\n{context}\n\n问题：{q['q']}"
                )
                answer = cloud_generate(prompt, max_tokens=400)
                score = score_answer(answer, q["keys"])
                hits += int(score >= 1.0)
                details.append(
                    {
                        "question": q["q"],
                        "answer": answer,
                        "keys": q["keys"],
                        "score": round(score, 3),
                    }
                )
                print(
                    f"  [{condition}] {q['q'][:26]:28s} score={score:.2f}",
                    flush=True,
                )
            report["llm"].append(
                {
                    "condition": condition,
                    "n": len(chosen),
                    "accuracy": round(hits / len(chosen), 3),
                    "details": details,
                }
            )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
