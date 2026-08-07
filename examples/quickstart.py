"""Mnemosis quickstart: wake -> recall -> sleep -> check."""

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def main() -> None:
    engine = MemoryEngine()  # in-memory; pass "memory.db" for persistence

    engine.remember(
        "The user prefers Chinese for technical discussions.",
        kind=MemoryKind.SEMANTIC,
        source=SourceRecord(origin=SourceType.USER),
        cues=["user", "language", "preference"],
        importance=0.9,
        context="work",
    )
    engine.remember(
        "Yesterday we debugged the SQLite locking issue together.",
        kind=MemoryKind.EPISODIC,
        source=SourceRecord(origin=SourceType.AGENT),
        cues=["sqlite", "debug", "yesterday"],
    )

    print("== recall ==")
    for r in engine.recall("what language does the user prefer?", top_k=3):
        print(f"  [{r.item.kind.value:8s}] {r.score:.2f}  {r.item.content}")

    print("\n== metacognition ==")
    check = engine.check("what language does the user prefer?")
    print(f"  gaps: {check.gaps or 'none'}")
    print(f"  contradictions: {len(check.contradictions)}")
    print(
        "  blocked (cues matched, not recalled): "
        f"{[b.content for b in check.blocked] or 'none'}"
    )

    for item, label, value in check.items:
        print(f"  {label.value:6s} ({value}) {item.content}")

    print("\n== working set ==")
    for item in engine.working_set(limit=3):
        print(f"  {item.content}")

    print("\n== sleep ==")
    print("  ", engine.sleep().summary())

    print("\n== stats ==")
    print("  ", engine.stats())


if __name__ == "__main__":
    main()
