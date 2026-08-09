"""Mnemosis 一分钟体验（中文场景，零依赖）。

安装后直接运行：
    pip install git+https://github.com/liyexiaoyi/Mnemosis.git
    python demo.py

演示：记住 -> 检索 -> 新旧矛盾 -> 睡眠整合 -> 元认知 -> 遗忘回收。
"""

from __future__ import annotations

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def sep(title: str) -> None:
    print(f"\n===== {title} =====")


def main() -> None:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)

    sep("1. 记住（事件和事实分开存）")
    engine.remember(
        "用户喜欢用中文讨论技术问题。",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["语言", "偏好"],
        importance=0.9,
    )
    engine.remember(
        "昨天一起修了 SQLite 锁死的问题。",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["SQLite", "锁死"],
    )
    print("已记住 2 条记忆（1 条事实 + 1 条事件）")

    sep("2. 检索（换个说法也能找到）")
    for r in engine.recall("用户用什么语言聊天？", top_k=3):
        print(f"  [{r.item.kind.value}] 相关度 {r.score:.2f}  {r.item.content}")

    sep("3. 新旧矛盾（新信息覆盖旧信息）")
    engine.remember(
        "2026年7月1日 物业费调整为一年3000元。",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["2026-07-01", "物业费"],
        importance=0.8,
    )
    engine.remember(
        "2026年1月6日 缴纳物业费一年2400元。",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["2026-01-06", "物业费"],
        importance=0.8,
    )
    hint = engine.temporal_hint("现在物业费一年多少钱？")
    if hint:
        print("  时序提示:", hint)
    rows = [r.item.content for r in engine.recall("现在物业费一年多少钱？", top_k=2)]
    print("  检索到:", " / ".join(rows))

    sep("4. 睡眠整合（离线整理、去重、查矛盾）")
    engine.remember(
        "用户喜欢用中文讨论技术问题。",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["语言", "偏好"],
        importance=0.9,
    )
    print("  睡眠前活跃记忆数:", engine.stats()["active"])
    summary = engine.sleep().summary()
    print("  睡眠后:", summary)

    sep("5. 元认知（不知道就说不知道）")
    check = engine.check("用户最喜欢的电影是什么？")
    print("  知识缺口:", check.gaps or "无")
    print("  矛盾条数:", len(check.contradictions))

    sep("6. 遗忘回收（删除进回收站，可恢复）")
    target = engine.recall("SQLite", top_k=1)[0].item
    engine.forget(target.id)
    print("  已移入回收站:", target.content)
    print("  回收站条数:", len(engine.recycle.list_trash()))
    engine.restore(target.id)
    print("  已恢复，检索仍能找到:", engine.recall("SQLite", top_k=1)[0].item.content)

    sep("完成！更多玩法见 README 和 examples/")


if __name__ == "__main__":
    main()
