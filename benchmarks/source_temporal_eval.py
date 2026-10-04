"""Frozen synthetic retrieval challenge. Repeated executions are not independent samples."""
from datetime import datetime
from pathlib import Path
import argparse
import hashlib
import json
import statistics
import tempfile
import time

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def snapshot(engine):
    return json.dumps(dict(items=[i.to_dict() for i in engine.store.all_active()],
        links=sorted(engine.backend.all_links()), log=engine.get_recall_log()),sort_keys=True)


def run(args):
    raw=args.fixture.read_bytes()
    protocol=json.loads(args.protocol.read_text(encoding='utf-8'))
    assert hashlib.sha256(raw).hexdigest()==protocol['fixture_sha256'], 'fixture changed'
    cases=json.loads(raw)['cases']
    if args.split!='all': cases=[c for c in cases if c['split']==args.split]
    rows=[]
    args.workdir.mkdir(parents=True,exist_ok=True)
    for case in cases:
        clock=datetime.fromisoformat(case['now'])
        for disk in (False,True):
            for mode in args.modes.split(','):
                for k in (1,5):
                    with tempfile.TemporaryDirectory(dir=args.workdir) as folder:
                        with MemoryEngine(str(Path(folder)/'memory.db') if disk else None,auto_warmup=False) as engine:
                            items=[]
                            for i,record in enumerate(case['items']):
                                source=SourceRecord(SourceType.USER,ref=record.get('ref'),
                                    occurred_at=datetime.fromisoformat(record['occurred_at']) if record.get('occurred_at') else None)
                                items.append(engine.remember(record['content'],kind=MemoryKind(record.get('kind','episodic')),
                                    source=source,cues=record.get('cues',[]),context=record.get('context'),
                                    evidence_count=20 if i==0 else 1,created_at=clock,auto_cues=False,auto_context=False))
                            before=snapshot(engine)
                            start=time.perf_counter()
                            if mode=='bm25': result=engine.recall_bm25(case['query'],top_k=k)
                            elif mode=='normalized_fused': result=engine.recall_fused(case['query'],top_k=k,now=clock,
                                read_only=True,normalize_fusion=True,bm25_weight=1.0)
                            else:
                                kw={'temporal_policy':'source'} if mode in ('source','source_no_anchor') else {}
                                if mode=='source_no_anchor': kw['temporal_anchor']=False
                                result=engine.recall(case['query'],top_k=k,now=clock,read_only=True,**kw)
                            elapsed=(time.perf_counter()-start)*1000
                            ids=[r.item.id for r in result]
                            target=case['expected_top']
                            target_id=items[target].id if target is not None else None
                            required={items[i].id for i in case['required_evidence']}
                            rows.append(dict(case=case['id'],category=case['category'],split=case['split'],
                                mode=mode,backend='sqlite' if disk else 'dict',top_k=k,
                                answerable=target is not None,hit1=bool(ids and ids[0]==target_id) if target is not None else None,
                                all_evidence=required.issubset(ids) if required else None,
                                uncertain_expected=case['expected_uncertain'],
                                uncertain_signal=not result or not result[0].confident,
                                read_only=before==snapshot(engine),no_duplicates=len(ids)==len(set(ids)),
                                ms=round(elapsed,3),context_characters=sum(len(r.item.content) for r in result),
                                returned=[dict(content=r.item.content,confident=r.confident,reasons=r.reasons) for r in result]))
    summary={}
    for mode in args.modes.split(','):
        selected=[r for r in rows if r['mode']==mode]
        known=[r for r in selected if r['answerable'] and r['top_k']==1]
        timed=[r for r in known if r['category']=='time']
        uncertain=[r for r in selected if r['category']=='time' and r['uncertain_expected'] and r['top_k']==1]
        summary[mode]=dict(executions=len(selected),hit1=sum(r['hit1'] for r in known),known_executions=len(known),
            time_hit1=sum(r['hit1'] for r in timed),time_known_executions=len(timed),
            time_uncertain_correct=sum(r['uncertain_signal'] for r in uncertain),time_uncertain_executions=len(uncertain),
            read_only=all(r['read_only'] for r in selected),no_duplicates=all(r['no_duplicates'] for r in selected),
            median_ms=round(statistics.median(r['ms'] for r in selected),3) if selected else None)
    return dict(protocol=protocol,split=args.split,trajectories=len(cases),summary=summary,rows=rows,
        source_sha256={name:hashlib.sha256((Path(__import__('mnemosis').__file__).parent/name).read_bytes()).hexdigest()
            for name in ['retrieval_mixin.py','schema.py']},
        scope='authored synthetic retrieval regression; not independent external holdout, answer accuracy, calibrated truth, or market ranking')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--fixture',type=Path,required=True);p.add_argument('--protocol',type=Path,required=True)
    p.add_argument('--split',choices=['dev','acceptance','all'],default='dev')
    p.add_argument('--modes',default='recall,bm25,normalized_fused')
    p.add_argument('--workdir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    result=run(args)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(trajectories=result['trajectories'],summary=result['summary']),ensure_ascii=False))
