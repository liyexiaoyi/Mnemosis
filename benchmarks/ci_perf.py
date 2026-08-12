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
_AUTO_RESET_STREAK = 5
_WARN_RATIO = 2.5
_MIN_WARN_MS = {100: 5.0, 500: 20.0, 2000: 80.0}
_RESET_ENV = "MNEMOSIS_PERF_RESET"
_TREND_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "results",
        "get_many_trend.json",
    )
)


def _empty_meta() -> dict:
    return {
        "runs": [],
        "baselines": {},
        "warn_streaks": {},
        "reset_history": [],
    }


def _load_trend() -> dict:
    try:
        with open(_TREND_PATH, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return _empty_meta()
    if isinstance(data, list):
        # Migrate the pre-round-23 list-only format.
        data.sort(key=lambda entry: entry.get("ts", ""))
        return {
            "runs": data,
            "baselines": {},
            "warn_streaks": {},
            "reset_history": [],
        }
    if isinstance(data, dict):
        data.setdefault("runs", [])
        data.setdefault("baselines", {})
        data.setdefault("warn_streaks", {})
        data.setdefault("reset_history", [])
        data["runs"].sort(key=lambda entry: entry.get("ts", ""))
        return data
    return _empty_meta()


def _save_trend(meta: dict) -> None:
    os.makedirs(os.path.dirname(_TREND_PATH), exist_ok=True)
    tmp_path = _TREND_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(meta, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, _TREND_PATH)


def _trim_runs(meta: dict) -> dict:
    """Keep the most recent _HISTORY_KEEP runs per id-count, time-ordered."""
    runs = meta["runs"]
    kept: list[dict] = []
    for count in _CEILINGS_MS:
        entries = [
            entry for entry in runs if entry["count"] == count
        ]
        kept.extend(entries[-_HISTORY_KEEP:])
    kept.sort(key=lambda entry: entry.get("ts", ""))
    meta["runs"] = kept
    meta["reset_history"] = meta.get("reset_history", [])[-50:]
    return meta


def _recent_median_ms(runs: list[dict], count: int) -> float | None:
    values = [
        entry["best_ms"]
        for entry in runs
        if entry["count"] == count
        and entry["best_ms"] <= _CEILINGS_MS[count]
    ][-_HISTORY_KEEP:]
    if len(values) < _BASELINE_MIN:
        return None
    return statistics.median(values)


def _first_runs_median_ms(runs: list[dict], count: int) -> float | None:
    """Fixed baseline: median of the first runs for this id-count."""
    values = [
        entry["best_ms"]
        for entry in runs
        if entry["count"] == count
        and entry["best_ms"] <= _CEILINGS_MS[count]
    ][:_BASELINE_MAX]
    if len(values) < _BASELINE_MIN:
        return None
    return statistics.median(values)


def _update_trend(
    meta: dict,
    best_by_count: dict[int, float],
    *,
    now_iso: str = "",
) -> tuple[dict, list[int], dict[int, float], dict[int, float]]:
    """Update baselines/warn streaks; return (meta, resets, medians, baselines)."""
    history = meta["runs"]
    medians: dict[int, float] = {}
    baselines: dict[int, float] = {}
    for count in _CEILINGS_MS:
        recent = _recent_median_ms(history, count)
        if recent is not None:
            medians[count] = recent
        baseline = meta["baselines"].get(str(count))
        if baseline is None:
            baseline = _first_runs_median_ms(history, count)
            if baseline is not None:
                meta["baselines"][str(count)] = baseline
        if baseline is not None:
            baselines[count] = baseline
    resets: list[int] = []
    for count, baseline_ms in baselines.items():
        current = best_by_count[count]
        ratio = current / baseline_ms if baseline_ms > 0 else 0.0
        warned = (
            ratio > _WARN_RATIO
            and current > _MIN_WARN_MS[count]
        )
        streak = (
            int(meta["warn_streaks"].get(str(count), 0)) + 1
            if warned
            else 0
        )
        meta["warn_streaks"][str(count)] = streak
        if streak >= _AUTO_RESET_STREAK:
            recent = _recent_median_ms(history, count)
            if recent is not None:
                meta["baselines"][str(count)] = recent
                meta["warn_streaks"][str(count)] = 0
                baselines[count] = recent
                resets.append(count)
                meta.setdefault("reset_history", []).append(
                    {
                        "ts": now_iso,
                        "count": count,
                        "old_ms": baseline_ms,
                        "new_ms": recent,
                    }
                )
    return meta, resets, medians, baselines


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
    meta = _load_trend()
    if os.environ.get(_RESET_ENV, "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        meta = _empty_meta()
        print("BASELINE RESET: trend history cleared (env requested)")
    history = meta["runs"]
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
    best_by_count = dict(_results)
    meta, resets, medians, baselines = _update_trend(
        meta, best_by_count, now_iso=now_iso
    )
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
            f"baseline {count}: fixed {baseline_ms:.2f} ms, "
            f"current {current:.2f} ms ({ratio:.2f}x)"
        )
        if ratio > _WARN_RATIO and current > _MIN_WARN_MS[count]:
            print(
                f"WARNING: {count} ids are {ratio:.2f}x slower than the "
                "fixed baseline"
            )
    if resets:
        print(
            "TREND NOTE: baseline(s) auto-reset this run: "
            + ", ".join(str(count) for count in resets)
        )
        for count in resets:
            print(
                f"BASELINE RESET: {count} ids baseline -> "
                f"{baselines[count]:.2f} ms "
                "(5 consecutive soft warnings, no hard gate hit)"
            )
            if os.environ.get("GITHUB_ACTIONS", "") == "true":
                print(
                    f"::warning::get_many baseline auto-reset for {count} "
                    "ids; check recent changes for a legitimate perf step"
                )
    _save_trend(_trim_runs(meta))
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
