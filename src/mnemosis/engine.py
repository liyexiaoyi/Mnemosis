"""Mnemosis public facade."""

from __future__ import annotations

import math
import re
import statistics
import threading
from collections import deque
from datetime import datetime
from typing import ClassVar

from .analysis_mixin import AnalysisMixin
from .association import AssociationIndex
from .backend import Backend, make_backend
from .consolidation import (  # noqa: F401  (public re-exports)
    ConsolidationReport,
    Consolidator,
)
from .dual_track import DualTrackStore
from .embedding import Embedder
from .forgetting import ForgettingCurve, ReviewScheduler
from .importance import ImportanceScorer
from .metacognition import ConfidenceLabel, Metacognition, MetacognitiveCheck
from .planning_mixin import PlanningMixin
from .recycle import RecycleBin
from .retrieval_mixin import RetrievalMixin
from .review_mixin import ReviewMixin
from .schema import EventChainIndex
from .types import (
    MemoryItem,
    MemoryKind,
    MemoryStatus,
    RecallResult,  # noqa: F401  (public re-export)
    SourceRecord,
    SourceType,
    _zh_numeral,
    extract_cues,
    hash_content,
    normalize_cues,
    tokenize,  # noqa: F401  (public re-export)
    utcnow,
)
from .zh_nlp import expand_synonyms, has_cjk  # noqa: F401  (public re-exports)


class MemoryEngine(RetrievalMixin, PlanningMixin, ReviewMixin, AnalysisMixin):
    """The one thing most users touch.

    ```python
    engine = MemoryEngine("memory.db")   # persistent
    engine = MemoryEngine()              # in-memory
    engine.remember(...)
    engine.recall(...)
    engine.sleep()
    engine.check(...)
    ```
    """

    def __init__(
        self,
        memory_file: str | None = None,
        *,
        decay_rate: float | None = None,
        base_interval_hours: float = 24.0,
        importance_scorer: ImportanceScorer | None = None,
        embedder: Embedder | None = None,
        vector_index=None,
        index_embedder: Embedder | None = None,
    ) -> None:
        self.backend: Backend = make_backend(memory_file)
        if decay_rate is None:
            stored = self.backend.get_setting("decay_rate")
            try:
                decay_rate = float(stored) if stored is not None else 0.002
            except (TypeError, ValueError):
                decay_rate = 0.002
        self.curve = ForgettingCurve(decay_rate)
        self.scheduler = ReviewScheduler(self.curve, base_interval_hours)
        self.scorer = importance_scorer or ImportanceScorer()
        self.embedder = embedder
        self.vector_index = vector_index
        self.index_embedder = index_embedder
        self.store = DualTrackStore(self.backend, self.curve, self.scorer)
        self.associations = AssociationIndex(self.backend)
        self.event_chain = EventChainIndex(self.backend)
        self.consolidator = Consolidator(self.store, self.backend)
        self.meta = Metacognition(self.store, self.curve, self.consolidator)
        self.recycle = RecycleBin(self.backend)
        self._recall_log: deque[dict] = deque(maxlen=100)
        self._intents: dict[str, dict] = {}
        self._suppressed_ids: dict[str, str] = {}
        self._lock = threading.RLock()

    # -- wake cycle ---------------------------------------------------------

    @staticmethod
    def _extract_context(content: str) -> str | None:
        """Auto-tag the situational context of a memory (round 71).

        Context-dependent memory (Godden & Baddeley, 1975): where something
        happened is a powerful retrieval cue. Patterns like "在会议室里"
        / "在公司" / "去家里" are extracted so later fuzzy-context recall
        can use them without the caller tagging every memory by hand.
        """

        match = re.search(
            r"(?:在|去|到)([\u4e00-\u9fff]{2,6}?)"
            r"(?:里|中|上|内|旁边)?",
            content,
        )
        if not match:
            return None
        candidate = match.group(1)
        if len(candidate) == 2:
            following = content[match.end():match.end() + 1]
            if following in "室馆店站楼场院厅":
                candidate += following
        if candidate in (
            "这里", "那里", "这时", "当时", "今天", "昨天", "明天",
            "现在", "这", "那", "现场", "家里家外",
        ):
            return None
        return candidate

    def remember(
        self,
        content: str,
        *,
        kind: MemoryKind = MemoryKind.EPISODIC,
        source: SourceRecord | None = None,
        cues: list[str] | None = None,
        importance: float | None = None,
        confidence: float = 1.0,
        strength: float = 1.0,
        created_at: datetime | None = None,
        context: str | None = None,
        affect: str | None = None,
        evidence_count: int = 1,
        storage_strength: float = 1.0,
        auto_cues: bool = True,
        auto_context: bool = True,
    ) -> MemoryItem:
        source = source or SourceRecord(origin=SourceType.USER)
        if auto_context and context is None:
            context = self._extract_context(content)
        if auto_cues:
            cues = normalize_cues(list(cues or []) + extract_cues(content))
        item = self.store.remember(
            content,
            kind,
            source,
            cues=cues,
            importance=importance,
            confidence=confidence,
            strength=strength,
            created_at=created_at,
            context=context,
            affect=affect,
            evidence_count=evidence_count,
            storage_strength=storage_strength,
        )
        self.associations.index(item)
        self.associations.link_related(item)
        if self.vector_index is not None and self.index_embedder is not None:
            self.vector_index.add(
                item.id, self.index_embedder.embed(content)
            )
        if item.kind is MemoryKind.EPISODIC:
            self.event_chain.invalidate()
        return item

    def remember_many(
        self,
        memories: list[dict],
        *,
        auto_cues: bool = True,
        auto_context: bool = True,
    ) -> list[MemoryItem]:
        """Batch remember: same semantics as ``remember`` per record.

        Each dict accepts ``remember``'s keyword arguments (content required;
        kind/source/cues/importance/confidence/strength/created_at/context/
        affect/evidence_count/storage_strength optional). Storage and term
        indexing are committed in bulk, so large imports are several times
        faster than calling ``remember`` in a loop.
        """
        with self._lock:
            records: list[dict] = []
            for memory in memories:
                content = memory["content"]
                record = dict(memory)
                record.setdefault(
                    "kind", MemoryKind.EPISODIC
                )
                record["source"] = record.get("source") or SourceRecord(
                    origin=SourceType.USER
                )
                if auto_context and record.get("context") is None:
                    record["context"] = self._extract_context(content)
                if auto_cues:
                    record["cues"] = normalize_cues(
                        list(record.get("cues") or [])
                        + extract_cues(content)
                    )
                records.append(record)
            # Embed BEFORE writing: if the batch API fails halfway, the
            # store is untouched and a retry cannot create duplicates.
            vectors = None
            if (
                self.vector_index is not None
                and self.index_embedder is not None
            ):
                vectors = self.index_embedder.embed_many(
                    [record["content"] for record in records]
                )
            stored = self.store.remember_many(records)
            if vectors is not None and len(vectors) != len(stored):
                raise RuntimeError(
                    "embedder returned "
                    f"{len(vectors)} vectors for {len(stored)} memories"
                )
            for item in stored:
                self.associations.index(item)
            pairs = self.associations.link_related_batch(stored)
            if pairs:
                self.backend.add_links_many(pairs)
            if vectors is not None:
                self.vector_index.add_many(
                    [
                        (item.id, vector)
                        for item, vector in zip(stored, vectors)
                    ]
                )
            if any(
                item.kind is MemoryKind.EPISODIC for item in stored
            ):
                self.event_chain.invalidate()
            return stored

    def rebuild_missing_vectors(
        self, embedder: Embedder | None = None
    ) -> int:
        """Re-embed active memories missing from the vector index.

        If a batch embed fails mid-way, the store is already written but
        some memories have no vector (lexical recall still works). This
        repairs that state in one pass and returns the number rebuilt.
        """
        embedder = embedder or self.index_embedder
        if self.vector_index is None or embedder is None:
            return 0
        missing = [
            item
            for item in self.store.all_active()
            if not self.vector_index.has(item.id)
        ]
        if not missing:
            return 0
        # Embed outside the engine lock: a slow external API must not block
        # concurrent recalls; only the final index write takes the lock.
        vectors = embedder.embed_many([item.content for item in missing])
        if len(vectors) != len(missing):
            raise RuntimeError(
                f"embedder returned {len(vectors)} vectors for "
                f"{len(missing)} memories"
            )
        with self._lock:
            self.vector_index.add_many(
                [
                    (item.id, vector)
                    for item, vector in zip(missing, vectors)
                ]
            )
            return len(missing)

    def remember_turn(
        self,
        text: str,
        *,
        kind: MemoryKind | None = None,
        max_segments: int = 4,
        now: datetime | None = None,
    ) -> dict:
        """Save the sentences of one conversation turn in a single call.

        Splits a user/assistant exchange into sentences and remembers each
        one with automatic cues and context. Agents can call this once per
        turn (see README) instead of hand-writing ``remember()`` calls.
        """
        parts = [
            part.strip()
            for part in re.split(r"[。！？!?；;\n]+", text)
            if part.strip()
        ]
        parts = parts[: max(1, int(max_segments))]
        memories: list[dict] = []
        for part in parts:
            item = self.remember(
                part,
                kind=kind
                or (
                    MemoryKind.SEMANTIC
                    if len(part) <= 60
                    else MemoryKind.EPISODIC
                ),
                auto_cues=True,
                auto_context=True,
                created_at=now,
            )
            memories.append(
                {
                    "id": item.id,
                    "content": item.content[:80],
                    "kind": item.kind.value,
                }
            )
        return {"saved": len(memories), "memories": memories}

    def update(
        self,
        memory_id: str,
        *,
        content: str | None = None,
        importance: float | None = None,
        confidence: float | None = None,
        cues: list[str] | None = None,
        now: datetime | None = None,
    ) -> MemoryItem | None:
        """Revise a memory (reconsolidation: Nader et al., 2000).

        The retrieved trace is made labile: content changes destabilize
        confidence/strength, the revision is recorded, and the memory
        re-stabilizes through future access.
        """
        item = self.backend.get(memory_id)
        if item is None:
            return None
        now = now or utcnow()
        if content is not None and content.strip() and content != item.content:
            new_hash = hash_content(content)
            if item.kind is MemoryKind.SEMANTIC:
                duplicate = self.backend.find_by_hash(MemoryKind.SEMANTIC, new_hash)
                if duplicate is not None and duplicate.id != item.id:
                    raise ValueError("update would create a semantic duplicate")
            item.content = content
            item.content_hash = new_hash
            item.revision_count += 1
            item.updated_at = now
            item.confidence = (item.confidence + 0.4) / 2.0
            item.strength = max(0.3, item.strength * 0.8)
        if importance is not None:
            item.importance = max(0.0, min(1.0, importance))
        if confidence is not None:
            item.confidence = max(0.0, min(1.0, confidence))
        if cues is not None:
            item.cues = normalize_cues(cues)
            self.backend.add_cues(item.id, item.cues)
        self.backend.update(item)
        self.store.reindex_terms(item)
        return item








    _ENTITY_QUESTION_RE = None
    _ENTITY_RECORD_RE = None
    _VALUE_QUESTION_RE = None
    _VALUE_PATTERN_RE = None
    _TIME_RANGE_RE = None
    _TEMPORAL_PAST_RE = re.compile(
        r"上次|上一次|最近|最新|刚才|最后一次|前一次|"
        r"现在|目前|当前|第一次|首次|头一回|"
        r"结果|成绩|考了多少分|评分结果|考核结果|"
        r"什么时候[^？?]{0,6}(?:的|了)"
    )
    _TEMPORAL_FUTURE_RE = re.compile(
        r"下次|下一次|接下来|"
        r"什么时候(续费|到期|上门|开工|交房|开始|结束|还款|复诊|面试|入职|复查)"
    )
    _TEMPORAL_DATE_Q_RE = re.compile(
        r"(\d{1,2})\s*月\s*(\d{1,2})\s*日"
    )
    _TEMPORAL_DATE_RE = re.compile(
        r"(\d{4})年(\d{1,2})月(\d{1,2})日"
        r"|(\d{4})-(\d{1,2})-(\d{1,2})"
    )
    _TEMPORAL_MD_RE = re.compile(
        r"(?<!年)(\d{1,2})\s*月\s*(\d{1,2})\s*日"
    )
    _TEMPORAL_ZH_DATE_RE = re.compile(
        r"(\d{4})年([一二三四五六七八九十零两]+)月"
        r"([一二三四五六七八九十零两]+)日"
    )
    _TEMPORAL_ZH_MD_RE = re.compile(
        r"(?<!年)([一二三四五六七八九十零两]+)月"
        r"([一二三四五六七八九十零两]+)日"
    )
    _TEMPORAL_YEAR_RE = re.compile(r"(\d{4})\s*年")
    _TEMPORAL_NOTICE_RE = re.compile(
        r"预约|通知|提醒|改到|调时间|约了|收到|说|协议|要求|请假"
    )
    _TEMPORAL_NOISE = (
        "是了的吗呢吧啊呀和与及或在有就都还也很这那"
        "什么哪一天上下次第几多少怎么如何何时几号点分"
    )
    _TEMPORAL_STRIP_RE = re.compile(
        r"(上次|上一次|最近|最新|刚才|最后一次|前一次|"
        r"下次|下一次|接下来)"
        r"|(是什么时候|是哪一天|是什么时间|什么时候|考了多少分|"
        r"面了什么内容|结果如何|怎么样|推荐了什么|要准备什么|"
        r"要带什么|是多少|是什么|多少分|多少钱|出了什么问题|"
        r"什么问题|怎么解决|怎么办|怎么回事)"
    )
    _TEMPORAL_CLEAN_RE = re.compile(
        "[" + _TEMPORAL_NOISE + "年月日0-9\\s，。？：:、（）()]"
    )




    @staticmethod
    def _latest_date(text: str) -> tuple[int, int, int]:
        """Latest parsed date in a record; (0, 0, 0) when none."""
        best = (0, 0, 0)
        year: int | None = None
        for match in MemoryEngine._TEMPORAL_DATE_RE.finditer(text):
            if match.group(1):
                year = int(match.group(1))
                cur = (year, int(match.group(2)), int(match.group(3)))
            else:
                year = int(match.group(4))
                cur = (year, int(match.group(5)), int(match.group(6)))
            best = max(best, cur)
        for match in MemoryEngine._TEMPORAL_ZH_DATE_RE.finditer(text):
            cur = (
                int(match.group(1)),
                _zh_numeral(match.group(2)),
                _zh_numeral(match.group(3)),
            )
            year = cur[0]
            best = max(best, cur)
        if year is not None:
            for match in MemoryEngine._TEMPORAL_MD_RE.finditer(text):
                cur = (year, int(match.group(1)), int(match.group(2)))
                best = max(best, cur)
            for match in MemoryEngine._TEMPORAL_ZH_MD_RE.finditer(text):
                cur = (
                    year,
                    _zh_numeral(match.group(1)),
                    _zh_numeral(match.group(2)),
                )
                best = max(best, cur)
        return best




































    _PLAN_VERBS = (
        "做", "写", "创建", "设计", "开发", "测试", "部署", "分析",
        "调研", "优化", "修复", "完成", "检查", "收集", "整理", "实现",
        "重构", "发布", "验证", "运行", "配置", "安装", "更新", "规划",
        "评估", "阅读", "发送", "记录", "确认", "制定", "拆分",
    )







    _PLAN_STATUSES = ("pending", "in_progress", "done", "blocked")







































    def suppress_memories(
        self,
        memory_ids: list[str],
        now: datetime | None = None,
    ) -> dict:
        """Temporarily suppress memories from retrieval (directed
        forgetting; Anderson & Green, 2001).

        Unlike deletion, suppression keeps the trace intact but blocks it
        from recall - the agent can deliberately stop being reminded of
        something, then unsuppress it later.
        """
        now = now or utcnow()
        suppressed = 0
        for memory_id in memory_ids:
            if self.backend.get(memory_id) is None:
                continue
            with self._lock:
                if memory_id not in self._suppressed_ids:
                    self._suppressed_ids[memory_id] = now.isoformat()
                    suppressed += 1
        return {"suppressed": suppressed}

    def unsuppress_memories(self, memory_ids: list[str]) -> dict:
        """Restore suppressed memories to normal retrieval."""
        unsuppressed = 0
        for memory_id in memory_ids:
            with self._lock:
                if memory_id in self._suppressed_ids:
                    del self._suppressed_ids[memory_id]
                    unsuppressed += 1
        return {"unsuppressed": unsuppressed}

    def suppressed_report(self) -> dict:
        """List currently suppressed memories with their previews."""
        out = []
        with self._lock:
            suppressed = list(self._suppressed_ids.items())
        for memory_id, suppressed_at in suppressed:
            item = self.backend.get(memory_id)
            if item is None:
                continue
            out.append(
                {
                    "id": memory_id,
                    "preview": item.content[:40],
                    "suppressed_at": suppressed_at,
                }
            )
        out.sort(key=lambda r: r["suppressed_at"])
        return {"count": len(out), "memories": out}


















    _MATH_TYPES = (
        ("加", "加法"),
        ("减", "减法"),
        ("乘", "乘法"),
        ("除", "除法"),
        ("每小时", "速度"),
        ("速度", "速度"),
        ("平均", "平均数"),
        ("比例", "比例"),
        ("概率", "概率"),
        ("方程", "方程"),
        ("百分", "百分数"),
    )
    _MATH_SYMBOLS: ClassVar[dict[str, str]] = {
        "加法": "a + b = c",
        "减法": "a - b = c",
        "乘法": "a × b = c",
        "除法": "a ÷ b = c",
        "速度": "速度 = 路程 ÷ 时间",
        "平均数": "平均数 = 总和 ÷ 个数",
        "比例": "a : b = c : d",
        "概率": "概率 = 有利结果 ÷ 全部结果",
        "方程": "未知数 = x，等式两边同时变化求解",
        "百分数": "百分数 = 部分 ÷ 整体 × 100%",
    }


    _PHYSICS_TYPES = (
        ("落下", "自由落体"),
        ("掉落", "自由落体"),
        ("扔", "抛体"),
        ("推", "推力"),
        ("撞", "碰撞"),
        ("滑", "滑动摩擦"),
        ("滚", "滚动"),
        ("浮", "浮力"),
        ("沉", "浮力"),
        ("杠杆", "杠杆"),
        ("重力", "重力"),
        ("摩擦", "摩擦力"),
        ("能量", "能量守恒"),
        ("动量", "动量守恒"),
        ("加速度", "加速度"),
        ("匀速", "匀速运动"),
        ("每小时", "速度"),
    )
    _PHYSICS_RULES: ClassVar[dict[str, str]] = {
        "自由落体": "下落时间 ≈ √(2h/g)，g≈9.8米/秒²",
        "抛体": "水平方向匀速，竖直方向自由落体",
        "推力": "加速度 a = F/m（牛顿第二定律）",
        "碰撞": "碰撞前后总动量守恒",
        "滑动摩擦": "摩擦力 = 压力 × 摩擦系数",
        "滚动": "滚动摩擦力一般小于滑动摩擦力",
        "浮力": "浮力 = 排开液体的重量（阿基米德原理）",
        "杠杆": "动力 × 动力臂 = 阻力 × 阻力臂",
        "重力": "重力 = 质量 × 9.8",
        "摩擦力": "摩擦力 = 压力 × 摩擦系数",
        "能量守恒": "总能量守恒：动能 + 势能 + 内能不变",
        "动量守恒": "碰撞前后总动量不变",
        "加速度": "加速度 = 速度变化 ÷ 时间",
        "匀速运动": "路程 = 速度 × 时间",
        "速度": "速度 = 路程 ÷ 时间",
    }
















    def export_memories(self) -> dict:
        """Export all active memories as a portable JSON payload."""
        items = [
            item
            for item in self.store.all_active()
            if item.status is MemoryStatus.ACTIVE
        ]
        return {
            "version": 1,
            "exported_at": utcnow().isoformat(),
            "memories": [item.to_dict() for item in items],
            "intents": [dict(r) for r in self._snapshot_intents()],
            "suppressed_ids": self._snapshot_suppressed(),
        }

    def _snapshot_intents(self) -> list[dict]:
        with self._lock:
            return list(self._intents.values())

    def _snapshot_suppressed(self) -> dict[str, str]:
        with self._lock:
            return dict(self._suppressed_ids)

    def import_memories(self, payload: dict) -> int:
        """Import memories from an export payload (round 106).

        Rebuilds each MemoryItem from its dict and adds it back into the
        store with cues and associations. Ids are preserved for portability;
        importing the same payload twice creates duplicates.
        """

        with self._lock:
            items = [
                MemoryItem.from_dict(data)
                for data in payload.get("memories", [])
            ]
            self.backend.add_many(items)
            self.backend.index_terms_many(
                (item.id, self.store._terms(item), item.kind)
                for item in items
            )
            self.store.invalidate_term_index()
            for item in items:
                self.associations.index(item)
                self.associations.link_related(item)
            if any(
                item.kind is MemoryKind.EPISODIC for item in items
            ):
                self.event_chain.invalidate()
            for record in payload.get("intents", []):
                record = dict(record)
                if record.get("id"):
                    self._intents[record["id"]] = record
            for memory_id, suppressed_at in payload.get(
                "suppressed_ids", {}
            ).items():
                if self.backend.get(memory_id) is not None:
                    self._suppressed_ids[memory_id] = suppressed_at
        return len(items)







    def tag_memories(
        self,
        memory_ids: list[str],
        tags: list[str],
        action: str = "add",
    ) -> dict:
        """Add or remove tags (cues) on memories in bulk.

        Tags are first-class retrieval cues, so this is an indexing
        maintenance tool: add "工作" to a set of memories and they become
        reachable through that tag.
        """
        if action not in ("add", "remove"):
            raise ValueError("action must be 'add' or 'remove'")
        new_tags = set(normalize_cues(tags))
        updated = added = removed = 0
        with self._lock:
            changed: list[MemoryItem] = []
            cue_changes: list[tuple[str, set[str]]] = []
            for memory_id in memory_ids:
                item = self.backend.get(memory_id)
                if item is None:
                    continue
                cues = set(item.cues)
                if action == "add":
                    added_tags = new_tags - cues
                    added += len(added_tags)
                    cues |= new_tags
                else:
                    removed_tags = cues & new_tags
                    removed += len(removed_tags)
                    cues -= new_tags
                item.cues = normalize_cues(list(cues))
                changed.append(item)
                cue_changes.append((item.id, added_tags if action == "add" else removed_tags))
                updated += 1
            self.backend.update_many(changed)
            if action == "remove":
                self.backend.remove_cues_many(cue_changes)
            else:
                self.backend.add_cues_many(cue_changes)
        return {"updated": updated, "added": added, "removed": removed}




    # -- sleep cycle ----------------------------------------------------------



    # -- active forgetting ----------------------------------------------------

    def forget(self, memory_id: str) -> bool:
        return self.recycle.trash(memory_id)

    def restore(self, memory_id: str) -> bool:
        return self.recycle.restore(memory_id)

    def purge(self, before: datetime | None = None, limit: int = 1000) -> int:
        return self.recycle.purge(before=before, limit=limit)





    # -- metacognition ----------------------------------------------------------

    def check(
        self,
        query: str,
        top_k: int = 3,
        now: datetime | None = None,
        embedder: Embedder | None = None,
    ) -> MetacognitiveCheck:
        return self.meta.check(
            query, top_k=top_k, now=now, embedder=embedder or self.embedder
        )

    def confidence(
        self, item: MemoryItem, now: datetime | None = None
    ) -> tuple[ConfidenceLabel, float]:
        return self.meta.confidence(item, now)

    def calibrated_confidence(
        self, item: MemoryItem, now: datetime | None = None
    ) -> tuple[ConfidenceLabel, float]:
        """Confidence blended with the memory's empirical retrieval hit rate."""
        return self.meta.calibrated_confidence(item, now)

    # -- associations -------------------------------------------------------------

    def related(self, memory_id: str, depth: int = 1, max_nodes: int = 20) -> list[MemoryItem]:
        return self.associations.related(memory_id, depth=depth, max_nodes=max_nodes)

    # -- misc ------------------------------------------------------------------------

    def stats(self) -> dict:
        stats = self.backend.stats()
        stats["trash"] = len(self.recycle.list_trash())
        stats["review_due"] = len(self.review_due(limit=1000))
        return stats

    def calibrate_decay_rate(
        self,
        now: datetime | None = None,
        min_span_hours: float = 1.0,
        floor: float = 0.0005,
        cap: float = 0.02,
        min_samples: int = 5,
    ) -> dict:
        """Calibrate the forgetting rate from real retrieval history.

        A memory that was accessed again after a long gap survived that
        span, so the median creation-to-last-access span across accessed
        memories approximates this user's half-life. The new per-hour
        decay rate is ``ln(2) / median_span``, clamped to ``[floor, cap]``.
        Returns a report and updates ``self.curve.decay_rate`` in place.
        """
        now = now or utcnow()
        spans: list[float] = []
        for item in self.store.all_active():
            if item.access_count <= 0:
                continue
            anchor = item.last_access_at or item.created_at
            span = (anchor - item.created_at).total_seconds() / 3600.0
            if span >= min_span_hours:
                spans.append(span)
        if len(spans) < min_samples:
            return {
                "calibrated": False,
                "decay_rate": self.curve.decay_rate,
                "samples": len(spans),
                "reason": (
                    f"need at least {min_samples} accessed memories with "
                    f"a >= {min_span_hours}h span"
                ),
            }
        median = statistics.median(spans)
        rate = min(cap, max(floor, math.log(2.0) / median))
        old = self.curve.decay_rate
        self.curve.decay_rate = rate
        self.backend.set_setting("decay_rate", str(rate))
        return {
            "calibrated": True,
            "old_decay_rate": old,
            "decay_rate": rate,
            "median_survival_hours": round(median, 1),
            "samples": len(spans),
            "persisted": True,
        }

    def close(self) -> None:
        if hasattr(self.backend, "close"):
            self.backend.close()
        if self.vector_index is not None and hasattr(
            self.vector_index, "close"
        ):
            self.vector_index.close()

    def __enter__(self) -> MemoryEngine:  # noqa: PYI034 (3.10 CI)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()




__all__ = ["MemoryEngine"]
