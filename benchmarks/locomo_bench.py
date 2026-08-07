"""LoCoMo-style long-conversation memory evaluation for Mnemosis.

Deterministic synthetic persona conversations spanning many sessions:
stable facts (semantic) plus dated events (episodic). Question types:

  - fact      : semantic recall of persona facts
  - event     : episodic recall of a specific dated event
  - temporal  : event-ordering reasoning (both events must be retrieved)
  - distractor: never-mentioned topics (must be reported as gaps)

Metrics: retrieval hit@1 / hit@5 per category, distractor pass rate, and
(optionally) LLM answer accuracy with and without Mnemosis grounding.

Usage:
    python benchmarks/locomo_bench.py                      # retrieval only
    python benchmarks/locomo_bench.py --with-llm           # + local LLM eval
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from collections import defaultdict
from datetime import date, timedelta

from mnemosis import MemoryEngine
from mnemosis.embedding import NGramEmbedder
from mnemosis.types import MemoryKind, SourceRecord, SourceType

from bm25_baseline import Bm25Index
from embedding_baseline import EmbeddingBaseline

try:
    from compare_with_models import ollama_generate, score_answer  # script mode
except ImportError:  # package mode (e.g. from tests)
    from benchmarks.compare_with_models import ollama_generate, score_answer


COLORS = ["teal", "amber", "indigo", "coral", "olive", "plum", "mint", "rust"]
FOODS = ["ramen", "tacos", "pad thai", "borscht", "couscous", "dim sum"]
CITIES = ["Kyoto", "Lyon", "Oslo", "Valencia", "Quebec", "Chiang Mai"]
PLACES = [
    "botanical garden", "aquarium", "art museum", "planetarium", "old town",
    "harbor", "national park", "opera house",
]
ITEMS = [
    "notebook", "camera", "coffee beans", "hiking boots", "vinyl record",
    "sketchbook",
]
UNUSED_TOPICS = ["music genre", "sports team", "season", "dessert"]


def make_person(rng: random.Random, name: str) -> dict:
    return {
        "name": name,
        "color": rng.choice(COLORS),
        "food": rng.choice(FOODS),
        "city": rng.choice(CITIES),
        "hobby": rng.choice(PLACES),
        "drink": rng.choice(ITEMS),
        "birthday": "April 12",
    }


def _event(rng: random.Random, person: str, day: date) -> tuple[dict, str]:
    date_str = day.isoformat()
    template = rng.choice(["visit", "dinner", "purchase"])
    if template == "visit":
        obj = rng.choice(PLACES)
        content = f"{person} visited {obj} on {date_str}."
    elif template == "dinner":
        obj = rng.choice(FOODS)
        content = f"{person} had {obj} for dinner on {date_str}."
    else:
        obj = rng.choice(ITEMS)
        content = f"{person} bought {obj} on {date_str}."
    return {
        "content": content,
        "person": person,
        "date": date_str,
        "kind": "episodic",
        "cues": [person.lower(), date_str],
        "answer": obj,
    }, template


def generate_dataset(
    seed: int = 42,
    sessions: int = 24,
    events_per_session: int = 5,
) -> dict:
    rng = random.Random(seed)
    names = ["Alice", "Bob", "王芳", "Lina"]
    persons = [make_person(rng, name) for name in names]

    facts: list[dict] = []
    questions: list[dict] = []
    for person in persons:
        for key in ("color", "food", "city", "hobby", "drink", "birthday"):
            if key == "birthday":
                content = f"{person['name']}'s birthday is {person['birthday']}."
                question = f"When is {person['name']}'s birthday?"
            else:
                content = f"{person['name']}'s favorite {key} is {person[key]}."
                question = f"What is {person['name']}'s favorite {key}?"
            facts.append(
                {
                    "content": content,
                    "person": person["name"],
                    "kind": "semantic",
                    "cues": [person["name"].lower(), key],
                }
            )
            questions.append(
                {
                    "kind": "fact",
                    "q": question,
                    "answer": person[key],
                    "expected": [content],
                }
            )

    events: list[dict] = []
    start = date(2026, 2, 1)
    for session in range(sessions):
        session_start = start + timedelta(days=session * 7)
        person = rng.choice(persons)["name"]
        session_events: list[dict] = []
        for offset in range(events_per_session):
            day = session_start + timedelta(days=offset)
            event, _ = _event(rng, person, day)
            event["session"] = session
            event["cues"] = [person.lower(), day.isoformat(), f"session{session}"]
            events.append(event)
            session_events.append(event)

        picked = session_events[rng.randrange(len(session_events))]
        if "visited" in picked["content"]:
            question = f"Where did {person} go on {picked['date']}?"
        elif "dinner" in picked["content"]:
            question = f"What did {person} have for dinner on {picked['date']}?"
        else:
            question = f"What did {person} buy on {picked['date']}?"
        questions.append(
            {
                "kind": "event",
                "q": question,
                "answer": picked["answer"],
                "expected": [picked["content"]],
            }
        )

        if len(session_events) >= 2:
            i = rng.randrange(len(session_events) - 1)
            first, second = session_events[i], session_events[i + 1]
            questions.append(
                {
                    "kind": "temporal",
                    "q": (
                        f"After {_action_clause(first, person)} "
                        f"on {first['date']}, "
                        f"what did {person} do next?"
                    ),
                    "answer": second["answer"],
                    "expected": [first["content"], second["content"]],
                }
            )

    for person in persons:
        for topic in UNUSED_TOPICS:
            questions.append(
                {
                    "kind": "distractor",
                    "q": f"What is {person['name']}'s favorite {topic}?",
                    "answer": "unknown",
                    "expected": [],
                }
            )

    return {
        "seed": seed,
        "sessions": sessions,
        "events_per_session": events_per_session,
        "persons": persons,
        "facts": facts,
        "events": events,
        "questions": questions,
    }


def _action_clause(event: dict, person: str) -> str:
    content = event["content"]
    if "visited" in content:
        return f"visiting {event['answer']}"
    if "dinner" in content:
        return f"having {event['answer']} for dinner"
    return f"buying {event['answer']}"


def build_engine(dataset: dict, embedder=None) -> MemoryEngine:
    engine = MemoryEngine(embedder=embedder)
    user = SourceRecord(origin=SourceType.USER)
    for memory in dataset["facts"] + dataset["events"]:
        importance = 0.8 if memory["kind"] == "semantic" else 0.5
        engine.remember(
            memory["content"],
            kind=MemoryKind(memory["kind"]),
            source=user,
            cues=memory.get("cues"),
            importance=importance,
        )
    return engine


def eval_retrieval(
    engine: MemoryEngine,
    questions: list[dict],
    top_k: int = 5,
    now=None,
    pattern_completion: bool = True,
    kind_preference: bool = False,
) -> dict:
    stats: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "hit1": 0, "hit5": 0, "pass": 0, "anchor5": 0, "mrr": 0.0}
    )
    details = []
    for question in questions:
        kind = question["kind"]
        stats[kind]["n"] += 1
        if kind == "distractor":
            gaps = engine.check(question["q"]).gaps
            passed = bool(gaps)
            stats[kind]["pass"] += int(passed)
            details.append({"kind": kind, "q": question["q"], "pass": passed})
            continue
        results = engine.recall(
            question["q"],
            top_k=top_k,
            now=now,
            pattern_completion=pattern_completion,
            kind_preference=kind_preference,
        )
        contents = [r.item.content for r in results]
        expected = question["expected"]
        hit1 = bool(results) and contents[0] == expected[0]
        hit5 = all(item in contents for item in expected)
        anchor5 = bool(results) and expected[0] in contents
        rank = 0
        for index, content in enumerate(contents, start=1):
            if content == expected[0]:
                rank = index
                break
        mrr = 1.0 / rank if rank else 0.0
        stats[kind]["hit1"] += int(hit1)
        stats[kind]["hit5"] += int(hit5)
        stats[kind]["anchor5"] += int(anchor5)
        stats[kind]["mrr"] += mrr
        details.append(
            {
                "kind": kind,
                "q": question["q"],
                "hit1": hit1,
                "hit5": hit5,
                "anchor5": anchor5,
                "mrr": round(mrr, 3),
                "top": contents[:top_k],
            }
        )
    return {"stats": dict(stats), "details": details}


def eval_baseline(
    questions: list[dict],
    search_fn,
    top_k: int = 5,
    pass_fn=None,
) -> dict:
    """Evaluate a plain ranked baseline (BM25 / embedding kNN) on the questions."""
    stats: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "hit1": 0, "hit5": 0, "pass": 0}
    )
    for question in questions:
        kind = question["kind"]
        stats[kind]["n"] += 1
        results = search_fn(question["q"], top_k)
        contents = [content for content, _ in results]
        if kind == "distractor":
            passed = pass_fn(results) if pass_fn else (not contents)
            stats[kind]["pass"] += int(passed)
            continue
        expected = question["expected"]
        stats[kind]["hit1"] += int(bool(contents) and contents[0] == expected[0])
        stats[kind]["hit5"] += int(all(item in contents for item in expected))
    return {"stats": dict(stats), "details": []}


def eval_bm25(dataset: dict, questions: list[dict], top_k: int = 5) -> dict:
    """Evaluate a plain BM25 index on the same questions (no memory logic)."""
    index = Bm25Index(dataset["facts"] + dataset["events"])
    return eval_baseline(
        questions,
        index.search,
        top_k=top_k,
        pass_fn=lambda results: (results[0][1] == 0.0) if results else True,
    )


def eval_embedding(dataset: dict, questions: list[dict], top_k: int = 5) -> dict:
    """Evaluate pure embedding kNN (naive vector-store RAG)."""
    index = EmbeddingBaseline(dataset["facts"] + dataset["events"])
    return eval_baseline(
        questions,
        index.search,
        top_k=top_k,
        pass_fn=lambda results: (results[0][1] < 0.15) if results else True,
    )


def eval_with_llm(
    engine: MemoryEngine,
    questions: list[dict],
    models: list[str],
    url: str,
    timeout: int,
    limit: int,
    context_k: int = 3,
) -> list[dict]:
    chosen: list[dict] = []
    for kind in ("fact", "event", "temporal", "distractor"):
        pool = [q for q in questions if q["kind"] == kind]
        chosen.extend(pool[: max(1, limit // 4)])
    chosen = chosen[:limit]

    rows = []
    for model in models:
        for condition in ("llm_alone", "llm_with_mnemosis"):
            hits = 0
            elapsed = 0.0
            details: list[dict] = []
            for question in chosen:
                if condition == "llm_alone":
                    prompt = (
                        "Answer with only the requested fact. "
                        "If you do not know, answer 'unknown'.\n"
                        f"Question: {question['q']}"
                    )
                else:
                    k = (
                        context_k + 2
                        if question["kind"] == "temporal"
                        else context_k
                    )
                    results = engine.recall(question["q"], top_k=k)
                    if question["kind"] == "temporal":
                        def event_date(result) -> str:
                            match = re.search(
                                r"\d{4}-\d{2}-\d{2}", result.item.content
                            )
                            return (
                                match.group(0)
                                if match
                                else result.item.created_at.date().isoformat()
                            )

                        results.sort(key=event_date)
                        context = "\n".join(
                            f"- {event_date(r)}: {r.item.content}"
                            for r in results
                        )
                    else:
                        context = "\n".join(f"- {r.item.content}" for r in results)
                    prompt = (
                        "Answer using ONLY the memory context below. "
                        "If the context lacks the answer, answer 'unknown'.\n\n"
                        f"Context:\n{context}\n\nQuestion: {question['q']}"
                    )
                    if question["kind"] == "temporal":
                        prompt += (
                            "\nThe 'next' event is the one with the earliest "
                            "date strictly after the anchor date in the context."
                        )
                start = time.perf_counter()
                answer = ollama_generate(model, prompt, url, timeout)
                elapsed += time.perf_counter() - start
                score = score_answer(answer, question["answer"])
                hits += int(score >= 1.0)
                details.append(
                    {
                        "kind": question["kind"],
                        "question": question["q"],
                        "answer": answer,
                        "expected": question["answer"],
                        "score": round(score, 3),
                        "seconds": round(time.perf_counter() - start, 2),
                    }
                )
            rows.append(
                {
                    "approach": condition,
                    "model": model,
                    "n": len(chosen),
                    "accuracy": round(hits / len(chosen), 3),
                    "avg_seconds": round(elapsed / len(chosen), 2),
                    "details": details,
                }
            )
    return rows


def print_report(retrieval: dict, llm_rows: list[dict]) -> None:
    print("\n== Mnemosis retrieval ==")
    print(
        f"{'category':12s} {'n':>4s} {'hit@1':>7s} {'hit@5':>7s} "
        f"{'anchor@5':>9s} {'MRR':>7s} {'pass':>6s}"
    )
    totals = {"n": 0, "hit1": 0, "hit5": 0, "pass": 0, "anchor5": 0, "mrr": 0.0}
    for kind, values in sorted(retrieval["stats"].items()):
        n = values["n"]
        for key in totals:
            totals[key] += values[key]
        h1 = values["hit1"] / n if n else 0.0
        h5 = values["hit5"] / n if n else 0.0
        anchor5 = values["anchor5"] / n if n else 0.0
        mrr = values["mrr"] / n if n else 0.0
        print(
            f"{kind:12s} {n:>4d} {h1:>7.3f} {h5:>7.3f} "
            f"{anchor5:>9.3f} {mrr:>7.3f} {values['pass']:>6d}"
        )
    print(
        f"{'total':12s} {totals['n']:>4d} "
        f"{totals['hit1'] / totals['n']:>7.3f} "
        f"{totals['hit5'] / totals['n']:>7.3f} "
        f"{totals['anchor5'] / totals['n']:>9.3f} "
        f"{totals['mrr'] / totals['n']:>7.3f}"
    )
    if llm_rows:
        print("\n== LLM answer accuracy ==")
        print(
            f"{'approach':20s} {'model':16s} {'n':>4s} "
            f"{'mean(min-max)':>18s} {'avg s':>7s}"
        )
        for row in llm_rows:
            if "min" in row:
                acc_text = (
                    f"{row['accuracy']:.3f} "
                    f"({row['min']:.3f}-{row['max']:.3f})"
                )
            else:
                acc_text = f"{row['accuracy']:.3f}"
            print(
                f"{row['approach']:20s} {row['model']:16s} {row['n']:>4d} "
                f"{acc_text:>18s} {row['avg_seconds']:>7.2f}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sessions", type=int, default=24)
    parser.add_argument("--events-per-session", type=int, default=5)
    parser.add_argument("--with-llm", action="store_true")
    parser.add_argument(
        "--mode",
        choices=["both", "keyword", "ngram"],
        default="both",
        help="which Mnemosis retrieval modes to evaluate",
    )
    parser.add_argument(
        "--no-baselines",
        action="store_true",
        help="skip BM25 and embedding-kNN baselines (large-scale runs)",
    )
    parser.add_argument(
        "--sleep",
        action="store_true",
        help="run engine.sleep() after ingestion, before evaluation",
    )
    parser.add_argument("--models", nargs="+", default=["gemma3:12b"])
    parser.add_argument("--url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--llm-questions", type=int, default=12)
    parser.add_argument("--llm-context-k", type=int, default=3)
    parser.add_argument(
        "--llm-rounds",
        type=int,
        default=1,
        help="repeat the LLM eval N times and report mean/min/max accuracy",
    )
    parser.add_argument(
        "--no-pattern-completion",
        action="store_true",
        help="disable hippocampal pattern completion (A/B control)",
    )
    parser.add_argument(
        "--kind-preference",
        action="store_true",
        help="enable gist/verbatim kind preference (A/B control, default off)",
    )
    parser.add_argument(
        "--llm-embedder",
        choices=["keyword", "ngram"],
        default="ngram",
        help="retrieval mode used to build LLM grounding context",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__),
            "results",
            f"locomo_{time.strftime('%Y%m%d_%H%M%S')}.json",
        ),
    )
    args = parser.parse_args()

    dataset = generate_dataset(args.seed, args.sessions, args.events_per_session)
    print(
        f"dataset: {len(dataset['facts'])} facts, {len(dataset['events'])} events, "
        f"{len(dataset['questions'])} questions"
    )

    reports = {}
    modes = [("keyword", None), ("ngram", NGramEmbedder())]
    if args.mode == "keyword":
        modes = modes[:1]
    elif args.mode == "ngram":
        modes = modes[1:]
    for label, embedder in modes:
        engine = build_engine(dataset, embedder=embedder)
        if args.sleep:
            engine.sleep()
        reports[label] = eval_retrieval(
            engine,
            dataset["questions"],
            pattern_completion=not args.no_pattern_completion,
            kind_preference=args.kind_preference,
        )
        print(f"\n-- retrieval with {label} --")
        print_report(reports[label], [])
        engine.close()

    llm_rows = []
    if args.with_llm:
        llm_embedder = (
            NGramEmbedder() if args.llm_embedder == "ngram" else None
        )
        llm_engine = build_engine(dataset, embedder=llm_embedder)
        rounds_results: dict[tuple[str, str], list[dict]] = {}
        for _ in range(max(1, args.llm_rounds)):
            for row in eval_with_llm(
                llm_engine,
                dataset["questions"],
                args.models,
                args.url,
                args.timeout,
                args.llm_questions,
                args.llm_context_k,
            ):
                rounds_results.setdefault(
                    (row["approach"], row["model"]), []
                ).append(row)
        for key, rows in rounds_results.items():
            accuracies = [row["accuracy"] for row in rows]
            llm_rows.append(
                {
                    "approach": key[0],
                    "model": key[1],
                    "n": rows[0]["n"],
                    "accuracy": round(sum(accuracies) / len(accuracies), 3),
                    "min": round(min(accuracies), 3),
                    "max": round(max(accuracies), 3),
                    "avg_seconds": round(
                        sum(row["avg_seconds"] for row in rows) / len(rows), 2
                    ),
                    "rounds": len(rows),
                }
            )
        llm_engine.close()
    summary_report = reports.get("keyword") or reports.get("ngram") or {}
    print_report(summary_report, llm_rows)

    bm25 = None
    embedding = None
    if not args.no_baselines:
        print("\n== BM25 baseline (hippo-memory-style retrieval) ==")
        bm25 = eval_bm25(dataset, dataset["questions"])
        print("\n== embedding kNN baseline (naive vector store) ==")
        embedding = eval_embedding(dataset, dataset["questions"])
        print(
            f"{'category':12s} {'n':>4s} {'hit@1':>7s} {'hit@5':>7s} {'pass':>6s}"
        )
        for label, report in (("bm25", bm25), ("embedding", embedding)):
            print(f"-- {label} --")
            for kind, values in sorted(report["stats"].items()):
                n = values["n"]
                print(
                    f"{kind:12s} {n:>4d} "
                    f"{values['hit1'] / n if n else 0.0:>7.3f} "
                    f"{values['hit5'] / n if n else 0.0:>7.3f} "
                    f"{values['pass']:>6d}"
                )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "dataset": {
                    "seed": args.seed,
                    "sessions": args.sessions,
                    "events_per_session": args.events_per_session,
                    "facts": len(dataset["facts"]),
                    "events": len(dataset["events"]),
                    "questions": len(dataset["questions"]),
                },
                "retrieval": {
                    label: {"stats": reports[label]["stats"]}
                    for label in reports
                },
                "bm25": (
                    {"stats": bm25["stats"]} if bm25 is not None else None
                ),
                "embedding_knn": (
                    {"stats": embedding["stats"]}
                    if embedding is not None
                    else None
                ),
                "llm": llm_rows,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\nresults saved to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
