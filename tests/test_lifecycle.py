import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "benchmarks"))

from lifecycle_eval import run_decay_eval, run_update_eval


class LifecycleEvalTest(unittest.TestCase):
    def test_review_beats_no_review(self):
        result = run_decay_eval(days=30, review_every_days=7)
        self.assertGreater(
            result["reviewed_avg_score"], result["unreviewed_avg_score"]
        )
        self.assertGreater(
            result["emotional_retrievability"],
            result["neutral_retrievability"],
        )

    def test_update_replaces_and_conflicts_detected(self):
        result = run_update_eval()
        self.assertIn("200 per minute", result["updated_top_content"])
        self.assertFalse(result["stale_content_survives"])
        self.assertEqual(result["conflicts_detected"], 1)

    def test_update_at_scale_and_concurrency(self):
        from lifecycle_eval import run_concurrency_check, run_update_at_scale

        scale = run_update_at_scale(count=100)
        self.assertIn("disabled", scale["top_content"])
        self.assertFalse(scale["stale_survives"])
        concurrency = run_concurrency_check()
        self.assertTrue(concurrency["reader_sees_writer_data"])


if __name__ == "__main__":
    unittest.main()
