"""Retrieval diagnostics mixin: quality, trace, community and schema reports."""
# mypy: disable-error-code="attr-defined"

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime


class RetrievalDiagnosticsMixin:
    def retrieval_quality(
        self,
        queries: list[str] | None = None,
        top_k: int = 5,
        now: datetime | None = None,
        limit: int = 10,
    ) -> dict:
        """Measure retrieval quality across a set of queries.

        Metacognitive monitoring of retrieval (Koriat & Goldsmith, 1996):
        run the real recall pipeline over known queries and report average
        top score, top retrievability, hit rate and weak rate.
        """
        if not queries:
            queries = [
                item.cues[0]
                for item in self.store.all_active()
                if item.cues
            ][: max(1, int(limit))]
        top_scores = []
        top_retrievability = []
        hit_count = 0
        weak_count = 0
        for query in queries:
            results = self.recall(query, top_k=max(1, int(top_k)), now=now)
            if not results:
                weak_count += 1
                continue
            top = results[0]
            top_scores.append(top.score)
            top_retrievability.append(
                self.curve.retrievability(top.item, now)
            )
            if any(
                "overlap" in reason or "semantic" in reason
                for reason in top.reasons
            ):
                hit_count += 1
            else:
                weak_count += 1
        evaluated = len(queries)
        hit_rate = (
            round(hit_count / evaluated, 3) if evaluated else 0.0
        )
        weak_rate = (
            round(weak_count / evaluated, 3) if evaluated else 0.0
        )
        verdict = (
            "good" if hit_rate >= 0.8 else (
                "fair" if hit_rate >= 0.5 else "poor"
            )
        )
        return {
            "queries_evaluated": evaluated,
            "hit_count": hit_count,
            "weak_count": weak_count,
            "avg_top_score": round(
                sum(top_scores) / max(1, len(top_scores)), 3
            ),
            "avg_top_retrievability": round(
                sum(top_retrievability) / max(1, len(top_retrievability)),
                3,
            ),
            "hit_rate": hit_rate,
            "weak_rate": weak_rate,
            "verdict": verdict,
        }

    def recall_trace(
        self,
        query: str,
        top_k: int = 5,
    ) -> dict:
        """Explain why a query recalls what it recalls.

        Metacognitive explanation (Koriat & Goldsmith, 1996): show how
        many candidates were scanned, the top results with scores and
        per-result reasons, so agents can audit their own retrieval.
        """
        candidates = self.store.all_active()
        results = self.recall(query, top_k=max(1, int(top_k)))
        traced = [
            {
                "id": result.item.id,
                "preview": result.item.content[:40],
                "score": round(result.score, 3),
                "confident": result.confident,
                "reasons": result.reasons[:6],
            }
            for result in results
        ]
        top = traced[0] if traced else None
        return {
            "query": query,
            "candidates_scanned": len(candidates),
            "results": traced,
            "top_reason_summary": (
                "; ".join(top["reasons"][:3]) if top else None
            ),
        }

    def community_report(
        self,
        limit: int = 10,
    ) -> dict:
        """Detect memory communities in the association network.

        Semantic networks have modular structure (community detection):
        strongly linked memories form clusters. This uses connected
        components so agents can see which memories form a theme-cluster
        and which are isolated.
        """

        items = self.store.all_active()
        parent = {item.id: item.id for item in items}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for src, dst, _weight in self.backend.all_links():
            if src in parent and dst in parent:
                union(src, dst)
        groups: dict[str, list] = defaultdict(list)
        for item in items:
            groups[find(item.id)].append(item)
        communities: list[dict] = []
        for root, members in groups.items():
            cue_counts: Counter = Counter()
            for member in members:
                for cue in member.cues:
                    cue_counts[cue] += 1
            communities.append(
                {
                    "id": root,
                    "size": len(members),
                    "members": [
                        {
                            "id": member.id,
                            "preview": member.content[:24],
                        }
                        for member in members[:4]
                    ],
                    "top_cues": [
                        cue for cue, _count in cue_counts.most_common(3)
                    ],
                }
            )
        communities.sort(key=lambda community: -community["size"])
        return {
            "total_communities": len(communities),
            "largest_size": (
                communities[0]["size"] if communities else 0
            ),
            "communities": communities[: max(1, int(limit))],
        }

    def schema_report(self, limit: int = 20) -> dict:
        """Group memories into topic schemas by their primary cue.

        Schema theory (Bartlett, 1932; event schemas, Gilboa & Marlatte,
        2017): the mind organizes related experiences under shared
        scripts/topics. This report clusters active memories by their
        primary cue and shows each cluster's size, average importance,
        kind mix and content samples, so agents can see what topics their
        memory store actually covers.
        """
        groups: dict[str, dict] = {}
        for item in self.store.all_active():
            topic = item.cues[0] if item.cues else "（无标签）"
            group = groups.setdefault(
                topic,
                {
                    "topic": topic,
                    "memory_count": 0,
                    "avg_importance": 0.0,
                    "kinds": {"semantic": 0, "episodic": 0},
                    "samples": [],
                },
            )
            group["memory_count"] += 1
            group["avg_importance"] += item.importance
            group["kinds"][item.kind.value] += 1
            if len(group["samples"]) < 3:
                group["samples"].append(item.content[:24])
        out = []
        for group in groups.values():
            group["avg_importance"] = round(
                group["avg_importance"] / group["memory_count"], 3
            )
            out.append(group)
        out.sort(key=lambda g: (-g["memory_count"], g["topic"]))
        return {
            "total_memories": len(self.store.all_active()),
            "group_count": len(out),
            "top_groups": out[: max(1, int(limit))],
        }
