"""Tests for the startup page-cache warmup (warm_pages / engine.warmup)."""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from unittest import mock

import mnemosis.engine as engine_module
from mnemosis import MemoryEngine
from mnemosis.backend import SQLiteBackend
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

    def test_auto_warmup_skipped_for_small_store(self) -> None:
        # 64MB threshold applies even when auto-warmup is requested: a tiny
        # fresh DB must not start a thread.
        fd, name = tempfile.mkstemp(prefix="mnemosis_small_", suffix=".db")
        os.close(fd)

        def _cleanup() -> None:
            for path in (name, name + "-wal", name + "-shm"):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except OSError:
                    pass

        self.addCleanup(_cleanup)
        engine = MemoryEngine(name, auto_warmup=True)
        self.assertFalse(engine._warmed_event.is_set())
        engine.close()

    def test_auto_warmup_started_for_large_store(self) -> None:
        # _warmed_event is set synchronously by warmup(); the scan itself
        # runs in the background daemon thread.
        with mock.patch.object(engine_module, "_AUTO_WARMUP_MIN_BYTES", 0):
            fd, name = tempfile.mkstemp(prefix="mnemosis_auto_", suffix=".db")
            os.close(fd)

            def _cleanup() -> None:
                for path in (name, name + "-wal", name + "-shm"):
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except OSError:
                        pass

            self.addCleanup(_cleanup)
            engine = MemoryEngine(name, auto_warmup=True)
        try:
            self.assertTrue(engine._warmed_event.is_set())
        finally:
            engine.close()

    def test_auto_warmup_can_be_disabled(self) -> None:
        with mock.patch.object(engine_module, "_AUTO_WARMUP_MIN_BYTES", 0):
            fd, name = tempfile.mkstemp(prefix="mnemosis_noauto_", suffix=".db")
            os.close(fd)

            def _cleanup() -> None:
                for path in (name, name + "-wal", name + "-shm"):
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except OSError:
                        pass

            self.addCleanup(_cleanup)
            engine = MemoryEngine(name, auto_warmup=False)
        try:
            self.assertFalse(engine._warmed_event.is_set())
        finally:
            engine.close()

    def test_auto_warmup_noop_for_dict_backend(self) -> None:
        with mock.patch.object(engine_module, "_AUTO_WARMUP_MIN_BYTES", 0):
            engine = MemoryEngine(auto_warmup=True)
        try:
            self.assertFalse(engine._warmed_event.is_set())
        finally:
            engine.close()

    def test_auto_warmup_close_waits_and_releases_file(self) -> None:
        # close() joins the background warmup thread, so the database file
        # is removable immediately afterwards (no Windows file-lock race).
        fd, name = tempfile.mkstemp(prefix="mnemosis_join_", suffix=".db")
        os.close(fd)

        def _cleanup() -> None:
            for path in (name, name + "-wal", name + "-shm"):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except OSError:
                    pass

        self.addCleanup(_cleanup)
        # Patch the class method BEFORE construction: the auto-warmup thread
        # starts during __init__, so the slow scan must already be in place.
        with (
            mock.patch.object(engine_module, "_AUTO_WARMUP_MIN_BYTES", 0),
            mock.patch.object(
                SQLiteBackend,
                "warm_pages",
                side_effect=lambda stop=None: time.sleep(0.2),
            ),
        ):
            engine = MemoryEngine(name, auto_warmup=True)
        start = time.perf_counter()
        engine.close()
        self.assertGreaterEqual(time.perf_counter() - start, 0.1)
        os.remove(name)  # must succeed without retries

    def test_warmup_exception_does_not_break_engine(self) -> None:
        engine = self._sqlite_engine()
        source = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "用户喜欢在周末爬山",
            kind=MemoryKind.SEMANTIC,
            source=source,
        )
        with mock.patch.object(
            engine.backend,
            "warm_pages",
            side_effect=RuntimeError("disk full"),
        ):
            engine.warmup(background=False)  # must swallow, not raise
        results = engine.recall("用户喜欢什么户外活动", top_k=3)
        self.assertGreaterEqual(len(results), 1)
        engine.close()

    def test_warmup_close_joins_slow_background_scan(self) -> None:
        # close() must wait (bounded) for an in-flight scan so the dedicated
        # SQLite connection is released before the file is deleted.
        engine = self._sqlite_engine()
        with mock.patch.object(
            engine.backend,
            "warm_pages",
            side_effect=lambda stop=None: time.sleep(0.5),
        ):
            engine.warmup()  # background thread with a deliberately slow scan
            start = time.perf_counter()
            engine.close()
            elapsed = time.perf_counter() - start
        self.assertGreaterEqual(elapsed, 0.4)

    def test_warmup_close_timeout_does_not_block(self) -> None:
        # If the scan outlives the join timeout, close() must still return
        # promptly (bounded wait), log a warning, and not crash.
        engine = self._sqlite_engine()
        with (
            mock.patch.object(engine_module, "_AUTO_WARMUP_JOIN_TIMEOUT", 0.2),
            mock.patch.object(
                engine.backend,
                "warm_pages",
                side_effect=lambda stop=None: time.sleep(1.0),
            ),
        ):
            engine.warmup()
            start = time.perf_counter()
            engine.close()
            elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 0.7)


if __name__ == "__main__":
    unittest.main()
