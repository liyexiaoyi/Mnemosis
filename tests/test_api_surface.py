"""Public API contract: what Mnemosis promises to stable users.

These assertions mirror docs/roadmap.md's 1.0 core-commitment table. If a
core method or export is renamed/removed, this test fails first.
"""

from __future__ import annotations

import dataclasses
import inspect
import re
import typing
import unittest

import mnemosis
from mnemosis import MemoryEngine
from mnemosis.mcp_tools import CORE_TOOLS, EXPERIMENTAL_TOOLS, TOOL_DEFINITIONS


class ApiSurfaceTests(unittest.TestCase):
    def test_top_level_exports(self) -> None:
        self.assertTrue(
            hasattr(mnemosis, "__all__"), "Module must define __all__"
        )
        required = {
            "MemoryEngine",
            "fused_recall",
            "MemoryItem",
            "MemoryKind",
            "MnemosisError",
            "RecallResult",
            "SourceRecord",
            "SourceType",
        }
        # 1.0 contract: lock the exact public surface; additions in 1.x are
        # deliberate and must update this test first.
        self.assertEqual(set(mnemosis.__all__), required)
        self.assertTrue(callable(mnemosis.fused_recall))
        try:
            fused_sig = inspect.signature(mnemosis.fused_recall)
        except (TypeError, ValueError):
            self.fail("fused_recall must remain introspectable")
        parameters = fused_sig.parameters
        # Contract note: parameter names (engine/query) are part of the 1.0
        # surface and must not be renamed.
        self.assertIn("engine", parameters)
        self.assertIn("query", parameters)
        try:
            hints = typing.get_type_hints(mnemosis.fused_recall)
            ret_type = hints.get("return", fused_sig.return_annotation)
        except (NameError, TypeError):
            ret_type = fused_sig.return_annotation
        def _type_names(tp: object) -> set[str]:
            names: set[str] = set()
            if isinstance(tp, str):
                names.update(re.findall(r"\b[A-Za-z_]\w*\b", tp))
            elif hasattr(tp, "__name__"):
                names.add(str(tp.__name__))
            for arg in typing.get_args(tp):
                names.update(_type_names(arg))
            return names

        self.assertIn(
            "RecallResult", _type_names(ret_type),
            "fused_recall return type must involve RecallResult",
        )

    def test_version_format(self) -> None:
        self.assertRegex(
            mnemosis.__version__, r"^\d+\.\d+\.\d+([a-zA-Z0-9.+-]+)?$"
        )

    def test_core_engine_methods(self) -> None:
        core_methods = [
            "remember", "remember_many", "remember_turn",
            "recall", "recall_fused", "check", "sleep",
            "update", "forget", "restore", "purge",
            "export_memories", "import_memories",
            "review_due", "review", "working_set", "stats",
        ]
        missing = [
            name
            for name in core_methods
            if not inspect.isroutine(getattr(MemoryEngine, name, None))
        ]
        # Contract note: core methods are callables, not properties; a future
        # refactor must not convert them into property accessors.
        self.assertEqual(missing, [])
        init_params = inspect.signature(MemoryEngine).parameters
        # memory_file is locked to match the CLI --db flag and README examples.
        self.assertIn("memory_file", init_params)
        # Lifecycle contract (kept separate from the core method list above).
        self.assertTrue(inspect.isroutine(getattr(MemoryEngine, "close", None)))
        self.assertTrue(hasattr(MemoryEngine, "__enter__"))
        self.assertTrue(hasattr(MemoryEngine, "__exit__"))

    def test_enum_members_and_error_base(self) -> None:
        from mnemosis import MemoryKind, MnemosisError, SourceType

        self.assertIn(MemoryKind.EPISODIC, MemoryKind)
        self.assertIn(MemoryKind.SEMANTIC, MemoryKind)
        self.assertEqual(MemoryKind.EPISODIC.value, "episodic")
        self.assertEqual(MemoryKind.SEMANTIC.value, "semantic")
        for origin in (SourceType.USER, SourceType.DOCUMENT,
                       SourceType.AGENT, SourceType.INFERENCE):
            self.assertIn(origin, SourceType)
        self.assertEqual(SourceType.USER.value, "user")
        self.assertEqual(SourceType.DOCUMENT.value, "document")
        self.assertEqual(SourceType.AGENT.value, "agent")
        self.assertEqual(SourceType.INFERENCE.value, "inference")
        self.assertTrue(issubclass(MnemosisError, Exception))

    def test_dataclass_contracts(self) -> None:
        from mnemosis import MemoryItem, SourceRecord

        self.assertTrue(
            dataclasses.is_dataclass(MemoryItem),
            "MemoryItem must remain a dataclass",
        )
        memory_item_fields = {f.name for f in dataclasses.fields(MemoryItem)}
        self.assertTrue(
            {"id", "content", "kind", "source"}.issubset(memory_item_fields)
        )
        self.assertTrue(
            dataclasses.is_dataclass(SourceRecord),
            "SourceRecord must remain a dataclass",
        )
        source_fields = {f.name for f in dataclasses.fields(SourceRecord)}
        self.assertTrue({"origin", "trust"}.issubset(source_fields))

    def test_recall_result_contract(self) -> None:
        from mnemosis import RecallResult

        self.assertTrue(
            dataclasses.is_dataclass(RecallResult),
            "RecallResult must remain a dataclass",
        )
        recall_fields = {f.name for f in dataclasses.fields(RecallResult)}
        self.assertTrue(
            {"item", "score", "reasons"}.issubset(recall_fields)
        )

    def test_mcp_tier_coherence(self) -> None:
        def _tool_name(tool: object) -> str | None:
            if isinstance(tool, str):
                return tool
            if isinstance(tool, dict):
                return tool.get("name")
            return getattr(tool, "name", None)

        if isinstance(TOOL_DEFINITIONS, dict):
            schema_names = set()
            for key, value in TOOL_DEFINITIONS.items():
                name = _tool_name(value)
                self.assertIsNotNone(
                    name, f"tool {key!r} is missing a 'name'"
                )
                self.assertEqual(name, key, "dict key must equal tool name")
                schema_names.add(name)
            self.assertEqual(
                len(TOOL_DEFINITIONS),
                len(schema_names),
                "found duplicate tool names in dict values",
            )
        else:
            raw_names = list(map(_tool_name, TOOL_DEFINITIONS))
            self.assertNotIn(
                None, raw_names, "found tool(s) missing a 'name' key/attribute"
            )
            schema_names = set(raw_names)
            self.assertEqual(
                len(TOOL_DEFINITIONS),
                len(schema_names),
                "found duplicate tool names",
            )
        core_names = list(map(_tool_name, CORE_TOOLS))
        self.assertNotIn(
            None, core_names, "found core tool(s) missing a 'name'"
        )
        core_set = set(core_names)
        experimental_names = list(map(_tool_name, EXPERIMENTAL_TOOLS))
        self.assertNotIn(
            None, experimental_names,
            "found experimental tool(s) missing a 'name'",
        )
        experimental_set = set(experimental_names)
        # 1.0 baseline: 130 tools; 1.x may grow without breaking this contract.
        self.assertGreaterEqual(len(TOOL_DEFINITIONS), 130)
        self.assertLessEqual(len(TOOL_DEFINITIONS), 10_000)  # sanity ceiling
        self.assertEqual(len(TOOL_DEFINITIONS), len(schema_names))
        self.assertGreaterEqual(len(CORE_TOOLS), 16)  # baseline may grow
        self.assertGreaterEqual(len(EXPERIMENTAL_TOOLS), 32)  # baseline may grow
        # CORE (16) + EXPERIMENTAL (32) = 48; the remaining 82 tools form the
        # implicit "advanced" tier shown by --expose advanced (default).
        self.assertTrue(core_set.issubset(schema_names))
        self.assertTrue(experimental_set.issubset(schema_names))
        self.assertFalse(core_set & experimental_set)


if __name__ == "__main__":
    unittest.main()
