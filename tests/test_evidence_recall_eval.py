"""Evaluation must compare the same pool and count failures in its denominator."""
import importlib
from datetime import datetime, timezone

from evidence_fixtures import FixedAnnotator, FrozenEngine, results


def test_frozen_http_responses_replay_exact_support_and_selected_ids(monkeypatch):
    import json
    import mnemosis.ollama_evidence as ollama
    from test_ollama_evidence import Response, envelope
    bench = importlib.import_module("evidence_recall_eval")
    bodies = iter([{"scope": "finite", "aspects": ["destination", "date"]}, {"decisions": [
        dict(memory_id="A", aspect_id="a0", verdict="supported", quote="Osaka"),
        dict(memory_id="C", aspect_id="a1", verdict="supported", quote="October")]}])
    monkeypatch.setattr(ollama, "urlopen", lambda request, timeout: Response(
        json.dumps(envelope(json.dumps(next(bodies)))).encode()))
    row = bench.run_case(FrozenEngine(), {"q": "where and when?", "expected": [
        "Mina went to Osaka.", "The trip was in October."]}, ollama.OllamaEvidenceAnnotator(),
        now=datetime(2026, 10, 7, 12, tzinfo=timezone.utc), top_k=2)
    replayed = bench.replay_row(row)
    assert {k:v for k,v in replayed.items() if k != "timings"} == {
        k:v for k,v in row["report"].items() if k != "timings"}


def test_abc_pool_is_retrieved_once_and_model_never_receives_gold():
    bench = importlib.import_module("evidence_recall_eval")
    engine, provider = FrozenEngine(), FixedAnnotator()
    question = {"q": "Where and when was Mina's trip?", "expected": [
        "Mina went to Osaka.", "The trip was in October."], "id": "private-gold-id"}
    row = bench.run_case(engine, question, provider,
        now=datetime(2026, 10, 7, 12, tzinfo=timezone.utc), top_k=2)
    assert [kw["top_k"] for _, kw in engine.calls] == [2, 100]
    assert all(kw["read_only"] for _, kw in engine.calls)
    assert row["A"]["metrics"]["all"] is False
    assert row["B"]["metrics"]["all"] is False
    assert row["C"]["metrics"]["all"] is True
    assert [r["item"]["id"] for r in row["candidates"]] == ["A", "B", "C"]
    assert all(call[1] == question["q"] for call in provider.calls)
    assert row["C"]["seconds"] >= row["B"]["pool_seconds"]


def test_audit_counts_all_failures_and_pairs_without_evaluator_helpers():
    audit = importlib.import_module("evidence_recall_audit")
    def row(expected, a, b, c, status):
        pack = lambda texts: {"results": [{"item": {"content": t}} for t in texts], "seconds": .1}
        return {"question": {"expected": expected}, "A": pack(a), "B": pack(b), "C": pack(c),
                "report": {"status": status}, "candidates": [{"item": {"content": t}} for t in b]}
    rows = [row(["x", "y"], ["x"], ["x", "y"], ["x", "y"], "feasible"),
            row(["z"], ["z"], ["z"], [], "annotation_failed"),
            row(["v"], [], [], [], "not_applicable")]
    stats = audit.summarize(rows)
    assert stats["questions"] == 3
    assert stats["systems"]["A"]["all"] == 1
    assert stats["systems"]["B"]["all"] == 2
    assert stats["systems"]["C"]["all"] == 1
    assert stats["C_vs_B"] == {"gains": 0, "losses": 1}
    assert stats["statuses"] == {"feasible": 1, "annotation_failed": 1, "not_applicable": 1}


def test_public_runner_excludes_constructed_case_without_source_index(tmp_path):
    import json
    bench = importlib.import_module("evidence_recall_eval")
    vectors = tmp_path / "vectors.json"; vectors.write_text("{}")
    protocol = tmp_path / "protocol.json"
    protocol.write_text(json.dumps({"embeddings": str(vectors), "now": "2026-10-06T12:00:00+00:00",
        "model": "qwen2.5:3b", "base_url": "http://127.0.0.1:11434"}))
    cases = tmp_path / "cases.json"
    cases.write_text('[{"name":"constructed","questions":[]}]')
    assert bench.main(["--protocol", str(protocol), "--cases", str(cases), "--output", str(tmp_path / "out"),
                       "--mode", "public"]) == 0
