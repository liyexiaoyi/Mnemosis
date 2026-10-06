# Calibration statistics: legacy memory-level diagnostic

`engine.meta.calibration_stats(items, now)` retains its `buckets` and `ece`
output keys. It groups heuristic per-memory predictions into five bins.
For bin b with n_b memories, pooled legacy successes H_b and failures F_b:

```text
p_b = mean of the memory predictions in bin b
q_b = (H_b + 1) / (H_b + F_b + 2)
D = sum_b n_b * abs(p_b - q_b) / sum_b n_b
```

Only bins with at least one legacy trial contribute to D. The Beta(1,1)
prior is applied once per pooled bin; predictions and table entries retain
existing rounding. D uses the unrounded pooled rates and means, then rounds
the final value to four decimals. An empty input or no observed bins returns
`ece=0.0` as a compatibility sentinel, not proof of perfect calibration.
Unobserved memories in an observed bin retain their existing contribution
to its prediction mean and population.

This is a smoothed discrepancy over memories and old retrieval/review
counters, not standard prediction-event ECE, verified usefulness, or fact
truth probability. `verified_successes`/`verified_failures` remain separate.
Strict task-level evaluation requires predictions recorded before independent
judged outcomes and a consistent event population. The old calibration
benchmark's raw grouped discrepancy and calibrated per-item discrepancy
have different definitions and cannot establish an ECE improvement by
comparing their magnitudes.

The 2026-10-06 fix weights each bin by its own n_b. Previously the last
input bin's population was reused for every output bin, producing an equal
bin average. The diagnostic repair does not alter confidence predictions,
recall ranking, feedback, counters, persistence, or dependencies.

Hand oracle: two memories predicted .96 with four failures each, and one
predicted .096 with four successes. The rates are .1 and 5/6. The result is
`(2*(.96-.1)+(5/6-.096))/3 = 1843/2250`, rounded `.8191`;
the old diagnostic returned `.7987`.
