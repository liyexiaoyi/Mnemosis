"""Tests for the ci_perf trend baseline and auto-reset logic."""

import json
import os
import sys
import tempfile
import unittest

_BENCH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "benchmarks")
)
sys.path.insert(0, _BENCH)

import ci_perf


def _meta_with_streak(streak: int, baseline: float) -> dict:
    runs = [
        {
            "ts": f"2026-08-{index:02d}T00:00:00+00:00",
            "count": 100,
            "best_ms": 1.0,
        }
        for index in range(1, 11)
    ]
    return {
        "runs": runs,
        "baselines": {"100": baseline},
        "warn_streaks": {"100": streak},
        "reset_history": [],
        "run_count": 30,
        "last_reset_ts": {},
    }


class TrendLogicTest(unittest.TestCase):
    def test_auto_reset_after_five_warnings(self):
        meta = _meta_with_streak(4, 0.2)
        updated, resets, _, baselines = ci_perf._update_trend(
            meta, {100: 10.0}, now_iso="2026-08-10T00:00:00+00:00"
        )
        self.assertIn(100, resets)
        self.assertEqual(updated["warn_streaks"]["100"], 0)
        self.assertEqual(baselines[100], 1.0)
        self.assertEqual(updated["reset_history"][-1]["count"], 100)
        self.assertEqual(updated["reset_history"][-1]["old_ms"], 0.2)
        self.assertEqual(updated["reset_history"][-1]["new_ms"], 1.0)

    def test_no_warning_below_absolute_floor(self):
        meta = _meta_with_streak(4, 0.2)
        updated, resets, _, _ = ci_perf._update_trend(
            meta, {100: 1.0}
        )
        self.assertEqual(resets, [])
        self.assertEqual(updated["warn_streaks"]["100"], 0)

    def test_streak_builds_then_resets(self):
        meta = _meta_with_streak(2, 0.2)
        for _ in range(2):
            meta, resets, _, _ = ci_perf._update_trend(
                meta, {100: 10.0}
            )
            self.assertEqual(resets, [])
        meta, resets, _, _ = ci_perf._update_trend(
            meta, {100: 10.0}
        )
        self.assertIn(100, resets)

    def test_manual_reset_env_clears_meta(self):
        # main() replaces the meta with _empty_meta when the env var is set.
        meta = _meta_with_streak(4, 0.2)
        cleared = ci_perf._empty_meta()
        self.assertEqual(cleared["runs"], [])
        self.assertEqual(cleared["baselines"], {})
        self.assertEqual(cleared["warn_streaks"], {})
        self.assertNotEqual(meta, cleared)

    def test_load_trend_migrates_old_list_format(self):
        original_path = ci_perf._TREND_PATH
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        ci_perf._TREND_PATH = path
        try:
            runs = [
                {
                    "ts": "2026-08-01T00:00:00+00:00",
                    "count": 100,
                    "best_ms": 1.0,
                },
                {
                    "ts": "2026-08-02T00:00:00+00:00",
                    "count": 500,
                    "best_ms": 5.0,
                },
            ]
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(runs, handle)
            meta = ci_perf._load_trend()
            self.assertEqual(len(meta["runs"]), 2)
            self.assertEqual(meta["baselines"], {})
            self.assertEqual(meta["reset_history"], [])
        finally:
            ci_perf._TREND_PATH = original_path
            if os.path.exists(path):
                os.remove(path)

    def test_reset_history_is_trimmed(self):
        meta = _meta_with_streak(0, 1.0)
        meta["reset_history"] = [
            {"ts": f"2026-08-{index:02d}T00:00:00+00:00"}
            for index in range(60)
        ]
        trimmed = ci_perf._trim_runs(meta)
        self.assertEqual(len(trimmed["reset_history"]), 50)

    def test_load_trend_drops_old_last_reset_run(self):
        original_path = ci_perf._TREND_PATH
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        ci_perf._TREND_PATH = path
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "runs": [],
                        "baselines": {},
                        "warn_streaks": {},
                        "last_reset_run": {"100": 5},
                    },
                    handle,
                )
            meta = ci_perf._load_trend()
            self.assertNotIn("last_reset_run", meta)
            self.assertEqual(meta["last_reset_ts"], {})
        finally:
            ci_perf._TREND_PATH = original_path
            if os.path.exists(path):
                os.remove(path)

    def test_auto_reset_blocked_by_cooldown(self):
        meta = _meta_with_streak(5, 0.2)
        meta["last_reset_ts"] = {
            "100": "2026-08-09T00:00:00+00:00"
        }
        updated, resets, _, baselines = ci_perf._update_trend(
            meta, {100: 10.0}, now_iso="2026-08-09T12:00:00+00:00"
        )
        self.assertEqual(resets, [])
        self.assertEqual(updated["warn_streaks"]["100"], 6)
        self.assertEqual(baselines[100], 0.2)

    def test_auto_reset_allowed_after_cooldown(self):
        meta = _meta_with_streak(5, 0.2)
        meta["last_reset_ts"] = {
            "100": "2026-08-08T00:00:00+00:00"
        }
        updated, resets, _, _ = ci_perf._update_trend(
            meta, {100: 10.0}, now_iso="2026-08-10T00:00:00+00:00"
        )
        self.assertIn(100, resets)
        self.assertEqual(updated["warn_streaks"]["100"], 0)
        self.assertEqual(
            updated["last_reset_ts"]["100"], "2026-08-10T00:00:00+00:00"
        )

    def test_summary_includes_delta_column(self):
        runs = [
            {
                "ts": "2026-08-01T00:00:00+00:00",
                "count": 100,
                "best_ms": 1.0,
            },
            {
                "ts": "2026-08-02T00:00:00+00:00",
                "count": 100,
                "best_ms": 1.0,
                "p95_ms": 1.0,
            },
            {
                "ts": "2026-08-02T00:00:00+00:00",
                "count": 500,
                "best_ms": 6.0,
            },
            {
                "ts": "2026-08-02T00:00:00+00:00",
                "count": 2000,
                "best_ms": 20.0,
            },
            {
                "ts": "2026-08-03T00:00:00+00:00",
                "count": 100,
                "best_ms": 2.0,
            },
            {
                "ts": "2026-08-03T00:00:00+00:00",
                "count": 500,
                "best_ms": 5.0,
            },
            {
                "ts": "2026-08-03T00:00:00+00:00",
                "count": 2000,
                "best_ms": 20.0,
            },
        ]
        summary = ci_perf._summary_markdown(
            [(100, 2.0, 2.5), (500, 5.0, 6.0), (2000, 20.0, 22.0)],
            {100: 2.0, 500: 5.0, 2000: 20.0},
            {100: 1.0, 500: 5.0, 2000: 20.0},
            [],
            runs,
        )
        self.assertIn("Δ vs prev(3)", summary)
        self.assertIn("p95 ms", summary)
        self.assertIn("🔴 +1.00", summary)
        self.assertIn("🟢 -1.00", summary)
        self.assertIn(
            "| 100 | 2.00 | 🔴 +1.00 | 2.00 | 2.50 ⚠️ |", summary
        )

    def test_percentile_nearest_rank(self):
        values = [float(index) for index in range(1, 11)]
        self.assertEqual(ci_perf._percentile(values, 50), 5.0)
        self.assertEqual(ci_perf._percentile(values, 95), 10.0)
        self.assertEqual(ci_perf._percentile(values, 99), 10.0)

    def test_p95_warning_logic(self):
        self.assertTrue(ci_perf._p95_warning(5.0, 1.0, 100))
        self.assertFalse(ci_perf._p95_warning(2.2, 2.0, 100))
        self.assertFalse(ci_perf._p95_warning(1.5, 1.0, 100))
        self.assertFalse(ci_perf._p95_warning(3.0, None, 100))

    def test_is_noisy(self):
        self.assertFalse(ci_perf._is_noisy(2.0, 1.0, 2))
        self.assertTrue(ci_perf._is_noisy(3.0, 1.0, 2))
        self.assertTrue(ci_perf._is_noisy(1.0, 3.0, 2))
        self.assertFalse(ci_perf._is_noisy(5.0, 5.0, 0))


if __name__ == "__main__":
    unittest.main()
