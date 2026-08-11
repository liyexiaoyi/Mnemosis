"""Tests for research-grounded mechanisms:
context-dependence, emotional persistence, evidence accumulation,
retrieval-induced forgetting, and blocking detection.
"""

import unittest
from datetime import timedelta

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


class CognitionTest(unittest.TestCase):
    def setUp(self):
        self.engine = MemoryEngine()
        self.user = SourceRecord(origin=SourceType.USER)

    def remember(self, content, **kwargs):
        kwargs.setdefault("kind", MemoryKind.SEMANTIC)
        kwargs.setdefault("source", self.user)
        return self.engine.remember(content, **kwargs)

    def test_context_dependent_recall_boost(self):
        a = self.remember(
            "We reviewed the alpha module design.",
            kind=MemoryKind.EPISODIC,
            context="project-a",
            cues=["alpha"],
        )
        self.remember(
            "We reviewed the alpha module design.",
            kind=MemoryKind.EPISODIC,
            context="project-b",
            cues=["alpha"],
        )
        results = self.engine.recall(
            "alpha module design", context="project-a", top_k=5
        )
        self.assertEqual(results[0].item.id, a.id)
        score_a = next(r.score for r in results if r.item.id == a.id)
        score_b = next(r.score for r in results if r.item.id != a.id)
        self.assertGreater(score_a, score_b)
        self.assertIn("context match", results[0].reasons)

    def test_context_partial_overlap_boost(self):
        a = self.remember(
            "We reviewed the alpha module design.",
            kind=MemoryKind.EPISODIC,
            context="会议室",
            cues=["alpha"],
            importance=0.5,
            strength=0.5,
        )
        b = self.remember(
            "We reviewed the alpha module design.",
            kind=MemoryKind.EPISODIC,
            context="办公室",
            cues=["alpha"],
            importance=0.5,
            strength=0.5,
        )
        # partial context "正在会议室开会" shares "会议室" with A only
        boosted = self.engine.recall(
            "alpha module design", context="正在会议室开会", top_k=5
        )
        self.assertEqual(boosted[0].item.id, a.id)
        self.assertTrue(
            any("context overlap" in r for r in boosted[0].reasons)
        )
        # without the boost the two memories are tied
        plain = self.engine.recall(
            "alpha module design",
            context="正在会议室开会",
            top_k=5,
            context_boost=False,
        )
        plain_a = next(r.score for r in plain if r.item.id == a.id)
        plain_b = next(r.score for r in plain if r.item.id == b.id)
        self.assertAlmostEqual(plain_a, plain_b, places=4)
        # with the boost, the partially-matching context item pulls ahead
        boosted_a = next(r.score for r in boosted if r.item.id == a.id)
        boosted_b = next(r.score for r in boosted if r.item.id == b.id)
        self.assertGreater(
            boosted_a - boosted_b,
            plain_a - plain_b,
        )

    def test_auto_context_extraction(self):
        meeting = self.remember("阿丽在会议室里讨论了方案一。")
        self.assertEqual(meeting.context, "会议室")
        dated = self.remember("阿丽在2026年4月1日准备了行李。")
        self.assertIsNone(dated.context)
        generic = self.remember("阿丽在这里等了一会儿。")
        self.assertIsNone(generic.context)
        explicit = self.remember(
            "阿丽讨论了方案二。", context="办公室"
        )
        self.assertEqual(explicit.context, "办公室")

    def test_recall_confidence_flag(self):
        def _clear():
            engine = MemoryEngine()
            engine.remember(
                "alpha two",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=["alpha"],
                importance=0.9,
                strength=0.5,
                auto_cues=False,
            )
            engine.remember(
                "alpha one",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=["alpha"],
                importance=0.5,
                strength=0.5,
                auto_cues=False,
            )
            return engine

        def _ambiguous():
            engine = MemoryEngine()
            for content in ("alpha one", "alpha two"):
                engine.remember(
                    content,
                    kind=MemoryKind.SEMANTIC,
                    source=SourceRecord(origin=SourceType.USER),
                    cues=["alpha"],
                    importance=0.5,
                    strength=0.5,
                    auto_cues=False,
                )
            return engine

        clear = _clear().recall("alpha", top_k=3)[0]
        self.assertTrue(clear.confident)
        ambiguous = _ambiguous().recall("alpha", top_k=3)[0]
        self.assertFalse(ambiguous.confident)
        self.assertTrue(
            any("低置信" in r for r in ambiguous.reasons)
        )

    def test_gist_preference_for_summary_questions(self):
        def _build():
            engine = MemoryEngine()
            user = SourceRecord(origin=SourceType.USER)
            now = utcnow()
            gist = engine.remember(
                "要点：阿丽喜欢红色。",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["红色"],
                importance=0.5,
                strength=0.5,
                created_at=now - timedelta(days=60),
            )
            verbatim = engine.remember(
                "阿丽说：我最喜欢红色。",
                kind=MemoryKind.EPISODIC,
                source=user,
                cues=["红色"],
                importance=0.5,
                strength=0.5,
                created_at=now - timedelta(days=2),
            )
            return engine, gist.id, verbatim.id

        engine_g, g_id, _ = _build()
        boosted = engine_g.recall(
            "总结一下阿丽喜欢什么颜色？", top_k=3
        )
        self.assertEqual(boosted[0].item.id, g_id)
        self.assertTrue(
            any("图式要点" in r for r in boosted[0].reasons)
        )
        engine_p, _, v_id = _build()
        plain = engine_p.recall(
            "总结一下阿丽喜欢什么颜色？",
            top_k=3,
            gist_preference=False,
        )
        self.assertEqual(plain[0].item.id, v_id)

    def test_emotional_salience_boost(self):
        def _build():
            engine = MemoryEngine()
            user = SourceRecord(origin=SourceType.USER)
            now = utcnow() - timedelta(days=10)
            emotional = engine.remember(
                "阿丽那次很紧张。",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["阿丽"],
                affect="negative",
                importance=0.5,
                strength=0.5,
                created_at=now,
            )
            neutral = engine.remember(
                "阿丽那次很普通。",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["阿丽"],
                importance=0.5,
                strength=0.5,
                created_at=now,
            )
            return engine, emotional.id, neutral.id

        engine_b, e_b, _ = _build()
        boosted = engine_b.recall("阿丽", top_k=3)
        self.assertEqual(boosted[0].item.id, e_b)
        self.assertTrue(
            any("情绪显著" in r for r in boosted[0].reasons)
        )
        engine_p, e_p, n_p = _build()
        plain = engine_p.recall(
            "阿丽", top_k=3, emotional_salience_boost=False
        )
        plain_emo = next(r.score for r in plain if r.item.id == e_p)
        plain_neu = next(r.score for r in plain if r.item.id == n_p)
        boosted_emo = next(
            r.score for r in boosted if r.item.id == e_b
        )
        boosted_neu = next(
            r.score for r in boosted if r.item.id != e_b
        )
        self.assertGreater(
            boosted_emo - boosted_neu,
            plain_emo - plain_neu,
        )

    def test_second_look_recollect(self):
        def _build():
            engine = MemoryEngine()
            user = SourceRecord(origin=SourceType.USER)
            now = utcnow() - timedelta(days=10)
            weak = engine.remember(
                "alpha weak",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["alpha"],
                importance=0.7,
                strength=0.6,
                evidence_count=1,
                created_at=now,
                auto_cues=False,
            )
            strong = engine.remember(
                "alpha strong",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["alpha"],
                importance=0.55,
                strength=0.5,
                evidence_count=3,
                created_at=now,
                auto_cues=False,
            )
            return engine, weak.id, strong.id

        engine_s, w_s, _ = _build()
        single = engine_s.recall(
            "alpha", top_k=3, corroboration_boost=False
        )
        self.assertEqual(single[0].item.id, w_s)
        self.assertFalse(single[0].confident)
        engine_l, _, s_l = _build()
        looked = engine_l.recall(
            "alpha",
            top_k=3,
            second_look=True,
            corroboration_boost=False,
        )
        self.assertEqual(looked[0].item.id, s_l)
        self.assertTrue(
            any("复核" in r for r in looked[0].reasons)
        )

    def test_conflict_flag(self):
        def _build():
            engine = MemoryEngine()
            user = SourceRecord(origin=SourceType.USER)
            now = utcnow() - timedelta(days=10)
            weak = engine.remember(
                "alpha old fact",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["alpha"],
                importance=0.98,
                strength=0.5,
                evidence_count=1,
                created_at=now,
                auto_cues=False,
            )
            strong = engine.remember(
                "alpha new fact",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["alpha"],
                importance=0.5,
                strength=0.5,
                evidence_count=4,
                created_at=now,
                auto_cues=False,
            )
            return engine, weak.id, strong.id

        engine_f, w_f, _ = _build()
        flagged = engine_f.recall("alpha", top_k=3)
        self.assertEqual(flagged[0].item.id, w_f)
        self.assertFalse(flagged[0].confident)
        self.assertTrue(
            any("更强证据冲突" in r for r in flagged[0].reasons)
        )
        engine_n, w_n, _ = _build()
        plain = engine_n.recall(
            "alpha",
            top_k=3,
            conflict_flag=False,
            corroboration_boost=False,
        )
        self.assertEqual(plain[0].item.id, w_n)
        self.assertTrue(plain[0].confident)

    def test_corroboration_boost(self):
        def _build():
            engine = MemoryEngine()
            user = SourceRecord(origin=SourceType.USER)
            now = utcnow() - timedelta(days=10)
            weak = engine.remember(
                "alpha single",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["alpha"],
                importance=0.77,
                strength=0.5,
                evidence_count=1,
                created_at=now,
                auto_cues=False,
            )
            strong = engine.remember(
                "alpha confirmed",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["alpha"],
                importance=0.5,
                strength=0.5,
                evidence_count=3,
                created_at=now,
                auto_cues=False,
            )
            return engine, weak.id, strong.id

        engine_b, _, s_b = _build()
        boosted = engine_b.recall("alpha", top_k=3)
        self.assertEqual(boosted[0].item.id, s_b)
        self.assertTrue(
            any("多来源印证" in r for r in boosted[0].reasons)
        )
        engine_p, w_p, _ = _build()
        plain = engine_p.recall(
            "alpha", top_k=3, corroboration_boost=False
        )
        self.assertEqual(plain[0].item.id, w_p)

    def test_revision_flag(self):
        user = SourceRecord(origin=SourceType.USER)
        now = utcnow() - timedelta(days=10)
        revised = self.engine.remember(
            "alpha old version",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["alpha"],
            importance=0.5,
            strength=0.5,
            created_at=now,
            auto_cues=False,
        )
        self.engine.update(
            revised.id, content="alpha new version", now=now
        )
        fresh = self.engine.remember(
            "beta unchanged",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["beta"],
            importance=0.5,
            strength=0.5,
            created_at=now,
            auto_cues=False,
        )
        res = self.engine.recall("alpha", top_k=3)
        self.assertTrue(
            any("已修订" in r for r in res[0].reasons)
        )
        res2 = self.engine.recall("beta", top_k=3)
        self.assertFalse(
            any("已修订" in r for r in res2[0].reasons)
        )
        res3 = self.engine.recall(
            "alpha", top_k=3, revision_flag=False
        )
        self.assertFalse(
            any("已修订" in r for r in res3[0].reasons)
        )
        self.assertIsNotNone(fresh)

    def test_decay_flag(self):
        user = SourceRecord(origin=SourceType.USER)
        now = utcnow()
        weak = self.engine.remember(
            "weak fading fact",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["weak"],
            importance=0.5,
            strength=0.3,
            created_at=now - timedelta(days=40),
            auto_cues=False,
        )
        strong = self.engine.remember(
            "strong fresh fact",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["strong"],
            importance=0.5,
            strength=0.9,
            created_at=now - timedelta(days=1),
            auto_cues=False,
        )
        res = self.engine.recall("weak", top_k=3)
        self.assertTrue(
            any("快遗忘" in r for r in res[0].reasons)
        )
        res2 = self.engine.recall("strong", top_k=3)
        self.assertFalse(
            any("快遗忘" in r for r in res2[0].reasons)
        )
        res3 = self.engine.recall(
            "weak", top_k=3, decay_flag=False
        )
        self.assertFalse(
            any("快遗忘" in r for r in res3[0].reasons)
        )
        self.assertIsNotNone(weak)
        self.assertIsNotNone(strong)

    def test_weak_important_replay(self):
        now = utcnow()
        important = self.remember(
            "Important fading fact about the launch.",
            kind=MemoryKind.SEMANTIC,
            cues=["launch"],
            importance=0.8,
            strength=0.3,
            created_at=now - timedelta(days=60),
        )
        strength_before = important.strength
        report = self.engine.sleep(now=now)
        self.assertGreaterEqual(report.weak_replayed, 1)
        refreshed = self.engine.backend.get(important.id)
        self.assertGreater(refreshed.strength, strength_before)

    def test_elaborate_co_retrieval_links(self):
        def _build():
            engine = MemoryEngine()
            for cue in ("alpha", "beta", "gamma"):
                engine.remember(
                    f"note about {cue}",
                    kind=MemoryKind.SEMANTIC,
                    cues=[cue],
                    importance=0.5,
                    strength=0.5,
                    auto_cues=False,
                )
            return engine

        linked = _build()
        linked.recall("alpha beta", top_k=5, elaborate_links=True)
        res = linked.recall("alpha", top_k=3, elaborate_links=False)
        ids = [r.item.id for r in res]
        beta = next(r for r in res if "beta" in r.item.cues)
        self.assertIn(beta.item.id, ids)
        self.assertTrue(
            any("linked to" in reason for reason in beta.reasons)
        )

        unlinked = _build()
        unlinked.recall("alpha beta", top_k=5, elaborate_links=False)
        res2 = unlinked.recall("alpha", top_k=3, elaborate_links=False)
        beta2 = [r for r in res2 if "beta" in r.item.cues]
        self.assertEqual(beta2, [])

    def test_self_reference_boost(self):
        def _build():
            engine = MemoryEngine()
            user = SourceRecord(origin=SourceType.USER)
            self_ = engine.remember(
                "我喜欢红色。",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["颜色"],
                importance=0.5,
                strength=0.5,
            )
            engine.remember(
                "小明喜欢红色。",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["颜色"],
                importance=0.5,
                strength=0.5,
            )
            return engine, self_

        engine_b, self_b = _build()
        boosted = engine_b.recall("我喜欢的颜色是什么？", top_k=5)
        self.assertEqual(boosted[0].item.id, self_b.id)
        self.assertTrue(
            any("自我参照" in r for r in boosted[0].reasons)
        )
        other_b = next(r for r in boosted if r.item.id != self_b.id)
        boost_gap = boosted[0].score - other_b.score
        engine_p, self_p = _build()
        plain = engine_p.recall(
            "我喜欢的颜色是什么？",
            top_k=5,
            self_reference_boost=False,
        )
        other_p = next(
            r for r in plain if r.item.id != self_p.id
        )
        plain_self = next(r.score for r in plain if r.item.id == self_p.id)
        plain_other = other_p.score
        self.assertGreater(boost_gap, plain_self - plain_other)

    def test_source_trust_boost(self):
        def _build():
            engine = MemoryEngine()
            winner = engine.remember(
                "alpha two",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER, trust=1.0),
                cues=["alpha"],
                importance=0.5,
                strength=0.5,
                auto_cues=False,
            )
            loser = engine.remember(
                "alpha one",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER, trust=0.4),
                cues=["alpha"],
                importance=0.5,
                strength=0.5,
                auto_cues=False,
            )
            return engine, winner.id, loser.id

        engine_b, w_b, _ = _build()
        boosted = engine_b.recall("alpha", top_k=3)
        self.assertEqual(boosted[0].item.id, w_b)
        self.assertTrue(
            any("来源可信" in r for r in boosted[0].reasons)
        )
        engine_p, _, l_p = _build()
        plain = engine_p.recall(
            "alpha", top_k=3, source_trust_boost=False
        )
        self.assertEqual(plain[0].item.id, l_p)

    def test_mood_congruent_boost(self):
        from datetime import timedelta

        def _build():
            engine = MemoryEngine()
            user = SourceRecord(origin=SourceType.USER)
            now = utcnow() - timedelta(days=10)
            happy = engine.remember(
                "提到红色我喜欢。",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["红色"],
                affect="positive",
                importance=0.5,
                strength=0.5,
                created_at=now,
            )
            anxious = engine.remember(
                "提到红色我害怕。",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["红色"],
                affect="negative",
                importance=0.5,
                strength=0.5,
                created_at=now,
            )
            return engine, happy.id, anxious.id

        engine_b, h_b, _ = _build()
        boosted = engine_b.recall(
            "为什么提到红色会开心？", top_k=3
        )
        self.assertEqual(boosted[0].item.id, h_b)
        self.assertTrue(
            any("情绪一致" in r for r in boosted[0].reasons)
        )
        engine_p, _, a_p = _build()
        plain = engine_p.recall(
            "为什么提到红色会开心？",
            top_k=3,
            mood_congruent_boost=False,
        )
        self.assertEqual(plain[0].item.id, a_p)

    def test_confidence_boost(self):
        def _build():
            engine = MemoryEngine()
            winner = engine.remember(
                "alpha two",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=["alpha"],
                importance=0.5,
                strength=0.5,
                confidence=0.9,
                auto_cues=False,
            )
            loser = engine.remember(
                "alpha one",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=["alpha"],
                importance=0.5,
                strength=0.5,
                confidence=0.4,
                auto_cues=False,
            )
            return engine, winner.id, loser.id

        engine_b, w_b, _ = _build()
        boosted = engine_b.recall("alpha", top_k=3)
        self.assertEqual(boosted[0].item.id, w_b)
        self.assertTrue(any("置信度" in r for r in boosted[0].reasons))
        engine_p, _, l_p = _build()
        plain = engine_p.recall(
            "alpha", top_k=3, confidence_boost=False
        )
        self.assertEqual(plain[0].item.id, l_p)

    def test_emotional_memory_decays_slower(self):
        now = utcnow()
        self.engine.curve.decay_rate = 0.01
        neutral = self.remember(
            "A routine note about the build pipeline.",
            created_at=now - timedelta(days=10),
        )
        emotional = self.remember(
            "The user was very anxious about the deadline.",
            affect="negative",
            created_at=now - timedelta(days=10),
        )
        neutral_r = self.engine.curve.retrievability(neutral, now)
        emotional_r = self.engine.curve.retrievability(emotional, now)
        self.assertGreater(emotional_r, neutral_r)
        self.assertEqual(emotional.affect, "negative")

    def test_emotion_regulation_normalizes_decay(self):
        now = utcnow()
        self.engine.curve.decay_rate = 0.01
        hot = self.remember(
            "The user was very anxious about the deadline.",
            affect="negative",
            created_at=now - timedelta(days=10),
        )
        processed = self.remember(
            "The user was very anxious about the launch.",
            affect="negative",
            created_at=now - timedelta(days=10),
        )
        processed.review_streak = 3
        self.assertAlmostEqual(
            self.engine.curve.effective_decay_rate(hot),
            self.engine.curve.decay_rate * 0.6,
        )
        self.assertAlmostEqual(
            self.engine.curve.effective_decay_rate(processed),
            self.engine.curve.decay_rate,
        )
        hot_r = self.engine.curve.retrievability(hot, now)
        processed_r = self.engine.curve.retrievability(processed, now)
        self.assertLess(processed_r, hot_r)

    def test_invalid_affect_is_rejected(self):
        item = self.remember("A note.", affect="not-a-real-affect")
        self.assertIsNone(item.affect)

    def test_evidence_accumulation_during_sleep(self):
        now = utcnow()
        content = "We fixed the SQLite bug."
        for _ in range(2):
            self.remember(
                content,
                kind=MemoryKind.EPISODIC,
                cues=["sqlite", "fix"],
                created_at=now - timedelta(days=2),
            )
        for _ in range(3):
            self.engine.recall("sqlite fix", top_k=5)
        report = self.engine.sleep(now=now)
        # near-duplicate episodes are merged first (complementary learning
        # systems), so the repeated evidence promotes as a single trace.
        self.assertEqual(report.merged, 1)
        self.assertEqual(len(report.promoted), 1)
        semantic = self.engine.store.all_active(MemoryKind.SEMANTIC)[0]
        self.assertEqual(semantic.evidence_count, 2)
        self.assertGreaterEqual(semantic.confidence, 0.7)

    def test_retrieval_induced_forgetting(self):
        target = self.remember(
            "The user likes coffee.",
            cues=["coffee", "user"],
        )
        rival = self.remember(
            "The user likes tea.",
            cues=["coffee", "user"],
        )
        strength_before = rival.strength
        results = self.engine.recall("coffee", top_k=1, suppression_factor=0.05)
        self.assertEqual(results[0].item.id, target.id)
        refreshed = self.engine.backend.get(rival.id)
        self.assertLess(refreshed.strength, strength_before)
        self.assertAlmostEqual(refreshed.strength, strength_before - 0.05)

    def test_blocked_retrieval_detection(self):
        blocked = self.remember(
            "An unrelated topic paragraph.",
            cues=["alpha"],
            confidence=0.9,
        )
        self.remember(
            "alpha details are here",
            cues=["beta"],
            confidence=0.9,
        )
        check = self.engine.check("alpha details", top_k=1)
        self.assertTrue(any(item.id == blocked.id for item in check.blocked))

    def test_associative_expansion_surfaces_linked_neighbor(self):
        first = self.engine.remember(
            "Alice visited the aquarium on 2026-02-02.",
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["alice", "2026-02-02", "session0"],
        )
        second = self.engine.remember(
            "Alice bought a camera on 2026-02-03.",
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["alice", "2026-02-03", "session0"],
        )
        results = self.engine.recall(
            "after visiting the aquarium, what did Alice do next?", top_k=5
        )
        contents = [r.item.content for r in results]
        self.assertIn(first.content, contents)
        self.assertIn(second.content, contents)
        self.assertTrue(
            any("linked to" in reason for r in results for reason in r.reasons)
        )

    def test_reinforcement_does_not_dominate_exact_match(self):
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        target = engine.remember(
            "Alice bought a vinyl record on 2026-07-08.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["alice", "2026-07-08", "session26"],
        )
        filler = engine.remember(
            "Alice's favorite color is coral.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["alice", "color"],
        )
        for _ in range(20):
            engine.recall("alice favorite color", top_k=1)
        self.assertGreater(
            engine.curve.retrievability(filler), 1.0  # storage multiplier
        )
        results = engine.recall(
            "What did Alice buy on 2026-07-08?", top_k=3
        )
        self.assertEqual(results[0].item.id, target.id)


class ConflictAdviceTest(unittest.TestCase):
    def _conflicting_pair(self, **kwargs):
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        defaults = {
            "kind": MemoryKind.SEMANTIC,
            "source": user,
            "cues": ["项目"],
            "importance": 0.5,
            "confidence": 1.0,
            "auto_cues": False,
        }
        defaults.update(kwargs)
        first = engine.remember("项目预算是5万", **defaults)
        second = engine.remember("项目预算是8万", **defaults)
        return engine, first, second

    def test_stronger_side_is_recommended(self):
        engine, weak, strong = self._conflicting_pair(
            importance=0.5, evidence_count=1,
        )
        # strong side: more evidence and higher importance
        engine.backend.get(strong.id).importance = 0.9
        engine.backend.get(strong.id).evidence_count = 5
        engine.backend.update(engine.backend.get(strong.id))
        report = engine.conflict_advice()
        self.assertGreaterEqual(report["conflicts"], 1)
        row = report["advice"][0]
        self.assertNotEqual(row["verdict"], "clarify")
        winner_id = (
            row["id_a"] if row["verdict"] == "prefer_a" else row["id_b"]
        )
        self.assertEqual(winner_id, strong.id)
        self.assertTrue(row["advice"])

    def test_balanced_pair_asks_to_clarify(self):
        engine, _, _ = self._conflicting_pair()
        report = engine.conflict_advice()
        self.assertGreaterEqual(report["conflicts"], 1)
        self.assertEqual(report["advice"][0]["verdict"], "clarify")


if __name__ == "__main__":
    unittest.main()
