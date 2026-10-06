"""Fixed constructed ranking comparison, not retrieval or answer accuracy."""
from contextlib import nullcontext
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from fractions import Fraction as F
from itertools import combinations
import argparse
import json
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

from bench_utils import pin_local_src, assert_local_mnemosis
pin_local_src()
LOCAL_MODULE = assert_local_mnemosis()
from mnemosis import MemoryEngine
from mnemosis.types import MemoryItem, MemoryKind, SourceRecord, SourceType
from mnemosis.evidence_selection import QueryAspect
from mnemosis.ranked_evidence import RankedChannel, select_ranked_evidence
from verification_utils import ReadOnlyGuard

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO/"benchmarks/data/ranked_evidence_cases.json"
NOW = datetime(2026,10,6,12,tzinfo=timezone.utc)
PRIMARY = ("normalized_rrf_topk", "ranked_coverage")


def exact_relevance(case):
    """Independent rational normalization; does not call the product scorer."""
    enabled = [c for c in case["channels"] if c["weight"] > 0]
    total = sum((F(str(c["weight"])) for c in enabled), F())
    scores = {}
    for c in enabled:
        for rank, ident in enumerate(c["memory_ids"], 1):
            scores.setdefault(ident, F())
            scores[ident] += F(str(c["weight"]))/total * F(61,60+rank)
    first = {ident: index for index, ident in enumerate(scores)}
    order = sorted(scores, key=lambda ident: (-scores[ident],first[ident]))
    return scores, order


def exact_proxy(case, selected, relevance):
    support = case["support"] or {}
    raw = {a["id"]: F(str(a["weight"])) for a in case["aspects"]}
    total = sum(raw.values(), F())
    weights = {a: value/total for a,value in raw.items()}
    coverage = {a: max((F(str(support.get(i,{}).get(a,0))) for i in selected),default=F())
                for a in weights}
    k = case["limit"]
    r = sum((relevance[i] for i in selected),F())/k if k else F()
    c = sum((weights[a]*value for a,value in coverage.items()),F())
    lam = F(str(case["lambda_"]))
    f = lam*r+(1-lam)*c if k else F()
    return dict(relevance_component=float(r),coverage_component=float(c),objective=float(f),
                objective_exact=str(f),aspect_coverage={a:float(v) for a,v in coverage.items()})


def snapshot(engine):
    conn = getattr(engine.backend,"_conn",None)
    return deepcopy(dict(memories=sorted((i.to_dict() for i in engine.backend.list_items()),
                                         key=lambda d:d["id"]),
                         links=sorted(engine.backend.all_links()),log=list(engine._recall_log),
                         sqlite_full_dump=list(conn.iterdump()) if conn is not None else None))


def coverage(required, selected):
    if required is None:
        return None
    assert required
    return set(required).issubset(selected)


def evaluate(case, backend, out):
    with tempfile.TemporaryDirectory(dir=out) as temp:
        engine = MemoryEngine(str(Path(temp)/"memory.sqlite") if backend=="sqlite" else None,
                              auto_warmup=False)
        try:
            engine.backend.add_many([MemoryItem(
                id=d["id"],content=d["content"],kind=MemoryKind(d["kind"]),
                source=SourceRecord(SourceType.USER,ref=d["source"],
                                    occurred_at=datetime.fromisoformat(d["occurred_at"])),
                created_at=NOW,last_access_at=NOW,access_count=7,confidence=.7,
                context=json.dumps({"entity":d["entity"],"scope":d["scope"]}),
                retrieval_successes=4,retrieval_failures=2,
                verified_successes=5,verified_failures=1,evidence_sources={d["source"]:2})
                for d in case["records"]])
            engine.backend.add_link("A","C",.5)
            engine._recall_log.append({"query":"earlier","ids":["B"]})
            before = snapshot(engine)
            conn = getattr(engine.backend,"_conn",None)
            with ReadOnlyGuard(conn) if conn is not None else nullcontext():
                actual = {i.id:i for i in engine.backend.get_many([d["id"] for d in case["records"]])}
                assert len(actual)==len(case["records"])
                channels = [RankedChannel(c["channel_id"],[actual[i].id for i in c["memory_ids"]],
                                          c["weight"],c["status"]) for c in case["channels"]]
                report = select_ranked_evidence(
                    channels,[QueryAspect(a["id"],a["weight"]) for a in case["aspects"]],
                    support=case["support"],limit=case["limit"],relevance_weight=case["lambda_"])
                rational, order = exact_relevance(case)
                assert list(report.candidate_ids)==order
                for ident,value in rational.items():
                    assert abs(report.relevance_by_id[ident]-float(value))<=1e-12
                selected = list(report.selection.selected_ids)
                proxy = exact_proxy(case,selected,rational)
                for metric in ("relevance_component","coverage_component","objective"):
                    assert abs(getattr(report.selection,metric)-proxy[metric])<=1e-12
                prior = 0.
                for index,step in enumerate(report.selection.steps,1):
                    current=exact_proxy(case,selected[:index],rational)["objective"]
                    assert abs(step.objective_after-current)<=1e-12
                    assert abs(step.total_gain-(current-prior))<=1e-12
                    prior=current
                methods = [(PRIMARY[0],order[:case["limit"]],order),
                           (PRIMARY[1],selected,order)]
                methods += [("channel_"+c["channel_id"]+"_topk",
                             c["memory_ids"][:case["limit"]],c["memory_ids"]) for c in case["channels"]]
                rows = [dict(method=name,selected_ids=ids,pool_ids=list(pool),
                             necessary_complete=coverage(case["necessary_ids"],ids),
                             necessary_pool_complete=coverage(case["necessary_ids"],pool),
                             proxy=exact_proxy(case,ids,rational)) for name,ids,pool in methods]
            assert before==snapshot(engine), "persistent memory/query state changed"
            optimum = max(exact_proxy(case,s,rational)["objective"]
                          for n in range(min(case["limit"],len(order))+1)
                          for s in combinations(order,n))
            return dict(name=case["name"],backend=backend,necessary_ids=case["necessary_ids"],
                        report=asdict(report),methods=rows,optimal_proxy=optimum,
                        all_state_unchanged=True,sql_guard_passed=conn is not None)
        finally:
            engine.close()


def timing():
    ids = [str(i) for i in range(100)]
    channels = [RankedChannel(str(j),ids[j:]+ids[:j],j+1) for j in range(8)]
    aspects = [QueryAspect(str(j)) for j in range(32)]
    support = {i:{str(j):(int(i)+j)%11/10 for j in range(32)} for i in ids}
    durations = []
    for _ in range(7):
        start = time.perf_counter_ns()
        report = select_ranked_evidence(channels,aspects,support=support,limit=5)
        durations.append(time.perf_counter_ns()-start)
    input_bytes = len(json.dumps(dict(channels=[asdict(c) for c in channels],
        aspects=[asdict(a) for a in aspects],support=support,limit=5)).encode("utf-8"))
    return dict(channels=8,candidate_union=100,aspects=32,limit=5,nanoseconds=durations,
        median_ms=statistics.median(durations)/1e6,
        serialized_input_bytes=input_bytes,serialized_output_bytes=len(json.dumps(asdict(report)).encode("utf-8")),
        scope="pure function only, rank normalization and selection; not model/DB/serialization timing")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out",required=True,type=Path)
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    data = FIXTURE.read_bytes()
    (out/"frozen-cases.json").write_bytes(data)
    (out/"harness.py").write_bytes(Path(__file__).read_bytes())
    cases = json.loads(data)["cases"]
    assert len(cases)==6 and sum(c["necessary_ids"] is not None for c in cases)==5
    git = ["git","-c","safe.directory="+REPO.as_posix(),"-C",str(REPO)]
    head = subprocess.check_output(git+["rev-parse","HEAD"],text=True).strip()
    protocol = dict(source_commit=head,module_path=LOCAL_MODULE,
        working_tree_status=subprocess.check_output(git+["status","--porcelain"],text=True).splitlines(),
        fixture=str(FIXTURE),trajectory_count=6,eligible_trajectories=5,
        primary_configurations=24,channel_reference_configurations=24,
        no_generated_support=True,no_answer_generation=True,no_retrieval_quality_claim=True,
        no_subagents=True,no_remote_push=True,
        scope="explicit fixed rankings/support; 48 repeat configurations, not 48 independent tasks")
    (out/"protocol.json").write_text(json.dumps(protocol,indent=2)+"\n",encoding="utf-8")
    rows = [evaluate(case,backend,out) for case in cases for backend in ("dict","sqlite")]
    summary = {}
    for backend in ("dict","sqlite"):
        eligible = [r for r in rows if r["backend"]==backend and r["necessary_ids"] is not None]
        counts = {method:sum(next(m["necessary_complete"] for m in r["methods"] if m["method"]==method)
                             for r in eligible) for method in PRIMARY}
        gains=[];losses=[]
        for r in eligible:
            original, selected = r["methods"][:2]
            if selected["necessary_complete"] and not original["necessary_complete"]:gains.append(r["name"])
            if original["necessary_complete"] and not selected["necessary_complete"]:losses.append(r["name"])
        summary[backend]=dict(eligible=5,complete=counts,gains=gains,losses=losses)
    assert summary["dict"]==summary["sqlite"]
    negative = next(r for r in rows if r["name"]=="necessary_time_chain_negative")
    assert negative["report"]["selection"]["selected_ids"]==("A","B")
    nonoptimal = next(r for r in rows if r["name"]=="greedy_nonoptimal")
    assert abs(nonoptimal["report"]["selection"]["objective"]-5/6)<=1e-12
    assert nonoptimal["optimal_proxy"]==1
    performance = timing()
    result = dict(protocol=protocol,rows=rows,summary=summary,timing=performance,
                  configurations=sum(len(r["methods"]) for r in rows),complete=True)
    assert result["configurations"]==48
    (out/"results.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(summary=summary,configs=48,state_checks=12,timing=performance),indent=2))


if __name__=="__main__":
    main()
