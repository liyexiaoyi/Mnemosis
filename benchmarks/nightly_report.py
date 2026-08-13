"""Collect nightly benchmark JSON summaries into one markdown report.

Reads every ``*.json`` in ``--dir`` (written by build_bench / sleep_bench /
high_df_recall_bench with ``--out``), prints a compact markdown table, writes
it to ``--out``, and exits 1 if any benchmark's gate failed.
"""

from __future__ import annotations

import argparse
import json
import os


def _fmt(value: object, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:g}{suffix}"
    return f"{value}{suffix}"


def _row(name: str, data: dict) -> tuple[str, str, bool | None]:
    gate = data.get("gate_passed")
    if "items_per_s" in data:
        metrics = (
            f"build {_fmt(data.get('build_s'), 's')}, "
            f"{_fmt(data.get('items_per_s'))} items/s, "
            f"peak {_fmt(data.get('peak_python_mb'), 'MB')}"
        )
        return name, metrics, gate
    if "warm" in data:
        warm = data.get("warm", {})
        first = data.get("first_after_build_ms")
        reopened = data.get("cold_start_ms")
        preheated = data.get("warm_reopen_ms")
        p99 = None
        if warm:
            p99 = warm.get("用户", {}).get("p99_ms")
        metrics = (
            f"first {_fmt(first, 'ms')}, "
            f"cold {_fmt(reopened, 'ms')}, "
            f"preheated {_fmt(preheated, 'ms')}, "
            f"warm p99 {_fmt(p99, 'ms')}"
        )
        return name, metrics, gate
    if "steady_median_s" in data:
        post = data.get("post_sleep_recall") or {}
        metrics = (
            f"first sleep {_fmt(data.get('first_sleep_s'), 's')}, "
            f"steady {_fmt(data.get('steady_median_s'), 's')} "
            f"(p99 {_fmt(data.get('steady_p99_s'), 's')}), "
            f"recall p99 {_fmt(post.get('p99_ms'), 'ms')}"
        )
        return name, metrics, gate
    return name, json.dumps(data, ensure_ascii=False)[:160], gate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument(
        "--expected",
        nargs="*",
        default=["build.json", "high_df.json", "sleep.json"],
        help="files that must exist; missing ones fail the report",
    )
    args = parser.parse_args()

    rows = []
    present = set()
    try:
        filenames = sorted(os.listdir(args.dir))
    except OSError:
        filenames = []
    for filename in filenames:
        if not filename.endswith(".json"):
            continue
        present.add(filename)
        path = os.path.join(args.dir, filename)
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            rows.append((filename, f"INVALID JSON: {exc}", False))
            continue
        rows.append(_row(os.path.splitext(filename)[0], data))
    for filename in args.expected:
        if filename not in present:
            rows.append(
                (os.path.splitext(filename)[0], "MISSING (bench crashed?)", False)
            )

    lines = [
        "## Nightly benchmark summary",
        "",
        "| Benchmark | Key metrics | Gate |",
        "|---|---|---|",
    ]
    for name, metrics, gate in rows:
        lines.append(
            f"| {name} | {metrics} | "
            f"{'PASS' if gate else ('FAIL' if gate is False else 'n/a')} |"
        )
    overall = all(gate is not False for _, _, gate in rows)
    lines.append("")
    lines.append(f"Overall: {'PASS' if overall else 'FAIL'}")
    body = "\n".join(lines)
    print(body)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(body + "\n")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
