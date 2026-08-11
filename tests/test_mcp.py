import json
import io
import http.client
import subprocess
import sys
import threading
import unittest

from mnemosis import MemoryEngine
from mnemosis.mcp_server import (
    EXPERIMENTAL_TOOLS,
    MCPServer,
    MAX_MESSAGE_SIZE,
    build_http_server,
    _read_message,
)


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

    def test_oversized_message_is_skipped_not_eof(self):
        size = MAX_MESSAGE_SIZE + 100
        fake = type(
            "FakeStdin",
            (),
            {"buffer": io.BytesIO(
                b"Content-Length: " + str(size).encode("ascii")
                + b"\r\n\r\n" + b"x" * 100
            )},
        )()
        old_stdin = sys.stdin
        try:
            sys.stdin = fake
            message, framed = _read_message()
        finally:
            sys.stdin = old_stdin
        self.assertEqual(message, "")
        self.assertTrue(framed)

    def test_stdio_emits_utf8(self):
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "from mnemosis.mcp_server import run_stdio; run_stdio()",
            ],
            input='{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n'.encode("utf-8"),
            capture_output=True,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0)
        obj = json.loads(proc.stdout.strip().decode("utf-8"))
        self.assertIn("tools", obj["result"])

    def test_stdio_content_length_framing(self):
        body = '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
        framed = (
            f"Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"
        ).encode("utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "from mnemosis.mcp_server import run_stdio; run_stdio()",
            ],
            input=framed,
            capture_output=True,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0)
        header, sep, payload = proc.stdout.partition(b"\r\n\r\n")
        self.assertTrue(sep)
        length = int(header.split(b":")[1].strip())
        obj = json.loads(payload[:length].decode("utf-8"))
        self.assertIn("tools", obj["result"])

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

    def test_tool_tiers(self):
        advanced = MCPServer(MemoryEngine(), expose="advanced")
        experimental = MCPServer(MemoryEngine(), expose="experimental")
        advanced_names = {tool["name"] for tool in advanced._tools}
        experimental_names = {tool["name"] for tool in experimental._tools}
        self.assertIn("remember", advanced_names)
        self.assertTrue(EXPERIMENTAL_TOOLS - advanced_names)
        self.assertTrue(EXPERIMENTAL_TOOLS <= experimental_names)

    def test_calibrate_decay_tool(self):
        result = self.server._call_tool("calibrate_decay", {})
        self.assertIn("calibrated", result)

    def test_remember_turn_tool(self):
        result = self.server._call_tool(
            "remember_turn", {"text": "用户喜欢咖啡。用户是程序员。"}
        )
        self.assertGreaterEqual(result["saved"], 2)

    def test_conflict_advice_tool(self):
        result = self.server._call_tool("conflict_advice", {})
        self.assertIn("advice", result)

    def test_memory_map_tool(self):
        result = self.server._call_tool("memory_map", {})
        self.assertIn("topics", result)

    def test_zero_values_are_not_swallowed(self):
        result = self.server._call_tool(
            "remember",
            {
                "content": "不可信消息",
                "confidence": 0,
            },
        )
        item = self.server.engine.backend.get(result["id"])
        self.assertEqual(item.confidence, 0.0)

    def test_short_body_read_is_eof_not_crash(self):
        fake = type(
            "FakeStdin",
            (),
            {"buffer": io.BytesIO(b"Content-Length: 10\r\n\r\nabc")},
        )()
        old_stdin = sys.stdin
        try:
            sys.stdin = fake
            message, framed = _read_message()
        finally:
            sys.stdin = old_stdin
        self.assertEqual(message, "")
        self.assertTrue(framed)

    def test_http_transport(self):
        server = build_http_server(MemoryEngine(), port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = http.client.HTTPConnection(
                "127.0.0.1", server.server_port, timeout=10
            )
            conn.request(
                "POST",
                "/",
                body=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {},
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            response = conn.getresponse()
            data = json.loads(response.read().decode("utf-8"))
            self.assertEqual(
                data["result"]["serverInfo"]["name"], "mnemosis"
            )
            self.assertIsNotNone(response.getheader("Mcp-Session-Id"))
            conn.request(
                "POST",
                "/",
                body=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/list",
                        "params": {},
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            tools = json.loads(conn.getresponse().read().decode("utf-8"))
            self.assertGreater(len(tools["result"]["tools"]), 10)
            conn.close()
        finally:
            server.shutdown()
            server.server_close()

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
        self.assertEqual(response["error"]["code"], -32602)
        self.assertIn("Invalid params", response["error"]["message"])

    def test_review_tools(self):
        remembered = self.call(
            "remember",
            {"content": "Alice likes tea.", "kind": "semantic"},
        )
        memory_id = remembered["id"]
        reviewed = self.call(
            "review",
            {"memory_id": memory_id, "success": True},
        )
        self.assertEqual(reviewed["review_streak"], 1)
        self.assertEqual(reviewed["retrieval_successes"], 1)
        due = self.call("review_due", {"limit": 5})
        self.assertIsInstance(due, list)


if __name__ == "__main__":
    unittest.main()
