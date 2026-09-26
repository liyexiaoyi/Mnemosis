"""Incremental lexical synchronization must equal a fresh rebuild."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType
import mnemosis.bm25 as bm25


class IncrementalBM25Tests(unittest.TestCase):
    def build(self, disk=True):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path=str(Path(temp.name)/"memory.db") if disk else None
        engine=MemoryEngine(path,auto_warmup=False)
        self.addCleanup(engine.close)
        items=engine.remember_many([dict(content=f"tea coffee rare{i}",kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.USER),cues=[]) for i in range(12)],
            auto_cues=False,auto_context=False)
        return engine,path,items

    def signatures(self, results):
        return [(r.item.id,r.score) for r in results]

    def assert_matches_rebuild(self,engine,query="tea coffee",kind=None):
        incremental=self.signatures(engine.recall_bm25(query,top_k=30,kind=kind))
        engine._bm25_cache=None
        rebuilt=self.signatures(engine.recall_bm25(query,top_k=30,kind=kind))
        self.assertEqual([i for i,s in incremental],[i for i,s in rebuilt])
        for (_,a),(_,b) in zip(incremental,rebuilt):self.assertAlmostEqual(a,b,places=12)

    def test_single_edit_retokenizes_only_changed_document(self):
        for disk in (True,False):
            with self.subTest(disk=disk):
                engine,_,items=self.build(disk)
                engine.recall_bm25("tea")
                engine.update(items[0].id,content="mango apple")
                calls=[]; original=bm25.tokenize
                def tracked(text):calls.append(text);return original(text)
                with patch.object(bm25,"tokenize",tracked):
                    found=engine.recall_bm25("mango")
                self.assertEqual(found[0].item.id,items[0].id)
                self.assertEqual(calls,["mango apple","mango"])
                self.assert_matches_rebuild(engine)

    def test_lifecycle_updates_equal_full_rebuild(self):
        for disk in (True,False):
            with self.subTest(disk=disk):
                engine,_,items=self.build(disk)
                engine.recall_bm25("tea")
                operations=[lambda:engine.update(items[1].id,content="tea tea mango",cues=["coffee"]),
                    lambda:engine.forget(items[2].id),lambda:engine.restore(items[2].id),
                    lambda:engine.remember("coffee mango",kind=MemoryKind.SEMANTIC),
                    lambda:engine.backend.delete(items[3].id)]
                for op in operations:
                    op();self.assert_matches_rebuild(engine)
                self.assert_matches_rebuild(engine,kind=MemoryKind.SEMANTIC)

    def test_cross_connection_edit_is_incremental(self):
        engine,path,items=self.build()
        engine.recall_bm25("tea")
        connection=sqlite3.connect(path)
        try:
            with connection:connection.execute("UPDATE memories SET content='mango' WHERE id=?",(items[0].id,))
        finally:connection.close()
        calls=[];original=bm25.tokenize
        def tracked(text):calls.append(text);return original(text)
        with patch.object(bm25,"tokenize",tracked):engine.recall_bm25("mango")
        self.assertEqual(calls,["mango","mango"])

    def test_rollback_and_new_branch_cannot_reuse_stale_delta(self):
        engine,_,items=self.build()
        engine.recall_bm25("tea")
        connection=engine.backend._conn
        connection.execute("UPDATE memories SET content='mango' WHERE id=?",(items[0].id,))
        self.assertTrue(engine.recall_bm25("mango"))
        connection.rollback()
        connection.execute("UPDATE memories SET content='apple' WHERE id=?",(items[0].id,))
        connection.commit()
        self.assertFalse(engine.recall_bm25("mango"))
        self.assertTrue(engine.recall_bm25("apple"))
        self.assert_matches_rebuild(engine)

    def test_change_log_is_bounded_and_missing_history_rebuilds(self):
        engine,_,items=self.build()
        engine.recall_bm25("tea")
        connection=engine.backend._conn
        with connection:
            connection.executemany("UPDATE memories SET content=? WHERE id=?",
                [(f"apple {i}",items[0].id) for i in range(5000)])
        count=connection.execute("SELECT COUNT(*) FROM bm25_lexical_changes").fetchone()[0]
        self.assertLessEqual(count,4351)
        self.assertTrue(engine.recall_bm25("apple"))
        self.assert_matches_rebuild(engine)

    def test_old_client_revision_gap_falls_back_safely(self):
        engine,_,items=self.build()
        engine.recall_bm25("tea")
        with engine.backend._conn:
            engine.backend._conn.execute("UPDATE bm25_lexical_state SET revision=randomblob(16) WHERE id=1")
        engine.update(items[0].id,content="mango")
        self.assertTrue(engine.recall_bm25("mango"))
        self.assert_matches_rebuild(engine)

    def test_upgrade_preserves_v1_database_memories(self):
        engine,path,items=self.build()
        before=[i.to_dict() for i in engine.store.all_active()]
        engine.close()
        connection=sqlite3.connect(path)
        try:
            with connection:
                for event in ("insert","delete","update"):
                    connection.execute(f"DROP TRIGGER bm25_lexical_{event}_v2")
                    connection.execute(f"""CREATE TRIGGER bm25_lexical_{event}
                        AFTER {event} ON memories BEGIN
                        UPDATE bm25_lexical_state SET revision=randomblob(16) WHERE id=1; END""")
                connection.execute("DROP TABLE bm25_lexical_changes")
        finally:connection.close()
        reopened=MemoryEngine(path,auto_warmup=False);self.addCleanup(reopened.close)
        self.assertEqual([i.to_dict() for i in reopened.store.all_active()],before)
        reopened.recall_bm25("tea")
        reopened.update(items[0].id,content="mango")
        self.assertTrue(reopened.recall_bm25("mango"))
        self.assert_matches_rebuild(reopened)

    def test_empty_index_then_reinsert_matches_rebuild(self):
        engine,_,items=self.build()
        engine.recall_bm25("tea")
        for item in items:engine.backend.delete(item.id)
        self.assertEqual(engine.recall_bm25("tea"),[])
        added=engine.remember("tea mango")
        self.assertEqual(engine.recall_bm25("mango")[0].item.id,added.id)
        self.assert_matches_rebuild(engine)

    def test_kind_change_is_removed_from_cached_corpus(self):
        engine,_,items=self.build()
        engine.recall_bm25("tea",kind=MemoryKind.EPISODIC)
        with engine.backend._conn:
            engine.backend._conn.execute("UPDATE memories SET kind='semantic' WHERE id=?",(items[0].id,))
        ids=[r.item.id for r in engine.recall_bm25("tea",kind=MemoryKind.EPISODIC,top_k=30)]
        self.assertNotIn(items[0].id,ids)
        self.assert_matches_rebuild(engine,kind=MemoryKind.EPISODIC)

    def test_seeded_mutation_stream_preserves_rank_and_score(self):
        import random
        for disk in (False,True):
            with self.subTest(disk=disk):
                engine,_,items=self.build(disk)
                rng=random.Random(20260926)
                for step in range(60):
                    # Several changes between reads exercise deduplication of
                    # changed IDs and removal followed by reinsertion.
                    for _ in range(3):
                        target=rng.choice(items)
                        operation=rng.randrange(4)
                        if operation==0:engine.update(target.id,content=f"tea mango {step}",cues=["coffee"])
                        elif operation==1:engine.forget(target.id)
                        elif operation==2:engine.restore(target.id)
                        else:engine.record_feedback(target.id,useful=bool(step%2))
                    self.assert_matches_rebuild(engine,"tea mango coffee")

    def test_event_budget_triggers_rebuild_before_history_is_pruned(self):
        engine,_,items=self.build()
        engine.recall_bm25("tea");token=engine.backend.revision_token()
        with engine.backend._conn:
            engine.backend._conn.executemany("UPDATE memories SET content=? WHERE id=?",
                [(f"mango {i}",items[0].id) for i in range(1025)])
        self.assertIsNone(engine.backend.lexical_changes_since(token))
        self.assertTrue(engine.recall_bm25("mango"))
        self.assert_matches_rebuild(engine)

    def test_sleep_merge_and_promotion_keep_cached_scores_correct(self):
        from datetime import timedelta
        from mnemosis.types import utcnow
        engine,_,items=self.build()
        for item in items:
            engine.update(item.id,content="Alice prefers tea")
            fresh=engine.backend.get(item.id)
            fresh.created_at=utcnow()-timedelta(days=4)
            fresh.access_count=3
            fresh.importance=0.9
            engine.backend.update(fresh)
        engine.recall_bm25("Alice tea")
        engine.sleep()
        self.assertTrue(engine.store.all_active(MemoryKind.SEMANTIC))
        self.assert_matches_rebuild(engine,"Alice tea")
        engine.sleep()
        self.assert_matches_rebuild(engine,"Alice tea")

if __name__=="__main__":unittest.main()
