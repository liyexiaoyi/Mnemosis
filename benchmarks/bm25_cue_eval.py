"""Frozen, read-only paired retrieval evaluation; no LLM or network calls.

Gold turn flags are used only for scoring, never ingestion or feedback.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import statistics
import tempfile
import time
from datetime import datetime
from pathlib import Path
from bench_utils import pin_local_src
pin_local_src()
from mnemosis import MemoryEngine
from mnemosis.embedding import NGramEmbedder
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def percentile(values, quantile):
    return sorted(values)[max(0, math.ceil(len(values)*quantile)-1)] if values else None


def is_answerable(qid, gold_refs):
    return not qid.endswith("_abs") and bool(gold_refs)


def snapshot(engine):
    payload = engine.export_memories()
    payload.pop("exported_at", None)  # wall-clock export metadata is not learning state
    payload["links"] = sorted(engine.backend.all_links())
    payload["recall_log"] = engine.get_recall_log()
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def evaluate_question(question, protocol, workdir):
    start = datetime.fromisoformat(protocol["clock"])
    with tempfile.TemporaryDirectory(prefix="cue-eval-", dir=workdir) as tmp:
        assert Path(tmp).resolve().parent == workdir.resolve()
        engine = MemoryEngine(str(Path(tmp)/"memory.db"), auto_warmup=False)
        try:
            records, gold_refs, gold_contents = [], set(), set()
            sessions = question.get("haystack_session_ids", [])
            dates = question.get("haystack_dates", [])
            for si, session in enumerate(question["haystack_sessions"]):
                sid = sessions[si] if si < len(sessions) else str(si)
                cues = [f"sid:{sid}"]
                if si < len(dates):
                    cues.append(f"date:{dates[si]}")
                for ti, turn in enumerate(session):
                    content = turn.get("content", "")
                    if not content:
                        continue
                    ref = f"{si}:{sid}:turn:{ti}"
                    if turn.get("has_answer"):
                        gold_refs.add(ref)
                        gold_contents.add(content)
                    records.append(dict(content=content, kind=MemoryKind.EPISODIC,
                        source=SourceRecord(origin=SourceType.USER if turn.get("role")=="user" else SourceType.AGENT, ref=ref),
                        cues=list(cues), importance=0.5, created_at=start))
            ingest_start = time.perf_counter()
            engine.remember_many(records)
            ingest_ms = 1000*(time.perf_counter()-ingest_start)
            before = snapshot(engine)
            query = question["question"]
            calls = {
                "ngram": lambda: engine.recall(query, top_k=10, embedder=NGramEmbedder(), read_only=True, now=start),
                "legacy_hybrid": lambda: engine.recall_fused(query, top_k=10, pass_k=30, rrf_k=30, ng_weight=2, read_only=True, now=start),
                "bm25": lambda: engine.recall_bm25(query, top_k=10),
                "bm25_ngram_bounded": lambda: engine.recall_fused(query, top_k=10, read_only=True, now=start, **protocol["new_config"]),
            }
            rows = {}
            for mode in protocol["modes"]:
                began = time.perf_counter()
                results = calls[mode]()
                elapsed = 1000*(time.perf_counter()-began)
                refs = [r.item.source.ref for r in results]
                hit_ranks = [i+1 for i, ref in enumerate(refs) if ref in gold_refs]
                rows[mode] = {"ms":elapsed, "refs":refs,
                    "hit1": any(r<=1 for r in hit_ranks),
                    "hit5": any(r<=5 for r in hit_ranks),
                    "hit10":bool(hit_ranks),
                    "all5":bool(gold_refs) and gold_refs.issubset(refs[:5]),
                    "coverage5":len(gold_refs.intersection(refs[:5]))/len(gold_refs) if gold_refs else None,
                    "mrr10":1/min(hit_ranks) if hit_ranks else 0,
                    "legacy_content_hit5":any(r.item.content in gold_contents for r in results[:5]),
                    "scores":[r.score for r in results]}
            began = time.perf_counter()
            warm = engine.recall_bm25(query, top_k=10)
            warm_ms = 1000*(time.perf_counter()-began)
            assert [r.item.source.ref for r in warm] == rows["bm25"]["refs"]
            assert snapshot(engine) == before, "retrieval modified stored state"
            return {"qid":question["question_id"], "type":question["question_type"],
                    "answerable":is_answerable(question["question_id"], gold_refs), "gold_refs":sorted(gold_refs),
                    "turns":len(records), "ingest_ms":ingest_ms, "bm25_warm_ms":warm_ms,
                    "modes":rows}
        finally:
            engine.close()


def summarize(rows, modes):
    eligible = [row for row in rows if row["answerable"]]
    result = {"n":len(rows), "answerable":len(eligible), "unanswerable":len(rows)-len(eligible),
              "abstention_evaluated":False, "modes":{}}
    for mode in modes:
        scores = [r["modes"][mode] for r in eligible]
        result["modes"][mode] = {key:round(statistics.mean(r[key] for r in scores),4)
            for key in ("hit1","hit5","hit10","all5","coverage5","mrr10","legacy_content_hit5")}
        result["modes"][mode].update({"p50_ms":round(statistics.median(r["modes"][mode]["ms"] for r in rows),2),
            "p95_ms":round(percentile([r["modes"][mode]["ms"] for r in rows],.95),2)})
    result["bm25_warm_p95_ms"] = round(percentile([r["bm25_warm_ms"] for r in rows],.95),2)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--data",type=Path,required=True)
    parser.add_argument("--protocol",type=Path,required=True)
    parser.add_argument("--split",choices=("dev","holdout"),required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--workdir",type=Path,required=True)
    args=parser.parse_args()
    protocol=json.loads(args.protocol.read_text(encoding="utf-8"))
    raw=args.data.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==protocol["dataset_sha256"]
    data={q["question_id"]:q for q in json.loads(raw)}
    args.workdir.mkdir(parents=True,exist_ok=True)
    ids=protocol[args.split+"_ids"]
    rows=[]
    # A fresh output is required; never silently mix code/config versions.
    if args.output.exists():
        raise FileExistsError(args.output)
    for i,qid in enumerate(ids):
        rows.append(evaluate_question(data[qid],protocol,args.workdir))
        report={"protocol":protocol,"split":args.split,"rows":rows,
                "complete":len(rows)==len(ids),"summary":summarize(rows,protocol["modes"])}
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        if (i+1)%10==0:
            print(f"{args.split}: {i+1}/{len(ids)}",flush=True)
    print(json.dumps(report["summary"],ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
