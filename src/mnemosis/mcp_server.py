"""Minimal stdio MCP server for Mnemosis.

Implemented on `stdlib` only (JSON-RPC 2.0 over newline-delimited stdio), so
it follows the project's zero-dependency rule and can be wired into Claude
Code, Codex, or any MCP client:

    mnemosis mcp --db memory.db
"""

from __future__ import annotations

import argparse
import http.server
import json
import logging
import os
import sys
import uuid
from collections.abc import Sequence
from typing import Any

from . import __version__ as _MNEMOSIS_VERSION
from .embedding import make_embedder
from .engine import MemoryEngine
from .mcp_handlers import MCPHandlersMixin
from .mcp_registry import registered_handlers
from .mcp_tools import EXPERIMENTAL_TOOLS, TOOL_DEFINITIONS
from .vector_index import VectorIndex

PROTOCOL_VERSION = "2025-03-26"
MAX_MESSAGE_SIZE = 10 * 1024 * 1024
_LOG = logging.getLogger(__name__)


class MCPServer(MCPHandlersMixin):
    def __init__(
        self,
        engine: MemoryEngine | None = None,
        expose: str = "advanced",
    ) -> None:
        self.engine = engine or MemoryEngine()
        self.engine.warmup()  # background page-cache warm for cold starts
        self._tool_handlers = {
            name: getattr(self, method_name)
            for name, method_name in registered_handlers().items()
        }
        self._tools = list(TOOL_DEFINITIONS)
        if expose != "experimental":
            self._tools = [
                tool
                for tool in self._tools
                if tool["name"] not in EXPERIMENTAL_TOOLS
            ]

    def handle_line(self, line: str) -> str | None:
        """Handle one JSON-RPC message; return a response line or None."""
        line = line.strip()
        if not line:
            return None
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return self._error(None, -32700, "Parse error")

        method = message.get("method")
        message_id = message.get("id")
        if message_id is None:
            return None  # notification

        if method == "initialize":
            return self._result(
                message_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "mnemosis",
                        "version": _MNEMOSIS_VERSION,
                    },
                },
            )
        if method == "ping":
            return self._result(message_id, {})
        if method == "tools/list":
            return self._result(message_id, {"tools": self._tools})
        if method == "tools/call":
            params = message.get("params", {}) or {}
            name = params.get("name", "")
            arguments = params.get("arguments", {}) or {}
            try:
                payload = self._call_tool(name, arguments)
                return self._result(
                    message_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    payload, ensure_ascii=False, indent=2
                                ),
                            }
                        ],
                        "isError": False,
                    },
                )
            except KeyError as exc:
                return self._error(
                    message_id,
                    -32602,
                    f"Invalid params: missing required field {exc.args[0]}",
                )
            except (ValueError, TypeError) as exc:
                return self._error(
                    message_id,
                    -32602,
                    f"Invalid params: {exc}",
                )
            except Exception as exc:  # noqa: BLE001 - surface tool errors
                _LOG.exception("tool %s failed", name)
                return self._result(
                    message_id,
                    {
                        "content": [{"type": "text", "text": f"error: {exc}"}],
                        "isError": True,
                    },
                )
        return self._error(message_id, -32601, f"Method not found: {method}")

    def _call_tool(self, name: str, args: dict[str, Any]) -> Any:
        handler = self._tool_handlers.get(name)
        if handler is None:
            raise ValueError(f"unknown tool: {name}")
        return handler(args)

    def _result(self, message_id: Any, result: Any) -> str:
        return json.dumps(
            {"jsonrpc": "2.0", "id": message_id, "result": result},
            ensure_ascii=False,
        )

    def _error(self, message_id: Any, code: int, message: str) -> str:
        return json.dumps(
            {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {"code": code, "message": message},
            },
            ensure_ascii=False,
        )


def _read_message() -> tuple[str | None, bool]:
    """Read one JSON-RPC message; return (message, used_content_length)."""
    first = sys.stdin.buffer.readline()
    if not first:
        return None, False
    if not first.strip().lower().startswith(b"content-length"):
        return first.decode("utf-8").strip(), False  # newline-delimited JSON
    length = int(first.split(b":", 1)[1].strip())
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None, True
        if not line.strip():
            break
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1].strip())
    if length <= 0:
        return None, True
    if length > MAX_MESSAGE_SIZE:
        remaining = length
        while remaining > 0:
            chunk = sys.stdin.buffer.read(min(remaining, 65536))
            if not chunk:
                break
            remaining -= len(chunk)
        return "", True
    data = b""
    while len(data) < length:
        chunk = sys.stdin.buffer.read(length - len(data))
        if not chunk:
            break
        data += chunk
    if len(data) != length:
        return "", True
    return data.decode("utf-8"), True


def _write_message(text: str, framed: bool) -> None:
    body = text.encode("utf-8")
    if framed:
        sys.stdout.buffer.write(
            b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body
        )
    else:
        sys.stdout.buffer.write(body + b"\n")
    sys.stdout.buffer.flush()


def _build_engine(
    db_path: str | None = None,
    embedder: str = "none",
    embedding_model: str | None = None,
    embedding_base_url: str | None = None,
) -> MemoryEngine:
    if db_path:
        db_path = os.path.abspath(os.path.expanduser(db_path))
    dense = make_embedder(
        embedder,
        model=embedding_model,
        base_url=embedding_base_url,
        cache_path=(db_path + ".cache") if db_path else ":memory:",
    )
    engine = MemoryEngine(
        db_path,
        embedder=dense,
        index_embedder=dense,
        vector_index=VectorIndex((db_path + ".vec") if db_path else ":memory:")
        if dense
        else None,
    )
    return engine


def run_stdio(
    db_path: str | None = None,
    expose: str = "advanced",
    embedder: str = "none",
    embedding_model: str | None = None,
    embedding_base_url: str | None = None,
) -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    engine = _build_engine(
        db_path, embedder, embedding_model, embedding_base_url
    )
    server = MCPServer(engine, expose=expose)
    try:
        while True:
            message, framed = _read_message()
            if message is None:
                break
            response = server.handle_line(message)
            if response is not None:
                _write_message(response, framed)
    finally:
        engine.close()


def build_http_server(
    engine: MemoryEngine | None = None,
    expose: str = "advanced",
    host: str = "127.0.0.1",
    port: int = 0,
) -> http.server.ThreadingHTTPServer:
    """Build an MCP Streamable-HTTP server (POST-only, stdlib)."""
    mcp = MCPServer(engine or MemoryEngine(), expose=expose)
    sessions: set[str] = set()

    class _Handler(http.server.BaseHTTPRequestHandler):
        server_version = "MnemosisMCP"

        def _headers(self, session: str | None = None) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("MCP-Protocol-Version", PROTOCOL_VERSION)
            if session:
                self.send_header("Mcp-Session-Id", session)

        def _send_json(
            self,
            payload: dict,
            status: int = 200,
            session: str | None = None,
        ) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self._headers(session)
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header(
                "Access-Control-Allow-Methods", "POST, GET, OPTIONS"
            )
            self.send_header(
                "Access-Control-Allow-Headers",
                "Content-Type, Mcp-Session-Id, Authorization",
            )
            self.end_headers()

        def do_GET(self) -> None:
            # POST-only Streamable HTTP: SSE streaming is intentionally
            # not implemented; clients fall back to POST responses.
            self.send_response(405)
            self._headers()
            self.end_headers()

        def do_POST(self) -> None:
            session = self.headers.get("Mcp-Session-Id")
            if session:
                sessions.add(session)
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length <= 0 or length > MAX_MESSAGE_SIZE:
                self._send_json(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error: bad Content-Length",
                        },
                    },
                    400,
                    session,
                )
                return
            raw = self.rfile.read(length)
            try:
                message = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Parse error"},
                    },
                    400,
                    session,
                )
                return
            response_text = mcp.handle_line(
                json.dumps(message, ensure_ascii=False)
            )
            if response_text is None:  # notification
                self.send_response(202)
                self._headers(session)
                self.end_headers()
                return
            response = json.loads(response_text)
            new_session = session
            if message.get("method") == "initialize":
                new_session = uuid.uuid4().hex
                sessions.add(new_session)
            self._send_json(response, 200, new_session)

        def log_message(self, format: str, *args: Any) -> None:
            _LOG.debug("http: " + format, *args)

    return http.server.ThreadingHTTPServer((host, port), _Handler)


def run_http(
    db_path: str | None = None,
    expose: str = "advanced",
    embedder: str = "none",
    embedding_model: str | None = None,
    embedding_base_url: str | None = None,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Run the MCP server over Streamable HTTP (POST-only)."""
    engine = _build_engine(
        db_path, embedder, embedding_model, embedding_base_url
    )
    server = build_http_server(engine, expose=expose, host=host, port=port)
    print(
        f"mnemosis-mcp listening on http://{host}:{server.server_port} "
        f"(POST /, MCP Streamable HTTP)",
        flush=True,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
        engine.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mnemosis-mcp",
        description="Mnemosis MCP server (JSON-RPC over stdio)",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="SQLite path for persistent memory (default: in-memory)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"mnemosis-mcp {_MNEMOSIS_VERSION}",
    )
    parser.add_argument(
        "--expose",
        choices=("advanced", "experimental"),
        default="advanced",
        help=(
            "advanced: hide experimental tools from tools/list "
            "(default); experimental: show all 100+ tools"
        ),
    )
    parser.add_argument(
        "--embedder",
        choices=("none", "ollama", "openai"),
        default="none",
        help=(
            "enable dense semantic recall: ollama (local /api/embed) or "
            "openai (set MNEMOSIS_EMBEDDING_API_KEY)"
        ),
    )
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument("--embedding-base-url", default=None)
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="stdio (local process) or http (Streamable HTTP for remote)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    common = {
        "db_path": args.db,
        "expose": args.expose,
        "embedder": args.embedder,
        "embedding_model": args.embedding_model,
        "embedding_base_url": args.embedding_base_url,
    }
    if args.transport == "http":
        run_http(**common, host=args.host, port=args.port)
    else:
        run_stdio(**common)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "EXPERIMENTAL_TOOLS",
    "TOOL_DEFINITIONS",
    "MCPServer",
    "build_http_server",
    "main",
    "run_http",
    "run_stdio",
]
