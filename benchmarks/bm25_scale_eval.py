"""Local SQLite BM25 cold/warm cost; synthetic workload, not accuracy."""
import argparse
import json
import tempfile
import time
from pathlib import Path
from bench_utils import pin_local_src
pin_local_src()
from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--workdir",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    args.workdir.mkdir(parents=True,exist_ok=True)
    rows=[]
    for count in (1000,10000,100000):
        with tempfile.TemporaryDirectory(prefix="bm25-scale-",dir=args.workdir) as tmp:
            assert Path(tmp).resolve().parent == args.workdir.resolve()
            db=Path(tmp)/"memory.db"
            engine=MemoryEngine(str(db),auto_warmup=False)
            try:
                records=[dict(content=f"rare{i} "+"travel tea coffee meeting recipe music calendar garden "*8,
                    kind=MemoryKind.EPISODIC,source=SourceRecord(origin=SourceType.USER),cues=[])
                    for i in range(count)]
                began=time.perf_counter()
                engine.remember_many(records,auto_cues=False,auto_context=False)
                ingest=time.perf_counter()-began
                query=f"rare{count-1}"
                began=time.perf_counter()
                found=engine.recall_bm25(query)
                cold=1000*(time.perf_counter()-began)
                assert found and found[0].item.content.startswith(query+" ")
                warm=[]
                for _ in range(20):
                    began=time.perf_counter();engine.recall_bm25(query)
                    warm.append(1000*(time.perf_counter()-began))
                engine.record_feedback(found[0].item.id, useful=True)
                began=time.perf_counter();engine.recall_bm25(query)
                after_feedback=1000*(time.perf_counter()-began)
                began=time.perf_counter();engine.recall_bm25("tea")
                common=1000*(time.perf_counter()-began)
                rows.append(dict(memories=count,words_per_memory=65,ingest_seconds=round(ingest,3),
                    cold_ms=round(cold,3),warm_rare_p95_ms=round(sorted(warm)[18],3),
                    warm_common_ms=round(common,3),after_feedback_ms=round(after_feedback,3),disk_bytes=sum(x.stat().st_size for x in Path(tmp).iterdir())))
                print(json.dumps(rows[-1]),flush=True)
            finally:
                engine.close()
    args.output.write_text(json.dumps({"scope":"synthetic SQLite cost, 65 words/item; 20 warm rare queries and one common-term query", "rows":rows},indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":main()
