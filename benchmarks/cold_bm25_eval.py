"""Token parity + paired unprofiled cold BM25 measurements.

The only product change is types.tokenize. Switch the frozen old function and
current function into the same BM25 module to isolate that change while keeping
identical database rows, kernel, backend and cache lifecycle. Deallocation of
previous indexes occurs outside cold timers. OS cache is uncontrolled.
"""
from __future__ import annotations
import argparse
import csv
import gc
import hashlib
import importlib.util
import json
import platform
import sqlite3
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from mnemosis import MemoryEngine, types
import mnemosis.bm25 as bm25
from rust_bm25_eval import memory, state


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--rounds',type=int,default=7)
    args=parser.parse_args();assert args.rounds>=7
    args.output.mkdir(parents=True,exist_ok=True)
    result_path=args.output/'comparison.json'
    if result_path.exists():raise FileExistsError(result_path)
    oracle_path=Path(__file__).resolve().parents[1]/'tests/fixtures/tokenize_a2199c2.py'
    spec=importlib.util.spec_from_file_location('reference_tokenizer',oracle_path)
    reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
    optimized=bm25.tokenize
    functions={'before':reference.tokenize,'after':optimized}
    db=args.output/'memory.sqlite'
    if db.exists():raise FileExistsError(db)
    with sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro',uri=True) as a,sqlite3.connect(db) as b:a.backup(b)
    engines={name:MemoryEngine(str(db),auto_warmup=False,bm25_backend=name) for name in ('python','rust')}
    count=engines['python'].backend.count()
    report={'count':count,'rounds':args.rounds,'python':platform.python_version(),'platform':platform.platform(),
        'started_at_utc':datetime.now(timezone.utc).isoformat(),'cold':[],'warm':[],
        'memory_scope':'process holding one lexical index at each sample; allocator reuse between samples; not exact native heap',
        'baseline_oracle_sha256':hashlib.sha256(oracle_path.read_bytes()).hexdigest(),
        'optimized_types_sha256':hashlib.sha256(Path(types.__file__).read_bytes()).hexdigest(),
        'complete':False,'max_score_error':0.0,
        'comparison_scope':'only tokenizer changes, same engine/kernel/SQLite rows; cache cold, not OS cold'}
    import _mnemosis_rust as native
    assert native.BUILD_PROFILE=='release'
    report['native_profile']=native.BUILD_PROFILE
    report['native_binary_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(native.__file__).parent.glob('*.pyd')}
    def save():result_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def sig(rows):return [(r.item.id,r.score,tuple(r.reasons),r.confident) for r in rows]
    def measure(fn):
        start_cpu=time.process_time();start=time.perf_counter();value=fn()
        return value,(time.perf_counter()-start)*1000,(time.process_time()-start_cpu)*1000
    def compare(a,b):
        assert a==b,(a,b)
    try:
        baseline=state(engines['python'])
        needle=f'needle{count-1:06d}'
        for implementation,engine in engines.items():
            cold={v:[] for v in functions};cpus={v:[] for v in functions}
            warm={query:{v:[] for v in functions} for query in ('rare','common')}
            memories={v:[] for v in functions};signatures={}
            for trial in range(args.rounds):
                order=('before','after') if trial%2==0 else ('after','before')
                for version in order:
                    bm25.tokenize=functions[version]
                    engine._bm25_cache=None;gc.collect()
                    before_memory=memory()
                    rows,wall,cpu=measure(lambda:engine.recall_bm25(needle,top_k=5))
                    assert rows
                    current=sig(rows)
                    if version in signatures:compare(signatures[version],current)
                    signatures[version]=current
                    cold[version].append(wall);cpus[version].append(cpu)
                    memories[version].append({'before':before_memory,'after':memory()})
                    for query_name,query in (('rare',needle),('common','tea coffee 私教课')):
                        warm_rows,warm_wall,_=measure(lambda:engine.recall_bm25(query,top_k=5))
                        key=(version,query_name)
                        if key in signatures:compare(signatures[key],sig(warm_rows))
                        signatures[key]=sig(warm_rows);warm[query_name][version].append(warm_wall)
                    engine._bm25_cache=None
                    print(json.dumps({'count':count,'implementation':implementation,'trial':trial+1,'version':version,'cold_ms':wall}),flush=True)
                compare(signatures['before'],signatures['after'])
                for query_name in ('rare','common'):compare(signatures[('before',query_name)],signatures[('after',query_name)])
            medians={v:statistics.median(values) for v,values in cold.items()}
            report['cold'].append({'implementation':implementation,'wall_ms':cold,'cpu_ms':cpus,'median_ms':medians,
                'speedup':medians['before']/medians['after'],'memory':memories,'exact_rank_score_reasons':True})
            for query_name in warm:
                report['warm'].append({'implementation':implementation,'query':query_name,'wall_ms':warm[query_name],
                    'median_ms':{v:statistics.median(values) for v,values in warm[query_name].items()},'exact_results':True})
            save()
        report['read_only_unchanged']=state(engines['python'])==baseline
        assert report['read_only_unchanged']
        report['complete']=True;report['completed_at_utc']=datetime.now(timezone.utc).isoformat();save()
    finally:
        bm25.tokenize=optimized
        for engine in engines.values():engine.close()
        save()

if __name__=='__main__':main()
