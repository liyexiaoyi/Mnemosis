"""Planning mixin: intents, goal replay, plans and numeric reasoning."""

from __future__ import annotations

import math
import random
import re
import threading
import uuid
from collections import Counter, defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from itertools import combinations

from .association import AssociationIndex
from .backend import Backend, make_backend
from .consolidation import ConsolidationReport, Consolidator
from .dual_track import DualTrackStore
from .embedding import Embedder
from .forgetting import ForgettingCurve, ReviewScheduler
from .importance import ImportanceScorer
from .metacognition import ConfidenceLabel, Metacognition, MetacognitiveCheck
from .reasoning import suggested_pack_size
from .recycle import RecycleBin
from .schema import EventChainIndex
from .types import (
    MemoryItem,
    MemoryKind,
    MemoryStatus,
    RecallResult,
    SourceRecord,
    SourceType,
    extract_cues,
    hash_content,
    normalize_cues,
    tokenize,
    utcnow,
)
from .zh_nlp import expand_synonyms, has_cjk



class PlanningMixin:
    def remember_intent(
        self,
        content: str,
        due_at: datetime,
        *,
        context_cue: str | None = None,
        importance: float = 0.5,
        now: datetime | None = None,
    ) -> dict:
        """Register a future intention (prospective memory).

        Prospective memory is the capacity to remember to carry out an
        intended action at the right later moment (Einstein & McDaniel,
        1990): the intent stays in a small register with its deadline and
        optional context cue, and surfaces when due instead of being
        reinforced like a past fact.
        """

        now = now or utcnow()
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)
        record = {
            "id": uuid.uuid4().hex,
            "content": content.strip(),
            "due_at": due_at.isoformat(),
            "context_cue": (context_cue or "").strip() or None,
            "importance": max(0.0, min(1.0, float(importance))),
            "created_at": now.isoformat(),
            "status": "active",
            "completed_at": None,
        }
        with self._lock:
            self._intents[record["id"]] = record
        return dict(record)
    def intent_due(
        self,
        now: datetime | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Return active intents whose deadline has arrived."""

        now = now or utcnow()
        with self._lock:
            due = [
                r for r in self._intents.values()
                if r["status"] == "active"
                and datetime.fromisoformat(r["due_at"]) <= now
            ]
        due.sort(key=lambda r: r["due_at"])
        return [dict(r) for r in due[: max(1, int(limit))]]
    def complete_intent(
        self,
        intent_id: str,
        now: datetime | None = None,
    ) -> dict | None:
        """Mark an intent as completed."""
        now = now or utcnow()
        with self._lock:
            record = self._intents.get(intent_id)
            if record is None or record["status"] != "active":
                return None
            record["status"] = "completed"
            record["completed_at"] = now.isoformat()
        return dict(record)
    def cancel_intent(self, intent_id: str) -> dict | None:
        """Cancel an intent without completing it."""
        with self._lock:
            record = self._intents.get(intent_id)
            if record is None or record["status"] != "active":
                return None
            record["status"] = "cancelled"
        return dict(record)
    def intent_report(self, now: datetime | None = None) -> dict:
        """Summarize the intention register (due / upcoming / done)."""

        now = now or utcnow()
        with self._lock:
            all_intents = list(self._intents.values())
        active = [
            r for r in all_intents if r["status"] == "active"
        ]
        overdue = [
            r for r in active if datetime.fromisoformat(r["due_at"]) <= now
        ]
        upcoming = [
            r for r in active if datetime.fromisoformat(r["due_at"]) > now
        ]
        upcoming.sort(key=lambda r: r["due_at"])
        return {
            "active": len(active),
            "completed": sum(
                1 for r in all_intents
                if r["status"] == "completed"
            ),
            "cancelled": sum(
                1 for r in all_intents
                if r["status"] == "cancelled"
            ),
            "overdue": len(overdue),
            "next_upcoming": (
                dict(upcoming[0]) if upcoming else None
            ),
        }
    def intent_conflicts(
        self,
        time_window_minutes: int = 60,
    ) -> dict:
        """Detect intention clashes (time or context collisions).

        Prospective memory must schedule actions without collisions: two
        intentions due within a short window (Einstein & McDaniel, 1990)
        or sharing the same context cue risk one being forgotten. This
        tool reports both kinds so the agent can reschedule.
        """

        with self._lock:
            active = [
                r for r in self._intents.values() if r["status"] == "active"
            ]
        conflicts = []
        for i in range(len(active)):
            a = active[i]
            for b in active[i + 1:]:
                ta = datetime.fromisoformat(a["due_at"])
                tb = datetime.fromisoformat(b["due_at"])
                gap = abs((ta - tb).total_seconds()) / 60.0
                if gap < max(1, int(time_window_minutes)):
                    conflicts.append(
                        {
                            "type": "time",
                            "intent_a": a["id"],
                            "intent_b": b["id"],
                            "gap_minutes": round(gap, 1),
                        }
                    )
                if (
                    a.get("context_cue")
                    and a["context_cue"] == b.get("context_cue")
                ):
                    conflicts.append(
                        {
                            "type": "context",
                            "intent_a": a["id"],
                            "intent_b": b["id"],
                            "cue": a["context_cue"],
                }
            )
        return {"total": len(conflicts), "conflicts": conflicts}
    def action_queue(
        self,
        now: datetime | None = None,
        limit: int = 20,
    ) -> dict:
        """Order active intentions as an action queue.

        Goal-directed behavior prioritizes urgent tasks (ACT-R, Anderson,
        1983): overdue first, then upcoming by deadline, with clashing
        intentions flagged for rescheduling.
        """

        now = now or utcnow()
        conflicts = self.intent_conflicts()["conflicts"]
        clash_ids = {
            c["intent_a"] for c in conflicts
        } | {c["intent_b"] for c in conflicts}
        actions = []
        with self._lock:
            intent_records = list(self._intents.values())
        for record in intent_records:
            if record["status"] != "active":
                continue
            due = datetime.fromisoformat(record["due_at"])
            actions.append(
                {
                    "type": "intent",
                    "intent_id": record["id"],
                    "content": record["content"][:60],
                    "due_at": record["due_at"],
                    "overdue": due <= now,
                    "urgent": due <= now + timedelta(minutes=60),
                    "clash": record["id"] in clash_ids,
                }
            )
        actions.sort(key=lambda a: (not a["overdue"], a["due_at"]))
        return {
            "total": len(actions),
            "overdue": sum(1 for a in actions if a["overdue"]),
            "upcoming": sum(1 for a in actions if not a["overdue"]),
            "clashes": len(clash_ids),
            "actions": actions[: max(1, int(limit))],
        }
    def plan_quality(
        self,
        plan: list,
        context_memory_ids: list[str] | None = None,
    ) -> dict:
        """Score a Chinese agent plan's quality.

        Cognitive control decomposes goals into ordered sub-goals
        (Miller & Cohen, 2001); problem solving uses means-ends analysis
        (Newell & Simon, 1972). This checks step count, explicit action
        verbs, dependency ordering, duplicate steps and alignment with
        project memories.
        """

        steps = []
        for item in plan:
            if isinstance(item, str):
                text = item
            else:
                text = item.get("step") or item.get("action") or ""
            text = str(text).strip()
            if text:
                steps.append(text)
        if not steps:
            return {
                "score": 0,
                "verdict": "empty",
                "step_count": 0,
                "has_verbs": False,
                "has_ordering": False,
                "context_alignment": 0.0,
                "duplicate_steps": False,
                "suggestions": ["计划为空，先写第一步"],
            }
        verb_hits = sum(
            1 for step in steps
            if any(verb in step for verb in self._PLAN_VERBS)
        )
        has_verbs = verb_hits == len(steps)
        verb_score = 30.0 * verb_hits / len(steps)
        prev_anchors = []
        has_ordering = False
        for step in steps:
            if any(anchor in step for anchor in prev_anchors):
                has_ordering = True
                break
            prev_anchors.append(step[:8])
        duplicate_steps = len(steps) != len(set(steps))
        implicit_order = (
            len(steps) >= 4
            and verb_hits == len(steps)
            and not duplicate_steps
        )
        order_score = 15.0 if (has_ordering or implicit_order) else 5.0
        dup_penalty = 10.0 if duplicate_steps else 0.0
        context_terms: set[str] = set()
        if context_memory_ids:
            for memory_id in context_memory_ids:
                item = self.backend.get(memory_id)
                if item is not None:
                    context_terms |= set(tokenize(item.content))
        plan_terms = set()
        for step in steps:
            plan_terms |= set(tokenize(step))
        context_alignment = round(
            len(context_terms & plan_terms) / max(1, len(plan_terms)),
            3,
        ) if context_terms else 0.0
        context_score = 20.0 * min(1.0, context_alignment)
        count_penalty = (
            0.0 if 1 <= len(steps) <= 12
            else min(15.0, abs(len(steps) - 6))
        )
        score = max(
            0,
            min(
                100,
                int(round(
                    25 + verb_score + order_score + context_score
                    - count_penalty - dup_penalty
                )),
            ),
        )
        verdict = "good" if score >= 75 else (
            "fair" if score >= 50 else "weak"
        )
        suggestions = []
        if verb_hits < len(steps):
            suggestions.append("每步用明确动词开头（做/写/测试/部署…）")
        if not has_ordering:
            suggestions.append("让后面的步骤引用前面的产出，形成依赖链")
        if duplicate_steps:
            suggestions.append("去掉重复步骤")
        if context_memory_ids and context_alignment == 0:
            suggestions.append("计划与项目记忆没有重叠，检查是否跑题")
        return {
            "score": score,
            "verdict": verdict,
            "step_count": len(steps),
            "has_verbs": has_verbs,
            "has_ordering": has_ordering,
            "context_alignment": context_alignment,
            "duplicate_steps": duplicate_steps,
            "suggestions": suggestions[:4],
        }
    def project_brief(
        self,
        title: str,
        memory_ids: list[str] | None = None,
        limit: int = 8,
    ) -> dict:
        """Assemble a project brief from related memories and intentions.

        Starting a project activates relevant schemas (Bartlett, 1932):
        this gathers background, known requirements, known risks and
        pending actions so the agent can plan with full context.
        """
        if memory_ids:
            items = []
            for memory_id in memory_ids:
                item = self.backend.get(memory_id)
                if item is not None:
                    items.append(item)
        else:
            items = [
                result.item
                for result in self.recall(title, top_k=max(1, int(limit)))
            ]
        if not items:
            return {"title": title, "empty": True}
        background = [
            {"id": item.id, "preview": item.content[:40]}
            for item in items[: max(1, int(limit))]
        ]
        requirements = [
            {"id": item.id, "preview": item.content[:40]}
            for item in items
            if any(
                keyword in item.content
                for keyword in ("需求", "要求", "必须", "需要", "约束", "规格")
            )
        ]
        risks = [
            {"id": item.id, "preview": item.content[:40]}
            for item in items
            if any(
                keyword in item.content
                for keyword in ("风险", "问题", "担心", "冲突", "注意")
            )
        ]
        actions = self.action_queue(limit=3)["actions"]
        pending_actions = [
            {
                "intent_id": action["intent_id"],
                "content": action["content"],
                "overdue": action["overdue"],
            }
            for action in actions
        ]
        summary = (
            f"项目「{title}」：背景 {len(background)} 条、"
            f"需求 {len(requirements)} 条、风险 {len(risks)} 条、"
            f"待办 {len(pending_actions)} 件"
        )
        return {
            "title": title,
            "empty": False,
            "background": background,
            "requirements": requirements,
            "risks": risks,
            "pending_actions": pending_actions,
            "summary": summary,
        }
    def numeric_reasoning(
        self,
        problem: str,
        context_memory_ids: list[str] | None = None,
    ) -> dict:
        """Sanity-check numbers/units in a Chinese math or physics problem.

        Number sense relies on approximate quantity processing (Dehaene,
        1997) and physical intuition uses mental simulation
        (Johnson-Laird, 1983). This extracts numbers with units, flags
        unit mixes and division by zero, and cross-checks against known
        facts in memory (e.g. speed x time = distance).
        """

        pairs = re.findall(
            r"(\d+(?:\.\d+)?)\s*"
            r"(元|米|秒|千克|个|天|小时|公里|千米|分钟|%|斤|吨|升|毫升)",
            problem,
        )
        numbers = [
            {"value": float(value), "unit": unit}
            for value, unit in pairs
        ]
        chinese_numbers = re.findall(
            r"[零一二三四五六七八九十百千万]+", problem
        )
        checks = []
        units = [entry["unit"] for entry in numbers]
        if "米" in units and ("公里" in units or "千米" in units):
            checks.append(
                {
                    "type": "unit_mix",
                    "message": "同时出现米和公里/千米，注意 1 公里=1000 米",
                    "ok": False,
                }
            )
        if re.search(r"除以\s*0(?!\d)|÷\s*0(?!\d)", problem):
            checks.append(
                {
                    "type": "zero_division",
                    "message": "出现除以 0，结果无意义",
                    "ok": False,
                }
            )
        ctx_facts: list[dict] = []
        if context_memory_ids:
            for memory_id in context_memory_ids:
                item = self.backend.get(memory_id)
                if item is None:
                    continue
                speed_match = re.search(
                    r"(\d+(?:\.\d+)?)\s*(千米每小时|公里每小时|米每秒)",
                    item.content,
                )
                if speed_match:
                    ctx_facts.append(
                        {
                            "type": "speed",
                            "value": float(speed_match.group(1)),
                            "unit": speed_match.group(2),
                        }
                    )
        time_dist = re.search(
            r"(\d+(?:\.\d+)?)\s*小时(?:行驶|走|前进)"
            r"(\d+(?:\.\d+)?)\s*(千米|公里)",
            problem,
        )
        speed_ok = True
        if ctx_facts and time_dist:
            hours = float(time_dist.group(1))
            distance = float(time_dist.group(2))
            speed = ctx_facts[0]["value"]
            expected = speed * hours
            speed_ok = abs(expected - distance) / max(1.0, distance) < 0.05
            checks.append(
                {
                    "type": "memory_consistency",
                    "message": (
                        f"记忆速度 {speed:.0f}，{hours:.0f} 小时应走 "
                        f"{expected:.0f}，题面 {distance:.0f}"
                        + ("，一致" if speed_ok else "，不一致请复核")
                    ),
                    "ok": speed_ok,
                }
            )
        verdict = (
            "consistent"
            if all(check["ok"] for check in checks)
            else "review_needed"
        )
        return {
            "numbers": numbers,
            "chinese_numbers": chinese_numbers,
            "checks": checks,
            "verdict": verdict,
        }
    def plan_support(
        self,
        plan: list,
        top_k: int = 3,
    ) -> dict:
        """Retrieve supporting memories for each plan step.

        Working memory continuously pulls task-relevant information from
        long-term memory while executing a plan (Baddeley & Hitch, 1974):
        this returns per-step evidence so the agent acts with context.
        """
        steps = []
        for item in plan:
            if isinstance(item, str):
                text = item
            else:
                text = item.get("step") or item.get("action") or ""
            text = str(text).strip()
            if text:
                steps.append(text)
        out = []
        for step in steps:
            results = self.recall(step, top_k=max(1, int(top_k)))
            support = [
                {
                    "id": result.item.id,
                    "preview": result.item.content[:40],
                    "score": round(result.score, 3),
                }
                for result in results
            ]
            out.append(
                {
                    "step": step,
                    "support_count": len(support),
                    "support": support,
                }
            )
        return {
            "steps": out,
            "total_supported": sum(
                1 for entry in out if entry["support_count"] > 0
            ),
        }
    def dependency_map(
        self,
        plan: list,
    ) -> dict:
        """Build the dependency graph and critical path of a plan.

        Plans are hierarchical and ordered (Miller & Cohen, 2001); the
        critical-path method (CPM) finds which steps gate the finish.
        Each step may declare "depends_on" (0-based indices); otherwise
        references to earlier steps' keywords imply a dependency.
        """
        steps = []
        for item in plan:
            if isinstance(item, str):
                text = item
                declared = None
            else:
                text = item.get("step") or item.get("action") or ""
                declared = item.get("depends_on")
            text = str(text).strip()
            if text:
                steps.append((text, declared))
        if not steps:
            return {"steps": [], "critical_path": [], "parallel_groups": []}
        resolved: list[set[int]] = []
        anchors: list[str] = []
        for i, (text, declared) in enumerate(steps):
            deps: set[int] = set()
            if declared:
                for index in declared:
                    if 0 <= int(index) < i:
                        deps.add(int(index))
            else:
                for j, anchor in enumerate(anchors):
                    if anchor and anchor in text:
                        deps.add(j)
            resolved.append(deps)
            anchors.append(text[:8])
        level = [0] * len(steps)
        for i in range(len(steps)):
            for dep in resolved[i]:
                level[i] = max(level[i], level[dep] + 1)
        successors: list[list[int]] = [[] for _ in steps]
        for i, deps in enumerate(resolved):
            for dep in deps:
                successors[dep].append(i)
        # longest path from any start (critical path)
        starts = [i for i, deps in enumerate(resolved) if not deps]
        best: list[int] = []
        for start in starts:
            path = [start]
            while True:
                candidates = [
                    s for s in successors[path[-1]] if level[s] == level[path[-1]] + 1
                ]
                if not candidates:
                    break
                path.append(candidates[0])
            if len(path) > len(best):
                best = path
        critical_path = [
            {
                "index": i,
                "step": steps[i][0],
                "level": level[i],
            }
            for i in best
        ]
        by_level: dict[int, list[int]] = {}
        for i, lev in enumerate(level):
            by_level.setdefault(lev, []).append(i)
        parallel_groups = [
            {
                "level": lev,
                "step_indices": indices,
                "count": len(indices),
            }
            for lev, indices in sorted(by_level.items())
            if len(indices) > 1
        ]
        return {
            "steps": [
                {
                    "index": i,
                    "step": text,
                    "depends_on": sorted(deps),
                    "level": level[i],
                }
                for i, (text, _declared) in enumerate(steps)
            ],
            "critical_path": critical_path,
            "parallel_groups": parallel_groups,
            "finish_level": max(level) if level else 0,
        }
    def project_risk(
        self,
        memory_ids: list[str] | None = None,
        compare_limit: int = 20,
    ) -> dict:
        """Score project risk from memories and intention state.

        Risk management is memory-driven: known problem traces, conflicts,
        overdue intentions and clashing schedules all raise the risk score
        (0-100), with suggestions for mitigation.
        """

        if memory_ids:
            items = []
            for memory_id in memory_ids:
                item = self.backend.get(memory_id)
                if item is not None:
                    items.append(item)
        else:
            items = self.store.all_active()
        risk_memories = [
            {"id": item.id, "preview": item.content[:40]}
            for item in items
            if any(
                keyword in item.content
                for keyword in ("风险", "问题", "担心", "冲突", "注意",
                                "延期", "失败")
            )
        ]
        conflicts = 0
        compare_items = items[: max(2, int(compare_limit))]
        for a, b in combinations(compare_items, 2):
            verdict = self.compare_memories(a.id, b.id)["verdict"]
            if verdict == "conflict":
                conflicts += 1
        queue = self.action_queue(limit=10)
        overdue = queue["overdue"]
        clashes = queue["clashes"]
        score = min(
            100,
            len(risk_memories) * 10
            + conflicts * 15
            + overdue * 15
            + clashes * 10,
        )
        verdict = (
            "high" if score >= 60 else (
                "moderate" if score >= 30 else "low"
            )
        )
        suggestions = []
        if risk_memories:
            suggestions.append("有已知风险记忆，先逐条确认是否仍有效")
        if conflicts:
            suggestions.append("记忆之间存在冲突，需要查证并统一")
        if overdue:
            suggestions.append("有过期待办，先补上或明确取消")
        if clashes:
            suggestions.append("待办有时间/地点撞车，错开安排")
        return {
            "risk_score": score,
            "verdict": verdict,
            "factors": {
                "risk_memories": len(risk_memories),
                "conflicts": conflicts,
                "overdue_intents": overdue,
                "intent_clashes": clashes,
            },
            "risk_memory_previews": risk_memories[:5],
            "suggestions": suggestions[:4],
        }
    def plan_tracker(
        self,
        plan: list,
        statuses: dict | None = None,
    ) -> dict:
        """Track execution status of each plan step.

        Executing a plan requires monitoring progress toward goals
        (Miller & Cohen, 2001). Statuses are keyed by step index
        (pending / in_progress / done / blocked); a completion ratio is
        computed.
        """
        steps = []
        for item in plan:
            if isinstance(item, str):
                text = item
            else:
                text = item.get("step") or item.get("action") or ""
            text = str(text).strip()
            if text:
                steps.append(text)
        statuses = statuses or {}
        counts = {
            "pending": 0,
            "in_progress": 0,
            "done": 0,
            "blocked": 0,
        }
        tracked = []
        for i, step in enumerate(steps):
            status = statuses.get(str(i), statuses.get(i, "pending"))
            if status not in self._PLAN_STATUSES:
                status = "pending"
            counts[status] += 1
            tracked.append(
                {
                    "index": i,
                    "step": step,
                    "status": status,
                }
            )
        total = len(tracked)
        return {
            "total": total,
            "steps": tracked,
            "progress": counts,
            "completion_ratio": round(
                counts["done"] / max(1, total), 3
            ),
        }
    def plan_rewrite(self, plan: list) -> dict:
        """Rewrite a weak Chinese plan into an executable one.

        Planning under executive control (Miller & Cohen, 2001) turns
        vague intents into ordered action verbs. This normalizes each
        step to a standard verb phrase, removes duplicates and orders
        steps along the standard build flow.
        """
        raw = []
        for item in plan:
            if isinstance(item, str):
                text = item
            else:
                text = item.get("step") or item.get("action") or ""
            text = str(text).strip()
            if text:
                raw.append(text)
        flow = {
            "需求": "调研需求",
            "设计": "设计架构",
            "架构": "设计架构",
            "开发": "开发功能",
            "功能": "开发功能",
            "实现": "开发功能",
            "测试": "测试功能",
            "部署": "部署上线",
            "上线": "部署上线",
            "文档": "写文档",
            "写": "写文档",
            "复盘": "项目复盘",
            "总结": "项目复盘",
        }
        rewritten = []
        changes = []
        seen = set()
        for i, step in enumerate(raw):
            new_step = None
            for keyword, template in flow.items():
                if keyword in step:
                    new_step = template
                    break
            if new_step is None:
                new_step = f"完成{step}"
            if new_step in seen:
                changes.append(
                    {
                        "index": i,
                        "original": step,
                        "rewritten": None,
                        "reason": "重复步骤已删除",
                    }
                )
                continue
            seen.add(new_step)
            if new_step != step:
                changes.append(
                    {
                        "index": i,
                        "original": step,
                        "rewritten": new_step,
                        "reason": "补动词并规范化",
                    }
                )
            rewritten.append(new_step)
        order = {
            "调研需求": 1,
            "设计架构": 2,
            "开发功能": 3,
            "测试功能": 4,
            "部署上线": 5,
            "写文档": 6,
            "项目复盘": 7,
        }
        reordered = sorted(
            rewritten, key=lambda step: order.get(step, 8)
        )
        if reordered != rewritten and rewritten:
            changes.append(
                {
                    "index": None,
                    "original": list(rewritten),
                    "rewritten": list(reordered),
                    "reason": "按标准流程排序",
                }
            )
        return {
            "original": raw,
            "rewritten": reordered,
            "changes": changes[:8],
        }
    def lesson_learned(
        self,
        memory_ids: list[str] | None = None,
        limit: int = 10,
    ) -> dict:
        """Extract lessons learned from project memories.

        Experience is consolidated into reusable schemas (Bartlett,
        1932): successes, failures and lessons become templates for
        future projects. This scans memories and tags the ones that carry
        experience.
        """
        if memory_ids:
            items = []
            for memory_id in memory_ids:
                item = self.backend.get(memory_id)
                if item is not None:
                    items.append(item)
        else:
            items = self.store.all_active()
        lessons = []
        for item in items:
            content = item.content
            if any(
                keyword in content
                for keyword in ("成功", "完成", "搞定")
            ):
                tag = "success"
            elif any(
                keyword in content
                for keyword in ("失败", "出错", "坑", "教训")
            ):
                tag = "failure"
            elif any(
                keyword in content
                for keyword in ("经验", "学到", "注意", "建议")
            ):
                tag = "lesson"
            else:
                continue
            lessons.append(
                {
                    "id": item.id,
                    "preview": content[:48],
                    "tag": tag,
                }
            )
        tags = {
            "success": sum(1 for item in lessons if item["tag"] == "success"),
            "failure": sum(1 for item in lessons if item["tag"] == "failure"),
            "lesson": sum(1 for item in lessons if item["tag"] == "lesson"),
        }
        return {
            "total": len(lessons),
            "tags": tags,
            "lessons": lessons[: max(1, int(limit))],
        }
    def effort_estimate(
        self,
        plan: list,
        base_hours: float = 2.0,
    ) -> dict:
        """Estimate per-step and total effort for a plan.

        Humans systematically underestimate duration (planning fallacy;
        Buehler, Griffin & Ross, 1994). This tool assigns base hours per
        standard step type, sums totals and critical-path hours, then
        adds a 20% buffer.
        """
        dep = self.dependency_map(plan)
        base_rules = (
            ("需求", 4.0),
            ("设计", 6.0),
            ("架构", 6.0),
            ("开发", 8.0),
            ("实现", 8.0),
            ("测试", 5.0),
            ("功能", 8.0),
            ("部署", 3.0),
            ("上线", 3.0),
            ("文档", 3.0),
            ("复盘", 2.0),
            ("总结", 2.0),
        )

        def _hours(step: str) -> float:
            for keyword, hours in base_rules:
                if keyword in step:
                    return hours
            return float(base_hours)

        estimates = []
        for step in dep["steps"]:
            hours = _hours(step["step"])
            if len(step["step"]) > 12:
                hours *= 1.2
            estimates.append(
                {
                    "index": step["index"],
                    "step": step["step"],
                    "estimated_hours": round(hours, 1),
                }
            )
        by_index = {entry["index"]: entry for entry in estimates}
        total = sum(entry["estimated_hours"] for entry in estimates)
        critical = dep["critical_path"]
        critical_hours = sum(
            by_index[entry["index"]]["estimated_hours"]
            for entry in critical
        )
        return {
            "steps": estimates,
            "total_hours": round(total, 1),
            "critical_path_hours": round(critical_hours, 1),
            "buffered_total_hours": round(total * 1.2, 1),
            "note": "按规划谬误加 20% 缓冲（Buehler et al. 1994）",
        }
    def decision_review(
        self,
        plan: list,
        results: dict,
    ) -> dict:
        """Review a finished plan against its results.

        Post-task metacognitive monitoring (Koriat & Goldsmith, 1996)
        compares intended vs actual outcomes and distills reusable
        lessons: success rate, score, patterns and failure notes.
        """
        steps = []
        for item in plan:
            if isinstance(item, str):
                text = item
            else:
                text = item.get("step") or item.get("action") or ""
            text = str(text).strip()
            if text:
                steps.append(text)
        per_step = []
        for i, step in enumerate(steps):
            entry = results.get(str(i), results.get(i, {}))
            if isinstance(entry, str):
                status = entry
                note = ""
            else:
                status = entry.get("status", "unknown")
                note = entry.get("note", "")
            per_step.append(
                {
                    "index": i,
                    "step": step,
                    "status": status,
                    "note": note,
                }
            )
        successes = [p for p in per_step if p["status"] == "success"]
        failures = [p for p in per_step if p["status"] == "failure"]
        success_rate = round(len(successes) / max(1, len(per_step)), 3)
        score = int(round(success_rate * 100))
        verdict = (
            "good" if score >= 80 else (
                "fair" if score >= 50 else "poor"
            )
        )
        lessons = [
            {
                "type": "failure",
                "text": (
                    f"注意：{p['step']} 失败"
                    + (f"——{p['note']}" if p["note"] else "")
                ),
            }
            for p in failures
        ] + [
            {
                "type": "success",
                "text": f"可复用：{p['step']} 顺利通过",
            }
            for p in successes
        ]
        return {
            "total_steps": len(per_step),
            "per_step": per_step,
            "success_rate": success_rate,
            "score": score,
            "verdict": verdict,
            "patterns": {
                "success_steps": [p["step"] for p in successes],
                "failure_steps": [p["step"] for p in failures],
            },
            "lessons": lessons[:6],
        }
    def transfer_report(
        self,
        plan: list,
        lessons_memory_ids: list[str] | None = None,
    ) -> dict:
        """Map past lessons onto a new plan's steps.

        Reusable schemas transfer to new tasks (Bartlett, 1932): this
        matches each lesson memory (success/failure/experience) against
        plan steps by token overlap and reports which lessons apply.
        """

        steps = []
        for item in plan:
            if isinstance(item, str):
                text = item
            else:
                text = item.get("step") or item.get("action") or ""
            text = str(text).strip()
            if text:
                steps.append(text)
        if lessons_memory_ids:
            items = []
            for memory_id in lessons_memory_ids:
                item = self.backend.get(memory_id)
                if item is not None:
                    items.append(item)
        else:
            items = self.store.all_active()
        lessons = []
        for item in items:
            content = item.content
            if not any(
                keyword in content
                for keyword in ("成功", "失败", "经验", "注意", "教训", "建议")
            ):
                continue
            content_terms = set(tokenize(content))
            matched_steps = [
                step for step in steps
                if content_terms & set(tokenize(step))
            ]
            tag = (
                "failure"
                if any(k in content for k in ("失败", "注意", "教训"))
                else "success" if "成功" in content else "lesson"
            )
            lessons.append(
                {
                    "id": item.id,
                    "preview": content[:48],
                    "tag": tag,
                    "matched_steps": matched_steps,
                }
            )
        applicable = [lesson for lesson in lessons if lesson["matched_steps"]]
        return {
            "plan_steps": steps,
            "total_lessons": len(lessons),
            "applicable_lessons": applicable,
            "suggestion": "把适用的经验写进计划注意事项，避免重复踩坑",
        }
    def goal_replay(
        self,
        goal: str,
        *,
        top_k: int = 5,
        now: datetime | None = None,
    ) -> dict:
        """Replay goal-related memories to plan the next move.

        Planning in the brain is implemented through prefrontal-
        hippocampal replay: goal states are replayed offline to improve
        decisions (Jensen, Hennequin & Mattar, 2024), and complex
        problem solving cycles through goal silencing and reactivation
        (Watanabe et al., 2023). This tool replays memories relevant to
        a goal, checks past successes/failures and overdue intentions,
        and produces a replay-ready step plan.
        """
        results = self.recall(goal, top_k=max(1, int(top_k)), now=now)
        evidence = [
            {
                "id": result.item.id,
                "preview": result.item.content[:44],
                "kind": result.item.kind.value,
                "score": round(result.score, 3),
                "has_lesson": any(
                    marker in result.item.content
                    for marker in ("成功", "失败", "learned", "success")
                ),
            }
            for result in results
            if result.score >= 0.05
        ]
        lessons = [item for item in evidence if item["has_lesson"]]
        queue = self.action_queue(now=now)
        overdue = queue["overdue"]
        conflicts = len(self.consolidator.detect_conflicts())
        replay_steps = [
            {
                "order": 1,
                "step": "目标回放：想起与目标相关的记忆",
                "evidence_ids": [item["id"] for item in evidence],
                "verdict": "ok" if evidence else "weak",
            },
            {
                "order": 2,
                "step": "经验提取：过去的成功/失败",
                "evidence_ids": [item["id"] for item in lessons],
                "verdict": "ok" if lessons else "weak",
            },
            {
                "order": 3,
                "step": "待办重激活：把搁置的下一步找回来",
                "evidence_ids": [],
                "verdict": "ok" if overdue else "weak",
            },
            {
                "order": 4,
                "step": "冲突检查后形成计划",
                "evidence_ids": [],
                "verdict": "ok" if not conflicts else "weak",
            },
        ]
        evidence_ratio = min(1.0, len(evidence) / max(1, int(top_k)))
        lesson_ratio = 1.0 if lessons else 0.0
        conflict_ratio = 0.0 if conflicts else 1.0
        replay_score = round(
            0.4 * evidence_ratio + 0.3 * lesson_ratio + 0.3 * conflict_ratio,
            3,
        )
        return {
            "goal": goal,
            "evidence_used": evidence,
            "lessons_found": len(lessons),
            "overdue_reactivations": overdue,
            "replay_steps": replay_steps,
            "replay_score": replay_score,
            "advice": (
                "重放就绪：按步骤执行，先做逾期待办，"
                "并在行动前复查经验教训。"
                if replay_score >= 0.7
                else "重放证据不足：先补记忆（经验/待办），再开始行动。"
            ),
        }
    def plan_for_goal(
        self,
        goal: str,
        *,
        top_k: int | None = None,
        now: datetime | None = None,
        zh_synonyms: bool = True,
        outcome_aware: bool = True,
        effort: str | None = None,
    ) -> list[RecallResult]:
        """Agent planning: turn a goal into an ordered step plan.

        Prefrontal goal maintenance (Miller & Cohen, 2001): the agent holds
        the goal and pulls the task-relevant schema - the person's own past
        steps or, when the goal references another person ("参考阿丽"),
        that person's steps as an analogical template (Gick & Holyoak, 1980).
        Outcome-aware reranking (law of effect, Thorndike 1911; Smolen et
        al., 2016): steps whose past executions succeeded more often get a
        bounded boost, failed steps get demoted, so the plan prefers
        what actually worked.
        Falls back to the reasoning premise pack for non-step goals.
        """
        if effort is None:
            effort = self._plan_effort(goal)
        if effort == "low":
            outcome_aware = False
            top_k = top_k or 6
        elif effort == "high":
            top_k = top_k or 14
        else:
            top_k = top_k or self._suggested_plan_size(goal)
        if top_k is None:
            top_k = self._suggested_plan_size(goal)
        if any(marker in goal for marker in (
            "想", "要", "打算", "计划", "准备", "希望", "怎么", "如何",
        )):
            plan = self.recall_steps(
                goal,
                top_k=top_k,
                now=now,
                zh_synonyms=zh_synonyms,
            )
            # outcome records are evidence, not plan steps: filter them out
            plan = [
                r for r in plan
                if "执行成功" not in r.item.content
                and "执行失败" not in r.item.content
            ]
            if outcome_aware:
                self._apply_outcome_rerank(plan)
            return plan
        return self.recall_reasoning(goal, top_k=top_k, now=now)
    def _plan_effort(self, goal: str) -> str:
        """Resource-rational planning depth (Lieder & Griffiths, 2020).

        Simple goals get a shallow, fast plan; goals with many references /
        constraints get a deep plan. Constraint words: 预算/人数/时间/地点/
        要求/限制/完整/全部/按顺序; references: 参考/参照/学/模仿/按照/像.
        """

        refs = len(re.findall(
            r"(?:参考|参照|学|模仿|按照|像)([\u4e00-\u9fff]{2})"
            r"|和([\u4e00-\u9fff]{2})",
            goal,
        ))
        constraints = sum(
            1 for token in (
                "预算", "人数", "时间", "地点", "要求", "限制",
                "完整", "全部", "按顺序", "一共", "几天",
            ) if token in goal
        )
        score = refs * 2 + constraints
        if score >= 4:
            return "high"
        if score >= 2:
            return "medium"
        return "low"
    def replan(
        self,
        goal: str,
        failed_step: str,
        *,
        top_k: int | None = None,
        now: datetime | None = None,
    ) -> list[RecallResult]:
        """Replan after a failed step (error monitoring and re-planning).

        The anterior cingulate cortex monitors errors (Botvinick et al.,
        2001) and the prefrontal cortex re-plans. The failed step is moved
        to the end of the plan (avoided), marked with a 重规划 reason, and
        the re-planning decision itself is stored so future plans remember
        what to avoid.
        """
        _ACTION_PREFIXES = "订买卖打包收拾请找定学搬选入"
        noun = failed_step.lstrip(_ACTION_PREFIXES) or failed_step
        # which person(s) actually failed this step? (evidence-weighted)
        failing_persons: dict[str, float] = {}
        for item in self.backend.list(kind=MemoryKind.EPISODIC):
            if "执行失败" not in item.content or len(item.cues) < 3:
                continue
            step_cue = item.cues[1]
            step_noun = step_cue.lstrip(_ACTION_PREFIXES)
            if noun and step_noun != noun and step_cue != failed_step:
                continue
            person = item.cues[0][:2]
            failing_persons[person] = (
                failing_persons.get(person, 0.0)
                + max(1, item.evidence_count)
            )
        plan = self.plan_for_goal(
            goal,
            top_k=top_k,
            now=now,
            effort="high",
            outcome_aware=True,
        )
        kept: list[RecallResult] = []
        failed: list[RecallResult] = []
        for r in plan:
            person = (
                r.item.cues[0][:2]
                if r.item.cues
                else r.item.content[:2]
            )
            should_avoid = bool(
                noun and noun in r.item.content
                and (
                    not failing_persons
                    or failing_persons.get(person, 0.0) > 0.0
                )
            )
            if should_avoid:
                if not any("重规划" in reason for reason in r.reasons):
                    r.reasons.append(
                        f"\u91cd\u89c4\u5212:\u5df2\u907f\u5f00"
                        f"\u5931\u8d25\u6b65\u9aa4{failed_step}"
                    )
                failed.append(r)
            else:
                kept.append(r)
        self.remember(
            f"项目“{goal[:8]}”重新规划：避开失败步骤“{failed_step}”。",
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.AGENT),
            cues=[goal[:8], failed_step, "重规划"],
            importance=0.75,
            evidence_count=1,
            created_at=now,
        )
        return kept + failed
    def _suggested_plan_size(self, goal: str) -> int:
        """Working-memory capacity matching (Miller, 1956).

        Plans need enough context slots to hold the whole step sequence:
        base 8, +2 per referenced person ("参考阿丽和小波"), +2 for chain
        or multi-step hints, capped at 14.
        """

        size = 8
        refs = re.findall(
            r"(?:参考|参照|学|模仿|按照|像)([\u4e00-\u9fff]{2})"
            r"|和([\u4e00-\u9fff]{2})",
            goal,
        )
        refs = [a or b for a, b in refs if (a or b)]
        if refs:
            size += 2 * (len(refs) - 1)
        if any(token in goal for token in (
            "三个步骤", "四个步骤", "五个步骤", "三步", "四步", "五步",
            "完整", "全部", "按顺序",
        )):
            size += 2
        return min(size, 14)
    def _apply_outcome_rerank(
        self,
        results: list[RecallResult],
        *,
        bonus_scale: float = 0.08,
    ) -> None:
        """Boost steps whose outcome history is successful; demote failures.

        Outcome records written by ``record_outcome`` carry cues
        ``[goal[:8], step[:8], result]``. One lightweight pass over the
        store collects evidence-weighted success/failure per step cue, then
        each plan step that matches a step cue is nudged by
        ``clamp((success_evidence - failure_evidence) * bonus_scale)``.
        """

        if not results:
            return
        _ACTION_PREFIXES = "订买卖打包收拾请找定学搬选入"
        outcome_by_step: dict[tuple[str, str], float] = {}
        for item in self.backend.list(kind=MemoryKind.EPISODIC):
            if "执行成功" not in item.content and "执行失败" not in item.content:
                continue
            if len(item.cues) < 3:
                continue
            person = item.cues[0][:2]
            step_cue = item.cues[1]
            weight = max(1, item.evidence_count)
            delta = weight if "执行成功" in item.content else -weight
            nouns = {step_cue, step_cue.lstrip(_ACTION_PREFIXES)}
            for noun in nouns:
                key = (person, noun)
                outcome_by_step[key] = (
                    outcome_by_step.get(key, 0.0) + delta
                )
        if not outcome_by_step:
            return
        deltas: list[float] = []
        for result in results:
            content = result.item.content
            person = (
                result.item.cues[0][:2]
                if result.item.cues
                else content[:2]
            )
            match_key = ""
            for (operson, noun), total in outcome_by_step.items():
                if operson == person and noun and noun in content:
                    match_key = (operson, noun)
                    break
            if not match_key:
                deltas.append(0.0)
                continue
            delta = max(
                -0.15,
                min(0.15, outcome_by_step[match_key] * bonus_scale),
            )
            deltas.append(delta)
            result.score = round(result.score + delta, 4)
            if not any("结果加权" in reason for reason in result.reasons):
                result.reasons.append(
                    f"\u7ed3\u679c\u52a0\u6743({delta:+.2f},"
                    f"\u6210\u529f\u8ba1\u5212\u4f18\u5148)"
                )
        # group by outcome delta (successful plans first), keep original
        # chronological order inside each group
        results[:] = [
            results[i]
            for i in sorted(
                range(len(results)),
                key=lambda i: (-deltas[i], i),
            )
        ]
    def record_outcome(
        self,
        goal: str,
        step: str,
        *,
        success: bool,
        note: str | None = None,
        now: datetime | None = None,
    ) -> MemoryItem:
        """Record an execution outcome (agent judgment loop).

        The prefrontal cortex monitors action outcomes and updates
        predictions (Miller & Cohen, 2001; Smolen et al., 2016). The outcome
        is stored with evidence accumulation, so repeated success/failure
        strengthens the trace and future plans can prefer it.

        Prediction-error weighting (Schultz et al., 1997; Rescorla & Wagner,
        1972): outcomes that contradict the accumulated history get a higher
        importance and an "意外" cue, so surprising events are easy to find
        and the prediction is updated more visibly.
        """
        result = "成功" if success else "失败"
        prior = self._step_success_ratio(step)
        error = abs((1.0 if success else 0.0) - prior)
        importance = round(min(0.95, 0.75 + 0.15 * error), 3)
        cues = [goal[:8], step[:8], result]
        if error >= 0.6:
            cues.append("意外")
        content = (
            f"项目“{goal}”的步骤“{step}”执行{result}"
            + (f"（{note}）" if note else "")
            + "。"
        )
        return self.remember(
            content,
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.AGENT),
            cues=cues,
            importance=importance,
            evidence_count=1,
            created_at=now,
        )
    def _step_success_ratio(self, step: str) -> float:
        """Prior success probability of a step from its outcome records."""
        _ACTION_PREFIXES = "订买卖打包收拾请找定学搬选入"
        noun = step.lstrip(_ACTION_PREFIXES) or step
        success = failure = 0
        for item in self.backend.list(kind=MemoryKind.EPISODIC):
            if "执行成功" not in item.content and "执行失败" not in item.content:
                continue
            if len(item.cues) < 3:
                continue
            step_cue = item.cues[1]
            step_noun = step_cue.lstrip(_ACTION_PREFIXES)
            if step_cue != step and step_noun != noun:
                continue
            weight = max(1, item.evidence_count)
            if "执行成功" in item.content:
                success += weight
            else:
                failure += weight
        total = success + failure
        if total == 0:
            return 0.5
        return success / total
    def predict_step(self, step: str) -> dict:
        """Predict a step's success probability from outcome history."""
        _ACTION_PREFIXES = "订买卖打包收拾请找定学搬选入"
        noun = step.lstrip(_ACTION_PREFIXES) or step
        # fast path: consolidated step-experience summary from sleep replay
        for item in self.backend.list(kind=MemoryKind.SEMANTIC):
            if "历史成功率" not in item.content:
                continue
            if noun not in item.content and step not in item.content:
                continue
            match = re.search(
                r"(\d+)\s*/\s*(\d+)", item.content
            )
            if match:
                success = float(match.group(1))
                total = float(match.group(2))
                if total > 0:
                    ratio = success / total
                    return {
                        "step": step,
                        "success_probability": round(ratio, 3),
                        "confidence": round(abs(ratio - 0.5) * 2, 3),
                        "source": "consolidated",
                    }
        ratio = self._step_success_ratio(step)
        return {
            "step": step,
            "success_probability": round(ratio, 3),
            "confidence": round(abs(ratio - 0.5) * 2, 3),
            "source": "records",
        }
    def plan_rehearsal(
        self,
        goal: str,
        *,
        top_k: int | None = None,
        now: datetime | None = None,
    ) -> dict:
        """Mentally rehearse a plan before acting (episodic simulation).

        Schacter & Addis (2007): the episodic memory system recombines
        past episodes into imagined futures, so planning is simulated
        experience; Momennejad et al. (2017) and Na et al. (2021): humans
        value each step by its projected outcome (forward thinking).
        This read-only tool pre-plays the plan: every step gets a success
        probability from stored outcome history, the weakest link is
        flagged, and a remembered successful alternative is offered as a
        fallback.
        """
        plan = self.plan_for_goal(
            goal, top_k=top_k, now=now, effort="high"
        )
        steps = []
        for result in plan:
            content = result.item.content
            person = (
                result.item.cues[0][:2]
                if result.item.cues
                else content[:2]
            )
            probe = self._plan_rehearsal_probe(content, person)
            steps.append(
                {
                    "step": content,
                    "person": person,
                    "success_probability": probe["success_probability"],
                    "confidence": probe["confidence"],
                    "source": probe["source"],
                }
            )
        weakest = min(
            steps,
            key=lambda s: s["success_probability"],
            default=None,
        )
        fallback = (
            self._plan_rehearsal_fallback(
                weakest["step"], weakest["person"]
            )
            if weakest is not None
            else None
        )
        if weakest is None:
            advice = (
                "记忆里还没有可预演的计划或资料，先记录目标步骤再预演。"
            )
            overall = 0.0
        else:
            overall = round(
                min(s["success_probability"] for s in steps),
                3,
            )
            if fallback:
                advice = (
                    "先在脑子里预演一遍全计划；最薄弱的是"
                    f"“{weakest['step'][:22]}”（成功率"
                    f"{weakest['success_probability']:.0%}）；"
                    f"如果失败，记得的备选是“{fallback}”。"
                )
            else:
                advice = (
                    "先在脑子里预演一遍全计划；最薄弱的是"
                    f"“{weakest['step'][:22]}”（成功率"
                    f"{weakest['success_probability']:.0%}）；"
                    "没有现成备选，先小步试一次再继续。"
                )
        return {
            "goal": goal,
            "steps": steps,
            "step_count": len(steps),
            "weakest_step": weakest,
            "overall_success_probability": overall,
            "fallback": fallback,
            "rehearsal_advice": advice,
        }
    def _plan_rehearsal_probe(
        self,
        step: str,
        person: str,
    ) -> dict:
        """Evidence-weighted success probe for one plan step."""
        _ACTION_PREFIXES = "订买卖打包收拾请找定学搬选入"
        success = failure = 0
        for item in self.backend.list(kind=MemoryKind.EPISODIC):
            if (
                "执行成功" not in item.content
                and "执行失败" not in item.content
            ):
                continue
            if len(item.cues) < 3:
                continue
            if item.cues[0][:2] != person:
                continue
            step_cue = item.cues[1]
            nouns = {step_cue, step_cue.lstrip(_ACTION_PREFIXES)}
            if not any(noun and noun in step for noun in nouns):
                continue
            weight = max(1, item.evidence_count)
            if "执行成功" in item.content:
                success += weight
            else:
                failure += weight
        total = success + failure
        if total == 0:
            pred = self.predict_step(step)
            return {
                "success_probability": pred["success_probability"],
                "confidence": pred["confidence"],
                "source": pred["source"],
            }
        ratio = success / total
        return {
            "success_probability": round(ratio, 3),
            "confidence": round(abs(ratio - 0.5) * 2, 3),
            "source": "records",
        }
    def _plan_rehearsal_fallback(
        self,
        step: str,
        person: str,
    ) -> str | None:
        """Find a remembered successful alternative for the same person."""
        _ACTION_PREFIXES = "订买卖打包收拾请找定学搬选入"
        step_cue_alt = ""
        for item in self.backend.list(kind=MemoryKind.EPISODIC):
            if "执行成功" not in item.content or len(item.cues) < 3:
                continue
            if item.cues[0][:2] != person:
                continue
            step_cue = item.cues[1]
            if step_cue in step or step_cue.lstrip(_ACTION_PREFIXES) in step:
                continue
            if step_cue_alt and step_cue_alt != step_cue:
                continue
            step_cue_alt = step_cue
            return item.content[:48]
        return None
    def math_ladder(
        self,
        problem: str,
        *,
        top_k: int = 4,
    ) -> dict:
        """Climb the math abstraction ladder: concrete -> symbolic -> general.

        Mathematical knowledge forms a distinct semantic subspace in the
        human brain (Amalric & Dehaene, 2019) and learning is helped by
        moving from concrete examples to symbols to general rules
        (concreteness fading; Fyfe, McNeil & Borriello, 2014). This
        read-only tool detects the problem type, extracts concrete
        numbers, builds the symbolic template, then looks for the
        matching formula already stored in memory (or falls back to the
        template as a general rule).
        """

        detected = [
            label
            for keyword, label in self._MATH_TYPES
            if keyword in problem
        ]
        numbers = [
            {
                "value": float(raw),
                "raw": raw,
            }
            for raw in re.findall(r"\d+(?:\.\d+)?", problem)
        ]
        results = self.recall(problem, top_k=max(1, int(top_k)))
        evidence = [
            {
                "id": result.item.id,
                "preview": result.item.content[:48],
                "score": round(result.score, 3),
            }
            for result in results
            if result.score >= 0.05
        ]
        formula_memories = []
        for item in self.backend.list(kind=MemoryKind.SEMANTIC):
            text = item.content
            cue_text = " ".join(item.cues)
            if "公式" not in cue_text and "公式" not in text:
                continue
            if "=" not in text and "÷" not in text and "×" not in text:
                continue
            formula_memories.append(
                {
                    "id": item.id,
                    "rule": text[:80],
                    "cues": item.cues[:3],
                }
            )
        matched_formula = None
        if detected:
            head = detected[0]
            for formula in formula_memories:
                if head in formula["rule"] or head in " ".join(
                    formula["cues"]
                ):
                    matched_formula = formula
                    break
        templates = [self._MATH_SYMBOLS[label] for label in detected]
        if matched_formula:
            general = {
                "rule": matched_formula["rule"],
                "source": "memory",
                "formula_memory_id": matched_formula["id"],
            }
        elif templates:
            general = {
                "rule": templates[0],
                "source": "symbolic",
                "formula_memory_id": None,
            }
        else:
            general = None
        concrete_desc = (
            f"题目里的具体数字：{'、'.join(n['raw'] for n in numbers)}。"
            if numbers
            else "题目里没找到阿拉伯数字，先补全条件。"
        )
        symbolic_desc = (
            f"用符号表示关系：{'；'.join(templates)}。"
            if templates
            else "还没识别出题型，无法给出符号模板。"
        )
        general_desc = (
            f"一般规则（来自记忆）：{general['rule']}。"
            if general and general["source"] == "memory"
            else (
                f"一般规则（通用模板）：{general['rule']}。"
                if general
                else "记忆里没有对应公式，先补充数学知识。"
            )
        )
        ladder = [
            {"rung": "具体", "description": concrete_desc},
            {"rung": "符号", "description": symbolic_desc},
            {"rung": "一般", "description": general_desc},
        ]
        if numbers and general:
            verdict = "ready"
        else:
            verdict = "review_needed"
        if general and general["source"] == "memory":
            advice = (
                f"已从记忆中找到公式“{general['rule']}”，"
                "把题目数字代入就能算。"
            )
        elif general:
            advice = (
                f"记忆里没有这个公式，先按通用模板“{general['rule']}”算；"
                "建议把算过的例子存进记忆，下次直接用。"
            )
        else:
            advice = "缺少公式或具体数字，先补充相关数学记忆再解题。"
        return {
            "problem": problem,
            "types": detected,
            "concrete": {
                "numbers": numbers,
                "description": concrete_desc,
            },
            "symbolic": {
                "templates": templates,
                "description": symbolic_desc,
            },
            "general": general,
            "ladder": ladder,
            "evidence": evidence,
            "verdict": verdict,
            "advice": advice,
        }
    def physics_simulate(
        self,
        scene: str,
        *,
        top_k: int = 4,
    ) -> dict:
        """Run a mental physics simulation from stored laws.

        Human intuitive physics works like an internal physics engine
        (Battaglia, Hamrick & Tenenbaum, 2013) supported by dedicated
        brain networks (Fischer et al., 2016). This read-only tool
        detects the scene type, extracts quantities, recalls the
        applicable law from memory (falling back to common built-in
        rules), then plays the scene forward in ordered phases.
        """

        detected = [
            label
            for keyword, label in self._PHYSICS_TYPES
            if keyword in scene
        ]
        numbers = [
            {
                "value": float(raw),
                "raw": raw,
            }
            for raw in re.findall(r"\d+(?:\.\d+)?", scene)
        ]
        law_memories = []
        for item in self.backend.list(kind=MemoryKind.SEMANTIC):
            text = item.content
            cue_text = " ".join(item.cues)
            if "物理" not in cue_text and "定律" not in text:
                continue
            if "=" not in text and "≈" not in text:
                continue
            law_memories.append(
                {
                    "id": item.id,
                    "rule": text[:80],
                    "cues": item.cues[:3],
                }
            )
        matched_law = None
        if detected:
            head = detected[0]
            for law in law_memories:
                if head in law["rule"] or head in " ".join(law["cues"]):
                    matched_law = law
                    break
        if matched_law:
            law_used = {
                "rule": matched_law["rule"],
                "source": "memory",
                "memory_id": matched_law["id"],
            }
        elif detected:
            law_used = {
                "rule": self._PHYSICS_RULES[detected[0]],
                "source": "builtin",
                "memory_id": None,
            }
        else:
            law_used = None

        simulation = None
        if detected and numbers:
            head = detected[0]
            if head == "自由落体":
                height = next(
                    (n["value"] for n in numbers if n["value"] > 0),
                    None,
                )
                if height is not None:
                    fall_time = math.sqrt(2 * height / 9.8)
                    simulation = (
                        f"脑内推演：{height:g} 米高处落下，"
                        f"落地时间约 {fall_time:.2f} 秒。"
                    )
            elif head in ("匀速运动", "速度") and len(numbers) >= 2:
                speed, hours = numbers[0]["value"], numbers[1]["value"]
                if speed and hours:
                    simulation = (
                        f"脑内推演：{speed:g} × {hours:g} = "
                        f"{speed * hours:g}（路程=速度×时间）。"
                    )
        if simulation is None and detected:
            simulation = (
                f"脑内推演：按“{law_used['rule']}”"
                "把题面条件逐一代入核对。"
            )

        phases = [
            {
                "order": 1,
                "phase": "初始状态",
                "description": (
                    f"场景类型：{'、'.join(detected) if detected else '未识别'}；"
                    f"提取到的数量：{'、'.join(n['raw'] for n in numbers) or '无'}。"
                ),
            },
            {
                "order": 2,
                "phase": "适用规律",
                "description": (
                    f"使用规律（来源：{law_used['source'] if law_used else '无'}）："
                    f"{law_used['rule'] if law_used else '记忆与内置规律都没有命中'}。"
                ),
            },
            {
                "order": 3,
                "phase": "脑内推演",
                "description": simulation or "条件不足，无法推演。",
            },
            {
                "order": 4,
                "phase": "结果判断",
                "description": (
                    "推演完成，可以按这个预期去验证；若结果不符，"
                    "回来补充物理规律记忆。"
                ),
            },
        ]
        verdict = "ready" if numbers and law_used else "review_needed"
        if law_used and law_used["source"] == "memory":
            advice = (
                f"记忆里找到规律“{law_used['rule']}”，"
                f"脑内推演完成：{simulation or '条件不足'}。"
            )
        elif law_used:
            advice = (
                f"记忆里没有这个物理规律，先用通用规律"
                f"“{law_used['rule']}”推演；"
                "建议把推演过程和结果存进记忆。"
            )
        else:
            advice = "场景信息或物理规律不足，先补充条件再模拟。"
        return {
            "scene": scene,
            "types": detected,
            "quantities": numbers,
            "law_used": law_used,
            "phases": phases,
            "simulation": simulation,
            "verdict": verdict,
            "advice": advice,
        }
    def analogy_prompt(
        self,
        *,
        topic: str | None = None,
        count: int = 3,
        min_mastery: float = 0.7,
        now: datetime | None = None,
    ) -> dict:
        """Generate same-structure / new-surface practice prompts.

        Analogical encoding (Gentner, Loewenstein & Thompson, 2003):
        comparing two cases that share structure but differ in surface
        details promotes learning and transfer. This tool takes a
        mastered memory, keeps its relation structure, and swaps people /
        places / objects to produce a new question that tests whether
        the structure (not the surface) was really learned.
        """
        mastery = self.mastery_map(now=now)
        candidates = [
            entry
            for entry in mastery["topics"]
            if entry["flag"] == "mastered"
            and entry["mastery"] >= min_mastery
        ]
        if topic:
            narrowed = [
                entry for entry in candidates if entry["topic"] == topic
            ]
            if narrowed:
                candidates = narrowed
        if not candidates:
            candidates = mastery["topics"][: max(1, int(count))]
        chosen = candidates[: max(1, int(count))]
        names = ["阿丽", "小波", "大壮", "小美", "阿强", "小月", "小禾"]
        cities = ["成都", "北京", "上海", "广州", "西安", "杭州", "南京"]
        objects = ["相机", "机票", "手机", "自行车", "吉他", "笔记本", "球鞋"]
        prompts: list[dict] = []
        for index, entry in enumerate(chosen):
            items = [
                item
                for item in self.store.all_active()
                if item.cues and item.cues[0] == entry["topic"]
            ]
            if not items:
                continue
            item = items[0]
            original = item.content
            surface_new = original
            mapping: list[str] = []
            for name in names:
                if name in surface_new:
                    alt = names[(names.index(name) + 1 + index) % len(names)]
                    if alt != name:
                        surface_new = surface_new.replace(name, alt)
                        mapping.append(f"{name}→{alt}")
                    break
            for city in cities:
                if city in surface_new:
                    alt = cities[
                        (cities.index(city) + 1 + index) % len(cities)
                    ]
                    if alt != city:
                        surface_new = surface_new.replace(city, alt)
                        mapping.append(f"{city}→{alt}")
                    break
            for obj in objects:
                if obj in surface_new:
                    alt = objects[
                        (objects.index(obj) + 1 + index) % len(objects)
                    ]
                    if alt != obj:
                        surface_new = surface_new.replace(obj, alt)
                        mapping.append(f"{obj}→{alt}")
                    break
            prompts.append(
                {
                    "memory_id": item.id,
                    "topic": entry["topic"],
                    "original": original,
                    "question": surface_new,
                    "surface_mapping": mapping,
                    "structure_note": (
                        "结构不变（关系照旧），只换表面细节——"
                        "看你能不能抓住真正的结构。"
                    ),
                    "answer_hidden": True,
                }
            )
        return {
            "topics": [
                {"topic": entry["topic"], "mastery": entry["mastery"]}
                for entry in chosen
            ],
            "prompts": prompts,
            "advice": (
                "类比题已生成：同一结构、换新表面，检验的是结构理解"
                "而不是死记表面（Gentner et al., 2003）。"
                if prompts
                else "记忆库里还没有可出题的内容，先积累已掌握主题。"
            ),
        }
