"""Evidence-weighted conflict resolution (round 29).

Learning science: memory strength grows with confirmations (Anderson 1974;
McClelland et al. 1995). When several same-pattern facts compete, the one
with the most evidence should win the top spot instead of being buried by
pattern separation.
"""

from __future__ import annotations

import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def _conflict_engine(winner: str, loser: str, winner_evidence: int) -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    engine.remember(
        f"阿丽最喜欢的颜色是{loser}。",
        kind=MemoryKind.SEMANTIC,
        source=source,
        cues=["阿丽", "颜色"],
        evidence_count=1,
    )
    engine.remember(
        f"阿丽最喜欢的颜色是{winner}。",
        kind=MemoryKind.SEMANTIC,
        source=source,
        cues=["阿丽", "颜色"],
        evidence_count=winner_evidence,
    )
    # an unrelated same-person fact to crowd the window
    engine.remember(
        "阿丽喜欢蓝色。",
        kind=MemoryKind.SEMANTIC,
        source=source,
        cues=["阿丽"],
    )
    return engine


class EvidenceConflictTests(unittest.TestCase):
    def test_high_evidence_wins(self) -> None:
        engine = _conflict_engine("琥珀色", "红色", winner_evidence=5)
        results = engine.recall("阿丽最喜欢的颜色是什么？", top_k=3)
        self.assertEqual(results[0].item.content, "阿丽最喜欢的颜色是琥珀色。")
        self.assertTrue(
            any(
                "\u8bc1\u636e\u52a0\u6743\u4fdd\u62a4" in reason
                for reason in results[0].reasons
            )
        )

    def test_evidence_switches_winner(self) -> None:
        engine = _conflict_engine("红色", "琥珀色", winner_evidence=6)
        results = engine.recall("阿丽最喜欢的颜色是什么？", top_k=3)
        self.assertEqual(results[0].item.content, "阿丽最喜欢的颜色是红色。")

    def test_tie_keeps_first_inserted(self) -> None:
        # both evidence=1: no evidence weighting, first-inserted wins
        engine = _conflict_engine("琥珀色", "红色", winner_evidence=1)
        results = engine.recall("阿丽最喜欢的颜色是什么？", top_k=3)
        self.assertEqual(results[0].item.content, "阿丽最喜欢的颜色是红色。")


if __name__ == "__main__":
    unittest.main()
