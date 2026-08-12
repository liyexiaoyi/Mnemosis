"""Reusable regression dashboard: run the CI gate and render a Chinese SVG chart.

Zero dependencies (stdlib only). Writes ``benchmarks/results/regression_*.json``
and ``regression_*.svg`` next to the other benchmark outputs.
"""

from __future__ import annotations

import html
import json
import os
import sys
import time

_BENCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BENCH)

import ci_regression


def render_svg(checks: list[tuple[str, bool, str]], title: str) -> str:
    width, row_h, pad = 860, 34, 24
    height = pad * 2 + len(checks) * row_h + 60
    rows = []
    for index, (name, ok, detail) in enumerate(checks):
        y = pad + index * row_h
        color = "#16a34a" if ok else "#dc2626"
        rows.append(
            f'<rect x="20" y="{y}" width="18" height="18" rx="4" fill="{color}"/>'
            f'<text x="48" y="{y + 14}" font-size="15" fill="#111">{html.escape(name)}</text>'
            f'<text x="640" y="{y + 14}" font-size="14" fill="#555" '
            f'text-anchor="end">{html.escape(detail)}</text>'
        )
    body = "".join(rows)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}">'
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>'
        f'<text x="24" y="34" font-size="20" font-weight="bold" fill="#111">'
        f"{html.escape(title)}</text>"
        f"{body}</svg>"
    )


def main() -> int:
    exit_code = ci_regression.main()
    checks = ci_regression._CHECKS
    stamp = time.strftime("%Y%m%d_%H%M%S")
    results_dir = os.path.join(_BENCH, "results")
    os.makedirs(results_dir, exist_ok=True)
    base = os.path.join(results_dir, f"regression_{stamp}")
    with open(base + ".json", "w", encoding="utf-8") as handle:
        json.dump(
            {
                "timestamp": stamp,
                "passed": sum(1 for _, ok, _ in checks if ok),
                "total": len(checks),
                "checks": [
                    {"name": name, "ok": ok, "detail": detail}
                    for name, ok, detail in checks
                ],
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
    title = f"Mnemosis 能力回归看板 {time.strftime('%Y-%m-%d %H:%M')}"
    svg = render_svg(checks, title)
    with open(base + ".svg", "w", encoding="utf-8") as handle:
        handle.write(svg)
    print(f"saved {base}.json / {base}.svg")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
