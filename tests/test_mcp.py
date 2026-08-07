import json
import unittest

from mnemosis import MemoryEngine
from mnemosis.mcp_server import MCPServer


class MCPTest(unittest.TestCase):
    def setUp(self):
        self.server = MCPServer(MemoryEngine())

    def send(self, payload: dict) -> dict | None:
        response = self.server.handle_line(json.dumps(payload))
        return json.loads(response) if response else None

    def call(self, name: str, arguments: dict) -> dict:
        result = self.send(
            {
                "jsonrpc": "2.0",
                "id": 100,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        self.assertIsNotNone(result)
        return json.loads(result["result"]["content"][0]["text"])

    def test_initialize(self):
        response = self.send(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )
        self.assertEqual(response["result"]["serverInfo"]["name"], "mnemosis")
        self.assertIn("tools", response["result"]["capabilities"])

    def test_tools_list(self):
        response = self.send(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        names = [tool["name"] for tool in response["result"]["tools"]]
        for expected in [
            "remember",
            "recall",
            "sleep",
            "check",
            "update",
            "forget",
            "restore",
            "stats",
            "working_set",
        ]:
            self.assertIn(expected, names)

    def test_remember_recall_roundtrip(self):
        saved = self.call(
            "remember",
            {
                "content": "User likes mint tea.",
                "kind": "semantic",
                "cues": ["tea", "user"],
            },
        )
        self.assertIn("id", saved)
        results = self.call("recall", {"query": "mint tea"})
        self.assertTrue(results)
        self.assertIn("mint tea", results[0]["content"])

    def test_sleep_and_stats(self):
        self.call("remember", {"content": "A note.", "kind": "episodic"})
        report = self.call("sleep", {})
        self.assertIn("summary", report)
        stats = self.call("stats", {})
        self.assertEqual(stats["active"], 1)

    def test_update_tool(self):
        saved = self.call("remember", {"content": "Old fact.", "kind": "semantic"})
        updated = self.call(
            "update",
            {"memory_id": saved["id"], "content": "New fact."},
        )
        self.assertEqual(updated["revision_count"], 1)
        self.assertEqual(updated["content"], "New fact.")

    def test_notifications_are_ignored(self):
        self.assertIsNone(
            self.server.handle_line(
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
            )
        )

    def test_unknown_method_returns_error(self):
        response = self.send(
            {"jsonrpc": "2.0", "id": 9, "method": "bogus", "params": {}}
        )
        self.assertEqual(response["error"]["code"], -32601)

    def test_tool_error_is_reported(self):
        response = self.send(
            {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "tools/call",
                "params": {
                    "name": "remember",
                    "arguments": {"content": "x", "kind": "bogus"},
                },
            }
        )
        self.assertTrue(response["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
