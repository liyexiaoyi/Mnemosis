"""Expanded aliases must not exceed the optional cue overlap budget."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from mnemosis import MemoryEngine, MemoryKind, SourceRecord, SourceType

NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)


class CueOverlapBoundTests(unittest.TestCase):
    def engine(self, disk, texts):
        path = None
        if disk:
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            path = str(Path(tmp.name) / "memory.sqlite")
        e = MemoryEngine(path, auto_warmup=False)
        self.addCleanup(e.close)
        items = e.store.remember_many([
            dict(content=text, kind=MemoryKind.EPISODIC, cues=[], importance=.5,
                 created_at=NOW, source=SourceRecord(SourceType.USER))
            for text in texts + ["weather background"] * (1000-len(texts))
        ])
        return e, items

    def recall(self, e, query, policy="inflection"):
        return e.store.recall(query, now=NOW, read_only=True, lexical_policy=policy,
            top_k=5, source_trust_boost=False, confidence_boost=False,
            kind_preference=False, temporal_reason=False, reasoning_pack=False,
            pattern_completion=False)

    def test_expanded_aliases_saturate_for_one_or_multiple_original_cues(self):
        for disk in (False, True):
            for query, text in (("spent", "spent cost paid bought spending unrelated"),
                ("bike", "bike bicycle cycling unrelated"),
                ("money spent", "money spent cost amount price payment paid bought spending unrelated")):
                with self.subTest(disk=disk, query=query):
                    e, _ = self.engine(disk, [text])
                    rows = self.recall(e, query)
                    self.assertEqual([r.item.content for r in rows], [text])
                    # All expanded groups occur once in a rare document:
                    # uniform capped IDF => scale 1. Fresh baseline=.35.
                    self.assertAlmostEqual(rows[0].score, .75)

    def test_single_exact_and_alias_matches_keep_their_geometry(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                e, _ = self.engine(disk, ["spent unrelated", "cost unrelated",
                    "spent cost paid bought spending unrelated"])
                rows = {r.item.content: r for r in self.recall(e, "spent")}
                # Every query group has positive capped IDF in this corpus.
                for text in ("spent unrelated", "cost unrelated"):
                    self.assertAlmostEqual(rows[text].score, .632842712474619)

    def test_repeated_word_forms_still_count_as_one_group(self):
        e, _ = self.engine(False, ["research unrelated", "research researching researched unrelated"])
        rows = self.recall(e, "research")
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertAlmostEqual(row.score, .632842712474619)

    def test_literal_preserves_previous_uncapped_scoring(self):
        e, _ = self.engine(False, ["spent cost paid bought spending unrelated"])
        rows = self.recall(e, "spent", policy="literal")
        # Legacy uniform weighting is capped at 2 for five expanded hits.
        self.assertAlmostEqual(rows[0].score, 1.9829931618554524)

    def test_capping_relevance_preserves_all_read_only_state(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                e, items = self.engine(disk, ["spent cost paid bought spending unrelated", "spent unrelated"])
                e.backend.add_link(items[0].id, items[1].id, .2)
                before = [i.to_dict() for i in e.store.all_active()]
                links, log = sorted(e.backend.all_links()), e.get_recall_log()
                self.recall(e, "spent")
                self.assertEqual([i.to_dict() for i in e.store.all_active()], before)
                self.assertEqual(sorted(e.backend.all_links()), links)
                self.assertEqual(e.get_recall_log(), log)


if __name__ == "__main__":
    unittest.main()
