"""Paired import timing and exact database/graph comparison against a Git archive.

Run from a local trusted checkout. Baseline methods are extracted from the
supplied pre-change archive; the remaining engine/storage/tokenizer is shared.
"""
from __future__ import annotations
import argparse
import ast
import gc
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import time
from datetime import datetime, timezone
from unittest.mock import patch
import uuid
import zipfile
from verification_utils import TableVerifier, ReadOnlyGuard
import mnemosis.association as assoc
import mnemosis.backend as backend
from mnemosis import MemoryEngine, MemoryKind, SourceRecord, SourceType

NOW = datetime(2026, 10, 6, tzinfo=timezone.utc)
METHODS = ((assoc, assoc.AssociationIndex, 'association.py', 'link_related_batch'),
           (assoc, assoc.AssociationIndex, 'association.py', 'link_related_batch_incremental'),
           (backend, backend.SQLiteBackend, 'backend.py', 'add_links_many'))

def baseline_methods(archive):
    old = []
    with zipfile.ZipFile(archive) as z:
        for module, cls, filename, name in METHODS:
            tree = ast.parse(z.read('src/mnemosis/'+filename).decode('utf-8'))
            definition = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name==cls.__name__)
            fn = next(n for n in definition.body if isinstance(n, ast.FunctionDef) and n.name==name)
            ns = module.__dict__.copy()
            exec(compile('from __future__ import annotations\n'+ast.unparse(fn),str(archive)+':'+filename,'exec'),ns)
            old.append(ns[name])
    return old

def digest_tables(conn):
    result = {}
    for table in ('memories', 'cues', 'terms', 'links'):
        count = 0
        h = hashlib.sha256()
        # Every persisted column is included; random cache revision BLOBs
        # in tracking tables are intentionally excluded from equivalence.
        columns = len(conn.execute(f'PRAGMA table_info({table})').fetchall())
        sql = f'SELECT * FROM {table} ORDER BY '+','.join(str(i) for i in range(1,columns+1))
        for row in conn.execute(sql):
            h.update(json.dumps(tuple(row),ensure_ascii=True,separators=(',',':')).encode('utf-8')+b'\n')
            count += 1
        result[table] = dict(rows=count,sha256=h.hexdigest())
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline-archive',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--count',type=int,default=10000)
    p.add_argument('--rounds',type=int,default=7)
    p.add_argument('--mode',choices=['batch','chunked','repeated'],default='chunked')
    p.add_argument('--workload',choices=['linked','sparse'],default='linked')
    p.add_argument('--verification',choices=['boundary','full'],default='boundary')
    a=p.parse_args()
    if a.count<=0 or a.rounds<=0: p.error('count and rounds must be positive')
    a.out.mkdir(parents=True,exist_ok=True)
    out=a.out/'comparison.json'
    if out.exists(): p.error('refusing to replace existing results')
    old=baseline_methods(a.baseline_archive)
    new=[getattr(cls,n) for _,cls,_,n in METHODS]
    records=[dict(content=f'needle{i:06d} privateevent 旅行项目', kind=MemoryKind.EPISODIC,
        cues=[f'group{i//64}' if a.workload=='linked' else f'person{i:06d}'],
        source=SourceRecord(SourceType.USER,ref=f'synthetic:{i}',occurred_at=NOW),
        created_at=NOW,importance=.5) for i in range(a.count)]
    result=dict(count=a.count,rounds=a.rounds,mode=a.mode,workload=a.workload,
        python=platform.python_version(),platform=platform.platform(),
        scope='same current engine, frozen old vs new graph/link methods; no vectors; unique episodic inputs, group size 64; timing includes one staged-row count inspection per bulk import; OS/background load uncontrolled',
        baseline_archive_sha256=hashlib.sha256(a.baseline_archive.read_bytes()).hexdigest(),
        optimized_source_sha256={filename:hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() for filename,module in {filename:module for module,_,filename,_ in METHODS}.items()},
        samples=[],complete=False)
    result['verification_mode']=a.verification
    result['verification_limits']='Middle rounds in boundary mode compare exact counts, schema and fixed key samples; unsampled changes may be missed. Readonly guard is a diagnostic, not an exhaustive write audit.'
    checks=TableVerifier(dict(memories=('id',),cues=('cue','memory_id'),terms=('term','memory_id'),links=('src','dst')),a.rounds,mode=a.verification)
    expected=None;expected_ids=None
    for round_index in range(a.rounds):
        for version in (('before','after') if round_index%2==0 else ('after','before')):
            funcs=old if version=='before' else new
            for (_,cls,_,name),fn in zip(METHODS,funcs): setattr(cls,name,fn)
            db=a.out/f'round{round_index}-{version}.sqlite'
            assert not db.exists()
            gc.collect()
            e=MemoryEngine(str(db),auto_warmup=False)
            staged=[];finish=[];end=e.backend.end_bulk_mode
            def capture_end():
                staged.append(e.backend._conn.execute('SELECT COUNT(*) FROM links_bulk').fetchone()[0])
                start=time.perf_counter()
                end()
                finish.append(time.perf_counter()-start)
            e.backend.end_bulk_mode=capture_end
            rng=random.Random(20261006)
            def stable_uuid(): return uuid.UUID(int=rng.getrandbits(128))
            try:
                with patch('mnemosis.types.uuid.uuid4',stable_uuid):
                    cpu=time.process_time();start=time.perf_counter()
                    if a.mode=='batch': items=e.remember_many(records,auto_cues=False,auto_context=False)
                    elif a.mode=='chunked': items=e.remember_many_chunked(records,chunk_size=1000,auto_cues=False,auto_context=False)
                    else: items=[it for n in range(0,len(records),1000) for it in e.remember_many(records[n:n+1000],auto_cues=False,auto_context=False)]
                    wall=time.perf_counter()-start;cpu=time.process_time()-cpu
                assert len(items)==a.count and e.backend.count()==a.count
                assert not e.associations._batch_pool and not e.backend._bulk_terms_index_deferred
                assert e.backend._conn.execute('PRAGMA synchronous').fetchone()[0]==1
                signature=checks.check(e.backend._conn,round_index,digest_tables)
                with ReadOnlyGuard(e.backend._conn):
                    recall=[(r.item.id,r.score,r.reasons,r.confident) for r in e.recall_bm25(f'needle{a.count-1:06d}',top_k=5)]
                ids=[i.id for i in items]
                if expected_ids is None: expected_ids=ids
                if expected is None: expected=recall
                assert ids==expected_ids and recall==expected,'returned order/recall differs from baseline'
                signature['returned_order_parity']=True
                signature['recall']=recall
                sample=dict(round=round_index,version=version,wall_seconds=wall,cpu_seconds=cpu,staged_link_rows=sum(staged),end_bulk_seconds=sum(finish),signature=signature)
                result['samples'].append(sample)
                print(json.dumps({k:v for k,v in sample.items() if k!='signature'}),flush=True)
            finally:
                e.close()
                for (_,cls,_,name),fn in zip(METHODS,new): setattr(cls,name,fn)
            # Keep the final pair of databases; retain every measurement and
            # signature. Delete only files created by this benchmark in out.
            if round_index<a.rounds-1:
                for suffix in ('','-wal','-shm'):
                    own=Path(str(db)+suffix)
                    assert own.resolve().parent==a.out.resolve()
                    own.unlink(missing_ok=True)
            out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    before=statistics.median(s['wall_seconds'] for s in result['samples'] if s['version']=='before')
    after=statistics.median(s['wall_seconds'] for s in result['samples'] if s['version']=='after')
    modes=[s['signature']['mode'] for s in result['samples']]
    result.update(complete=True,verification=dict(full_runs=modes.count('full'),sample_runs=modes.count('sample'),all_runs_exhaustive=all(m=='full' for m in modes),boundary_full_parity=True,sampled_middle_parity=True,result_order_parity=True),median_seconds=dict(before=before,after=after),speedup=before/after)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('count','rounds','mode','workload','median_seconds','speedup','complete')}),flush=True)

if __name__=='__main__':main()
