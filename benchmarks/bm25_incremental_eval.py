"""Measure incremental edits against identical full rebuilds, local SQLite."""
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path
from bench_utils import pin_local_src
pin_local_src()
from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def retained_bytes(value, seen=None):
    # Approximate retained Python object graph, not process RSS or peak memory.
    seen=seen if seen is not None else set()
    if id(value) in seen:return 0
    seen.add(id(value)); size=sys.getsizeof(value)
    if isinstance(value,dict):return size+sum(retained_bytes(k,seen)+retained_bytes(v,seen) for k,v in value.items())
    if isinstance(value,(tuple,list,set)):return size+sum(retained_bytes(v,seen) for v in value)
    return size


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--workdir",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();args.workdir.mkdir(parents=True,exist_ok=True)
    rows=[]
    for count in (1000,10000,100000):
        with tempfile.TemporaryDirectory(prefix="incremental-",dir=args.workdir) as tmp:
            assert Path(tmp).resolve().parent==args.workdir.resolve()
            engine=MemoryEngine(str(Path(tmp)/"memory.db"),auto_warmup=False)
            try:
                records=[dict(content=f"rare{i} "+"travel tea coffee meeting recipe music calendar garden "*8,
                    kind=MemoryKind.EPISODIC,source=SourceRecord(origin=SourceType.USER),cues=[]) for i in range(count)]
                began=time.perf_counter()
                items=engine.remember_many(records,auto_cues=False,auto_context=False)
                ingest=time.perf_counter()-began
                began=time.perf_counter();engine.recall_bm25(f"rare{count-1}")
                cold=1000*(time.perf_counter()-began)
                last=items[-1];began=time.perf_counter()
                engine.update(last.id,content="revisedmango travel meeting")
                write=1000*(time.perf_counter()-began)
                began=time.perf_counter();incremental=engine.recall_bm25("revisedmango",top_k=10)
                delta=1000*(time.perf_counter()-began)
                assert incremental and incremental[0].item.id==last.id
                # Compare common-term rankings too: df/average length may move.
                inc_common=engine.recall_bm25("tea coffee",top_k=10)
                engine._bm25_cache=None
                began=time.perf_counter();full=engine.recall_bm25("revisedmango",top_k=10)
                rebuild=1000*(time.perf_counter()-began)
                full_common=engine.recall_bm25("tea coffee",top_k=10)
                for a,b in ((incremental,full),(inc_common,full_common)):
                    assert [r.item.id for r in a]==[r.item.id for r in b]
                    assert all(abs(x.score-y.score)<1e-12 for x,y in zip(a,b))
                engine.forget(last.id)
                assert not engine.recall_bm25("revisedmango")
                engine.restore(last.id)
                assert engine.recall_bm25("revisedmango")[0].item.id==last.id
                count_log=engine.backend._conn.execute("SELECT COUNT(*) FROM bm25_lexical_changes").fetchone()[0]
                assert count_log<=4351
                memory=retained_bytes(vars(engine._bm25_cache[2]))
                rows.append(dict(memories=count,words_per_original=65,ingest_seconds=round(ingest,3),
                    first_query_ms=round(cold,3),content_write_ms=round(write,3),
                    query_after_one_edit_ms=round(delta,3),forced_rebuild_ms=round(rebuild,3),
                    exact_rank_and_score_match=True,change_log_rows=count_log,
                    approximate_index_object_bytes=memory))
                print(json.dumps(rows[-1]),flush=True)
            finally:engine.close()
    args.output.write_text(json.dumps({"scope":"Synthetic SQLite, same edited corpus and formula; single latency samples; approximate retained Python objects not peak RSS", "rows":rows},indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":main()
