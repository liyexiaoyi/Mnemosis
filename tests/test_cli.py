import contextlib
import io
import os
import tempfile
import unittest

from mnemosis.cli import main


class CliTest(unittest.TestCase):
    def setUp(self):
        self.db = os.path.join(tempfile.gettempdir(), "mnemosis_cli_test.db")
        if os.path.exists(self.db):
            os.remove(self.db)

    def tearDown(self):
        if os.path.exists(self.db):
            os.remove(self.db)

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
