"""SQLiteBackend-specific tests: dedupe, persistence, schema migration."""

import json
import os
import sqlite3
import tempfile
import unittest
import uuid
from datetime import datetime, timezone

from mnemosis import MemoryEngine
from mnemosis.backend import SQLiteBackend
from mnemosis.types import MemoryKind, SourceRecord, SourceType


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

