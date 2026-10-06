"""Cue discovery must preserve budgets, original questions and learned state."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from mnemosis import MemoryEngine, MemoryKind, SourceRecord, SourceType
from mnemosis.embedding import Embedder

NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)

class RecordingEmbedder(Embedder):
    def __init__(self):
        self.queries = []
        self.batches = []
    def embed(self, text):
        self.queries.append(text)
        return [1.0, 0.0]
    def embed_many(self, texts):
        self.batches.append(list(texts))
        return [[1.0, 0.0] for _ in texts]

class InflectionCueTests(unittest.TestCase):
    def engine(self, disk=False, **kwargs):
        if disk:
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            path = str(Path(tmp.name) / "memory.sqlite")
        else:
            path = None
        engine = MemoryEngine(path, auto_warmup=False, **kwargs)
        self.addCleanup(engine.close)
        return engine
    def remember(self, engine, text, **kwargs):
        return engine.remember(text, cues=[], auto_cues=False, auto_context=False,
                               importance=kwargs.pop("importance", .5), created_at=NOW,
                               source=SourceRecord(SourceType.USER), **kwargs)
    def recall(self, engine, query, **kwargs):
        return engine.recall(query, now=NOW, read_only=True,
                             lexical_policy="inflection", **kwargs)
    def state(self, engine):
        return ([i.to_dict() for i in engine.store.all_active()],
                sorted(engine.backend.all_links()), engine.get_recall_log())

    def test_variant_survives_more_than_one_hundred_same_name_distractors(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                wanted = self.remember(engine, "Nora is researching marine habitats.")
                for i in range(150):
                    self.remember(engine, f"Nora sends newsletter number {i}.", importance=.8)
                self.assertEqual(self.recall(engine, "Nora research", top_k=1)[0].item.id, wanted.id)

    def test_read_and_reading_find_complementary_book_memories(self):
        engine = self.engine()
        a = self.remember(engine, "Elena read the book Lighthouse.")
        b = self.remember(engine, "Elena loved reading the novel River.")
        for i in range(120):
            self.remember(engine, f"Elena shares a photo number {i}.")
        ids = {r.item.id for r in self.recall(engine, "Elena books read", top_k=5)}
        self.assertTrue({a.id, b.id} <= ids)

    def test_plural_past_and_doubled_consonant_variants(self):
        for stored, query in (("Mira owns a bicycle", "Mira bicycles"),
                              ("Mira visited a museum", "Mira visit"),
                              ("Mira is running along the shore", "Mira run")):
            with self.subTest(stored=stored):
                engine = self.engine()
                wanted = self.remember(engine, stored)
                self.remember(engine, "Mira discusses the weather", importance=.9)
                self.assertEqual(self.recall(engine, query, top_k=1)[0].item.id, wanted.id)

    def test_multiple_variants_in_one_memory_count_once(self):
        engine = self.engine()
        a = self.remember(engine, "Nora research unrelated")
        b = self.remember(engine, "Nora research researching researched unrelated")
        results = {r.item.id: r.score for r in self.recall(engine, "Nora research", top_k=2)}
        self.assertAlmostEqual(results[a.id], results[b.id])

    def test_duplicate_query_variants_do_not_multiply_weight(self):
        engine = self.engine()
        wanted = self.remember(engine, "Nora research unrelated")
        self.remember(engine, "Nora researching unrelated")
        a = self.recall(engine, "Nora research", top_k=2)
        b = self.recall(engine, "Nora research researching", top_k=2)
        self.assertEqual([r.item.id for r in a], [r.item.id for r in b])
        self.assertAlmostEqual(next(r.score for r in a if r.item.id == wanted.id),
                               next(r.score for r in b if r.item.id == wanted.id))

    def test_query_embedding_and_log_use_original_question(self):
        embedder = RecordingEmbedder()
        engine = self.engine(embedder=embedder)
        self.remember(engine, "Nora is researching marine habitats")
        question = "What did Nora research?"
        self.recall(engine, question)
        self.assertEqual(embedder.queries, [question])
        self.assertEqual(engine.get_recall_log(), [])

    def test_dense_embedding_budget_is_not_expanded(self):
        embedder = RecordingEmbedder()
        engine = self.engine(embedder=embedder)
        for i in range(150):
            self.remember(engine, f"Nora is researching marine habitats number {i}")
        results = self.recall(engine, "Nora research", top_k=5)
        self.assertLessEqual(sum(map(len, embedder.batches)), 64)
        self.assertLessEqual(len(results), 5)

    def test_repeated_read_only_queries_preserve_items_links_and_log(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                self.remember(engine, "Nora is researching marine habitats")
                self.remember(engine, "Nora studies ocean temperatures")
                before = self.state(engine)
                for _ in range(3):
                    self.recall(engine, "Nora research")
                self.assertEqual(self.state(engine), before)

    def test_final_learning_never_creates_verified_evidence(self):
        engine = self.engine()
        item = self.remember(engine, "Nora is researching marine habitats")
        engine.recall("Nora research", lexical_policy="inflection", learning_policy="final", now=NOW)
        fresh = engine.backend.get(item.id)
        self.assertEqual(fresh.access_count, 1)
        self.assertEqual(fresh.verified_successes, 0)
        self.assertEqual(fresh.evidence_count, 1)
        self.assertEqual(fresh.retrieval_successes, 0)

    def test_excluded_suppressed_recycled_and_other_kind_cannot_return(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                excluded = self.remember(engine, "Nora researching excluded")
                suppressed = self.remember(engine, "Nora researching suppressed")
                recycled = self.remember(engine, "Nora researching recycled")
                self.remember(engine, "Nora researching other kind", kind=MemoryKind.SEMANTIC)
                wanted = self.remember(engine, "Nora researching wanted")
                engine.suppress_memories([suppressed.id])
                engine.forget(recycled.id)
                result = self.recall(engine, "Nora research", kind=MemoryKind.EPISODIC,
                                     exclude_ids={excluded.id}, top_k=5)
                self.assertEqual([r.item.id for r in result], [wanted.id])

    def test_default_and_explicit_literal_are_identical(self):
        engine = self.engine()
        self.remember(engine, "Nora is researching marine habitats")
        self.remember(engine, "Nora discusses the weather")
        a = engine.recall("Nora research", now=NOW, read_only=True)
        b = engine.recall("Nora research", lexical_policy="literal", now=NOW, read_only=True)
        self.assertEqual([(r.item.id, r.score, r.reasons) for r in a],
                         [(r.item.id, r.score, r.reasons) for r in b])

    def test_chinese_query_preserves_legacy_behavior(self):
        engine = self.engine()
        self.remember(engine, "小林喜欢阅读科幻小说")
        a = engine.recall("小林喜欢读什么", now=NOW, read_only=True)
        b = self.recall(engine, "小林喜欢读什么")
        self.assertEqual([(r.item.id, r.score, r.reasons) for r in a],
                         [(r.item.id, r.score, r.reasons) for r in b])

    def test_invalid_policy_is_rejected_before_embedding(self):
        embedder = RecordingEmbedder()
        engine = self.engine(embedder=embedder)
        with self.assertRaises(ValueError):
            engine.recall("Nora research", lexical_policy="unknown")
        self.assertEqual(embedder.queries, [])

    def test_zero_hit_cache_is_isolated_between_policies(self):
        engine = self.engine()
        wanted = self.remember(engine, "gardening roses", importance=.1)
        for i in range(160):
            self.remember(engine, f"unrelated weather {i}", importance=.9)
        engine.recall("garden", top_k=1, lexical_policy="literal")
        self.assertEqual(engine.recall("garden", top_k=1, lexical_policy="inflection")[0].item.id,
                         wanted.id)

    def test_variant_reason_does_not_claim_confirmation(self):
        engine = self.engine()
        item = self.remember(engine, "Nora researching marine habitats")
        results = self.recall(engine, "Nora research", top_k=1)
        self.assertTrue(any("inflection cue" in reason for reason in results[0].reasons))
        self.assertEqual(engine.backend.get(item.id).evidence_count, 1)

class WordFormBoundaryTests(unittest.TestCase):
    def test_identifiers_unicode_and_derivation_stay_separate(self):
        from mnemosis.lexical_cues import inflection_forms
        for token in ("mu523", "al-889", "中文", "x", "ab"):
            with self.subTest(token=token):
                self.assertEqual(inflection_forms(token), frozenset((token,)))
        self.assertNotIn("researcher", inflection_forms("research"))
        self.assertNotIn("went", inflection_forms("go"))

    def test_forms_are_bounded_and_overlapping_groups_are_disjoint(self):
        from mnemosis.lexical_cues import inflection_forms, inflection_groups
        for word in ("run", "running", "read", "reading", "studies", "studied", "bicycles"):
            with self.subTest(word=word):
                self.assertIn(word, inflection_forms(word))
                self.assertLessEqual(len(inflection_forms(word)), 32)
        groups = inflection_groups({"research", "researching", "researched", "museum"})
        self.assertEqual(len(groups), 2)
        self.assertFalse(groups[0] & groups[1])

if __name__ == "__main__":
    unittest.main()
