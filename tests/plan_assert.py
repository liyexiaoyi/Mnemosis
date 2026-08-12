"""Query-plan assertion helpers for SQLite EXPLAIN output.

SQLite versions differ in wording (``SEARCH``/``TABLE``, ``USING INDEX``/
``USING COVERING INDEX``), so CI asserts on stable features instead of
exact strings: the lookup must go through an index with the expected name
and must not scan the target table.
"""


def assert_plan_uses_index(
    testcase,
    plan: str,
    index_name: str,
    *,
    alias: str = "m",
    table: str | None = None,
) -> None:
    testcase.assertIn("USING INDEX", plan, f"plan should use an index: {plan}")
    testcase.assertIn(
        index_name, plan, f"plan should use {index_name}: {plan}"
    )
    testcase.assertNotIn(
        f"SCAN {alias}", plan, f"plan must not scan {alias}: {plan}"
    )
    if table is not None:
        testcase.assertNotIn(
            f"SCAN {table}", plan, f"plan must not scan {table}: {plan}"
        )
