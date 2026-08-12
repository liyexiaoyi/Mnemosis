"""Shared helpers for standalone benchmark scripts.

Every standalone benchmark must pin the local ``src/`` on ``sys.path``
BEFORE importing ``mnemosis``; otherwise Python silently falls back to a
stale site-packages install and the numbers describe the wrong code (see
the history note in ``high_df_recall_bench.py``).
"""

from __future__ import annotations

import os
import sys

BENCH = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(BENCH, "..", "src"))


def pin_local_src() -> None:
    """Insert this repo's ``benchmarks/`` and ``src/`` on ``sys.path``."""
    if BENCH not in sys.path:
        sys.path.insert(0, BENCH)
    if SRC not in sys.path:
        sys.path.insert(0, SRC)


def assert_local_mnemosis() -> str:
    """Import mnemosis and fail loudly if it is not the local src copy."""
    import mnemosis

    path = os.path.abspath(mnemosis.__file__)
    if not os.path.normcase(path).startswith(
        os.path.normcase(SRC) + os.sep
    ):
        raise RuntimeError(
            f"FATAL: imported mnemosis from {path!r} instead of local "
            f"src {SRC!r} — refusing to benchmark a stale install."
        )
    return path


def percentile(values: list[float], pct: float) -> float:
    """Linear-interpolated percentile (no nearest-rank collapse)."""
    ordered = sorted(values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    position = pct * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight
