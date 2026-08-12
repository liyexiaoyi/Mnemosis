"""CI performance gate for SQLite bulk id lookups.

Builds a synthetic 20k-row store in memory and times get_many at 100/500/
2000 ids. Thresholds are deliberately generous (100-1000x headroom over the
measured ~1/6/30ms) so they only catch catastrophic constant regressions
(e.g. the 324ms-per-70-ids status-index scan) and stay stable on shared CI
runners. The query-plan unit test guards the *plan*; this gate guards the
*constants*.
"""

from __future__ import annotations

import os
import sys
import time

_SRC = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)
sys.path.insert(0, _SRC)

from mnemosis.backend import SQLiteBackend
from mnemosis.types import (
    MemoryItem,
    MemoryKind,
    MemoryStatus,
    SourceRecord,
    SourceType,
)

_CEILINGS_MS = {100: 300.0, 500: 700.0, 2000: 2500.0}
_ACTIVE_ROWS = 20_000
_RECYCLED_ROWS = 500


def _build_backend() -> SQLiteBackend:
    backend = SQLiteBackend(":memory:")
    user = SourceRecord(origin=SourceType.USER)
    active = [
        MemoryItem(
            content=f"perf memory {index} alpha beta",
            kind=MemoryKind.EPISODIC,
            source=user,
            status=MemoryStatus.ACTIVE,
        )
        for index in range(_ACTIVE_ROWS)
    ]
    recycled = [
        MemoryItem(
            content=f"recycled perf memory {index}",
            kind=MemoryKind.EPISODIC,
            source=user,
            status=MemoryStatus.RECYCLED,
        )
        for index in range(_RECYCLED_ROWS)
    ]
    backend.add_many(active)
    backend.add_many(recycled)
    return backend


def main() -> int:
    backend = _build_backend()
    ids = [item.id for item in backend.list(limit=2000)]
    recycled_id = backend.list(
        status=MemoryStatus.RECYCLED, limit=1
    )[0].id
    failures: list[str] = []
    _results: list[tuple[int, float]] = []
    for count in (100, 500, 2000):
        sample = ids[:count] + [recycled_id]
        backend.get_many(sample)  # warm
        best = float("inf")
        for _ in range(3):
            start = time.perf_counter()
            items = backend.get_many(sample)
            best = min(best, (time.perf_counter() - start) * 1000)
            if len(items) != count:
                raise RuntimeError(
                    f"expected {count} items, got {len(items)}"
                )
            if recycled_id in {item.id for item in items}:
                raise RuntimeError("recycled memory leaked through get_many")
        ceiling = _CEILINGS_MS[count]
        status = "OK" if best <= ceiling else "FAIL"
        print(f"get_many {count}: best {best:.2f} ms (ceiling {ceiling:.0f}) {status}")
        _results.append((count, best))
        if best > ceiling:
            failures.append(f"{count} ids took {best:.2f} ms")
    backend.close()
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(
                "## get_many performance gate\n\n"
                "| ids | best ms | ceiling ms |\n|---|---|---|\n"
            )
            for count, best in _results:
                handle.write(
                    f"| {count} | {best:.2f} | {_CEILINGS_MS[count]:.0f} |\n"
                )
    if failures:
        print("PERF GATE FAILED:", "; ".join(failures))
        return 1
    print("PERF GATE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
