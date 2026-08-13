import contextlib
import io
import os
import tempfile
import unittest

from mnemosis.cli import main


class CliTest(unittest.TestCase):
    def setUp(self):
        fd, self.db = tempfile.mkstemp(
            prefix="mnemosis_cli_", suffix=".db"
        )
        os.close(fd)
        os.remove(self.db)  # let the CLI create a fresh database

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.db + suffix)
            except FileNotFoundError:
                pass

    def run_cli(self, *args: str) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main(["--db", self.db, *args])
        return out.getvalue()

    def test_remember_recall_stats_sleep(self):
        saved = self.run_cli(
            "remember",
            "The user likes purple.",
            "--kind",
            "semantic",
            "--cues",
            "user,color",
            "--importance",
            "0.8",
        )
        self.assertIn("saved", saved)
        self.assertIn("semantic", saved)

        recalled = self.run_cli("recall", "purple color")
        self.assertIn("purple", recalled)
        self.assertIn("semantic", recalled)

        stats = self.run_cli("stats")
        self.assertIn("semantic: 1", stats)

        sleep = self.run_cli("sleep")
        self.assertIn("promoted", sleep)

    def test_memory_map_command(self):
        self.run_cli("remember", "The user likes purple.", "--cues", "color")
        self.run_cli("remember", "The user likes green.", "--cues", "color")

        raw = self.run_cli("memory-map", "--json")
        self.assertIn('"sampled": 2', raw)
        self.assertIn('"topics"', raw)
        self.assertIn('"strength"', raw)

        human = self.run_cli("memory-map", "--limit", "5")
        self.assertIn("已采样 2 条记忆", human)
        self.assertIn("color: 2条", human)

    def test_memory_map_topic_min(self):
        self.run_cli("remember", "alpha one.", "--cues", "shared")
        self.run_cli("remember", "alpha two.", "--cues", "shared")
        self.run_cli("remember", "solo fact.", "--cues", "solo")

        out = self.run_cli("memory-map", "--topic-min", "2")
        self.assertIn("shared: 2条", out)
        self.assertNotIn("solo:", out)

    def test_memory_map_svg_output(self):
        self.run_cli("remember", "alpha one.", "--cues", "shared")
        svg_path = os.path.join(
            tempfile.gettempdir(),
            f"mnemosis_cli_map_{os.getpid()}.svg",
        )
        if os.path.exists(svg_path):
            os.remove(svg_path)
        try:
            out = self.run_cli("memory-map", "--out", svg_path)
            self.assertIn("saved", out)
            with open(svg_path, encoding="utf-8") as handle:
                svg = handle.read()
            self.assertIn("<svg", svg)
            self.assertIn("记忆强度分布", svg)
        finally:
            if os.path.exists(svg_path):
                os.remove(svg_path)

    def test_memory_map_svg_empty_store(self):
        svg_path = os.path.join(
            tempfile.gettempdir(),
            f"mnemosis_cli_map_empty_{os.getpid()}.svg",
        )
        if os.path.exists(svg_path):
            os.remove(svg_path)
        try:
            out = self.run_cli("memory-map", "--out", svg_path)
            self.assertIn("saved", out)
            with open(svg_path, encoding="utf-8") as handle:
                svg = handle.read()
            self.assertIn("<svg", svg)
            self.assertIn("记忆强度分布", svg)
        finally:
            if os.path.exists(svg_path):
                os.remove(svg_path)

    def test_update_and_recycle_via_cli(self):
        saved = self.run_cli("remember", "The deadline is Friday.")
        memory_id = saved.split()[1]
        updated = self.run_cli("update", memory_id, "--content", "The deadline is Monday.")
        self.assertIn("revisions=1", updated)
        self.assertIn("Monday", updated)

        self.assertIn("forgot", self.run_cli("forget", memory_id))
        self.assertIn("restored", self.run_cli("restore", memory_id))

    def test_check_command(self):
        self.run_cli("remember", "User prefers Chinese.", "--kind", "semantic")
        out = self.run_cli("check", "sqlite debug")
        self.assertIn("gaps:", out)
        self.assertIn("sqlite", out)


if __name__ == "__main__":
    unittest.main()
