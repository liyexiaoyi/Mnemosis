"""Experimental evidence retrieval is explicit and works through both transports."""
import http.client
import io
import json
import threading
from datetime import datetime, timezone

import pytest

from evidence_fixtures import FixedAnnotator
from mnemosis import MemoryEngine
import mnemosis.mcp_server as mcp


def engine():
    e = MemoryEngine(auto_warmup=False)
    now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
    e.remember("Mina trip was to Osaka.", cues=["mina", "trip"], created_at=now)
    e.remember("Mina trip was in October.", cues=["mina", "trip"], created_at=now)
    return e


def request(args=None):
    return {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "recall_evidence", "arguments": {"query": "Mina trip destination and date?",
        "now": "2026-10-07T12:00:00+00:00", **(args or {})}}}


def parse_report(response):
    assert "error" not in response and not response["result"]["isError"]
    return json.loads(response["result"]["content"][0]["text"])


@pytest.mark.parametrize("expose", ["core", "advanced", "experimental"])
def test_explicit_exposure_controls_manifest_and_direct_call(expose):
    e = engine(); provider = FixedAnnotator()
    try:
        server = mcp.MCPServer(e, expose, evidence_annotator=provider)
        names = {t["name"] for t in server._tools}
        assert ("recall_evidence" in names) == (expose == "experimental")
        if expose == "experimental":
            assert names == set(server._tool_handlers)
            result = parse_report(json.loads(server.handle_line(json.dumps(request()))))
            assert result["status"] == "feasible" and result["selector"]["completeness"] == "1/1"
        else:
            assert "error" in json.loads(server.handle_line(json.dumps(request())))
            assert provider.calls == []
    finally:
        e.close()


def test_disabled_annotator_fails_without_changing_old_recall():
    e = engine()
    try:
        server = mcp.MCPServer(e, "experimental")
        assert "error" in json.loads(server.handle_line(json.dumps(request())))
        old = request({"read_only": True})
        old["params"]["name"] = "recall"
        assert isinstance(parse_report(json.loads(server.handle_line(json.dumps(old)))), list)
    finally:
        e.close()


@pytest.mark.parametrize("args", [{"model": "evil"}, {"base_url": "https://example.com"},
    {"read_only": False}, {"learning_policy": "final"}, {"top_k": True}, {"top_k": 0},
    {"exclude_ids": ["A", "A"]}, {"exclude_ids": [12]}, {"now": "2026-10-07T12:00:00"}])
def test_invalid_mcp_params_do_not_start_annotation(args):
    e = engine(); provider = FixedAnnotator()
    try:
        server = mcp.MCPServer(e, "experimental", evidence_annotator=provider)
        response = json.loads(server.handle_line(json.dumps(request(args))))
        assert response["error"]["code"] == -32602 and provider.calls == []
    finally:
        e.close()


def test_real_http_post_serializes_exact_math_and_separate_requests():
    e = engine()
    server = None
    try:
        server = mcp.build_http_server(e, expose="experimental", evidence_annotator=FixedAnnotator())
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        def post():
            conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            try:
                conn.request("POST", "/", json.dumps(request()), {"Content-Type": "application/json"})
                response = conn.getresponse()
                assert response.status == 200
                return parse_report(json.loads(response.read()))
            finally:
                conn.close()
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            reports = list(pool.map(lambda _: post(), range(2)))
        assert all(r["selector"]["completeness"] == "1/1" for r in reports)
        assert reports[0]["support"] == reports[1]["support"]
    finally:
        if server is not None:
            server.shutdown(); server.server_close()
        e.close()


@pytest.mark.parametrize("framed", [False, True])
def test_stdio_transport_uses_configured_provider_and_preserves_framing(monkeypatch, framed):
    e = engine()
    body = json.dumps(request()).encode()
    wire = b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body if framed else body + b"\n"
    inp = io.TextIOWrapper(io.BytesIO(wire), encoding="utf8")
    out_bytes = io.BytesIO(); out = io.TextIOWrapper(out_bytes, encoding="utf8")
    monkeypatch.setattr(mcp.sys, "stdin", inp); monkeypatch.setattr(mcp.sys, "stdout", out)
    monkeypatch.setattr(mcp, "_build_engine", lambda *args: e)
    monkeypatch.setattr(mcp, "_build_evidence_annotator", lambda *args: FixedAnnotator())
    mcp.run_stdio(expose="experimental", evidence_annotator="ollama")
    out.flush()
    raw = out_bytes.getvalue()
    if framed:
        assert raw.startswith(b"Content-Length: ")
        raw = raw.split(b"\r\n\r\n", 1)[1]
    report = parse_report(json.loads(raw))
    assert report["status"] == "feasible"


@pytest.mark.parametrize("transport", ["stdio", "http"])
def test_cli_evidence_configuration_reaches_both_transports(monkeypatch, transport):
    received = []
    monkeypatch.setattr(mcp, "run_stdio", lambda **kw: received.append(kw))
    monkeypatch.setattr(mcp, "run_http", lambda **kw: received.append(kw))
    assert mcp.main(["--transport", transport, "--expose", "experimental", "--evidence-annotator", "ollama",
                     "--evidence-model", "qwen2.5:3b", "--evidence-base-url", "http://127.0.0.1:11434"]) == 0
    assert received[0]["evidence_annotator"] == "ollama" and received[0]["evidence_model"] == "qwen2.5:3b"
