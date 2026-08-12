"""CI performance gate for SQLite bulk id lookups.

Builds a synthetic 20k-row store in memory and times get_many at 100/500/
2000 ids. Thresholds are deliberately generous (100-1000x headroom over the
measured ~1/6/30ms) so they only catch catastrophic constant regressions
(e.g. the 324ms-per-70-ids status-index scan) and stay stable on shared CI
runners. The query-plan unit test guards the *plan*; this gate guards the
*constants*.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone

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
_HISTORY_KEEP = 100
_BASELINE_MIN = 3
_BASELINE_MAX = 10
_TREND_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "results",
        "get_many_trend.json",
    )
)


def _load_history() -> list[dict]:
    try:
        with open(_TREND_PATH, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            return []
        data.sort(key=lambda entry: entry.get("ts", ""))
        return data
    except (OSError, ValueError):
        return []


def _save_history(history: list[dict]) -> None:
    os.makedirs(os.path.dirname(_TREND_PATH), exist_ok=True)
    tmp_path = _TREND_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(history, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, _TREND_PATH)


def _trim_history(history: list[dict]) -> list[dict]:
    """Keep the most recent _HISTORY_KEEP runs per id-count."""
    trimmed: list[dict] = []
    for count in _CEILINGS_MS:
        entries = [
            entry for entry in history if entry["count"] == count
        ]
        trimmed.extend(entries[-_HISTORY_KEEP:])
    return trimmed


def _baseline_ms(history: list[dict], count: int) -> float | None:
    """Fixed baseline: median of the first runs for this id-count."""
    entries = [
        entry["best_ms"]
        for entry in history
        if entry["count"] == count
        and entry["best_ms"] <= _CEILINGS_MS[count]
    ][:_BASELINE_MAX]
    if len(entries) < _BASELINE_MIN:
        return None
    return statistics.median(entries)


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
    history = _load_history()
    if not history:
        print(
            "WARNING: trend history is empty; soft baseline warnings are "
            "disabled for this run (first run or cache restore failed)."
        )
    now_iso = datetime.now(timezone.utc).isoformat()
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
        history.append({"ts": now_iso, "count": count, "best_ms": best})
        if best > ceiling:
            failures.append(f"{count} ids took {best:.2f} ms")
    backend.close()
    _save_history(_trim_history(history))
    best_by_count = dict(_results)
    medians: dict[int, float] = {}
    baselines: dict[int, float] = {}
    for count, ceiling in _CEILINGS_MS.items():
        values = [
            entry["best_ms"]
            for entry in history
            if entry["count"] == count
            and entry["best_ms"] <= ceiling
        ][-_HISTORY_KEEP:]
        if len(values) >= 3:
            medians[count] = statistics.median(values)
        baseline = _baseline_ms(history, count)
        if baseline is not None:
            baselines[count] = baseline
    for count, median_ms in medians.items():
        current = best_by_count[count]
        ratio = current / median_ms if median_ms > 0 else 0.0
        print(
            f"trend {count}: median {median_ms:.2f} ms, "
            f"current {current:.2f} ms ({ratio:.2f}x)"
        )
    for count, baseline_ms in baselines.items():
        current = best_by_count[count]
        ratio = current / baseline_ms if baseline_ms > 0 else 0.0
        print(
            f"baseline {count}: first-runs median {baseline_ms:.2f} ms, "
            f"current {current:.2f} ms ({ratio:.2f}x)"
        )
        # Slow drift must be caught against the *fixed* baseline: a median
        # over all history would warm up together with the regression.
        if ratio > 2.5 and current > 0.5 * _CEILINGS_MS[count]:
            print(
                f"WARNING: {count} ids are {ratio:.2f}x slower than the "
                "fixed baseline"
            )
    if not baselines:
        print(
            "NOTE: fixed baseline not established yet "
            "(need >= 3 recorded runs per id-count)."
        )
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(
                "## get_many performance gate\n\n"
                "| ids | best ms | median ms | baseline ms | ceiling ms |\n"
                "|---|---|---|---|---|\n"
            )
            for count, best in _results:
                median_ms = (
                    f"{medians[count]:.2f}" if count in medians else "-"
                )
                baseline_ms = (
                    f"{baselines[count]:.2f}"
                    if count in baselines
                    else "-"
                )
                handle.write(
                    f"| {count} | {best:.2f} | {median_ms} | "
                    f"{baseline_ms} | "
                    f"{_CEILINGS_MS[count]:.0f} |\n"
                )
    if failures:
        print("PERF GATE FAILED:", "; ".join(failures))
        return 1
    print("PERF GATE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
