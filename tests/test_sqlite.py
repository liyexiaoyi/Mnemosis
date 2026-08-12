"""SQLiteBackend-specific tests: dedupe, persistence, schema migration."""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid
from dataclasses import fields
from datetime import datetime, timezone

from mnemosis import MemoryEngine
from mnemosis.backend import SQLiteBackend, _row_to_item
from mnemosis.types import (
    MemoryItem,
    MemoryKind,
    MemoryStatus,
    SourceRecord,
    SourceType,
)


class SQLiteBackendTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        if os.path.exists(self.path):
            os.remove(self.path)
        self.engine = MemoryEngine(self.path)
        self.user = SourceRecord(origin=SourceType.USER)

    def tearDown(self):
        self.engine.close()
        for suffix in ("", "-wal", "-shm"):
            path = self.path + suffix
            if os.path.exists(path):
                os.remove(path)

    def remember(self, content, **kwargs):
        kwargs.setdefault("kind", MemoryKind.SEMANTIC)
        kwargs.setdefault("source", self.user)
        return self.engine.remember(content, **kwargs)

    def test_semantic_dedupe_and_recall(self):
        self.remember("Alice likes mint tea.", importance=0.5)
        second = self.remember("Alice likes mint tea.", importance=0.9)
        self.assertEqual(self.engine.stats()["semantic"], 1)
        self.assertEqual(second.importance, 0.9)
        results = self.engine.recall("mint tea")
        self.assertEqual(results[0].item.content, "Alice likes mint tea.")

    def test_update_and_recycle(self):
        item = self.remember("The deadline is Friday.")
        updated = self.engine.update(item.id, content="The deadline is Monday.")
        self.assertEqual(updated.revision_count, 1)
        self.assertTrue(self.engine.forget(item.id))
        self.assertEqual(self.engine.recall("deadline", top_k=5), [])
        self.assertTrue(self.engine.restore(item.id))
        self.assertTrue(self.engine.recall("deadline"))

    def test_seq_assignment_is_unique_and_never_reused(self):
        """seq must be atomic (MAX+1), including after deletes and batches."""
        first = self.remember("seq fact 1")
        second = self.remember("seq fact 2")
        self.assertEqual(second.seq, first.seq + 1)

        # deleting a row must not cause its seq to be reused
        self.engine.forget(first.id)
        third = self.remember("seq fact 3")
        self.assertGreater(third.seq, second.seq)

        # batch import continues the same counter with unique seqs
        payload = {
            "memories": [
                {
                    "content": f"imported {index}",
                    "kind": "semantic",
                    "source": self.user.to_dict(),
                }
                for index in range(3)
            ]
        }
        self.engine.import_memories(payload)
        seqs = [item.seq for item in self.engine.backend.list()]
        self.assertEqual(len(seqs), len(set(seqs)))
        self.assertEqual(max(seqs), third.seq + 3)

    def test_seq_is_atomic_across_processes(self):
        """Two processes inserting concurrently must never share a seq."""
        self.engine.close()
        src = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "src")
        )
        worker = (
            "import sys;"
            "from mnemosis.backend import SQLiteBackend;"
            "from mnemosis.types import MemoryItem, MemoryKind,"
            " SourceRecord, SourceType;"
            "b = SQLiteBackend(sys.argv[1]);"
            "src = SourceRecord(origin=SourceType.USER);"
            "[b.add(MemoryItem(content='race %s-%d' % (sys.argv[2], i),"
            " kind=MemoryKind.SEMANTIC, source=src))"
            " for i in range(25)];"
            "b.close()"
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
        procs = [
            subprocess.Popen(
                [sys.executable, "-c", worker, self.path, str(index)],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for index in range(2)
        ]
        for proc in procs:
            _, err = proc.communicate(timeout=120)
            self.assertEqual(proc.returncode, 0, err.decode("utf-8", "ignore"))
        backend = SQLiteBackend(self.path)
        try:
            seqs = [item.seq for item in backend.list()]
            self.assertEqual(len(seqs), 50)
            self.assertEqual(len(set(seqs)), 50)
            self.assertEqual(set(seqs), set(range(1, 51)))
        finally:
            backend.close()

    def test_count_is_cheap_and_respects_status(self):
        first = self.remember("count fact 1")
        self.remember("count fact 2")
        self.assertEqual(self.engine.backend.count(), 2)
        self.assertEqual(
            self.engine.backend.count(kind=MemoryKind.SEMANTIC), 2
        )
        self.engine.forget(first.id)
        self.assertEqual(self.engine.backend.count(), 1)

    def test_term_df_ignores_recycled_memories(self):
        item = self.remember("rareword alpha")
        self.assertEqual(self.engine.backend.term_df("rareword", None), 1)
        self.engine.forget(item.id)
        self.assertEqual(self.engine.backend.term_df("rareword", None), 0)

    def test_row_fast_path_fields_match_dataclass(self):
        """Every MemoryItem field must be populated by the trusted fast path."""
        self.remember("fast path field check")
        row = self.engine.backend._conn.execute(
            "SELECT * FROM memories LIMIT 1"
        ).fetchone()
        item = _row_to_item(row)
        for field in fields(MemoryItem):
            self.assertTrue(hasattr(item, field.name), field.name)
        self.assertEqual(item.content, "fast path field check")

    def test_new_database_has_status_seq_index(self):
        """A brand-new store must also get the recency-fallback index."""
        indexes = {
            row[1]
            for row in self.engine.backend._conn.execute(
                "PRAGMA index_list(memories)"
            ).fetchall()
        }
        self.assertIn("idx_memories_status_seq", indexes)

    def test_core_query_plans_use_indexes(self):
        backend = SQLiteBackend(":memory:")
        try:
            # Seed enough rows with mixed statuses so the planner has real
            # selectivity statistics (80 active / 20 recycled) instead of
            # empty-table heuristics that differ across SQLite builds.
            stored: list[MemoryItem] = []
            for index in range(100):
                status = (
                    MemoryStatus.ACTIVE
                    if index < 80
                    else MemoryStatus.RECYCLED
                )
                item = MemoryItem(
                    content=f"seed memory {index} alpha beta",
                    kind=MemoryKind.EPISODIC,
                    source=SourceRecord(origin=SourceType.USER),
                    cues=["alpha", "beta"],
                    importance=0.5 + (index % 10) * 0.05,
                    status=status,
                )
                backend.add(item)
                backend.add_cues(item.id, item.cues)
                backend.index_terms(
                    item.id, frozenset(["alpha", "beta"]), item.kind
                )
                stored.append(item)
            backend.add_link(stored[0].id, stored[1].id, 1.0)
            backend.add_link(stored[1].id, stored[0].id, 1.0)
            backend._conn.execute("ANALYZE")
            plans = backend.audit_query_plans()
            self.assertIn("USING INDEX", plans["get_many"])
            self.assertIn(
                "sqlite_autoindex_memories_1",
                plans["get_many"],
            )
            self.assertNotIn(
                "idx_memories_status_importance", plans["get_many"]
            )
            self.assertNotIn("SCAN m", plans["get_many"])
            self.assertIn("USING INDEX", plans["get_many_long"])
            self.assertIn(
                "sqlite_autoindex_memories_1",
                plans["get_many_long"],
            )
            self.assertNotIn(
                "idx_memories_status_importance",
                plans["get_many_long"],
            )
            self.assertNotIn("SCAN m", plans["get_many_long"])
            self.assertIn("idx_memories_status_seq", plans["list_recent"])
            self.assertNotIn("SCAN", plans["list_recent"])
            self.assertIn(
                "idx_memories_status_importance", plans["list_strongest"]
            )
            self.assertNotIn("SCAN", plans["list_strongest"])
            self.assertIn("sqlite_autoindex_cues_1", plans["find_by_cue"])
            self.assertIn(
                "sqlite_autoindex_terms_1", plans["find_by_terms"]
            )
            self.assertIn("sqlite_autoindex_terms_1", plans["term_df"])
            self.assertIn(
                "sqlite_autoindex_links_1", plans["related_links"]
            )
            self.assertIn(
                "sqlite_autoindex_memories_1", plans["related_memories"]
            )
        finally:
            backend.close()

    def test_persistence_across_reopen(self):
        self.remember("The password hint is 'blue whale'.", cues=["password"])
        self.engine.close()
        reopened = MemoryEngine(self.path)
        try:
            results = reopened.recall("password hint")
            self.assertTrue(results)
            self.assertEqual(
                results[0].item.content, "The password hint is 'blue whale'."
            )
        finally:
            reopened.close()

    def test_migration_from_old_schema(self):
        """A v0.1 database (without new columns) must open and read cleanly."""
        self.engine.close()
        conn = sqlite3.connect(self.path)
        conn.execute("DROP TABLE IF EXISTS memories")
        conn.execute(
            """
            CREATE TABLE memories (
                id            TEXT PRIMARY KEY,
                kind          TEXT NOT NULL,
                content       TEXT NOT NULL,
                content_hash  TEXT NOT NULL,
                source_json   TEXT NOT NULL,
                cues_json     TEXT NOT NULL DEFAULT '[]',
                created_at    TEXT NOT NULL,
                last_access_at TEXT,
                access_count  INTEGER NOT NULL DEFAULT 0,
                importance    REAL NOT NULL DEFAULT 0.5,
                strength      REAL NOT NULL DEFAULT 1.0,
                confidence    REAL NOT NULL DEFAULT 1.0,
                status        TEXT NOT NULL DEFAULT 'active'
            )
            """
        )
        source = SourceRecord(origin=SourceType.USER)
        row = (
            uuid.uuid4().hex,
            MemoryKind.SEMANTIC.value,
            "old fact",
            "old-hash",
            json.dumps(source.to_dict()),
            "[]",
            datetime.now(timezone.utc).isoformat(),
            None,
            0,
            0.5,
            1.0,
            0.8,
            "active",
        )
        conn.execute(
            """
            INSERT INTO memories (
                id, kind, content, content_hash, source_json, cues_json,
                created_at, last_access_at, access_count, importance,
                strength, confidence, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
        conn.commit()
        conn.close()

        backend = SQLiteBackend(self.path)
        try:
            items = backend.list()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].content, "old fact")
            self.assertEqual(items[0].storage_strength, 1.0)
            self.assertEqual(items[0].evidence_count, 1)
            self.assertEqual(items[0].revision_count, 0)
        finally:
            backend.close()


if __name__ == "__main__":
    unittest.main()
