"""Paired full vector-ingest evaluation; only NGramEmbedder differs.

Trusted local baseline ZIP required. No external model calls or quality claims.
"""
from __future__ import annotations
import argparse, ast, gc, hashlib, json, logging, platform, random, statistics, time, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from bench_utils import pin_local_src, assert_local_mnemosis
pin_local_src()
assert_local_mnemosis()
from mnemosis import MemoryEngine, SourceRecord, SourceType
import mnemosis.embedding as embedding
from mnemosis.vector_index import VectorIndex
from ingest_pair_eval import digest_tables
from verification_utils import TableVerifier, ReadOnlyGuard

NOW = datetime(2026, 10, 6, tzinfo=timezone.utc)

def texts_for(case, n):
    rng=random.Random(20261006)
    result=[]
    for i in range(n):
        if case in ('short_shared','no_vectors'):
            text=f'User {i} prefers local coffee and green tea. 本地记忆检索与睡眠整理。'
        elif case=='long_shared':
            text=f'User {i} '+' '.join(['retrieval memory consolidation performance evidence projection embedding policy']*8)+' 仿生记忆需要来源证据与时间适用性。'
        else:
            text=f'User {i} '+''.join(rng.choices('abcdefghijklmnopqrstuvwxyz',k=160))+' '+''.join(chr(rng.randrange(0x4e00,0x9fff)) for _ in range(30))
        result.append(text)
    return result


def digest_vector(conn):
    result={}
    for table in ('meta','vectors','buckets'):
        h=hashlib.sha256();count=0
        for row in conn.execute(f'SELECT * FROM {table} ORDER BY 1,2'):
            for value in row:
                payload=value if isinstance(value,bytes) else repr(value).encode()
                h.update(len(payload).to_bytes(8,'little'));h.update(payload)
            count+=1
        result[table]=dict(rows=count,sha256=h.hexdigest())
    return result


def main(args):
    with zipfile.ZipFile(args.baseline) as z:
        old_source=z.read('src/mnemosis/embedding.py').decode('utf-8-sig')
    cls=next(n for n in ast.parse(old_source).body if isinstance(n,ast.ClassDef) and n.name=='NGramEmbedder')
    namespace=dict(embedding.__dict__)
    exec(compile('from __future__ import annotations\n'+ast.unparse(cls),str(args.baseline),'exec'),namespace)
    old_class=namespace['NGramEmbedder']
    args.output.mkdir(parents=True,exist_ok=True)
    assert not (args.output/'comparison.json').exists()
    report=dict(python=platform.python_version(),platform=platform.platform(),rounds=args.rounds,
                scope='synthetic complete SQLite engine ingest; auto cues/context off, no links; local NGram256,13bits,8buckets; not agent answer quality',
                baseline_zip_sha256=hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
                current_source_sha256=hashlib.sha256(Path(embedding.__file__).read_bytes()).hexdigest(),
                cache_scope='fresh per chunk of 1000, no cross-chunk/run warming',
                caveats=['OS cache/background load uncontrolled','setup/snapshots/close excluded','full current engine; only embedder implementation differs'],cases=[])
    report['verification_mode']=args.verification
    report['caveats'].append('boundary mode samples middle rounds; unsampled changes may be missed; readonly guard is a diagnostic, not an exhaustive write audit')
    workloads=[(n,case) for case in ('short_shared','long_shared','diverse') for n in args.counts]+[(max(args.counts),'no_vectors')]
    for n,case in workloads:
        texts=texts_for(case,n)
        source=SourceRecord(origin=SourceType.USER,ref='synthetic',occurred_at=NOW)
        records=[dict(content=t,cues=[],source=source,created_at=NOW,importance=.5) for t in texts]
        out=args.output/f'{case}-{n}';out.mkdir()
        row=dict(n=n,case=case,samples=[],complete=False);expected=None;expected_ids=None
        memory_checks=TableVerifier(dict(memories=('id',),cues=('cue','memory_id'),terms=('term','memory_id'),links=('src','dst')),args.rounds,mode=args.verification)
        vector_checks=TableVerifier(dict(meta=('key',),vectors=('memory_id',),buckets=('bucket','memory_id')),args.rounds,mode=args.verification)
        report['cases'].append(row)
        for round_id in range(args.rounds):
            for variant in (('before','after') if round_id%2==0 else ('after','before')):
                db=out/f'{round_id}-{variant}.sqlite';vdb=out/f'{round_id}-{variant}-vectors.sqlite'
                assert not db.exists() and not vdb.exists();gc.collect()
                cls=old_class if variant=='before' else embedding.NGramEmbedder
                engine=MemoryEngine(str(db),auto_warmup=False,
                        vector_index=VectorIndex(str(vdb),dim=256) if case!='no_vectors' else None,
                        index_embedder=cls() if case!='no_vectors' else None)
                rng=random.Random(20261006)
                def stable_uuid():return uuid.UUID(int=rng.getrandbits(128))
                try:
                    with patch('mnemosis.types.uuid.uuid4',stable_uuid):
                        cpu=time.process_time();wall=time.perf_counter()
                        items=engine.remember_many_chunked(records,chunk_size=1000,auto_cues=False,auto_context=False,max_links=0)
                        elapsed=time.perf_counter()-wall;cpu=time.process_time()-cpu
                    assert len(items)==engine.backend.count()==n
                    ids=[i.id for i in items]
                    if expected_ids is None: expected_ids=ids
                    assert ids==expected_ids, 'returned memory order changed'
                    state=dict(memory=memory_checks.check(engine.backend._conn,round_id,digest_tables), returned_order_parity=True)
                    results={}
                    if case!='no_vectors':
                        assert engine.vector_index.size==n
                        state['vector']=vector_checks.check(engine.vector_index._conn,round_id,digest_vector)
                        query=cls().embed(texts[-1])
                        with ReadOnlyGuard(engine.vector_index._conn):
                            results['exact_recall']=engine.vector_index.search(query,top_k=5)
                            engine.vector_index.full_scan_threshold=0
                            engine.vector_index.exact_scan_limit=0
                            results['lsh_recall']=engine.vector_index.search(query,top_k=5)
                    if expected is None: expected=results
                    assert results==expected,'exact/LSH query results changed'
                    state.update(results)
                    row['samples'].append(dict(round=round_id,variant=variant,wall_s=elapsed,cpu_s=cpu,state=state))
                    print(json.dumps(dict(n=n,case=case,round=round_id,variant=variant,wall_s=elapsed)),flush=True)
                finally:engine.close()
                if round_id<args.rounds-1:
                    for owned in (db,vdb):
                        for suffix in ('','-wal','-shm'):
                            p=Path(str(owned)+suffix)
                            assert p.resolve().parent==out.resolve()
                            p.unlink(missing_ok=True)
                (args.output/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        row['medians_s']={v:statistics.median(s['wall_s'] for s in row['samples'] if s['variant']==v) for v in ('before','after')}
        row['latency_reduction_pct']=100*(1-row['medians_s']['after']/row['medians_s']['before'])
        modes=[s['state']['memory']['mode'] for s in row['samples']]
        row.update(complete=True,verification=dict(full_runs=modes.count('full'),sample_runs=modes.count('sample'),all_runs_exhaustive=all(m=='full' for m in modes),boundary_full_parity=True,sampled_middle_parity=True,result_order_parity=True))
    (args.output/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for c in report['cases']:print(c['case'],c['n'],c['medians_s'],c['latency_reduction_pct'])

if __name__=='__main__':
    logging.basicConfig(level=logging.ERROR)
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--rounds',type=int,default=7)
    p.add_argument('--verification',choices=['boundary','full'],default='boundary')
    p.add_argument('--counts',type=int,nargs='+',default=[1000,10000])
    a=p.parse_args()
    if a.rounds<1 or any(n<1 for n in a.counts):p.error('rounds/counts must be positive')
    if len(set(a.counts))!=len(a.counts):p.error('counts must be unique')
    main(a)
