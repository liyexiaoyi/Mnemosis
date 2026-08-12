"""Tests for the startup page-cache warmup (warm_pages / engine.warmup)."""

from __future__ import annotations

import os
import tempfile
import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


class WarmupTests(unittest.TestCase):
    def _sqlite_engine(self) -> MemoryEngine:
        fd, name = tempfile.mkstemp(prefix="mnemosis_warmup_", suffix=".db")
        os.close(fd)

        def _cleanup() -> None:
            for path in (name, name + "-wal", name + "-shm"):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except OSError:
                    pass  # background warmup may still hold the file briefly

        self.addCleanup(_cleanup)
        return MemoryEngine(name)

    def test_warmup_sync_on_sqlite_file(self) -> None:
        engine = self._sqlite_engine()
        source = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "用户喜欢用中文讨论技术问题",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=["语言"],
        )
        engine.warmup(background=False)
        results = engine.recall("用户喜欢什么语言", top_k=3)
        self.assertGreaterEqual(len(results), 1)
        engine.close()

    def test_warmup_background_then_recall(self) -> None:
        engine = self._sqlite_engine()
        source = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "用户喜欢喝咖啡",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=["咖啡"],
        )
        engine.warmup()  # background daemon thread
        results = engine.recall("用户喜欢喝什么", top_k=3)
        self.assertGreaterEqual(len(results), 1)
        engine.close()

    def test_warmup_noop_on_dict_backend(self) -> None:
        engine = MemoryEngine()
        engine.warmup(background=False)
        engine.warmup()  # returns immediately, no thread for DictBackend
        engine.backend.warm_pages()  # direct call is a pure no-op
        engine.recall("anything", top_k=1)

    def test_warmup_skips_after_close(self) -> None:
        engine = self._sqlite_engine()
        source = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "用户喜欢跑步",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=["运动"],
        )
        engine._closed_event.set()
        engine.warmup(background=False)  # closed -> warmup returns immediately
        results = engine.recall("用户喜欢什么运动", top_k=3)
        self.assertGreaterEqual(len(results), 1)
        engine.close()

    def test_warmup_background_close_no_crash(self) -> None:
        engine = self._sqlite_engine()
        source = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "用户喜欢爬山",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=["户外"],
        )
        engine.warmup()  # background daemon thread
        engine.close()  # stop flag set; thread must exit without crashing


if __name__ == "__main__":
    unittest.main()
