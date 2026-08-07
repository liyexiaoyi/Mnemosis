import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "benchmarks"))

from locomo_bench import (  # noqa: E402
    build_engine,
    eval_retrieval,
    generate_dataset,
)


class LoCoMoBenchTest(unittest.TestCase):
    def test_dataset_is_deterministic(self):
        first = generate_dataset(seed=7, sessions=4, events_per_session=3)
        second = generate_dataset(seed=7, sessions=4, events_per_session=3)
        self.assertEqual(
            [m["content"] for m in first["events"]],
            [m["content"] for m in second["events"]],
        )
        self.assertEqual(
            [q["q"] for q in first["questions"]],
            [q["q"] for q in second["questions"]],
        )

    def test_different_seeds_differ(self):
        first = generate_dataset(seed=1, sessions=4, events_per_session=3)
        second = generate_dataset(seed=2, sessions=4, events_per_session=3)
        self.assertNotEqual(first["events"][0]["content"], second["events"][0]["content"])

    def test_small_scale_retrieval_sanity(self):
        dataset = generate_dataset(seed=7, sessions=4, events_per_session=3)
        engine = build_engine(dataset)
        try:
            report = eval_retrieval(engine, dataset["questions"])
            fact = report["stats"]["fact"]
            distractor = report["stats"]["distractor"]
            self.assertEqual(fact["n"], 24)  # 4 persons x 6 facts
            self.assertEqual(distractor["pass"], distractor["n"])
        finally:
            engine.close()


if __name__ == "__main__":
    unittest.main()

