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
import math
import os
import platform
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
_ITERATIONS = 10
_HISTORY_KEEP = 100
_BASELINE_MIN = 3
_BASELINE_MAX = 10
_AUTO_RESET_STREAK = 5
_RESET_COOLDOWN_HOURS = 24.0
_WARN_RATIO = 2.5
_MIN_WARN_MS = {100: 5.0, 500: 20.0, 2000: 80.0}
_P95_WARN_RATIO = 1.2
_MIN_P95_WARN_MS = {100: 2.0, 500: 8.0, 2000: 30.0}
_GRADUAL_MIN_RUNS = 6
_GRADUAL_WINDOW = 8
_GRADUAL_SLOPE_MS = {100: 0.05, 500: 0.2, 2000: 1.0}
_GRADUAL_TOTAL_MS = {100: 0.2, 500: 1.0, 2000: 4.0}
_RESET_ENV = "MNEMOSIS_PERF_RESET"
_SUMMARY_ENV = "MNEMOSIS_PERF_SUMMARY_PATH"
_STATS_ENV = "MNEMOSIS_PERF_STATS_PATH"
_DEFAULT_STATS_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "results",
        "get_many_stats.json",
    )
)
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
        "run_count": 0,
        "last_reset_ts": {},
        "runner": "",
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
            "run_count": 0,
            "last_reset_ts": {},
            "runner": "",
        }
    if isinstance(data, dict):
        data.setdefault("runs", [])
        data.setdefault("baselines", {})
        data.setdefault("warn_streaks", {})
        data.setdefault("reset_history", [])
        data.setdefault("run_count", 0)
        data.setdefault("last_reset_ts", {})
        data.setdefault("runner", "")
        data.pop("last_reset_run", None)
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


def _cooldown_elapsed(
    last_reset_ts: str | None,
    now_iso: str,
    hours: float,
) -> bool:
    """True when no recorded reset, or it happened at least `hours` ago."""
    if not last_reset_ts:
        return True
    try:
        last = datetime.fromisoformat(last_reset_ts)
        now = datetime.fromisoformat(now_iso)
        return (now - last).total_seconds() >= hours * 3600
    except (TypeError, ValueError):
        return True


def _percentile(values: list[float], percent: float) -> float:
    """Nearest-rank percentile over a non-empty list."""
    ordered = sorted(values)
    index = max(0, math.ceil(percent / 100.0 * len(ordered)) - 1)
    return ordered[index]


def _reference_value(
    runs: list[dict], count: int, field: str
) -> float | None:
    """Median of the up-to-3 previous runs for a field (excludes current)."""
    entries = [entry for entry in runs if entry["count"] == count]
    previous = [
        entry.get(field)
        for entry in entries[:-1][-3:]
        if isinstance(entry.get(field), (int, float))
    ]
    if not previous:
        return None
    return statistics.median(previous)


def _is_noisy(load1: float, load5: float, cores: int) -> bool:
    """CI host is likely contended when either load average beats cores."""
    if cores <= 0:
        return False
    return max(load1, load5) > cores


def _p95_warning(
    current_p95: float, reference_p95: float | None, count: int
) -> bool:
    """Long-tail regression: >20% worse than the recent median AND above
    an absolute floor, so tiny jitter on fast lookups never warns."""
    if reference_p95 is None:
        return False
    return (
        current_p95 > reference_p95 * _P95_WARN_RATIO
        and current_p95 > _MIN_P95_WARN_MS[count]
    )


def _slope_ms_per_run(values: list[float]) -> float:
    """Least-squares slope of values over their run index."""
    n = len(values)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    numerator = sum(
        (index - mean_x) * (value - mean_y)
        for index, value in enumerate(values)
    )
    denominator = sum(
        (index - mean_x) ** 2 for index in range(n)
    )
    return numerator / denominator if denominator else 0.0


def _r_squared(values: list[float], slope: float) -> float:
    """Coefficient of determination for the least-squares fit."""
    n = len(values)
    if n < 2:
        return 1.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    predicted = [
        slope * (index - mean_x) + mean_y for index in range(n)
    ]
    ss_res = sum(
        (value - fitted) ** 2
        for value, fitted in zip(values, predicted)
    )
    ss_tot = sum((value - mean_y) ** 2 for value in values)
    if ss_tot < 1e-9:
        return 1.0
    return max(0.0, 1.0 - ss_res / ss_tot)


def _gradual_metrics(
    runs: list[dict], count: int
) -> tuple[float, float, float]:
    """Return (slope, r2, total_drift) over the last N runs of best_ms."""
    entries = [
        entry.get("best_ms")
        for entry in runs
        if entry["count"] == count
        and isinstance(entry.get("best_ms"), (int, float))
    ]
    window = entries[-_GRADUAL_WINDOW:]
    if len(window) < _GRADUAL_MIN_RUNS:
        return 0.0, 0.0, 0.0
    slope = _slope_ms_per_run(window)
    r2 = _r_squared(window, slope)
    total_drift = window[-1] - window[0]
    return slope, r2, total_drift


def _gradual_warning(
    runs: list[dict], count: int
) -> tuple[bool, float, float]:
    """Detect slow, monotonic drift that single-run ratios miss.

    Fits a line to the last N runs of best_ms and warns when the slope
    exceeds a per-count floor AND the total drift over the window is
    material AND the fit is credible (R2 > 0.7), so a noisy but flat
    series never trips.
    """
    slope, r2, total_drift = _gradual_metrics(runs, count)
    warned = (
        slope > _GRADUAL_SLOPE_MS[count]
        and total_drift > _GRADUAL_TOTAL_MS[count]
        and r2 > 0.7
    )
    return warned, slope, r2


def _gradual_status(runs: list[dict], count: int) -> str:
    """'warn' (credible drift), 'weak' (drift but poor fit), or 'ok'."""
    slope, r2, total_drift = _gradual_metrics(runs, count)
    if (
        slope > _GRADUAL_SLOPE_MS[count]
        and total_drift > _GRADUAL_TOTAL_MS[count]
    ):
        return "warn" if r2 > 0.7 else "weak"
    return "ok"


def _runner_label() -> str:
    """GitHub-hosted runner identity; local runs collapse to unknown."""
    image = os.environ.get("ImageOS")
    if image:
        return image
    os_name = os.environ.get("RUNNER_OS") or "unknown"
    arch = os.environ.get("RUNNER_ARCH") or "unknown"
    if os_name != "unknown" and arch != "unknown":
        return f"{os_name}-{arch}"
    return f"{platform.system()}-{platform.machine()}"


def _runner_changed(meta: dict, runner: str) -> bool:
    """A different runner makes historical baselines incomparable."""
    return bool(meta.get("runner")) and meta.get("runner") != runner


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
            if recent is not None and _cooldown_elapsed(
                meta.get("last_reset_ts", {}).get(str(count)),
                now_iso,
                _RESET_COOLDOWN_HOURS,
            ):
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
                meta.setdefault("last_reset_ts", {})[
                    str(count)
                ] = now_iso
    return meta, resets, medians, baselines


def _summary_markdown(
    results: list[tuple[int, float, float]],
    medians: dict[int, float],
    baselines: dict[int, float],
    resets: list[int],
    runs: list[dict],
    *,
    noisy_env: bool = False,
    load1: float = 0.0,
    gradual: dict[int, tuple[float, float]] | None = None,
    gradual_weak: dict[int, tuple[float, float]] | None = None,
) -> str:
    lines = [
        "## get_many performance gate",
        "",
        (
            "| ids | best ms | Δ vs prev(3) | median ms | "
            "p95 ms | baseline ms | ceiling ms |"
        ),
        "|---|---|---|---|---|---|---|",
    ]
    for count, best, p95 in results:
        reference = _reference_value(runs, count, "best_ms")
        if reference is None:
            delta = "-"
        else:
            diff = best - reference
            if diff > 0.05:
                delta = f"🔴 +{diff:.2f}"
            elif diff < -0.05:
                delta = f"🟢 {diff:.2f}"
            else:
                delta = "≈"
        median_ms = f"{medians[count]:.2f}" if count in medians else "-"
        baseline_ms = (
            f"{baselines[count]:.2f}" if count in baselines else "-"
        )
        p95_cell = f"{p95:.2f}"
        if _p95_warning(
            p95, _reference_value(runs, count, "p95_ms"), count
        ):
            p95_cell += " ⚠️"
        lines.append(
            f"| {count} | {best:.2f} | {delta} | {median_ms} | "
            f"{p95_cell} | {baseline_ms} | {_CEILINGS_MS[count]:.0f} |"
        )
    if noisy_env:
        lines.append("")
        lines.append(
            f"> ⚠️ noisy CI env: 1-min load {load1:.2f} "
            f"> cores {os.cpu_count() or 1}; treat deltas with caution."
        )
    gradual = gradual or {}
    for count, (slope, r2) in sorted(gradual.items()):
        n_entries = sum(
            1
            for entry in runs
            if entry["count"] == count
            and isinstance(entry.get("best_ms"), (int, float))
        )
        window_size = min(_GRADUAL_WINDOW, n_entries)
        lines.append("")
        lines.append(
            f"> ⚠️ gradual regression on {count} ids: best is drifting "
            f"~{slope:.2f} ms per run (R² {r2:.2f}) over the last "
            f"{window_size} runs."
        )
    gradual_weak = gradual_weak or {}
    for count, (slope, r2) in sorted(gradual_weak.items()):
        lines.append("")
        lines.append(
            f"> ℹ️ low-confidence drift on {count} ids: ~{slope:.2f} ms/run "
            f"(R² {r2:.2f}); monitoring without blocking."
        )
    if resets:
        lines.append("")
        lines.append(
            "**Baseline auto-reset**: "
            + ", ".join(str(count) for count in resets)
            + " ids"
        )
    return "\n".join(lines) + "\n"


def _write_stats(payload: dict) -> str:
    """Persist structured metrics for dashboards (overwrites per run)."""
    path = os.environ.get(_STATS_ENV) or _DEFAULT_STATS_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return path


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
    _results: list[tuple[int, float, float]] = []
    meta = _load_trend()
    if os.environ.get(_RESET_ENV, "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        meta = _empty_meta()
        print("BASELINE RESET: trend history cleared (env requested)")
    runner = _runner_label()
    if _runner_changed(meta, runner):
        print(
            f"RUNNER CHANGED: {meta.get('runner')} -> {runner}; "
            "perf trend reset for the new environment"
        )
        meta = _empty_meta()
    meta["runner"] = runner
    meta["run_count"] = int(meta.get("run_count", 0)) + 1
    history = meta["runs"]
    if not history:
        print(
            "WARNING: trend history is empty; soft baseline warnings are "
            "disabled for this run (first run or cache restore failed)."
        )
    now_iso = datetime.now(timezone.utc).isoformat()
    noisy_env = False
    load1 = 0.0
    try:
        load1, load5, _ = os.getloadavg()
        noisy_env = _is_noisy(load1, load5, os.cpu_count() or 1)
    except (AttributeError, OSError):
        pass
    if noisy_env:
        print(
            f"WARNING: noisy CI env (load {load1:.2f} > "
            f"{os.cpu_count() or 1} cores)"
        )
    for count in (100, 500, 2000):
        sample = ids[:count] + [recycled_id]
        backend.get_many(sample)  # warm
        samples: list[float] = []
        for _ in range(_ITERATIONS):
            start = time.perf_counter()
            items = backend.get_many(sample)
            samples.append((time.perf_counter() - start) * 1000)
            if len(items) != count:
                raise RuntimeError(
                    f"expected {count} items, got {len(items)}"
                )
            if recycled_id in {item.id for item in items}:
                raise RuntimeError("recycled memory leaked through get_many")
        best = min(samples)
        median_ms = statistics.median(samples)
        p95 = _percentile(samples, 95)
        p99 = _percentile(samples, 99)
        ceiling = _CEILINGS_MS[count]
        status = "OK" if best <= ceiling else "FAIL"
        print(
            f"get_many {count}: best {best:.2f} / p95 {p95:.2f} ms "
            f"(ceiling {ceiling:.0f}) {status}"
        )
        _results.append((count, best, p95))
        history.append(
            {
                "ts": now_iso,
                "count": count,
                "best_ms": best,
                "median_ms": median_ms,
                "p95_ms": p95,
                "p99_ms": p99,
                "noisy_env": noisy_env,
                "load1": load1,
            }
        )
        if best > ceiling:
            failures.append(f"{count} ids took {best:.2f} ms")
    backend.close()
    best_by_count = {count: best for count, best, _ in _results}
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
    gradual_warns: dict[int, tuple[float, float]] = {}
    gradual_weak: dict[int, tuple[float, float]] = {}
    for count in _CEILINGS_MS:
        status = _gradual_status(history, count)
        slope, r2, _ = _gradual_metrics(history, count)
        if status == "warn":
            gradual_warns[count] = (slope, r2)
            print(
                f"GRADUAL WARNING: {count} ids drift "
                f"+{slope:.2f} ms/run (R² {r2:.2f}) over the last "
                f"{_GRADUAL_WINDOW} runs"
            )
        elif status == "weak":
            gradual_weak[count] = (slope, r2)
            print(
                f"INFO: {count} ids show high drift "
                f"(+{slope:.2f} ms/run) but low confidence "
                f"(R² {r2:.2f}); monitoring without blocking"
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
    stats_payload = {
        "ts": now_iso,
        "runner": runner,
        "noisy_env": noisy_env,
        "load1": load1,
        "gate_passed": not failures,
        "resets": resets,
        "per_count": {},
    }
    for count, best, p95 in _results:
        slope, r2, drift = _gradual_metrics(history, count)
        reference = _reference_value(history, count, "best_ms")
        stats_payload["per_count"][str(count)] = {
            "best_ms": best,
            "p95_ms": p95,
            "median_ms": medians.get(count),
            "baseline_ms": baselines.get(count),
            "delta_vs_prev3_ms": (
                round(best - reference, 4) if reference is not None else None
            ),
            "gradual_slope_ms_per_run": round(slope, 4),
            "gradual_r2": round(r2, 4),
            "gradual_total_drift_ms": round(drift, 4),
            "gradual_status": _gradual_status(history, count),
            "p95_warn": _p95_warning(
                p95,
                _reference_value(history, count, "p95_ms"),
                count,
            ),
        }
    stats_path = _write_stats(stats_payload)
    print(f"STATS: {stats_path}")
    summary = _summary_markdown(
        _results,
        medians,
        baselines,
        resets,
        history,
        noisy_env=noisy_env,
        load1=load1,
        gradual=gradual_warns,
        gradual_weak=gradual_weak,
    )
    step_summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary_path:
        with open(step_summary_path, "a", encoding="utf-8") as handle:
            handle.write(summary)
    perf_summary_path = os.environ.get(_SUMMARY_ENV)
    if perf_summary_path:
        # Overwrite (not append) so local/Self-hosted reruns never stack
        # duplicate summaries; GITHUB_STEP_SUMMARY above still appends.
        os.makedirs(
            os.path.dirname(perf_summary_path) or ".", exist_ok=True
        )
        with open(perf_summary_path, "w", encoding="utf-8") as handle:
            handle.write(summary)
    if failures:
        print("PERF GATE FAILED:", "; ".join(failures))
        return 1
    print("PERF GATE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
