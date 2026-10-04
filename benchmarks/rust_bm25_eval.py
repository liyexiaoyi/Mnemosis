"""Paired optional Rust/Python BM25 benchmark on identical cloned SQLite input.

All timings are unprofiled and sequential. Index-search measurements include
query tokenization/native conversion; end-to-end also includes revision checks
and fresh MemoryItem reads. No production-percentile or accuracy claims.
"""
from __future__ import annotations
import argparse
import ctypes
import gc
import hashlib
import json
import platform
import sqlite3
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from mnemosis import MemoryEngine
from mnemosis.types import tokenize


def memory():
    if platform.system() != "Windows":
        return {"available": False}
    from ctypes import wintypes
    size = ctypes.c_size_t
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, size) for name in ("peak_working", "working", "peak_paged", "paged",
            "peak_nonpaged", "nonpaged", "commit", "peak_commit")]
    current = ctypes.windll.kernel32.GetCurrentProcess
    current.restype = ctypes.c_void_p
    info = ctypes.windll.psapi.GetProcessMemoryInfo
    info.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), wintypes.DWORD]
    counters = Counters(); counters.cb = ctypes.sizeof(counters)
    if not info(current(), ctypes.byref(counters), counters.cb):
        return {"available": False}
    return dict(working_set_bytes=counters.working, peak_working_set_bytes=counters.peak_working,
                process_commit_charge_bytes=counters.commit)


def state(engine):
    digest = hashlib.sha256()
    for table in ("memories", "links"):
        for row in engine.backend._conn.execute(f"SELECT * FROM {table} ORDER BY 1"):
            digest.update(json.dumps(list(row), ensure_ascii=True, separators=(",", ":")).encode())
    digest.update(json.dumps(engine.get_recall_log(), sort_keys=True).encode())
    return digest.hexdigest()


def equivalent(a, b):
    assert [i for i, _ in a] == [i for i, _ in b], (a, b)
    error = max((abs(sa - sb) for (_, sa), (_, sb) in zip(a, b)), default=0.0)
    assert error <= 1e-12, error
    return error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=7)
    args = parser.parse_args()
    assert args.rounds >= 7
    args.output.mkdir(parents=True, exist_ok=True)
    result_path = args.output / "comparison.json"
    if result_path.exists():
        raise FileExistsError(result_path)
    engines = {}
    with sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True) as source:
        count = source.execute("SELECT COUNT(*) FROM memories WHERE status='active'").fetchone()[0]
        for name in ("python", "rust"):
            path = args.output / f"{name}.sqlite"
            if path.exists():
                raise FileExistsError(path)
            with sqlite3.connect(path) as target:
                source.backup(target)
            engines[name] = MemoryEngine(str(path), bm25_backend=name, auto_warmup=False)
    report = dict(count=count, python=platform.python_version(), platform=platform.platform(),
        rounds=args.rounds, dataset_source=str(args.database.resolve()), cold=[], cases=[],
        memory_scope="combined process holding both indexes; not isolated index allocation",
        complete=False, max_score_error=0.0)
    import _mnemosis_rust
    assert _mnemosis_rust.BUILD_PROFILE == "release", "Release build required"
    report["native_profile"] = _mnemosis_rust.BUILD_PROFILE
    report["native_api"] = _mnemosis_rust.API_VERSION
    report["native_module"] = _mnemosis_rust.__file__
    native_files = list(Path(_mnemosis_rust.__file__).parent.glob("*.pyd")) + list(Path(_mnemosis_rust.__file__).parent.glob("*.so"))
    report["native_binary_sha256"] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in native_files}
    report["started_at_utc"] = datetime.now(timezone.utc).isoformat()
    def save():
        result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    def signature(rows):
        return [(r.item.id, r.score) for r in rows]
    def measured(fn):
        start_cpu = time.process_time(); start = time.perf_counter()
        value = fn()
        return value, (time.perf_counter() - start)*1000, (time.process_time() - start_cpu)*1000
    try:
        baseline = {name: state(engine) for name, engine in engines.items()}
        assert baseline["python"] == baseline["rust"]
        report["baseline_state_sha256"] = baseline["python"]
        rare = f"needle{count-1:06d}"
        for name, engine in engines.items():
            rows, wall, cpu = measured(lambda: engine.recall_bm25(rare, top_k=5))
            assert rows
            report["cold"].append(dict(implementation=name, wall_ms=wall, cpu_ms=cpu, memory=memory()))
        indexes = {name: engine._bm25_cache[2] for name, engine in engines.items()}
        assert indexes["rust"].build_profile == "release"
        excluded = {row[0] for row in engines["python"].backend._conn.execute("SELECT id FROM memories ORDER BY seq, id LIMIT 20")}
        for query_name, query in (("rare", rare), ("common", "tea coffee 私教课")):
            for top_k in (1, 5, 20):
                for excluded_ids in (set(), excluded) if top_k == 5 else (set(),):
                    for scope in ("index_search_with_boundary", "end_to_end"):
                        samples = {name: [] for name in engines}
                        signatures = {}; cpus = {name: [] for name in engines}
                        # One unmeasured warmup per implementation/case.
                        def call(name):
                            if scope == "index_search_with_boundary":
                                return indexes[name].search(query, top_k, excluded_ids)
                            return signature(engines[name].recall_bm25(query, top_k=top_k, exclude_ids=excluded_ids))
                        equivalent(call("python"), call("rust"))
                        for trial in range(args.rounds):
                            order = ("python", "rust") if trial % 2 == 0 else ("rust", "python")
                            for name in order:
                                rows, wall, cpu = measured(lambda: call(name))
                                samples[name].append(wall); cpus[name].append(cpu)
                                if name in signatures:
                                    assert rows == signatures[name]
                                signatures[name] = rows
                            report["max_score_error"] = max(report["max_score_error"], equivalent(signatures["python"], signatures["rust"]))
                        medians = {name: statistics.median(values) for name, values in samples.items()}
                        case = dict(query=query_name, top_k=top_k, exclusions=len(excluded_ids), scope=scope,
                            wall_ms=samples, cpu_ms=cpus, median_ms=medians,
                            speedup=medians["python"]/medians["rust"], results=signatures,
                            memory=memory())
                        if scope == "index_search_with_boundary":
                            terms = sorted(set(tokenize(query)))
                            core_samples = []
                            for _ in range(args.rounds):
                                core_rows, nanoseconds = indexes["rust"].kernel.search_timed(terms, top_k, excluded_ids)
                                assert core_rows == signatures["rust"]
                                core_samples.append(nanoseconds / 1_000_000)
                            case["rust_core_ms"] = core_samples
                            case["rust_core_median_ms"] = statistics.median(core_samples)
                        case["query_text"] = query
                        report["cases"].append(case); save()
                        print(json.dumps({k: case[k] for k in ("query", "top_k", "exclusions", "scope", "median_ms", "speedup")}), flush=True)
        report["read_only_unchanged"] = all(state(engine) == baseline[name] for name, engine in engines.items())
        assert report["read_only_unchanged"]
        target = engines["python"].recall_bm25(rare)[0].item
        edits = {name: [] for name in engines}; writes = {name: [] for name in engines}
        for trial in range(args.rounds):
            for name in (("python", "rust") if trial%2 == 0 else ("rust", "python")):
                engine = engines[name]
                _, wall, _ = measured(lambda: engine.update(target.id, content=target.content + f" revisionpaired{trial}"))
                writes[name].append(wall)
                rows, wall, _ = measured(lambda: signature(engine.recall_bm25(rare)))
                edits[name].append(wall)
                signatures[name] = rows
            equivalent(signatures["python"], signatures["rust"])
        report["edits"] = dict(query_wall_ms=edits, write_wall_ms=writes,
            median_query_ms={name: statistics.median(v) for name, v in edits.items()})
        for name, engine in engines.items():
            incremental = signature(engine.recall_bm25("tea coffee 私教课", top_k=20))
            engine._bm25_cache = None
            rebuilt = signature(engine.recall_bm25("tea coffee 私教课", top_k=20))
            assert incremental == rebuilt
            signatures[name] = rebuilt
        equivalent(signatures["python"], signatures["rust"])
        report["incremental_matches_rebuild"] = True
        report["complete"] = True
        report["completed_at_utc"] = datetime.now(timezone.utc).isoformat(); save()
    finally:
        for engine in engines.values():
            engine.close()
        save()

if __name__ == "__main__":
    main()
