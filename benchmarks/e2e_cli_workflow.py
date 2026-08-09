"""End-to-end CLI acceptance: the whole memory lifecycle in Chinese.

Runs the real `python -m mnemosis` CLI against a fresh SQLite DB and checks
the accumulated mechanisms work together: zh remember/recall (with zh date
normalization), metacognitive gap check, sleep consolidation, update
(accommodation-ready revision), review scheduling, and stats.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))


def run_cli(db: str, *args: str) -> tuple[str, int]:
    env = dict(os.environ)
    env["PYTHONPATH"] = _SRC + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "mnemosis", "--db", db, *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    if proc.returncode != 0:
        return f"<exit {proc.returncode}> {proc.stderr.strip()}", proc.returncode
    return proc.stdout.strip(), proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__), "results", "e2e_cli_workflow.json"
        ),
    )
    args = parser.parse_args()

    steps: list[dict] = []

    def step(name: str, passed: bool, detail: str) -> None:
        steps.append({"name": name, "passed": passed, "detail": detail})

    tmpdir = tempfile.mkdtemp(prefix="mnemosis_e2e_")
    db = os.path.join(tmpdir, "mem.db")
    try:
        out, _ = run_cli(db, "remember", "阿丽最喜欢的颜色是琥珀色。",
                         "--kind", "semantic", "--cues", "阿丽,颜色")
        step("记住中文事实", "saved" in out, out)
        fact_id = out.split()[1] if "saved" in out else ""

        out, _ = run_cli(db, "recall", "请问阿丽最喜欢的颜色是什么？", "--top-k", "1")
        step("中文回忆（带虚词问题）", "琥珀色" in out, out)

        out, _ = run_cli(db, "remember", "阿丽在2026年3月1日买了笔记本。",
                         "--kind", "episodic", "--cues", "阿丽")
        step("记住中文日期事件", "saved" in out, out)

        out, _ = run_cli(db, "recall", "阿丽 2026-03-01", "--top-k", "1")
        step("跨格式日期回忆（中文存/ISO问）", "笔记本" in out, out)

        out, _ = run_cli(db, "check", "阿丽最喜欢的甜点是什么？")
        step("没聊过不乱说（知识缺口）", "甜点" in out, out)

        out, _ = run_cli(db, "sleep")
        step("睡眠巩固", "promoted" in out or "replayed" in out or "merged" in out,
             out)

        out, _ = run_cli(db, "stats")
        step("统计", "active" in out, out)

        if fact_id:
            out, _ = run_cli(db, "update", fact_id, "--content", "阿丽最喜欢的颜色是靛蓝色。")
            step("更新事实（修订）", "revised" in out.lower() or "updated" in out.lower()
                 or "靛蓝" in out, out)

        out, rc = run_cli(db, "review-due", "--limit", "5")
        step("到期复习清单", rc == 0 and (not out.strip() or "retrievability" in out), out)

        out, _ = run_cli(db, "working-set", "--limit", "5")
        step("工作集", bool(out.strip()), out)

        # MCP (in-process, real MCPServer over the same engine)
        from mnemosis import MemoryEngine
        from mnemosis.mcp_server import MCPServer

        mcp = MCPServer(MemoryEngine())

        def mcp_call(name: str, arguments: dict) -> dict:
            response = mcp.handle_line(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 7,
                        "method": "tools/call",
                        "params": {"name": name, "arguments": arguments},
                    }
                )
            )
            parsed = json.loads(response)
            return json.loads(parsed["result"]["content"][0]["text"])

        out = mcp_call(
            "remember",
            {"content": "小波最喜欢的食物是饺子。", "kind": "semantic",
             "cues": ["小波", "食物"]},
        )
        step("MCP 记住中文事实", "saved" in str(out) or "小波" in str(out), str(out))

        out = mcp_call("recall", {"query": "小波最喜欢的食物是什么？", "top_k": 1})
        step("MCP 中文回忆", "饺子" in str(out), str(out))

        out = mcp_call("check", {"query": "小波最喜欢的运动是什么？"})
        step("MCP 没聊过不乱说", "gaps" in str(out) and "运动" in str(out), str(out))
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    passed = sum(1 for s in steps if s["passed"])
    report = {"steps": steps, "passed": passed, "total": len(steps)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0 if passed == len(steps) else 1


if __name__ == "__main__":
    raise SystemExit(main())
