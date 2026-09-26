"""Re-score retained rankings using official abstention markers; paired CIs."""
import argparse
import json
import math
import random
from pathlib import Path
from bm25_cue_eval import is_answerable, summarize


def paired(rows, treatment, control, metric):
    qa=[r for r in rows if r["answerable"]]
    deltas=[int(r["modes"][treatment][metric])-int(r["modes"][control][metric]) for r in qa]
    rng=random.Random(20260926)
    samples=sorted(sum(rng.choices(deltas,k=len(deltas)))/len(deltas) for _ in range(5000))
    wins=[r["qid"] for r,d in zip(qa,deltas) if d==1]
    losses=[r["qid"] for r,d in zip(qa,deltas) if d==-1]
    n=len(wins)+len(losses)
    p=min(1,2*sum(math.comb(n,k) for k in range(min(len(wins),len(losses))+1))/2**n) if n else 1
    return dict(treatment=treatment,control=control,metric=metric,n=len(qa),wins=wins,losses=losses,
                difference=sum(deltas)/len(deltas),bootstrap_95=[samples[124],samples[4874]],
                mcnemar_exact_p=p)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--results-dir",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    report={"metric_note":"Official _abs IDs excluded even if incidental has_answer flags exist. Strict original turn identity. No answer generation. Confidence intervals descriptive, unadjusted for multiple comparisons.",
            "latency_note":"Main comparisons ran sequentially on one snapshot; caches differ between methods, so mode ms are diagnostic, not fair speed comparisons. See separate scale report for BM25 cold/warm cost.","splits":{}}
    for split in ("dev","holdout"):
        raw=json.loads((args.results_dir/f"phase2_{split}_final.json").read_text(encoding="utf-8"))
        assert raw["complete"]
        rows=raw["rows"]
        corrections=[]
        for row in rows:
            value=is_answerable(row["qid"],row["gold_refs"])
            if value!=row["answerable"]:corrections.append(row["qid"])
            row["answerable"]=value
        summary=summarize(rows,raw["protocol"]["modes"])
        for mode,metrics in summary["modes"].items():
            metrics["hit5_all_questions"]=sum(r["answerable"] and r["modes"][mode]["hit5"] for r in rows)/len(rows)
        comparisons=[paired(rows,treatment,control,metric)
                     for treatment,control in (("bm25","ngram"),("bm25_ngram_bounded","ngram"),("bm25_ngram_bounded","legacy_hybrid"),("bm25_ngram_bounded","bm25"))
                     for metric in ("hit1","hit5","hit10")]
        by_type={}
        for kind in sorted({r["type"] for r in rows}):
            subset=[r for r in rows if r["type"]==kind and r["answerable"]]
            if subset:by_type[kind]=summarize(subset,raw["protocol"]["modes"])
        report["splits"][split]={"summary":summary,"answerability_corrections":corrections,
            "comparisons":comparisons,"by_type":by_type,"rows":rows}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({s:r["summary"] for s,r in report["splits"].items()},indent=2))

if __name__=="__main__":main()
