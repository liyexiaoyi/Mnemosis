"""Run every capability eval and report the pass rate (round 97).

Discovers ``*_eval.py`` scripts, runs each in a subprocess (local-only,
cloud-model evals excluded), reads the JSON result's ``all_ok`` and writes
one summary JSON. Use this before every period matrix as a full-suite
regression check.
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time

_BENCH = os.path.dirname(os.path.abspath(__file__))
_EXCLUDE = {"codex_as_model_eval.py", "mcp_cloud_eval.py"}


def main() -> int:
    files = sorted(
        path
        for path in glob.glob(os.path.join(_BENCH, "*_eval.py"))
        if os.path.basename(path) not in _EXCLUDE
    )
    results = []
    for path in files:
        name = os.path.splitext(os.path.basename(path))[0]
        t0 = time.perf_counter()
        ok = False
        error = None
        status = "fail"
        try:
            subprocess.run(
                [sys.executable, path],
                cwd=_BENCH,
                check=True,
                capture_output=True,
                timeout=900,
            )
            out_path = os.path.join(_BENCH, "results", f"{name}.json")
            if not os.path.exists(out_path):
                status = "no_all_ok"
            else:
                with open(out_path, encoding="utf-8") as handle:
                    data = json.load(handle)
                if "all_ok" not in data:
                    status = "no_all_ok"
                else:
                    ok = bool(data.get("all_ok"))
                    status = "ok" if ok else "fail"
        except Exception as exc:  # noqa: BLE001 - report any failure
            error = f"{type(exc).__name__}: {exc}"
        results.append(
            {
                "eval": os.path.basename(path),
                "status": status,
                "all_ok": ok if status == "ok" else None,
                "seconds": round(time.perf_counter() - t0, 1),
                "error": error,
            }
        )
        print(
            f"{os.path.basename(path)}: {status.upper()}",
            flush=True,
        )
    passed = sum(1 for r in results if r["status"] == "ok")
    failed = sum(1 for r in results if r["status"] == "fail")
    verified = sum(1 for r in results if r["status"] in ("ok", "fail"))
    no_all_ok = sum(1 for r in results if r["status"] == "no_all_ok")
    summary = {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "verified": verified,
        "no_all_ok": no_all_ok,
        "all_ok": passed == verified,
        "results": results,
    }
    out = os.path.join(_BENCH, "results", "run_all_evals.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(
        f"summary: {passed}/{verified} verified passed, "
        f"{no_all_ok} legacy without all_ok, all_ok={summary['all_ok']}",
        flush=True,
    )
    return 0 if summary["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
