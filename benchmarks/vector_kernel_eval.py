"""Paired local vector benchmark; setup excluded, ranks checked before timing.

Run with NumPy installed and OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1.
The legacy kernels are loaded from a trusted local pre-change source ZIP.
This evaluates exact vector search, not answer quality or default LSH recall.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time
from types import MethodType
from unittest.mock import patch
import zipfile

from bench_utils import assert_local_mnemosis, pin_local_src

pin_local_src()
assert_local_mnemosis()
import numpy as np
import mnemosis.vector_index as module
from mnemosis.vector_index import VectorIndex


def paired(before, after, *, repeats=1, rounds=7, parity=True, before_context=nullcontext):
    with before_context():
        left = before()
    right = after()
    if parity:
        assert left == right, 'legacy and new results differ before timing'
    records = []
    for round_id in range(rounds):
        labels = ('before', 'after') if round_id % 2 == 0 else ('after', 'before')
        for label in labels:
            fn = before if label == 'before' else after
            # Import blocking is fixture setup, excluded from both clocks.
            with (before_context() if label == 'before' else nullcontext()):
                cpu = time.process_time_ns()
                wall = time.perf_counter_ns()
                for _ in range(repeats):
                    result = fn()
                elapsed = (time.perf_counter_ns() - wall) / repeats / 1e6
                cpu_elapsed = (time.process_time_ns() - cpu) / repeats / 1e6
            if parity:
                assert result == left
            records.append(dict(round=round_id, variant=label, wall_ms=elapsed,
                                cpu_ms=cpu_elapsed, repeats=repeats))
    medians = {label: statistics.median(r['wall_ms'] for r in records
                                       if r['variant'] == label)
               for label in ('before', 'after')}
    return dict(samples=records, medians_ms=medians,
                speedup=medians['before'] / medians['after'],
                latency_reduction_pct=100 * (1 - medians['after'] / medians['before']))


def old_kernels(archive):
    with zipfile.ZipFile(archive) as z:
        source = z.read('src/mnemosis/vector_index.py').decode('utf-8-sig')
    cls = next(n for n in ast.parse(source).body
               if isinstance(n, ast.ClassDef) and n.name == 'VectorIndex')
    nodes = [n for n in cls.body if isinstance(n, ast.FunctionDef)
             and n.name in ('_rerank', '_rerank_matrix')]
    assert len(nodes) == 2
    namespace = dict(module.__dict__)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(archive), 'exec'), namespace)
    return {n.name: namespace[n.name] for n in nodes}, hashlib.sha256(source.encode()).hexdigest()


def state(index):
    digest = hashlib.sha256()
    for table in ('meta', 'vectors', 'buckets'):
        for row in index._conn.execute(f'SELECT * FROM {table} ORDER BY 1, 2'):
            for value in row:
                payload = value if isinstance(value, bytes) else repr(value).encode()
                digest.update(len(payload).to_bytes(8, 'little'))
                digest.update(payload)
    return digest.hexdigest()


def run(args):
    legacy, legacy_hash = old_kernels(args.baseline)
    current = {name: getattr(VectorIndex, name) for name in legacy}
    report = dict(scope='synthetic exact vector queries; not quality or competitor ranking',
                  python=sys.version, platform=platform.platform(), numpy=np.__version__,
                  numpy_path=np.__file__,
                  threads={k: os.getenv(k) for k in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')},
                  seed=20261006, rounds=args.rounds,
                  baseline_source_sha256=legacy_hash,
                  current_source_sha256=hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),
                  baseline_zip_sha256=hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
                  setup_excluded=True, cache='warm application matrix/rows',
                  caveats=['OS caches and other background load not controlled',
                           'float32 NumPy and Python scalar precision/tie policies already differ',
                           '100k scalar comparison forces exact scan; default pure path may use LSH',
                           'SQL vectors inserted directly; not an ingestion performance benchmark'],
                  cases=[])
    for n, dim in ((1000, 32), (10000, 128), (100000, 128)):
        rng = np.random.default_rng(20261006 + n)
        matrix = rng.normal(size=(n, dim)).astype(np.float32)
        query = rng.normal(size=dim).astype(np.float32).tolist()
        ids = [f'm{i:06d}' for i in range(n)]
        rows = [(ident, matrix[i].tobytes()) for i, ident in enumerate(ids)]
        fast = VectorIndex(dim=dim, full_scan_threshold=n)
        with patch.dict(sys.modules, {'numpy': None}):
            scalar = VectorIndex(dim=dim, full_scan_threshold=n)
        try:
            for engine in (fast, scalar):
                engine._conn.executemany('INSERT INTO vectors VALUES (?,?)', rows)
                engine._conn.commit()
            assert fast._numpy_available and not scalar._numpy_available
            initial_state = state(fast)
            fast.search(query, top_k=5)
            with patch.dict(sys.modules, {'numpy': None}):
                scalar.search(query, top_k=5)
            assert fast._matrix_cache[1] is not None and scalar._matrix_cache[1] is None
            def search_with(kernels, top_k):
                for name, fn in kernels.items():
                    setattr(fast, name, MethodType(fn, fast))
                return fast.search(query, top_k=top_k)
            for top_k in (5, 20):
                case = dict(kind='warm_search_sort_change', n=n, dim=dim, top_k=top_k,
                            exact_result_and_score_parity=True)
                case.update(paired(lambda: search_with(legacy, top_k),
                                   lambda: search_with(current, top_k),
                                   repeats=25 if n < 100000 else 10, rounds=args.rounds))
                report['cases'].append(case)
            cold = dict(kind='uncached_candidate_rerank_sort_change', n=n, dim=dim, top_k=5,
                        exact_result_and_score_parity=True)
            cold.update(paired(lambda: legacy['_rerank'](fast, rows, query, 5),
                               lambda: current['_rerank'](fast, rows, query, 5),
                               repeats=3, rounds=args.rounds))
            report['cases'].append(cold)
            def scalar_search():
                return scalar.search(query, top_k=5)
            with patch.dict(sys.modules, {'numpy': None}):
                expected_scalar = scalar_search()
            expected_fast = search_with(current, 5)
            rank_match = [i for i, _ in expected_scalar] == [i for i, _ in expected_fast]
            # Compare matching IDs even if their order differs.
            old_scores, new_scores = dict(expected_scalar), dict(expected_fast)
            common_ids = old_scores.keys() & new_scores.keys()
            case = dict(kind='existing_scalar_vs_optional_numpy', n=n, dim=dim, top_k=5,
                        rank_match_on_fixture=rank_match, common_topk_ids=len(common_ids),
                        max_score_error=max(abs(old_scores[i] - new_scores[i]) for i in common_ids),
                        before='existing scalar fallback', after='NumPy plus new Top-k',
                        forced_full_scan_threshold=n)
            case.update(paired(scalar_search, lambda: fast.search(query, top_k=5),
                               rounds=args.rounds, parity=False,
                               before_context=lambda: patch.dict(sys.modules, {'numpy': None})))
            report['cases'].append(case)
            assert state(fast) == state(scalar) == initial_state
            case['sql_state_unchanged'] = True
            print(json.dumps(dict(n=n, completed=True)), flush=True)
        finally:
            fast.close()
            scalar.close()
    # Worst-case tie fallback and non-finite input overhead, isolated from dot product.
    for fixture in ('unique', 'cutoff_tie', 'all_equal', 'nan'):
        scores = np.random.default_rng(42).normal(size=100000).astype(np.float32)
        if fixture == 'cutoff_tie': scores[:24] = 10
        elif fixture == 'all_equal': scores[:] = 1
        elif fixture == 'nan': scores[3] = np.nan
        old = lambda: np.argsort(-scores)[:5].tolist()
        new = lambda: module._top_score_indices(np, scores, 5).tolist()
        case = dict(kind='selection_only', fixture=fixture, n=len(scores), top_k=5,
                    exact_index_parity=True)
        case.update(paired(old, new, repeats=30, rounds=args.rounds))
        report['cases'].append(case)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True,
                        help='Trusted local pre-change repository ZIP')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=7)
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error('--rounds must be positive')
    result = run(args)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for case in result['cases']:
        print(case['kind'], case.get('n'), case.get('top_k'), case.get('fixture'),
              case['medians_ms'], 'speedup', case['speedup'])
