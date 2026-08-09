"""Mnemosis public facade."""

from __future__ import annotations

import math
import re
import uuid
from itertools import combinations
from collections import Counter, defaultdict, deque
from datetime import date, datetime, timedelta

from .association import AssociationIndex
from .backend import Backend, make_backend
from .consolidation import ConsolidationReport, Consolidator
from .dual_track import DualTrackStore
from .embedding import Embedder
from .forgetting import ForgettingCurve, ReviewScheduler
from .importance import ImportanceScorer
from .metacognition import ConfidenceLabel, Metacognition, MetacognitiveCheck
from .recycle import RecycleBin
from .schema import EventChainIndex
from .reasoning import suggested_pack_size
from .zh_nlp import expand_synonyms, has_cjk
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

_TEMPORAL_STEM_WORDS: dict[str, tuple[str, ...]] = {
    "修": ("修", "维修", "检修", "检测"),
    "补": ("补", "补发", "补胎", "补牙"),
    "打": ("打", "打气", "打针"),
    "交": ("交", "缴费", "交房", "交付"),
    "买": ("买", "购买", "买入"),
    "续": ("续", "续费"),
    "复": ("复", "复查", "复诊"),
    "查": ("查", "检查", "复查", "查房"),
    "检": ("检", "检查", "检测", "体检"),
    "看": ("看", "查看", "看房"),
    "办": ("办", "办理"),
    "发": ("发", "发布", "发放"),
    "报": ("报", "报名", "报到", "报销"),
    "学": ("学", "学习", "上学"),
    "装": ("装", "安装", "加装"),
    "退": ("退", "退款", "退货", "退换"),
    "换": ("换", "更换", "换新", "换货"),
}
_TEMPORAL_ACTION_SYNONYMS: tuple[tuple[str, str], ...] = (
    ("复习", "备考"),
    ("复查", "复诊"),
    ("维修", "检测"),
    ("选品", "上新"),
    ("采摘", "摘", "收获", "收"),
    ("看电影", "观影", "看", "点映"),
    ("保洁", "清洁", "除螨", "擦玻璃", "大扫除", "深度保洁", "家政"),
    ("陪诊", "看门诊", "门诊", "取药", "取报告", "复查", "复诊", "检查", "手术"),
    ("上课", "复课", "补课", "公开课", "课程", "训练", "训练课", "集训", "训导"),
    ("维修", "修理", "检修", "疏通", "维护", "保养", "换修", "修复"),
)
_TEMPORAL_EXCLUSIONS: tuple[tuple[str, str], ...] = (
    ("主观题", "客观题"),
    ("爬山", "夜爬"),
    ("复诊", "复查"),
    ("模考", "考试"),
    ("模考", "通过"),
    ("模考", "出分"),
    ("模考", "成绩"),
)
_PROBLEM_Q_RE = re.compile(
    r"什么问题|什么病|什么毛病|怎么了|什么情况|怎么解决|怎么处理|"
    r"怎么办|怎么救|怎么治"
)
_PROBLEM_WORD_RE = re.compile(
    r"有虫|坏了|故障|失灵|破损|变形|闪烁|告警|鼓包|不制冷|"
    r"磨脚|偏大|漏|丢失|褪色|松动|异响|碎了|压坏|空鼓|"
    r"结膜炎|发炎|感染|过敏|瘦了|信号差|信号问题|"
    r"化水|烂根|黄叶|枯萎|生虫|抢救|控水"
)
_MONEY_Q_RE = re.compile(r"多少钱|价格|费用|价钱|多少元|几块|票价")
_MONEY_PAT_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:元|块|万)")
_MONEY_PRICE_RE = re.compile(
    r"价格|售价|成交价|费用|花了|花费|买成|入手价|报价|标价|收费"
)
_CONTACT_Q_RE = re.compile(r"电话|号码|联系方式")
_CONTACT_PAT_RE = re.compile(
    r"(?:\d{3,4}-){1,2}\d{3,4}|\d{3,4}-\d{7,8}|400-\d{3}-\d{4}"
)
_HOURS_Q_RE = re.compile(r"几点|营业时间|开门|关门")
_HOURS_WORD_RE = re.compile(r"营业|开门|关门|点到")
_PURCHASE_Q_RE = re.compile(
    r"买了什么|买了哪些|买过什么|买了什么设备|买了什么装备|"
    r"放了哪些|放了什么|存放了哪些|存放了些什么|存了什么|"
    r"装了哪些|收纳了哪些|放了什么物品|存了哪些"
)
_STORAGE_Q_RE = re.compile(
    r"放了哪些|放了什么|存放了哪些|存放了些什么|存了什么|"
    r"装了哪些|收纳了哪些|放了什么物品|存了哪些"
)
_SCOPE_Q_RE = re.compile(
    r"收哪些|收什么|可以收什么|有哪些|包含哪些|包括哪些|"
    r"有哪几类|分几类|什么书|哪些种类|哪些项目|哪些内容|"
    r"哪些服务|哪些业务|提供哪些|卖哪些"
)
_SCOPE_WORD_RE = re.compile(
    r"范围|包括|包含|均可|不收|种类|分类|清单|项目|内容|车型|型号|类型|"
    r"科室|部门|设施"
)
_PURCHASE_WORD_RE = re.compile(
    r"买|购买|购入|入手|添置|存放|放入|存了|装了|收纳|放进|搁置"
)
_STORAGE_WORD_RE = re.compile(r"存放|放入|存了|装了|收纳|放进|搁置")

class MemoryEngine:
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
        decay_rate: float = 0.002,
        base_interval_hours: float = 24.0,
        importance_scorer: ImportanceScorer | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        self.backend: Backend = make_backend(memory_file)
        self.curve = ForgettingCurve(decay_rate)
        self.scheduler = ReviewScheduler(self.curve, base_interval_hours)
        self.scorer = importance_scorer or ImportanceScorer()
        self.embedder = embedder
        self.store = DualTrackStore(self.backend, self.curve, self.scorer)
        self.associations = AssociationIndex(self.backend)
        self.event_chain = EventChainIndex(self.backend)
        self.consolidator = Consolidator(self.store, self.backend)
        self.meta = Metacognition(self.store, self.curve, self.consolidator)
        self.recycle = RecycleBin(self.backend)
        self._recall_log: deque[dict] = deque(maxlen=100)
        self._intents: dict[str, dict] = {}
        self._suppressed_ids: dict[str, str] = {}

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
        if item.kind is MemoryKind.EPISODIC:
            self.event_chain.invalidate()
        return item

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
        return item

    def recall(
        self,
        query: str,
        *,
        kind: MemoryKind | None = None,
        top_k: int = 5,
        now: datetime | None = None,
        context: str | None = None,
        context_boost: bool = True,
        elaborate_links: bool = True,
        self_reference_boost: bool = True,
        source_trust_boost: bool = True,
        source_trust_weight: float = 0.06,
        mood_congruent_boost: bool = True,
        mood_boost_weight: float = 0.05,
        confidence_boost: bool = True,
        confidence_weight: float = 0.05,
        gist_preference: bool = True,
        gist_boost: float = 0.20,
        emotional_salience_boost: bool = True,
        emotional_salience_weight: float = 0.05,
        second_look: bool = False,
        conflict_flag: bool = True,
        corroboration_boost: bool = True,
        corroboration_weight: float = 0.03,
        revision_flag: bool = True,
        decay_flag: bool = True,
        suppression_factor: float = 0.01,
        suppression_min_cues: int = 2,
        suppression_floor: float = 0.7,
        embedder: Embedder | None = None,
        expansion_discount: float = 0.95,
        temporal_boost: float = 1.0,
        temporal_reason: bool = True,
        reasoning_pack: bool = True,
        zh_synonyms: bool = True,
        pattern_completion: bool = True,
        separation: bool = True,
        kind_preference: bool = True,
        concept_coverage: bool = True,
        entity_anchor: bool = True,
        value_anchor: bool = True,
        temporal_anchor: bool = True,
        problem_anchor: bool = True,
        contact_anchor: bool = True,
        purchase_anchor: bool = True,
        scope_anchor: bool = True,
        exclude_ids: set[str] | None = None,
    ) -> list[RecallResult]:
        embedder = embedder or self.embedder
        exclude_ids = set(exclude_ids or ()) | set(self._suppressed_ids)
        results = self.store.recall(
            query,
            kind=kind,
            top_k=top_k,
            now=now,
            context=context,
            context_boost=context_boost,
            elaborate_links=elaborate_links,
            self_reference_boost=self_reference_boost,
            source_trust_boost=source_trust_boost,
            source_trust_weight=source_trust_weight,
            mood_congruent_boost=mood_congruent_boost,
            mood_boost_weight=mood_boost_weight,
            confidence_boost=confidence_boost,
            confidence_weight=confidence_weight,
            gist_preference=gist_preference,
            gist_boost=gist_boost,
            emotional_salience_boost=emotional_salience_boost,
            emotional_salience_weight=emotional_salience_weight,
            second_look=second_look,
            conflict_flag=conflict_flag,
            corroboration_boost=corroboration_boost,
            corroboration_weight=corroboration_weight,
            revision_flag=revision_flag,
            decay_flag=decay_flag,
            suppression_factor=suppression_factor,
            suppression_min_cues=suppression_min_cues,
            suppression_floor=suppression_floor,
            embedder=embedder,
            expansion_discount=expansion_discount,
            event_chain=self.event_chain,
            temporal_boost=temporal_boost,
            temporal_reason=temporal_reason,
            reasoning_pack=reasoning_pack,
            zh_synonyms=zh_synonyms,
            pattern_completion=pattern_completion,
            separation=separation,
            kind_preference=kind_preference,
            exclude_ids=exclude_ids,
        )
        self._recall_log.append(
            {
                "query": query,
                "top_id": results[0].item.id if results else None,
                "top_preview": (
                    results[0].item.content[:40] if results else None
                ),
                "confident": results[0].confident if results else None,
                "ts": utcnow().isoformat(),
            }
        )
        if concept_coverage:
            results = self._apply_concept_coverage(
                query,
                results,
                top_k=top_k,
                kind=kind,
                now=now,
                context=context,
                embedder=embedder,
                exclude_ids=exclude_ids,
                reasoning_pack=reasoning_pack,
                zh_synonyms=zh_synonyms,
                pattern_completion=pattern_completion,
                separation=separation,
            )
        if entity_anchor:
            results = self._apply_entity_anchor(
                query,
                results,
                top_k=top_k,
                kind=kind,
                exclude_ids=exclude_ids,
            )
        if value_anchor:
            results = self._apply_value_anchor(
                query,
                results,
                top_k=top_k,
                kind=kind,
                exclude_ids=exclude_ids,
            )
        if temporal_anchor:
            results = self._apply_temporal_anchor(
                query,
                results,
                top_k=top_k,
                kind=kind,
                exclude_ids=exclude_ids,
                now=now,
            )
        if problem_anchor:
            results = self._apply_problem_anchor(
                query,
                results,
                top_k=top_k,
                kind=kind,
                exclude_ids=exclude_ids,
            )
        if contact_anchor:
            results = self._apply_contact_anchor(
                query,
                results,
                top_k=top_k,
                kind=kind,
                exclude_ids=exclude_ids,
            )
        if purchase_anchor:
            results = self._apply_purchase_anchor(
                query,
                results,
                top_k=top_k,
                kind=kind,
                exclude_ids=exclude_ids,
            )
        if scope_anchor:
            results = self._apply_scope_anchor(
                query,
                results,
                top_k=top_k,
                kind=kind,
                exclude_ids=exclude_ids,
            )
        return results

    def _concept_chunks(self, query: str) -> list[str]:
        """Split a Chinese multi-concept query into chunks (working memory
        chunking; Miller, 1956). "A 和 B 分别是多少" becomes [A, B] so each
        concept gets a retrieval vote instead of being diluted in one
        bag-of-tokens query."""

        if not any("\u4e00" <= ch <= "\u9fff" for ch in query):
            return []
        parts = re.split(r"[和与以及、,，及]+", query)
        chunks = [part.strip() for part in parts if len(part.strip()) >= 2]
        return chunks if len(chunks) >= 2 else []

    def _apply_concept_coverage(
        self,
        query: str,
        results: list[RecallResult],
        *,
        top_k: int,
        kind: MemoryKind | None,
        now: datetime | None,
        context: str | None,
        embedder: Embedder | None,
        exclude_ids: set[str],
        reasoning_pack: bool,
        zh_synonyms: bool,
        pattern_completion: bool,
        separation: bool,
    ) -> list[RecallResult]:
        """Ensure every concept chunk of a multi-part question is covered.

        Multi-concept questions ("移动速度和跳跃力度分别是多少") dilute
        each concept's terms; one concept's best memory can fall just
        below top-k. This re-queries each uncovered chunk and inserts its
        best candidate (concept coverage), then re-ranks and truncates.
        """
        chunks = self._concept_chunks(query)
        if not chunks or not results:
            return results

        seen = {result.item.id for result in results}
        for chunk in chunks:
            terms = self._concept_terms(chunk)
            if not terms:
                continue
            candidates = self._chunk_top_candidates(
                chunk,
                terms,
                kind=kind,
                exclude_ids=exclude_ids,
                limit=3,
            )
            if any(
                candidate.id in seen and score >= 0.35
                for score, candidate in candidates
            ):
                continue
            for score, candidate in candidates:
                if candidate.id in seen or score < 0.35:
                    continue
                result = RecallResult(candidate, score)
                if not any(
                    reason.startswith("概念覆盖")
                    for reason in result.reasons
                ):
                    result.reasons.append(f"概念覆盖({chunk[:12]})")
                results.append(result)
                seen.add(candidate.id)
                break
        results.sort(key=lambda result: result.score, reverse=True)
        return results[: max(1, int(top_k))]

    def _chunk_top_candidates(
        self,
        chunk: str,
        terms: set[str],
        *,
        kind: MemoryKind | None,
        exclude_ids: set[str],
        limit: int = 3,
    ) -> list[tuple[float, MemoryItem]]:
        """Score every active memory against one concept chunk."""

        rows: list[tuple[float, MemoryItem]] = []
        for item in self.store.all_active(kind=kind):
            if item.id in exclude_ids:
                continue
            text = item.content + " " + " ".join(item.cues)
            item_terms = set(tokenize(text))
            overlap = len(terms & item_terms)
            if overlap == 0:
                continue
            score = overlap / max(1, len(terms))
            if chunk in text:
                score += 0.5
            rows.append((round(score, 4), item))
        rows.sort(key=lambda pair: (-pair[0], pair[1].id))
        return rows[: max(1, int(limit))]

    def _concept_terms(self, chunk: str) -> set[str]:
        """Meaningful terms of one concept chunk (no function words)."""

        generic = {
            "多少", "分别", "是", "什么", "哪些", "怎么", "如何",
            "一个", "那个", "这个", "还有", "哪些", "多少",
        }
        return {
            term
            for term in tokenize(chunk)
            if len(term) >= 2 and term not in generic
        }

    def concept_cover(
        self,
        query: str,
        *,
        top_k: int = 4,
        now: datetime | None = None,
    ) -> dict:
        """Expose the concept-coverage retrieval path to agents.

        For a multi-concept Chinese question ("A 和 B 分别是多少") this
        returns the detected chunks, each chunk's best candidates,
        whether each chunk is covered in the final top-k, and the final
        context - so the agent can see why every concept is represented
        (working-memory chunking; Miller, 1956). Read-only.
        """
        chunks = self._concept_chunks(query)
        final = self.recall(query, top_k=top_k, now=now)
        final_ids = {result.item.id for result in final}
        per_chunk: list[dict] = []
        for chunk in chunks:
            terms = self._concept_terms(chunk)
            candidates = [
                {
                    "id": item.id,
                    "preview": item.content[:50],
                    "score": score,
                }
                for score, item in self._chunk_top_candidates(
                    chunk,
                    terms,
                    kind=None,
                    exclude_ids=set(),
                    limit=3,
                )
            ]
            covered = any(
                candidate["id"] in final_ids
                and candidate["score"] >= 0.35
                for candidate in candidates
            )
            per_chunk.append(
                {
                    "chunk": chunk,
                    "terms": sorted(terms),
                    "covered": covered,
                    "candidates": candidates,
                }
            )
        multi = len(chunks) >= 2
        if multi and all(entry["covered"] for entry in per_chunk):
            advice = (
                "多概念问题：每个概念都已在最终上下文里覆盖到，"
                "可以放心作答。"
            )
        elif multi:
            advice = (
                "多概念问题：还有概念没覆盖到，建议把缺失概念的候选"
                "单独加入上下文，或换个说法再问。"
            )
        else:
            advice = "单概念问题：不需要分块覆盖。"
        return {
            "query": query,
            "multi_concept": multi,
            "chunks": chunks,
            "per_chunk": per_chunk,
            "final_top_k": [
                {
                    "id": result.item.id,
                    "preview": result.item.content[:60],
                    "score": round(result.score, 3),
                    "reasons": result.reasons,
                }
                for result in final
            ],
            "verdict": "multi" if multi else "single",
            "advice": advice,
        }

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

    def _apply_entity_anchor(
        self,
        query: str,
        results: list[RecallResult],
        *,
        top_k: int,
        kind: MemoryKind | None,
        exclude_ids: set[str],
    ) -> list[RecallResult]:
        """Anchor entity-number questions to the canonical record.

        Questions like "航班号/票号/保单号/编号是多少" are often answered
        by a reminder or a changelog that merely mentions the identifier,
        while the canonical record (the booking, the policy) ranks just
        below top-k. This post-pass scans active memories for the entity
        word plus a real identifier token (e.g. 航班 MU523, 保单号
        AL-889900) and inserts the best such record into the top-k with
        an 实体锚点 reason.
        """

        if self._ENTITY_QUESTION_RE is None:
            self._ENTITY_QUESTION_RE = re.compile(
                r"(航班号|票号|保单号|订单号|编号|号码|房间号|"
                r"账号|卡号|单号|证号)"
            )
            self._ENTITY_RECORD_RE = re.compile(
                r"(航班|保单|票号|订单号|编号|房间号|账号|卡号|单号|证号|票)"
                r"[\s:：\-]*"
                r"([A-Za-z]{1,8}[-]?\d{2,}|\d{3,})"
            )
        if not self._ENTITY_QUESTION_RE.search(query) or not results:
            return results
        seen = {result.item.id for result in results}
        for memory_id in seen:
            item = self.backend.get(memory_id)
            if item is None:
                continue
            match = self._ENTITY_RECORD_RE.search(item.content)
            if match and (
                match.group(1) in query
                or match.group(1) + "号" in query
            ):
                return results
        candidates: list[tuple[float, MemoryItem]] = []
        for item in self.store.all_active(kind=kind):
            if item.id in exclude_ids or item.id in seen:
                continue
            match = self._ENTITY_RECORD_RE.search(item.content)
            if match:
                entity = match.group(1)
                score = (
                    0.62
                    if entity in query or entity + "号" in query
                    else 0.60
                )
                candidates.append((score, item))
        if not candidates:
            return results
        candidates.sort(key=lambda pair: (-pair[0], pair[1].id))
        for score, candidate in candidates[:1]:
            return self._append_anchor(
                results,
                candidate,
                score,
                "实体锚点(编号记录)",
                top_k,
            )
        return results

    def _apply_value_anchor(
        self,
        query: str,
        results: list[RecallResult],
        *,
        top_k: int,
        kind: MemoryKind | None,
        exclude_ids: set[str],
    ) -> list[RecallResult]:
        """Anchor value questions to the record that carries the answer.

        Questions like "几点到几点/多少/几号/什么时间" are often matched
        by a rule or summary memory while the record that actually carries
        the time range or quantity ranks just below top-k. This post-pass
        inserts the best value-carrying record (time ranges preferred for
        time questions) into the top-k with an 数值锚点 reason.
        """


        if self._VALUE_QUESTION_RE is None:
            self._VALUE_QUESTION_RE = re.compile(
                r"(几点|几点到几点|什么时间|什么时候|几号|多少|"
                r"哪几天|多少钱|多久|几点开始|几点结束|"
                r"几餐|几套|几件|几节|几杯|几盒|几斤|几个人|几小时)"
            )
            self._VALUE_PATTERN_RE = re.compile(
                r"\d{1,2}:\d{2}"
                r"|\d+\s*月\s*\d+\s*日"
                r"|\d+(?:\.\d+)?\s*(?:元|块|天|件|平|平米|%|期|mg|克|kg|万|"
                r"餐|套|节|杯|盒|斤|人|小时)"
                r"|[一二两三四五六七八九十]+\s*(?:餐|套|节|杯|盒|斤|人|"
                r"小时|天)"
            )
            self._TIME_RANGE_RE = re.compile(
                r"\d{1,2}:\d{2}\s*[-—~至到]\s*\d{1,2}:\d{2}"
                r"|(?:早|上午|下午|晚|晚上)?\s*\d{1,2}\s*点"
                r"(?:\d{1,2}\s*分)?\s*[-—~至到]\s*"
                r"(?:早|上午|下午|晚|晚上)?\s*\d{1,2}\s*点"
            )
        if not self._VALUE_QUESTION_RE.search(query) or not results:
            return results
        seen = {result.item.id for result in results}
        query_terms = self._concept_terms(query)
        if not query_terms:
            return results

        if has_cjk(query):
            query_terms = expand_synonyms(query_terms)
        time_marker = bool(
            re.search(r"几点|什么时间|几点到几点", query)
        )
        money_marker = bool(_MONEY_Q_RE.search(query))
        candidates: list[tuple[float, int, MemoryItem, bool]] = []
        for item in self.store.all_active(kind=kind):
            if item.id in exclude_ids:
                continue
            seen_flag = item.id in seen
            if not money_marker and seen_flag:
                continue
            # Money questions anchor only records that carry an amount:
            # a dated notice (开放日 5月22日) must not compete with the
            # actual price record just because it shares the domain term.
            if money_marker and not _MONEY_PAT_RE.search(item.content):
                continue
            if not self._VALUE_PATTERN_RE.search(item.content):
                continue
            text = item.content + " " + " ".join(item.cues)
            item_terms = set(tokenize(text))
            overlap = len(query_terms & item_terms)
            if (overlap < 1 and money_marker) or (
                overlap < 2 and not money_marker
            ):
                continue
            # A money question ("多少钱/价格") must anchor a record that
            # carries an amount (元/块/万), not any dated value record
            # like "日销 80 碗" (number-line units; Dehaene & Brannon,
            # 2011: the unit is part of the quantity).
            if money_marker and _MONEY_PAT_RE.search(item.content):
                # Prefer the record whose amount is the price of the
                # queried item (价格/费用/花了), not a related payment
                # like 年费/续费/充值 that merely sits on the same topic.
                near = any(
                    term in item.content
                    and abs(item.content.find(term) - _MONEY_PAT_RE.search(item.content).start()) <= 15
                    for term in query_terms
                )
                score = (
                    0.63
                    if _MONEY_PRICE_RE.search(item.content) or near
                    else 0.62
                )
            elif time_marker and self._TIME_RANGE_RE.search(item.content):
                score = 0.62
            else:
                score = 0.60
            candidates.append((score, overlap, item, seen_flag))
        if not candidates:
            return results
        if money_marker:
            candidates.sort(
                key=lambda pair: (
                    -pair[1],
                    -(1 if pair[0] >= 0.63 else 0),
                    tuple(-d for d in self._latest_date(pair[2].content)),
                    pair[2].id,
                )
            )
        else:
            candidates.sort(key=lambda pair: (-pair[0], pair[2].id))
        chosen = None
        for score, _overlap, candidate, seen_flag in candidates:
            # Already the top row? Keep it and look for a missing record
            # instead (the anchor adds, it does not duplicate).
            if seen_flag and results and results[0].item.id == candidate.id:
                continue
            chosen = (score, candidate)
            break
        if chosen is None:
            return results
        score, candidate = chosen
        if any(result.item.id == candidate.id for result in results):
            results = [
                result
                for result in results
                if result.item.id != candidate.id
            ]
            if not results:
                results = [RecallResult(candidate, 0.0)]
        return self._append_anchor(
            results,
            candidate,
            score,
            "数值锚点(值记录)",
            top_k,
        )

    @staticmethod
    def _append_anchor(
        results: list[RecallResult],
        candidate: MemoryItem,
        score: float,
        reason: str,
        top_k: int,
    ) -> list[RecallResult]:
        """Shared tail for anchor passes: insert, re-rank, truncate.

        The anchored record is scored just above the current best so a
        deliberate retrieval cue survives top-k truncation (ponytail: one
        path for every anchor instead of four copies).
        """
        result = RecallResult(
            candidate, max(score, results[0].score + 0.01)
        )
        result.reasons.append(reason)
        results.append(result)
        results.sort(key=lambda result: result.score, reverse=True)
        return results[: max(1, int(top_k))]

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
            if cur > best:
                best = cur
        if year is not None:
            for match in MemoryEngine._TEMPORAL_MD_RE.finditer(text):
                cur = (year, int(match.group(1)), int(match.group(2)))
                if cur > best:
                    best = cur
        return best

    def _apply_temporal_anchor(
        self,
        query: str,
        results: list[RecallResult],
        *,
        top_k: int,
        kind: MemoryKind | None,
        exclude_ids: set[str],
        now: datetime | None = None,
    ) -> list[RecallResult]:
        """Anchor "last/next/exact-date" questions to the dated record.

        Episodic retrieval is organized along a temporal-context axis
        (Howard & Kahana, 2002: the temporal context model), and the
        hippocampus encodes time cells that order events across scales
        (Howard & Eichenbaum, 2013). Human ordinal-time processing
        (Gauthier et al., 2020) means "上次复查" selects the latest past
        event while "下次复查" selects the closest future one; Dehaene &
        Brannon (2011) formalize this as a monotone ordering on the
        mental time/number line. An explicit calendar date ("7月2日") is
        treated as a precise point on that line: the record carrying the
        exact month-day is anchored directly. Direction questions parse
        dates as (year, month, day) tuples, keep only records whose date
        lies in the asked direction, and insert the strongest matching
        record into top-k with a 时间锚点 reason. Because a direction
        marker is a strong ordinal retrieval cue, the anchored record is
        scored just above the current best so it survives top-k
        truncation instead of being pushed out by an already-high-ranking
        generic match.
        """

        if not results:
            return results
        past_marker = self._TEMPORAL_PAST_RE.search(query)
        future_marker = self._TEMPORAL_FUTURE_RE.search(query)
        date_marker = self._TEMPORAL_DATE_Q_RE.search(query)
        if not past_marker and not future_marker and not date_marker:
            return results
        now = now or utcnow()
        today = (now.year, now.month, now.day)

        def _dates(
            text: str,
        ) -> tuple[
            list[tuple[int, int, int]], list[tuple[int, int, int]]
        ]:
            full: list[tuple[int, int, int]] = []
            year: int | None = None
            for match in self._TEMPORAL_DATE_RE.finditer(text):
                if match.group(1):
                    year = int(match.group(1))
                    full.append(
                        (
                            year,
                            int(match.group(2)),
                            int(match.group(3)),
                        )
                    )
                else:
                    year = int(match.group(4))
                    full.append(
                        (
                            year,
                            int(match.group(5)),
                            int(match.group(6)),
                        )
                    )
            # Year-less dates ("8 月 20 日") take the year of the first
            # full date in the same record; human memory does the same
            # anchoring (the event's own year supplies the missing digit).
            out = list(full)
            if year is not None:
                for match in self._TEMPORAL_MD_RE.finditer(text):
                    out.append(
                        (year, int(match.group(1)), int(match.group(2)))
                    )
            return full, out

        seen = {result.item.id for result in results}
        query_terms = self._concept_terms(query)
        if not query_terms:
            return results

        # tokenize drops particle forms (续的), so re-add raw verb+particle
        # 2-grams and expand only those ("续的" -> "续费"), never the whole
        # term set (健身 -> 运动/锻炼 would drag in unrelated records).
        particle_terms = {
            match.group(0)
            for match in re.finditer(
                r"[\u4e00-\u9fff](?:的|了|着|过)", query
            )
        }
        if particle_terms:
            query_terms |= expand_synonyms(particle_terms)
        (
            topic_len,
            query_finals,
            verb_stems,
            action_groups,
            excluded_terms,
        ) = self._temporal_probe(query)
        notice_q = self._TEMPORAL_NOTICE_RE.search(query)
        hours_q = bool(_HOURS_Q_RE.search(query))

        if date_marker:
            month, day = (
                int(date_marker.group(1)),
                int(date_marker.group(2)),
            )
            date_frag = f"{month}月{day}日"
            year = self._TEMPORAL_YEAR_RE.search(query)
            target_frag = (
                f"{int(year.group(1))}年{date_frag}" if year else date_frag
            )
            candidates: list[tuple[float, MemoryItem]] = []
            for item in self.store.all_active(kind=kind):
                if item.id in seen or item.id in exclude_ids:
                    continue
                text = item.content + " " + " ".join(item.cues)
                if target_frag not in "".join(text.split()):
                    continue
                if not self._temporal_relevant(
                    query_terms,
                    text,
                    topic_len,
                    query_finals,
                    verb_stems,
                    action_groups,
                    excluded_terms,
                ):
                    continue
                candidates.append((0.62, item))
            if not candidates:
                return results
            candidates.sort(key=lambda pair: (-pair[0], pair[1].id))
            return self._append_anchor(
                results,
                candidates[0][1],
                candidates[0][0],
                f"时间锚点(日期:{date_frag})",
                top_k,
            )

        # Past wins when both directions appear ("上次体检和下次体检分别
        # 是什么时候"): the multi-concept pass still queries each chunk, so
        # a direction-based tie-break keeps the post-pass deterministic.
        want_past = bool(past_marker) and (
            not future_marker or past_marker.start() <= future_marker.start()
        )
        want_earliest = bool(
            re.search(r"第一次|首次|头一回", query)
        )
        candidates: list[tuple[float, MemoryItem]] = []
        for item in self.store.all_active(kind=kind):
            if item.id in seen or item.id in exclude_ids:
                continue
            text = item.content + " " + " ".join(item.cues)
            full, dates = _dates(text)
            if not dates:
                continue
            is_notice = bool(self._TEMPORAL_NOTICE_RE.search(text))
            event_dates = [d for d in dates if d not in set(full)]
            side_dates = (
                event_dates
                if not want_past and is_notice and event_dates
                else dates
            )
            side = (
                [d for d in side_dates if d <= today]
                if want_past
                else [d for d in side_dates if d > today]
            )
            if not side:
                continue
            # Past-direction questions ask about the event itself, not a
            # notice about it: 预约/通知/提醒/调时间 records (source
            # monitoring; Johnson & Raye, 1981) are skipped unless the
            # query is itself asking about the notice OR the record also
            # carries the queried action (第一次预约篮球馆，办月卡 is the
            # 办卡 event, not just a reminder).
            if (
                want_past
                and not notice_q
                and self._TEMPORAL_NOTICE_RE.search(text)
                and not any(
                    word in text
                    for stem in verb_stems
                    for word in _TEMPORAL_STEM_WORDS.get(stem, (stem,))
                )
            ):
                continue
            # Candidates must carry the topic in their own content, not
            # just a cue: "新规则生效" with a 截单 cue is not the answer
            # to 什么时候截单.
            if not self._temporal_relevant(
                query_terms,
                item.content,
                topic_len,
                query_finals,
                verb_stems,
                action_groups,
                excluded_terms,
            ):
                continue
            # Hours questions (几点开门/营业时间) must anchor a record
            # that actually states opening hours: a newer but unrelated
            # same-shop event (四轮定位) must not win by date alone.
            if hours_q and not _HOURS_WORD_RE.search(item.content):
                continue
            # Money questions must anchor a record that actually carries
            # an amount, not e.g. a 协议 notice about the boarding shop.
            if _MONEY_Q_RE.search(query) and not _MONEY_PAT_RE.search(
                item.content
            ):
                continue
            if want_earliest:
                target = min(side)
            else:
                target = max(side) if want_past else min(side)
            # A record whose own full date is the direction target is the
            # event record (strong anchor). Records that merely mention
            # the date ("报名 3 月 20 日") score lower, so they cannot
            # displace the actual event record.
            full_side = (
                [d for d in full if d <= today]
                if want_past
                else [d for d in full if d > today]
            )
            extreme = (
                min(full) if want_earliest else max(full)
            ) if want_past else min(full)
            score = (
                0.62
                if full_side and target == extreme
                else 0.60
            )
            candidates.append((score, target, item))
        if not candidates:
            return results
        candidates.sort(
            key=lambda pair: (
                tuple(-d for d in pair[1])
                if want_past and not want_earliest
                else pair[1],
                -pair[0],
                pair[2].id,
            )
        )
        score, target, candidate = candidates[0]
        candidate_terms = set(
            tokenize(candidate.content + " " + " ".join(candidate.cues))
        )
        # For past questions about the event itself, notices (预约/通知/
        # 提醒/调时间) only confuse the answer model: the "latest class"
        # row with no content makes it answer 不知道. Drop them when
        # enough real event records exist (source monitoring; Johnson &
        # Raye, 1981).
        if want_past and not notice_q:
            event_rows = [
                result
                for result in results
                if not (
                    self._TEMPORAL_NOTICE_RE.search(
                        result.item.content
                        + " "
                        + " ".join(result.item.cues)
                    )
                    and not any(
                        word in result.item.content
                        for stem in verb_stems
                        for word in _TEMPORAL_STEM_WORDS.get(stem, (stem,))
                    )
                )
            ]
            if event_rows:
                results = event_rows
        # Topic opposites (爬山 vs 夜爬, 主观题 vs 客观题) must not sit in
        # the context and trick the answer model into picking the newer
        # but wrong record.
        if excluded_terms:
            clean_rows = [
                result
                for result in results
                if not any(
                    word in result.item.content for word in excluded_terms
                )
            ]
            if clean_rows:
                results = clean_rows
        # Future-direction questions ("下次/接下来") must not carry
        # stale dated records in the context: a past appointment only
        # tricks the answer model into picking a date that already
        # happened. Human "next" queries ignore expired schedule rows.
        if not want_past:
            future_rows = []
            for result in results:
                if result.item.id in exclude_ids:
                    future_rows.append(result)
                    continue
                text = result.item.content + " " + " ".join(result.item.cues)
                full, dates = _dates(text)
                if dates and not any(d > today for d in dates):
                    continue
                future_rows.append(result)
            if future_rows:
                results = future_rows
        # If some result already present is a relevant dated record at
        # least as strong in the asked direction, keep the current list.
        for result in results:
            if result.item.id in exclude_ids:
                continue
            text = result.item.content + " " + " ".join(result.item.cues)
            full, all_dates = _dates(text)
            if not all_dates:
                continue
            if (
                want_past
                and not notice_q
                and self._TEMPORAL_NOTICE_RE.search(text)
                and not any(
                    word in text
                    for stem in verb_stems
                    for word in _TEMPORAL_STEM_WORDS.get(stem, (stem,))
                )
            ):
                continue
            # A seen record only "covers" the question when its own
            # content (not just cues) carries a query term: "新规则生效"
            # with a 截单 cue must not block the 公告 that actually says
            # 每日截单.
            if not self._temporal_relevant(
                query_terms,
                result.item.content,
                topic_len,
                query_finals,
                verb_stems,
                action_groups,
                excluded_terms,
            ):
                continue
            if _MONEY_Q_RE.search(query) and not _MONEY_PAT_RE.search(
                result.item.content
            ):
                continue
            if not self._temporal_relevant(
                query_terms,
                text,
                topic_len,
                query_finals,
                verb_stems,
                action_groups,
                excluded_terms,
            ):
                continue
            if hours_q and not _HOURS_WORD_RE.search(text):
                continue
            # A seen record only "covers" the question when it is about
            # the same event as the candidate, not merely the same domain:
            # 钟点工保险 record must not block 考核完成 because both mention
            # 钟点工. Require a shared query-relevant term with the
            # candidate (the distinctive action/noun), except for
            # earliest-event questions where the covering record may be a
            # different but earlier instance.
            if (
                not want_earliest
                and not (set(tokenize(text)) & query_terms & candidate_terms)
            ):
                continue
            is_notice = bool(self._TEMPORAL_NOTICE_RE.search(text))
            event_dates = [d for d in all_dates if d not in set(full)]
            pool = (
                event_dates
                if not want_past and is_notice and event_dates
                else (full if want_past else all_dates)
            )
            side = [d for d in pool if d <= today] if want_past else [
                d for d in pool if d > today
            ]
            if not side:
                continue
            if want_earliest:
                seen_best = min(side)
            else:
                seen_best = max(side) if want_past else min(side)
            if (want_earliest and seen_best <= target) or (
                want_past and not want_earliest and seen_best >= target
            ) or (
                not want_past and seen_best <= target
            ):
                # The blocking record is already the strongest answer;
                # move it to the front so the answer model cannot miss it.
                results.remove(result)
                results.insert(0, result)
                return results
        return self._append_anchor(
            results,
            candidate,
            score,
            "时间锚点(最早)" if want_earliest else (
                "时间锚点(上次)" if want_past else "时间锚点(下次)"
            ),
            top_k,
        )

    def _apply_problem_anchor(
        self,
        query: str,
        results: list[RecallResult],
        *,
        top_k: int,
        kind: MemoryKind | None,
        exclude_ids: set[str],
    ) -> list[RecallResult]:
        """Anchor "what went wrong" questions to the fault record.

        "大米多少钱？出了什么问题？" matches the purchase record while
        the record that actually says 米有虫 ranks below top-k. This
        post-pass scans for records carrying a fault word (有虫/坏了/
        鼓包...) that also shares the query topic, and inserts the best
        one (source monitoring: the fault report is the event).
        """
        if not _PROBLEM_Q_RE.search(query) or not results:
            return results
        seen = {result.item.id for result in results}
        query_terms = self._concept_terms(query)
        if not query_terms:
            return results
        topic_len, query_finals, _s, _a, _e = self._temporal_probe(query)
        candidates: list[tuple[float, MemoryItem]] = []
        for item in self.store.all_active(kind=kind):
            if item.id in seen or item.id in exclude_ids:
                continue
            if not _PROBLEM_WORD_RE.search(item.content):
                continue
            if not self._temporal_relevant(
                query_terms,
                item.content,
                topic_len,
                query_finals,
                frozenset(),
                frozenset(),
                frozenset(),
            ):
                continue
            candidates.append((0.62, item))
        if not candidates:
            return results
        candidates.sort(key=lambda pair: (-pair[0], pair[1].id))
        return self._append_anchor(
            results,
            candidates[0][1],
            candidates[0][0],
            "问题锚点(故障记录)",
            top_k,
        )

    def _apply_contact_anchor(
        self,
        query: str,
        results: list[RecallResult],
        *,
        top_k: int,
        kind: MemoryKind | None,
        exclude_ids: set[str],
    ) -> list[RecallResult]:
        """Anchor phone/contact questions to the record carrying a number.

        "寄养店电话多少？" often matches visit notes while the record that
        actually holds 400-777-8888 ranks below top-k. This post-pass
        inserts the best contact record (highest relevance, then latest
        date) with a 联系锚点 reason.
        """
        if not _CONTACT_Q_RE.search(query) or not results:
            return results
        seen = {result.item.id for result in results}
        query_terms = self._concept_terms(query)
        if not query_terms:
            return results
        candidates: list[tuple[int, tuple[int, int, int], MemoryItem]] = []
        for item in self.store.all_active(kind=kind):
            if item.id in seen or item.id in exclude_ids:
                continue
            if not _CONTACT_PAT_RE.search(item.content):
                continue
            text = item.content + " " + " ".join(item.cues)

            overlap = len(query_terms & set(tokenize(text)))
            if overlap == 0:
                continue
            candidates.append((overlap, self._latest_date(item.content), item))
        if not candidates:
            return results
        candidates.sort(
            key=lambda pair: (-pair[0], tuple(-d for d in pair[1]), pair[2].id)
        )
        return self._append_anchor(
            results,
            candidates[0][2],
            0.62,
            "联系锚点(电话记录)",
            top_k,
        )

    def _apply_purchase_anchor(
        self,
        query: str,
        results: list[RecallResult],
        *,
        top_k: int,
        kind: MemoryKind | None,
        exclude_ids: set[str],
    ) -> list[RecallResult]:
        """Anchor "买了什么" questions to the purchase records.

        "买了什么安防设备？" often matches a service note while the actual
        purchase records (买监控摄像头 / 买智能门锁) rank below top-k.
        This post-pass inserts the best purchase records (up to 2, since
        the answer often spans several items) with a 购买锚点 reason.
        """

        if not _PURCHASE_Q_RE.search(query) or not results:
            return results
        seen = {result.item.id for result in results}
        query_terms = self._concept_terms(query)
        if has_cjk(query):
            query_terms = expand_synonyms(query_terms)
        if not query_terms:
            return results
        storage_q = bool(_STORAGE_Q_RE.search(query))
        word_re = _STORAGE_WORD_RE if storage_q else _PURCHASE_WORD_RE
        candidates: list[tuple[int, tuple[int, int, int], MemoryItem]] = []
        for item in self.store.all_active(kind=kind):
            if item.id in seen or item.id in exclude_ids:
                continue
            text = item.content + " " + " ".join(item.cues)
            if not word_re.search(text):
                continue

            overlap = len(query_terms & set(tokenize(text)))
            if overlap == 0:
                continue
            candidates.append(
                (overlap, self._latest_date(text), item)
            )
        if not candidates:
            return results
        candidates.sort(
            key=lambda pair: (-pair[0], tuple(-d for d in pair[1]), pair[2].id)
        )
        for score, _date, candidate in candidates[:2]:
            results = self._append_anchor(
                results,
                candidate,
                min(0.62, 0.60 + 0.01 * score),
                "购买锚点(购置记录)",
                top_k,
            )
        return results

    def _apply_scope_anchor(
        self,
        query: str,
        results: list[RecallResult],
        *,
        top_k: int,
        kind: MemoryKind | None,
        exclude_ids: set[str],
    ) -> list[RecallResult]:
        """Anchor scope/list questions ("收哪些书/有哪些服务") to the
        record that enumerates the categories (范围/包括/均可/不收).

        Generic recall ranks event records (回收了20本) above the rule
        that actually lists the accepted items, so the enumeration gets
        pushed out of top-k. This post-pass re-inserts it, mirroring
        semantic category memory (Collins & Quillian, 1969: a category
        node stores its members at one hop).
        """

        if not _SCOPE_Q_RE.search(query) or not results:
            return results
        seen = {result.item.id for result in results}
        query_terms = self._concept_terms(query)
        if has_cjk(query):
            query_terms = expand_synonyms(query_terms)
        if not query_terms:
            return results
        candidates: list[tuple[int, tuple[int, int, int], MemoryItem]] = []
        for item in self.store.all_active(kind=kind):
            if item.id in seen or item.id in exclude_ids:
                continue
            text = item.content + " " + " ".join(item.cues)
            if not _SCOPE_WORD_RE.search(text):
                continue
            overlap = len(query_terms & set(tokenize(text)))
            if overlap == 0:
                continue
            candidates.append(
                (overlap, self._latest_date(text), item)
            )
        if not candidates:
            return results
        candidates.sort(
            key=lambda pair: (
                -pair[0],
                tuple(-d for d in pair[1]),
                pair[2].id,
            )
        )
        for overlap, _date, candidate in candidates[:1]:
            return self._append_anchor(
                results,
                candidate,
                min(0.62, 0.60 + 0.01 * overlap),
                "范围锚点(清单记录)",
                top_k,
            )
        return results

    @classmethod
    def _temporal_probe(
        cls,
        query: str,
    ) -> tuple[
        int,
        frozenset[str],
        frozenset[str],
        frozenset[int],
        frozenset[str],
    ]:
        """Precompute per-query topic length and word-final chars once."""
        topic = cls._TEMPORAL_STRIP_RE.sub("", query)
        topic = cls._TEMPORAL_CLEAN_RE.sub("", topic)
        topic_len = sum(1 for ch in topic if "\u4e00" <= ch <= "\u9fff")
        noise = set(cls._TEMPORAL_NOISE)
        query_finals = frozenset(
            ch
            for i, ch in enumerate(query)
            if "\u4e00" <= ch <= "\u9fff"
            and ch not in noise
            and i > 0
            and "\u4e00" <= query[i - 1] <= "\u9fff"
        )
        verb_stems = frozenset(
            match.group(1)
            for match in re.finditer(
                r"([\u4e00-\u9fff])(?:的|了|着|过)", query
            )
            if match.group(1) in _TEMPORAL_STEM_WORDS
        )
        action_groups = frozenset(
            index
            for index, group in enumerate(_TEMPORAL_ACTION_SYNONYMS)
            if any(word in query for word in group)
        )
        excluded_terms = frozenset(
            word
            for group in _TEMPORAL_EXCLUSIONS
            for word in group
            if any(other in query for other in group if other != word)
        )
        return (
            topic_len,
            query_finals,
            verb_stems,
            action_groups,
            excluded_terms,
        )

    @staticmethod
    def _temporal_relevant(
        query_terms: set[str],
        text: str,
        topic_len: int,
        query_finals: frozenset[str],
        verb_stems: frozenset[str],
        action_groups: frozenset[int],
        excluded_terms: frozenset[str],
    ) -> bool:
        """Relevance gate for temporal anchors.

        Bigram overlap is the primary signal; a character-level fallback
        catches Chinese near-synonyms that share a morpheme but not a
        bigram ("面试" vs "终面" share 面). The fallback only fires for
        short topics (2 meaningful chars like 面试/复诊): when the topic
        is longer ("托福考试"), a lone shared final char (考试 vs 面试's
        试) is not enough and a real bigram overlap is required. Only
        word-final shared characters count, so "试用期" cannot
        masquerade as an interview memory via its 试. Function/noise
        characters are excluded so "上次/哪天/是什么" do not create false
        hits.
        """

        # Topic exclusions: asking about 客观题 must not match a record
        # that says 主观题 (and vice versa).
        if excluded_terms and any(word in text for word in excluded_terms):
            return False
        if query_terms & set(tokenize(text)):
            return True
        # Action synonyms: "现在怎么复习" matches records written as
        # 备考 (near-synonym actions in Chinese).
        if action_groups and any(
            any(word in text for word in _TEMPORAL_ACTION_SYNONYMS[index])
            for index in action_groups
        ):
            return True
        # Verb-stem fallback: "修的什么" -> 修 matches "修好" (the stem is
        # followed by a result complement in the record). Each stem maps
        # to a small set of near-synonym action words (修 -> 检修/检测),
        # so 考/试 cannot leak into 考核/面试.
        if verb_stems:
            for stem in verb_stems:
                for word in _TEMPORAL_STEM_WORDS.get(stem, (stem,)):
                    if word in text:
                        return True
        if topic_len >= 3:
            # Long topics (托福考试/去银行办信用卡) need a real shared
            # bigram; a single common character is not enough.
            return False
        if not query_finals:
            return False
        return any(
            ch in query_finals
            and j > 0
            and "\u4e00" <= text[j - 1] <= "\u9fff"
            for j, ch in enumerate(text)
        )

    def temporal_anchor(
        self,
        query: str,
        *,
        top_k: int = 4,
        kind: MemoryKind | None = None,
        now: datetime | None = None,
    ) -> dict:
        """Expose the temporal-anchor retrieval path to agents (round 265).

        Runs a normal recall and reports which memories were inserted by
        the time-anchor pass, so an agent can verify that "上次/下次" style
        questions surface the record carrying the requested date
        (ordinal-time processing; Gauthier et al., 2020). Read-only.
        """
        final = self.recall(query, top_k=top_k, kind=kind, now=now)
        anchored = [
            {
                "id": result.item.id,
                "preview": result.item.content[:60],
                "score": round(result.score, 3),
                "reasons": result.reasons,
            }
            for result in final
            if any(reason.startswith("时间锚点") for reason in result.reasons)
        ]
        return {
            "query": query,
            "anchored": anchored,
            "final_top_k": [
                {
                    "id": result.item.id,
                    "preview": result.item.content[:60],
                    "score": round(result.score, 3),
                    "reasons": result.reasons,
                }
                for result in final
            ],
            "verdict": "anchored" if anchored else "none",
        }

    def temporal_hint(self, query: str) -> str | None:
        """Return a one-line answer-model hint for temporal questions.

        Small and cloud models often answer 不知道 when several dated rows
        look plausible ("上次/最近/现在怎么复习"). This hint tells the
        answer model which direction to pick without revealing any answer
        content, so the retrieved context is self-guiding (retrieval cue
        elaboration; Craik & Tulving, 1975).
        """
        excluded = self._temporal_probe(query)[4]
        note = (
            "另注意：区分主观题与客观题、模考与正式考试，不要混用。"
            if excluded
            else ""
        )
        if re.search(r"第一次|首次|头一回", query):
            return (
                "提示：问题在问第一次/首次发生的事，答案应选日期最早"
                "且话题匹配的那条记忆。" + note
            )
        if self._TEMPORAL_PAST_RE.search(query):
            return (
                "提示：问题在问过去/最近/现在的情况，答案应选日期最新"
                "且话题匹配的那条记忆。" + note
            )
        if self._TEMPORAL_FUTURE_RE.search(query):
            return (
                "提示：问题在问接下来的安排，答案应选日期最近未来的"
                "那条记忆。" + note
            )
        if self._TEMPORAL_DATE_Q_RE.search(query):
            return (
                "提示：问题指定了具体日期，答案应选包含该日期的那条记忆。"
                + note
            )
        return note or None

    def get_recall_log(self, limit: int = 50) -> list[dict]:
        """Return the most recent recall entries (bounded audit log)."""
        return list(self._recall_log)[-max(1, int(limit)):]

    def search_batch(
        self,
        queries: list[str],
        *,
        top_k: int = 3,
        kind: MemoryKind | None = None,
        now: datetime | None = None,
    ) -> list[dict]:
        """Run several recall queries in one call.

        Returns one result group per query in the input order, so agents
        can fan out a whole question list through a single MCP round trip
        (working-memory chunking; Miller, 1956).
        """
        out: list[dict] = []
        for query in queries:
            results = self.recall(
                query, kind=kind, top_k=top_k, now=now
            )
            out.append(
                {
                    "query": query,
                    "count": len(results),
                    "results": [
                        {
                            "id": r.item.id,
                            "preview": r.item.content[:40],
                            "score": round(r.score, 4),
                            "confident": r.confident,
                        }
                        for r in results
                    ],
                }
            )
        return out

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
        self._intents[record["id"]] = record
        return dict(record)

    def intent_due(
        self,
        now: datetime | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Return active intents whose deadline has arrived."""

        now = now or utcnow()
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
        record = self._intents.get(intent_id)
        if record is None or record["status"] != "active":
            return None
        record["status"] = "completed"
        record["completed_at"] = now.isoformat()
        return dict(record)

    def cancel_intent(self, intent_id: str) -> dict | None:
        """Cancel an intent without completing it."""
        record = self._intents.get(intent_id)
        if record is None or record["status"] != "active":
            return None
        record["status"] = "cancelled"
        return dict(record)

    def intent_report(self, now: datetime | None = None) -> dict:
        """Summarize the intention register (due / upcoming / done)."""

        now = now or utcnow()
        active = [
            r for r in self._intents.values() if r["status"] == "active"
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
                1 for r in self._intents.values()
                if r["status"] == "completed"
            ),
            "cancelled": sum(
                1 for r in self._intents.values()
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

    def memory_health(self) -> dict:
        """Return one overall memory-health score with sub-metrics.

        Metacognitive monitoring (Koriat & Goldsmith, 1996): a memory
        system should know how healthy it is. This aggregates existing
        read-only signals - linked ratio, crowded cues, conflicts,
        overdue/clashing intentions and suppressed memories - into a
        0-100 score with itemized penalties.
        """
        active = self.store.all_active()
        memory_count = len(active)
        assoc = self.association_report(limit=5)
        connected = assoc["connected_count"]
        linked_ratio = (
            round(connected / memory_count, 3) if memory_count else 0.0
        )
        crowded = len(
            self.interference_report(shared_cue_min=3)["crowded_clusters"]
        )
        conflicts = len(self.consolidator.detect_conflicts())
        intents = self.intent_report()
        clashes = self.intent_conflicts()["total"]
        suppressed = self.suppressed_report()["count"]
        penalties = {
            "isolated": min(
                20, int(round((1.0 - linked_ratio) * 50))
            ),
            "crowded": min(15, crowded * 3),
            "conflicts": min(20, conflicts * 4),
            "overdue_intents": min(10, intents["overdue"] * 2),
            "intent_clashes": min(10, clashes * 3),
            "suppressed": min(5, suppressed),
        }
        score = max(0, 100 - sum(penalties.values()))
        return {
            "score": score,
            "memory_count": memory_count,
            "linked_ratio": linked_ratio,
            "crowded_clusters": crowded,
            "conflicts": conflicts,
            "overdue_intents": intents["overdue"],
            "intent_clashes": clashes,
            "suppressed_count": suppressed,
            "penalties": penalties,
        }

    def kg_export(self) -> dict:
        """Export the memory network as a knowledge-graph edge list.

        Semantic-network organization (Collins & Quillian, 1969): related
        facts form a graph. This returns nodes and deduplicated undirected
        edges so external tools can visualize or analyze the store.
        """
        items = {
            item.id: item for item in self.store.all_active()
        }
        nodes = [
            {
                "id": item.id,
                "label": item.content[:24],
                "kind": item.kind.value,
            }
            for item in items.values()
        ]
        edges = []
        seen: set[frozenset[str]] = set()
        for src, dst, weight in self.backend.all_links():
            if src not in items or dst not in items:
                continue
            pair = frozenset((src, dst))
            if pair in seen:
                continue
            seen.add(pair)
            edges.append(
                {
                    "source": src,
                    "target": dst,
                    "weight": round(float(weight), 3),
                }
            )
        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def learner_profile(self, now: datetime | None = None) -> dict:
        """Estimate the learner's rate from review history.

        Adaptive spaced repetition estimates learning rate from observed
        retrieval success (Mozer et al., 2009): fast learners get longer
        intervals, struggling ones get shorter ones. This reports the
        estimated profile and a suggested interval scale.
        """
        items = self.store.all_active()
        total_reviews = 0
        successes = 0
        retrievability_sum = 0.0
        importance_sum = 0.0
        for item in items:
            total_reviews += (
                item.retrieval_successes + item.retrieval_failures
            )
            successes += item.retrieval_successes
            retrievability_sum += self.curve.retrievability(item, now)
            importance_sum += item.importance
        n = len(items)
        success_rate = (
            successes / total_reviews if total_reviews else None
        )
        if n == 0 or success_rate is None:
            profile = "unknown"
            scale = 1.0
        elif success_rate >= 0.8:
            profile = "fast"
            scale = 1.2
        elif success_rate >= 0.6:
            profile = "steady"
            scale = 1.0
        else:
            profile = "struggling"
            scale = 0.8
        return {
            "total_memories": n,
            "total_reviews": total_reviews,
            "success_rate": (
                round(success_rate, 3) if success_rate is not None else None
            ),
            "avg_retrievability": round(
                retrievability_sum / max(1, n), 3
            ),
            "avg_importance": round(importance_sum / max(1, n), 3),
            "profile": profile,
            "suggested_interval_scale": scale,
        }

    def context_pack(
        self,
        queries: list[str],
        *,
        top_k: int = 3,
        max_chars: int = 1200,
        now: datetime | None = None,
    ) -> dict:
        """Pack the best matching memories into a bounded context.

        Working memory is limited; cognitive-load theory (Sweller, 1988)
        says only the essential information should reach the model. This
        runs recall for several queries, deduplicates by id, ranks by
        score and returns as much as fits the character budget.
        """
        best: dict[str, tuple[float, str]] = {}
        found = 0
        for query in queries:
            for result in self.recall(query, top_k=top_k, now=now):
                if not any(
                    "overlap" in r
                    or "semantic" in r
                    or r.startswith("概念覆盖")
                    for r in result.reasons
                ):
                    continue
                found += 1
                item = result.item
                current = best.get(item.id)
                if current is None or result.score > current[0]:
                    best[item.id] = (
                        result.score, item.content
                    )
        ranked = sorted(
            best.items(), key=lambda kv: kv[1][0], reverse=True
        )
        packed = []
        used = 0
        truncated = 0
        for memory_id, (score, content) in ranked:
            if used + len(content) > max(1, int(max_chars)) and packed:
                truncated += 1
                continue
            packed.append(
                {
                    "id": memory_id,
                    "content": content,
                    "score": round(score, 3),
                }
            )
            used += len(content)
        return {
            "query_count": len(queries),
            "total_found": found,
            "unique_found": len(best),
            "packed_count": len(packed),
            "packed_chars": used,
            "truncated_count": truncated,
            "packed": packed,
        }

    def encoding_quality(self, memory_id: str) -> dict | None:
        """Score how well one memory was encoded.

        Elaborative encoding (Craik & Tulving, 1975): deeper encoding
        (more cues, context, emotion, importance) makes a memory more
        retrievable. This scores 0-100 and suggests what is missing.
        """
        item = self.backend.get(memory_id)
        if item is None:
            return None
        cue_count = len(item.cues)
        has_context = bool(item.context)
        has_affect = bool(item.affect)
        content_length = len(item.content)
        score = 0.0
        suggestions = []
        if cue_count >= 2:
            score += 25
        elif cue_count == 1:
            score += 15
            suggestions.append("再补 1 个线索（日期/对象/主题）")
        else:
            suggestions.append("没有线索，先加 2 个检索线索")
        if has_context:
            score += 20
        else:
            suggestions.append("缺少情景上下文，补一句当时的环境")
        if has_affect:
            score += 10
        if item.importance >= 0.6:
            score += 15
        elif item.importance >= 0.3:
            score += 10
            suggestions.append("重要度偏低，确认是否值得长期保留")
        if item.strength >= 0.5:
            score += 15
        else:
            suggestions.append("记忆强度偏低，建议尽快复习一次")
        if 10 <= content_length <= 200:
            score += 15
        elif content_length > 200:
            score += 8
            suggestions.append("内容偏长，考虑拆成几条")
        else:
            score += 5
            suggestions.append("内容太短，补充一点细节")
        score = min(100, int(round(score)))
        if score >= 80:
            verdict = "well_encoded"
        elif score >= 60:
            verdict = "adequate"
        else:
            verdict = "weak"
        return {
            "memory_id": memory_id,
            "score": score,
            "verdict": verdict,
            "cue_count": cue_count,
            "has_context": has_context,
            "has_affect": has_affect,
            "importance": round(item.importance, 3),
            "strength": round(item.strength, 3),
            "content_length": content_length,
            "suggestions": suggestions[:4],
        }

    def explain_memory(
        self,
        memory_id: str,
        now: datetime | None = None,
    ) -> dict | None:
        """Explain one memory's full state in plain fields.

        Metacognitive monitoring (Koriat & Goldsmith, 1996): an agent
        should be able to say why a memory exists and how reachable it
        is. This returns content, cues, retrievability, importance,
        strength, confidence, evidence, links, suppression, access and
        review state.
        """
        item = self.backend.get(memory_id)
        if item is None:
            return None
        linked_count = sum(
            1
            for src, dst, _weight in self.backend.all_links()
            if src == memory_id or dst == memory_id
        )
        return {
            "memory_id": memory_id,
            "content": item.content,
            "kind": item.kind.value,
            "created_at": item.created_at.isoformat(),
            "cues": item.cues,
            "retrievability": round(
                self.curve.retrievability(item, now), 3
            ),
            "importance": round(item.importance, 3),
            "strength": round(item.strength, 3),
            "confidence": round(item.confidence, 3),
            "evidence_count": item.evidence_count,
            "linked_count": linked_count,
            "suppressed": memory_id in self._suppressed_ids,
            "access_count": item.access_count,
            "last_access_at": (
                item.last_access_at.isoformat()
                if item.last_access_at is not None
                else None
            ),
            "review_streak": item.review_streak,
            "last_review_at": (
                item.last_review_at.isoformat()
                if item.last_review_at is not None
                else None
            ),
        }

    def compare_memories(self, id_a: str, id_b: str) -> dict | None:
        """Compare two memories: overlap, differences and verdict.

        Source monitoring and schema integration (Johnson, Hashtroudi &
        Lindsay, 1993): agents holding two records of the same event must
        know whether they duplicate, conflict or are simply distinct. This
        reports token overlap, shared cues and a verdict.
        """

        a = self.backend.get(id_a)
        b = self.backend.get(id_b)
        if a is None or b is None:
            return None
        a_terms = set(tokenize(a.content))
        b_terms = set(tokenize(b.content))
        common_terms = sorted(a_terms & b_terms)
        overlap = (
            len(common_terms) / max(1, min(len(a_terms), len(b_terms)))
            if a_terms and b_terms
            else 0.0
        )
        shared_cues = sorted(set(a.cues) & set(b.cues))
        if overlap >= 0.6:
            verdict = "duplicate"
        elif shared_cues and a.content != b.content:
            verdict = "conflict"
        else:
            verdict = "distinct"
        return {
            "a": {
                "id": a.id,
                "preview": a.content[:40],
                "kind": a.kind.value,
                "importance": round(a.importance, 3),
                "confidence": round(a.confidence, 3),
                "evidence_count": a.evidence_count,
                "created_at": a.created_at.isoformat(),
            },
            "b": {
                "id": b.id,
                "preview": b.content[:40],
                "kind": b.kind.value,
                "importance": round(b.importance, 3),
                "confidence": round(b.confidence, 3),
                "evidence_count": b.evidence_count,
                "created_at": b.created_at.isoformat(),
            },
            "overlap": round(overlap, 3),
            "common_terms": common_terms[:5],
            "shared_cues": shared_cues[:5],
            "verdict": verdict,
        }

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
        for record in self._intents.values():
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

    def summarize_cluster(
        self,
        memory_ids: list[str],
    ) -> dict | None:
        """Summarize a cluster of related memories as one gist.

        Fuzzy-trace theory (Brainerd & Reyna, 1990): people keep the gist
        of repeated related experiences rather than every verbatim
        detail. This extracts shared cues, frequent terms and evidence
        counts into a compact summary an agent can use (or write back).
        """

        items = []
        for memory_id in memory_ids:
            item = self.backend.get(memory_id)
            if item is not None:
                items.append(item)
        if not items:
            return None
        cue_sets = [set(item.cues) for item in items]
        common_cues = sorted(set.intersection(*cue_sets)) if cue_sets else []
        term_counter: Counter = Counter()
        for item in items:
            for term in tokenize(item.content):
                term_counter[term] += 1
        top_terms = [
            term for term, _count in term_counter.most_common(6)
        ]
        total_chars = sum(len(item.content) for item in items)
        evidence = sum(item.evidence_count for item in items)
        previews = [item.content[:24] for item in items[:4]]
        summary = (
            f"共 {len(items)} 条记忆，共享线索："
            + ("、".join(common_cues) if common_cues else "无")
            + f"；高频词：{'、'.join(top_terms) if top_terms else '无'}；"
            + f"累计证据 {evidence} 次"
        )
        return {
            "memory_ids": [item.id for item in items],
            "summary": summary,
            "common_cues": common_cues,
            "top_terms": top_terms,
            "evidence_count": evidence,
            "total_chars": total_chars,
            "previews": previews,
        }

    def multi_hop_report(
        self,
        start_id: str,
        depth: int = 2,
        limit: int = 20,
    ) -> dict | None:
        """Walk the association network hop by hop from a start memory.

        Spreading activation (Collins & Loftus, 1975): related memories
        become reachable through their links, hop by hop. This BFS report
        shows which memories appear at each distance, so agents can gather
        multi-hop evidence for reasoning.
        """

        if self.backend.get(start_id) is None:
            return None
        adj: dict[str, set[str]] = defaultdict(set)
        for src, dst, _weight in self.backend.all_links():
            adj[src].add(dst)
            adj[dst].add(src)
        frontier = {start_id}
        seen = {start_id}
        hops = []
        for hop in range(1, max(1, int(depth)) + 1):
            next_frontier: set[str] = set()
            for node in frontier:
                next_frontier |= adj.get(node, set())
            next_frontier -= seen
            if not next_frontier:
                break
            seen |= next_frontier
            hops.append(
                {
                    "hop": hop,
                    "memory_ids": sorted(next_frontier)[: max(1, int(limit))],
                    "count": len(next_frontier),
                }
            )
            frontier = next_frontier
        return {
            "start_id": start_id,
            "depth": max(1, int(depth)),
            "hops": hops,
            "total_reached": len(seen) - 1,
            "reached_ids": sorted(seen - {start_id})[: max(1, int(limit))],
        }

    def cramming_plan(
        self,
        target_at: datetime,
        hours_available: float = 6.0,
        session_minutes: int = 30,
        limit: int = 20,
    ) -> dict:
        """Plan a last-minute review schedule before a deadline.

        Even with little time, spacing beats massing (Cepeda et al.,
        2006): the available hours are split into short sessions and the
        most at-risk important memories are reviewed first.
        """

        scored = []
        for item in self.store.all_active():
            need = item.importance * (
                1.0 - self.curve.retrievability(item, target_at)
            )
            scored.append((need, item))
        scored.sort(key=lambda pair: -pair[0])
        picked = scored[: max(1, int(limit))]
        n_sessions = max(
            1,
            int(float(hours_available) * 60 // max(1, int(session_minutes))),
        )
        per_session = len(picked) // n_sessions
        extra = len(picked) % n_sessions
        sessions = []
        for i in range(n_sessions):
            start = i * per_session + min(i, extra)
            size = per_session + (1 if i < extra else 0)
            chunk = picked[start:start + size]
            if not chunk:
                break
            start = target_at - timedelta(
                minutes=max(1, int(session_minutes)) * (n_sessions - i)
            )
            sessions.append(
                {
                    "start_at": start.isoformat(),
                    "duration_minutes": max(1, int(session_minutes)),
                    "memory_ids": [item.id for _need, item in chunk],
                    "count": len(chunk),
                }
            )
        return {
            "target_at": target_at.isoformat(),
            "hours_available": round(float(hours_available), 2),
            "sessions": sessions,
            "total_memories": len(picked),
        }

    def session_summary(
        self,
        memory_ids: list[str],
        compare_limit: int = 20,
    ) -> dict | None:
        """Summarize one work session's memories into facts/events/issues.

        Post-session consolidation integrates new traces into knowledge:
        this splits the memories into semantic facts and episodic events,
        then flags conflict and duplicate pairs so the agent can resolve
        them before moving on.
        """

        items = []
        for memory_id in memory_ids:
            item = self.backend.get(memory_id)
            if item is not None:
                items.append(item)
        if not items:
            return None
        facts = [
            {"id": item.id, "preview": item.content[:40]}
            for item in items if item.kind is MemoryKind.SEMANTIC
        ]
        events = [
            {"id": item.id, "preview": item.content[:40]}
            for item in items if item.kind is MemoryKind.EPISODIC
        ]
        conflicts = []
        duplicates = []
        compare_items = items[: max(2, int(compare_limit))]
        for a, b in combinations(compare_items, 2):
            verdict = self.compare_memories(a.id, b.id)["verdict"]
            if verdict == "conflict" and len(conflicts) < 5:
                conflicts.append(
                    {"id_a": a.id, "id_b": b.id,
                     "a_preview": a.content[:24],
                     "b_preview": b.content[:24]}
                )
            elif verdict == "duplicate" and len(duplicates) < 5:
                duplicates.append(
                    {"id_a": a.id, "id_b": b.id,
                     "a_preview": a.content[:24],
                     "b_preview": b.content[:24]}
                )
        summary = (
            f"共 {len(items)} 条记忆：事实 {len(facts)} 条、"
            f"事件 {len(events)} 条、冲突 {len(conflicts)} 对、"
            f"重复 {len(duplicates)} 对"
        )
        return {
            "total": len(items),
            "facts": facts,
            "events": events,
            "conflicts": conflicts,
            "duplicates": duplicates,
            "summary": summary,
        }

    def topic_drift_report(
        self,
        period_days: int = 30,
        limit: int = 20,
    ) -> dict:
        """Compare topic distribution between the two most recent periods.

        Schemas are reconstructed and shift over time (Bartlett, 1932):
        this compares the newest time bucket against the previous one and
        reports which themes grew, shrank, appeared or disappeared.
        """
        story = self.life_story(
            period_days=max(1, int(period_days)),
            limit=max(2, int(limit)),
        )
        periods = story["periods"]
        if len(periods) < 2:
            return {
                "periods": [p["period_start"] for p in periods],
                "topics": [],
                "total_drift": 0,
            }
        old, new = periods[-2], periods[-1]
        old_counts = {t["cue"]: t["count"] for t in old["top_themes"]}
        new_counts = {t["cue"]: t["count"] for t in new["top_themes"]}
        all_topics = sorted(set(old_counts) | set(new_counts))
        topics = []
        for topic in all_topics:
            old_count = old_counts.get(topic, 0)
            new_count = new_counts.get(topic, 0)
            delta = new_count - old_count
            if old_count == 0:
                status = "new"
            elif new_count == 0:
                status = "gone"
            elif delta > 0:
                status = "grew"
            elif delta < 0:
                status = "shrank"
            else:
                status = "same"
            topics.append(
                {
                    "topic": topic,
                    "old_count": old_count,
                    "new_count": new_count,
                    "delta": delta,
                    "status": status,
                }
            )
        total_drift = sum(
            1 for t in topics if t["status"] not in ("same",)
        )
        return {
            "periods": [old["period_start"], new["period_start"]],
            "topics": topics,
            "total_drift": total_drift,
        }

    def forgetting_export(
        self,
        memory_id: str,
        days: int = 30,
        step_days: int = 1,
    ) -> dict | None:
        """Export a memory's predicted forgetting curve.

        The forgetting curve (Ebbinghaus, 1885) predicts retrievability
        over time; this returns the forecast at regular intervals so
        agents or dashboards can plot it.
        """

        item = self.backend.get(memory_id)
        if item is None:
            return None
        now = utcnow()
        points = []
        for offset in range(
            0,
            max(1, int(days)) + 1,
            max(1, int(step_days)),
        ):
            points.append(
                {
                    "days_from_now": offset,
                    "retrievability": round(
                        self.curve.retrievability(
                            item, now + timedelta(days=offset)
                        ),
                        3,
                    ),
                }
            )
        return {
            "memory_id": memory_id,
            "content": item.content[:40],
            "initial": points[0]["retrievability"],
            "final": points[-1]["retrievability"],
            "points": points,
        }

    def coverage_report(
        self,
        now: datetime | None = None,
        limit: int = 20,
    ) -> dict:
        """Report review coverage per topic schema.

        Spaced-review systems need coverage monitoring: a topic with many
        never-reviewed memories is a blind spot. This reports, per topic,
        memory count, reviewed count, coverage ratio, average
        retrievability/importance and a status.
        """
        schema = self.schema_report(limit=max(1, int(limit)))
        topics = []
        for group in schema["top_groups"]:
            topic = group["topic"]
            members = [
                item
                for item in self.store.all_active()
                if item.cues and item.cues[0] == topic
            ]
            reviewed = [
                item for item in members
                if item.retrieval_successes + item.retrieval_failures > 0
            ]
            count = len(members)
            coverage = round(len(reviewed) / count, 3) if count else 1.0
            if coverage == 0:
                status = "unreviewed"
            elif coverage < 0.5:
                status = "partial"
            else:
                status = "good"
            topics.append(
                {
                    "topic": topic,
                    "memory_count": count,
                    "reviewed_count": len(reviewed),
                    "coverage": coverage,
                    "avg_retrievability": round(
                        sum(
                            self.curve.retrievability(item, now)
                            for item in members
                        ) / max(1, count),
                        3,
                    ),
                    "avg_importance": group["avg_importance"],
                    "status": status,
                }
            )
        return {
            "topics": topics,
            "total_topics": len(topics),
        }

    def source_calibration(self) -> dict:
        """Score the trustworthiness of each memory source.

        Source monitoring (Johnson, Hashtroudi & Lindsay, 1993): agents
        should know which origins are reliable. This groups memories by
        source origin and scores each source from its average confidence,
        evidence and importance.
        """

        groups: dict[str, list] = defaultdict(list)
        for item in self.store.all_active():
            groups[item.source.origin.value].append(item)
        sources = []
        for origin, members in sorted(groups.items()):
            count = len(members)
            avg_confidence = (
                sum(item.confidence for item in members) / count
            )
            avg_evidence = (
                sum(item.evidence_count for item in members) / count
            )
            avg_importance = (
                sum(item.importance for item in members) / count
            )
            avg_trust = sum(item.source.trust for item in members) / count
            trust_score = round(
                0.4 * avg_confidence
                + 0.3 * min(1.0, avg_evidence / 3.0)
                + 0.2 * avg_importance
                + 0.1 * avg_trust,
                3,
            )
            sources.append(
                {
                    "origin": origin,
                    "memory_count": count,
                    "avg_confidence": round(avg_confidence, 3),
                    "avg_evidence": round(avg_evidence, 3),
                    "avg_importance": round(avg_importance, 3),
                    "avg_source_trust": round(avg_trust, 3),
                    "trust_score": trust_score,
                }
            )
        sources.sort(key=lambda s: -s["trust_score"])
        return {
            "sources": sources,
            "total_memories": sum(s["memory_count"] for s in sources),
        }

    def forgetting_risk(
        self,
        now: datetime | None = None,
        limit: int = 20,
    ) -> dict:
        """Rank memories by forgetting risk.

        The riskiest memories are the most important ones closest to
        being forgotten (importance x forgetting); agents should review
        those first.
        """
        scored = []
        for item in self.store.all_active():
            retrievability = self.curve.retrievability(item, now)
            risk = item.importance * (1.0 - retrievability)
            scored.append(
                {
                    "id": item.id,
                    "preview": item.content[:40],
                    "importance": round(item.importance, 3),
                    "retrievability": round(retrievability, 3),
                    "risk": round(risk, 3),
                }
            )
        scored.sort(key=lambda entry: (-entry["risk"], entry["id"]))
        riskiest = scored[: max(1, int(limit))]
        return {
            "total": len(scored),
            "avg_risk": round(
                sum(entry["risk"] for entry in scored) / max(1, len(scored)),
                3,
            ),
            "riskiest": riskiest,
        }

    def bridge_suggestions(
        self,
        limit: int = 20,
    ) -> dict:
        """Suggest missing links between memories sharing cues.

        Spreading activation works through links (Collins & Loftus, 1975):
        memories that share a cue but have no link are a gap in the
        network. This lists those pairs so the agent can add bridges.
        """

        items = self.store.all_active()
        existing: set[frozenset[str]] = set()
        for src, dst, _weight in self.backend.all_links():
            existing.add(frozenset((src, dst)))
        suggestions = []
        compare_items = items[: max(2, int(limit) * 3)]
        for a, b in combinations(compare_items, 2):
            if len(suggestions) >= max(1, int(limit)):
                break
            shared = sorted(set(a.cues) & set(b.cues))
            if not shared:
                continue
            if frozenset((a.id, b.id)) in existing:
                continue
            suggestions.append(
                {
                    "id_a": a.id,
                    "id_b": b.id,
                    "a_preview": a.content[:24],
                    "b_preview": b.content[:24],
                    "shared_cues": shared[:4],
                }
            )
        return {
            "total": len(suggestions),
            "suggestions": suggestions,
        }

    _PLAN_VERBS = (
        "做", "写", "创建", "设计", "开发", "测试", "部署", "分析",
        "调研", "优化", "修复", "完成", "检查", "收集", "整理", "实现",
        "重构", "发布", "验证", "运行", "配置", "安装", "更新", "规划",
        "评估", "阅读", "发送", "记录", "确认", "制定", "拆分",
    )

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

    _PLAN_STATUSES = ("pending", "in_progress", "done", "blocked")

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
        communities = []
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

    def sleep_advice(self, now: datetime | None = None) -> dict:
        """Advise what to review before sleep for better consolidation.

        Sleep consolidates memories, and pre-sleep rehearsal of important
        material strengthens it (Rasch & Born, 2013). This tool collects
        weak-but-important memories to review before sleep, plus conflicts,
        overdue intentions and tomorrow's unreviewed topics.
        """
        items = self.store.all_active()
        weak_important = [
            item for item in items
            if item.importance >= 0.6
            and self.curve.retrievability(item, now) < 0.5
        ]
        weak_important.sort(key=lambda item: -item.importance)
        pre_sleep_review = [
            {
                "id": item.id,
                "preview": item.content[:40],
                "importance": round(item.importance, 3),
                "retrievability": round(
                    self.curve.retrievability(item, now), 3
                ),
            }
            for item in weak_important[:5]
        ]
        conflicts = len(self.consolidator.detect_conflicts())
        queue = self.action_queue(now=now)
        coverage = self.coverage_report(now=now)
        tomorrow_priorities = [
            {
                "topic": topic["topic"],
                "memory_count": topic["memory_count"],
                "coverage": topic["coverage"],
            }
            for topic in coverage["topics"]
            if topic["status"] == "unreviewed"
        ][:3]
        advice = (
            "睡前先过一遍“重要但快忘”的记忆，"
            "冲突留到明天集中处理，过期待办尽快收尾"
        )
        return {
            "pre_sleep_review": pre_sleep_review,
            "conflicts_to_resolve": conflicts,
            "overdue_intents": queue["overdue"],
            "tomorrow_priorities": tomorrow_priorities,
            "advice": advice,
        }

    def emotion_advice(
        self,
        memory_ids: list[str] | None = None,
    ) -> dict:
        """Profile emotional tone of memories and advise regulation.

        Emotion regulation (Gross, 2002) starts with awareness of the
        emotional load: this tool counts positive/negative/neutral/
        arousing traces, reports the negative ratio and suggests
        reappraisal or spacing when negativity is high.
        """

        if memory_ids:
            items = []
            for memory_id in memory_ids:
                item = self.backend.get(memory_id)
                if item is not None:
                    items.append(item)
        else:
            items = self.store.all_active()
        counts = Counter(
            item.affect or "neutral" for item in items
        )
        total = len(items)
        negative = counts["negative"]
        negative_ratio = round(negative / max(1, total), 3)
        flagged_topics = []
        topic_negative: dict[str, int] = {}
        for item in items:
            if item.affect == "negative" and item.cues:
                topic = item.cues[0]
                topic_negative[topic] = topic_negative.get(topic, 0) + 1
        for topic, count in sorted(
            topic_negative.items(), key=lambda kv: -kv[1]
        )[:3]:
            flagged_topics.append({"topic": topic, "negative_count": count})
        if negative_ratio >= 0.4:
            advice = (
                "消极记忆占比偏高：先重评一次（换个角度看待），"
                "重要的单独处理，避免整体情绪被带偏"
            )
        elif negative_ratio >= 0.2:
            advice = (
                "消极记忆有一定占比：建议逐条重评，"
                "把“当时很糟”改写为“当时学到什么”"
            )
        else:
            advice = "情绪分布较均衡，保持现状即可"
        return {
            "total_memories": total,
            "mood_profile": {
                "positive": counts["positive"],
                "negative": counts["negative"],
                "neutral": counts["neutral"],
                "arousing": counts["arousing"],
                "mixed": counts["mixed"],
            },
            "negative_ratio": negative_ratio,
            "flagged_topics": flagged_topics,
            "advice": advice,
        }

    def difficulty_estimator(
        self,
        limit: int = 10,
        now: datetime | None = None,
    ) -> dict:
        """Estimate current learning difficulty of each memory.

        Desirable difficulties (Bjork, 1994): learning benefits most when
        retrieval is effortful but still possible. This tool buckets every
        active memory by current retrievability into too-easy / sweet-spot /
        hard / very-hard, highlights the sweet-spot workload and gives
        concrete next actions per bucket.
        """
        items = self.store.all_active()
        buckets = {"too_easy": 0, "sweet_spot": 0, "hard": 0, "very_hard": 0}
        rows: list[dict] = []
        for item in items:
            r = self.curve.retrievability(item, now)
            if r >= 0.75:
                level = "too_easy"
            elif r >= 0.35:
                level = "sweet_spot"
            elif r >= 0.12:
                level = "hard"
            else:
                level = "very_hard"
            buckets[level] += 1
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:36],
                    "topic": item.cues[0] if item.cues else item.content[:10],
                    "level": level,
                    "retrievability": round(r, 3),
                    "importance": round(item.importance, 3),
                    "reviews": item.review_streak,
                }
            )
        rows.sort(key=lambda row: (-row["importance"], row["retrievability"]))
        total = len(items)
        sweet_ratio = round(buckets["sweet_spot"] / max(1, total), 3)
        topic_rows: list[dict] = []
        topic_buckets: dict[str, dict] = {}
        for row in rows:
            entry = topic_buckets.setdefault(
                row["topic"],
                {
                    "topic": row["topic"],
                    "count": 0,
                    "sweet_spot": 0,
                    "hard": 0,
                    "very_hard": 0,
                },
            )
            entry["count"] += 1
            if row["level"] == "sweet_spot":
                entry["sweet_spot"] += 1
            elif row["level"] == "hard":
                entry["hard"] += 1
            elif row["level"] == "very_hard":
                entry["very_hard"] += 1
        for entry in topic_buckets.values():
            if entry["count"] >= 2:
                topic_rows.append(entry)
        topic_rows.sort(
            key=lambda entry: (-entry["very_hard"], -entry["hard"], -entry["count"])
        )
        if buckets["very_hard"] and sweet_ratio < 0.3:
            advice = (
                "太难的太多：先给小步重编码（加线索、拆成更小的点），"
                "把 very_hard 拉回 hard 再进 sweet_spot，不要直接硬背。"
            )
        elif buckets["too_easy"] and sweet_ratio < 0.3:
            advice = (
                "太容易的太多：容易的推迟复习（间隔），等它掉进"
                " sweet_spot 再练，避免假熟练。"
            )
        elif sweet_ratio >= 0.3:
            advice = (
                "难度分布良好：重点保持 sweet_spot 节奏，"
                "太难的拆解、太容易的延后。"
            )
        else:
            advice = "按 importance 优先：sweet_spot 先练，hard 拆解，very_hard 重编码。"
        return {
            "total_memories": total,
            "buckets": buckets,
            "sweet_spot_ratio": sweet_ratio,
            "rows": rows[: max(1, int(limit))],
            "topic_summary": topic_rows[:5],
            "advice": advice,
        }

    def memory_integration(
        self,
        limit: int = 10,
        now: datetime | None = None,
    ) -> dict:
        """Suggest how related memories can be integrated or composed.

        Compositional inference in the hippocampal-prefrontal circuit
        (Schwartenbeck et al., 2023; Spens & Burgess, 2024): related
        traces replayed together form higher-level schemas; nearby
        episodes form event chains; unresolved contradictions block
        clean integration.
        """

        items = self.store.all_active()
        topic_groups: dict[str, list] = defaultdict(list)
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            topic_groups[topic].append(item)
        member_links: set[frozenset[str]] = set()
        for src, dst, _weight in self.backend.all_links():
            member_links.add(frozenset({src, dst}))

        schema_candidates: list[dict] = []
        event_chains: list[dict] = []
        for topic, members in topic_groups.items():
            member_ids = {member.id for member in members}
            linked_pairs = sum(
                1
                for pair in member_links
                if pair <= member_ids and len(pair) == 2
            )
            if len(members) >= 2:
                avg_importance = round(
                    sum(member.importance for member in members)
                    / len(members),
                    3,
                )
                schema_candidates.append(
                    {
                        "topic": topic,
                        "count": len(members),
                        "avg_importance": avg_importance,
                        "linked_pairs": linked_pairs,
                        "suggestion": (
                            "把同主题记忆重放并整合成一条总结记忆"
                            "（组合推理），减少碎片化"
                        ),
                    }
                )
            episodes = [
                member
                for member in members
                if member.kind == MemoryKind.EPISODIC
                and member.source.occurred_at is not None
            ]
            episodes.sort(key=lambda member: member.source.occurred_at)  # type: ignore[arg-type]
            chain = episodes
            if len(chain) >= 2:
                span_days = round(
                    (
                        chain[-1].source.occurred_at
                        - chain[0].source.occurred_at
                    ).total_seconds()
                    / 86400.0,
                    1,
                )
                if span_days <= 14:
                    event_chains.append(
                        {
                            "topic": topic,
                            "events": len(chain),
                            "span_days": span_days,
                            "suggestion": (
                                "把这段时间内的事件串成一条事件链，"
                                "回忆时按顺序重放"
                            ),
                        }
                    )
        schema_candidates.sort(
            key=lambda candidate: (
                -candidate["count"],
                -candidate["avg_importance"],
            )
        )
        event_chains.sort(key=lambda chain: -chain["events"])
        conflicts = self.consolidator.detect_conflicts()
        if conflicts:
            advice = (
                "先解决冲突再整合：同主题记忆互相矛盾时，"
                "先裁定哪条更可信，再合成总结。"
            )
        elif schema_candidates:
            advice = (
                "整合时机已到：同主题记忆可以重放整合成高层图式，"
                "近段事件可以串成事件链。"
            )
        else:
            advice = "当前记忆较分散，暂无整合候选；持续记录后会自动出现。"
        return {
            "total_memories": len(items),
            "schema_candidates": schema_candidates[: max(1, int(limit))],
            "event_chains": event_chains[: max(1, int(limit))],
            "conflicts": len(conflicts),
            "advice": advice,
        }

    def reasoning_trace(
        self,
        problem: str,
        *,
        topic: str | None = None,
        top_k: int = 4,
        store_conclusion: bool = True,
        now: datetime | None = None,
    ) -> dict:
        """Build a replay-friendly reasoning trace from stored memories.

        Mathematical reasoning relies on working memory + prefrontal
        control over quantity representations (Menon, 2016; Dehaene),
        and complex problem solving cycles through goal states that are
        replayed (Watanabe et al., 2023; Jensen et al., 2024). This tool
        recalls premise memories relevant to the problem, extracts the
        quantities, builds a step trace with per-step evidence, and can
        store the derived conclusion as an inference memory so the next
        reasoning round starts from a richer base.
        """

        topic = topic or (self.store.all_active()[0].cues[0] if self.store.all_active() else problem[:12])
        results = self.recall(problem, top_k=max(1, int(top_k)), now=now)
        evidence = [
            {
                "id": result.item.id,
                "preview": result.item.content[:48],
                "confidence": round(result.item.confidence, 3),
                "score": round(result.score, 3),
            }
            for result in results
            if result.score >= 0.05
        ]
        numbers: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for text in [problem] + [item["preview"] for item in evidence]:
            for raw in re.findall(r"-?\d+(?:\.\d+)?", text):
                key = (raw, text[:20])
                if key in seen:
                    continue
                seen.add(key)
                numbers.append(
                    {
                        "value": float(raw),
                        "raw": raw,
                        "where": "problem" if text == problem else "memory",
                    }
                )
        steps = [
            {
                "order": 1,
                "step": "读题：列出已知条件",
                "evidence_ids": [item["id"] for item in evidence],
                "verdict": "ok" if evidence else "weak",
            },
            {
                "order": 2,
                "step": "从记忆中核对已知量",
                "evidence_ids": [item["id"] for item in evidence[:2]],
                "verdict": "ok" if len(numbers) >= 2 else "weak",
            },
            {
                "order": 3,
                "step": "按数量关系计算",
                "evidence_ids": [item["id"] for item in evidence[:1]],
                "verdict": "ok" if numbers else "weak",
            },
            {
                "order": 4,
                "step": "得出结论并准备固化",
                "evidence_ids": [],
                "verdict": "ok",
            },
        ]
        stored_id = None
        if store_conclusion and evidence:
            conclusion = (
                f"推理结论：{problem}（依据 {len(evidence)} 条记忆，"
                f"提取 {len(numbers)} 个数量）"
            )
            item = self.remember(
                conclusion,
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.INFERENCE),
                cues=[topic],
                importance=0.6,
                confidence=0.7,
                evidence_count=len(evidence),
                auto_cues=False,
            )
            stored_id = item.id
        return {
            "problem": problem,
            "topic": topic,
            "evidence_used": evidence[: max(1, int(top_k))],
            "numbers": numbers,
            "steps": steps,
            "verdict": "consistent" if evidence else "review_needed",
            "stored_memory_id": stored_id,
            "advice": (
                "推理链已按记忆证据逐步展开；结论已存入记忆库，"
                "下次同类问题可直接引用。"
                if stored_id
                else "证据不足：先补充相关记忆，再重新推理。"
            ),
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

    def sleep_inference(
        self,
        *,
        limit: int = 5,
        now: datetime | None = None,
    ) -> dict:
        """Find memory pairs that sleep can weave into new inferences.

        NREM/REM sleep coordinates the weaving of inferential knowledge:
        the brain replays learned pairs offline and the prefrontal cortex
        codes the inferred outcome (Abdou, Nomoto et al., Nature
        Communications, 2024). This tool finds same-topic memory pairs
        that are consolidated enough to support a new inference, ranks
        them by readiness, and tells the agent what to "let sleep
        integrate" next.
        """

        items = self.store.all_active()
        topic_groups: dict[str, list] = defaultdict(list)
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            topic_groups[topic].append(item)
        candidates: list[dict] = []
        for topic, members in topic_groups.items():
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    a, b = members[i], members[j]
                    if a.content_hash == b.content_hash:
                        continue
                    shared_cues = len(set(a.cues) & set(b.cues))
                    ra = self.curve.retrievability(a, now)
                    rb = self.curve.retrievability(b, now)
                    need_consolidation = int(
                        min(ra, rb) < 0.6
                        and min(a.importance, b.importance) >= 0.4
                    )
                    readiness = round(
                        min(1.0, 0.5 * min(1.0, shared_cues)
                            + 0.5 * need_consolidation),
                        3,
                    )
                    candidates.append(
                        {
                            "topic": topic,
                            "a_preview": a.content[:36],
                            "b_preview": b.content[:36],
                            "shared_cues": shared_cues,
                            "retrievability_a": round(ra, 3),
                            "retrievability_b": round(rb, 3),
                            "readiness": readiness,
                            "reason": (
                                "同一主题、遗忘到需要巩固的程度，"
                                "睡眠重放后可组合出新推断"
                            ),
                        }
                    )
        candidates.sort(key=lambda candidate: -candidate["readiness"])
        ready = [candidate for candidate in candidates if candidate["readiness"] >= 0.5]
        return {
            "total_pairs": len(candidates),
            "ready_pairs": len(ready),
            "candidates": candidates[: max(1, int(limit))],
            "advice": (
                "睡眠整合窗口：已找到可组合的推断对，"
                "睡前复习一遍、睡后再查一次，把新推断补进记忆库。"
                if ready
                else "暂无可组合推断对：继续积累同主题记忆，睡眠后再看。"
            ),
        }

    def schema_fit(
        self,
        *,
        limit: int = 20,
    ) -> dict:
        """Measure how new memories fit existing schemas.

        Schemas speed up consolidation: memories congruent with an
        existing schema integrate rapidly in the neocortex (Tse et al.,
        Science, 2007), and reconstruction follows assimilation or
        accommodation (Bartlett, 1932). This tool scores each memory's
        fit to the best-matching schema (topic group) and labels it
        assimilate / borderline / accommodate.
        """


        items = self.store.all_active()
        groups: dict[str, list] = defaultdict(list)
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            groups[topic].append(item)
        schemas = {
            topic: members
            for topic, members in groups.items()
            if len(members) >= 2
        }
        rows: list[dict] = []
        for item in items:
            best_topic = None
            best_fit = 0.0
            item_cues = set(item.cues)
            item_terms = set(tokenize(item.content))
            for topic, members in schemas.items():
                if any(member.id == item.id for member in members):
                    members = [member for member in members if member.id != item.id]
                    if not members:
                        continue
                cue_union: set[str] = set()
                term_union: set[str] = set()
                for member in members:
                    cue_union.update(member.cues)
                    term_union.update(tokenize(member.content))
                cue_overlap = (
                    len(item_cues & cue_union) / max(1, len(item_cues | cue_union))
                    if (item_cues or cue_union)
                    else 0.0
                )
                term_overlap = (
                    len(item_terms & term_union) / max(1, len(item_terms | term_union))
                    if (item_terms or term_union)
                    else 0.0
                )
                fit = min(1.0, 0.6 * cue_overlap + 0.4 * term_overlap)
                if fit > best_fit:
                    best_fit = fit
                    best_topic = topic
            verdict = (
                "assimilate"
                if best_fit >= 0.5
                else "borderline"
                if best_fit >= 0.3
                else "accommodate"
            )
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:36],
                    "topic": item.cues[0] if item.cues else item.content[:10],
                    "best_schema": best_topic,
                    "fit": round(best_fit, 3),
                    "verdict": verdict,
                }
            )
        counts = defaultdict(int)
        for row in rows:
            counts[row["verdict"]] += 1
        schema_summary = []
        for topic, members in schemas.items():
            schema_rows = [row for row in rows if row["topic"] == topic]
            avg_fit = round(
                sum(row["fit"] for row in schema_rows) / max(1, len(schema_rows)),
                3,
            )
            schema_summary.append(
                {
                    "topic": topic,
                    "member_count": len(members),
                    "avg_fit": avg_fit,
                    "assimilate": sum(
                        1 for row in schema_rows if row["verdict"] == "assimilate"
                    ),
                    "accommodate": sum(
                        1 for row in schema_rows if row["verdict"] == "accommodate"
                    ),
                }
            )
        schema_summary.sort(key=lambda s: -s["member_count"])
        if counts["accommodate"] > counts["assimilate"]:
            advice = "新知识不成体系：多数记忆找不到合适图式，建议先建新图式再积累。"
        elif counts["assimilate"] >= max(1, counts["accommodate"]):
            advice = "记忆正顺利并入现有图式：与图式一致的记忆巩固更快（Tse 2007）。"
        else:
            advice = "有图式可并入，也有新图式在形成，按主题分别维护即可。"
        return {
            "total_memories": len(items),
            "schema_count": len(schemas),
            "rows": rows[: max(1, int(limit))],
            "verdict_counts": dict(counts),
            "schema_summary": schema_summary,
            "advice": advice,
        }

    def test_generator(
        self,
        *,
        topic: str | None = None,
        memory_ids: list[str] | None = None,
        count: int = 4,
    ) -> dict:
        """Generate retrieval-practice questions without giving answers.

        Testing effect (Roediger & Karpicke, 2006): taking a test on
        material beats re-reading it. This tool turns memories into
        cue-prompt and cloze questions (answers hidden) so the agent can
        self-quiz and then score with practice_answer.
        """
        if memory_ids:
            items = []
            for memory_id in memory_ids:
                item = self.backend.get(memory_id)
                if item is not None:
                    items.append(item)
        elif topic:
            items = [
                item
                for item in self.store.all_active()
                if topic in item.cues or topic in item.content
            ]
        else:
            items = self.store.all_active()
        items = items[: max(1, int(count))]
        questions: list[dict] = []
        for index, item in enumerate(items):
            content = item.content
            cue = item.cues[0] if item.cues else content[:10]
            if index % 2 == 0:
                question = (
                    f"【测试】提示词“{cue}”：请回忆这条记忆讲了什么。"
                )
                qtype = "cue_prompt"
            else:
                blank = "____"
                if len(content) > 8:
                    blank_len = min(4, max(2, len(content) // 3))
                    blank = "____" * max(1, blank_len // 4)
                    question = content[:-blank_len] + blank
                else:
                    question = f"【测试】请补全：{blank}（提示：{cue}）"
                qtype = "cloze"
            questions.append(
                {
                    "memory_id": item.id,
                    "question": question,
                    "qtype": qtype,
                    "hint_cues": item.cues[:3],
                    "answer_hidden": True,
                }
            )
        return {
            "topic": topic,
            "question_count": len(questions),
            "questions": questions,
            "advice": (
                "先自测再对答案：测试比重读记得牢（Roediger & Karpicke 2006）；"
                "答完用 practice_answer 打分并强化。"
            ),
        }

    def spacing_plan(
        self,
        *,
        days: int = 7,
        limit: int = 20,
        now: datetime | None = None,
    ) -> dict:
        """Build a spaced review schedule for the coming days.

        Distributed practice with longer gaps improves long-term
        retention (Cepeda et al., 2006). Memories close to fading are
        scheduled early; stronger ones wait; topics are interleaved so
        consecutive items in the same session differ.
        """
        days = max(1, int(days))
        items = self.store.all_active()
        items.sort(key=lambda item: -item.importance)
        items = items[: max(1, int(limit))]
        rows: list[dict] = []
        for item in items:
            r = self.curve.retrievability(item, now)
            review_day = min(
                days - 1,
                max(0, int(round(r * (days - 1)))),
            )
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:32],
                    "topic": item.cues[0] if item.cues else item.content[:10],
                    "importance": round(item.importance, 3),
                    "retrievability": round(r, 3),
                    "review_day": review_day,
                }
            )
        buckets: dict[int, list[dict]] = {day: [] for day in range(days)}
        for row in rows:
            buckets[row["review_day"]].append(row)
        daily_plan: list[dict] = []
        for day in range(days):
            bucket = buckets[day]
            bucket.sort(key=lambda row: -row["importance"])
            by_topic: dict[str, list[dict]] = {}
            for row in bucket:
                by_topic.setdefault(row["topic"], []).append(row)
            interleaved: list[dict] = []
            while by_topic:
                for topic in list(by_topic):
                    interleaved.append(by_topic[topic].pop(0))
                    if not by_topic[topic]:
                        del by_topic[topic]
            daily_plan.append(
                {
                    "day": day,
                    "items": [
                        {
                            "id": row["id"],
                            "preview": row["preview"],
                            "importance": row["importance"],
                            "retrievability": row["retrievability"],
                        }
                        for row in interleaved
                    ],
                }
            )
        return {
            "days": days,
            "total_scheduled": len(rows),
            "daily_plan": daily_plan,
            "advice": (
                "间隔复习：快忘的先复习，熟的后复习，同主题交错开"
                "（Cepeda et al. 2006）。"
            ),
        }

    def rumination_check(
        self,
        *,
        access_threshold: int = 5,
    ) -> dict:
        """Detect repeated retrieval of negative memories (rumination).

        Repetitive negative thinking is a transdiagnostic risk factor
        (Watkins, 2008; Ehring & Watkins, 2008), while reactivation makes
        a memory labile so it can be updated rather than merely replayed
        (Nader et al., 2000). This tool flags negative/arousing memories
        that are accessed far too often and suggests reappraisal +
        update instead of another replay.
        """

        threshold = max(1, int(access_threshold))
        items = self.store.all_active()
        risky: list[dict] = []
        negative_count = 0
        for item in items:
            if item.affect not in ("negative", "arousing"):
                continue
            negative_count += 1
            if item.access_count >= threshold:
                risky.append(
                    {
                        "id": item.id,
                        "preview": item.content[:36],
                        "affect": item.affect,
                        "access_count": item.access_count,
                        "topic": item.cues[0] if item.cues else item.content[:10],
                    }
                )
        topic_counts: defaultdict[str, int] = defaultdict(int)
        for item in risky:
            topic_counts[item["topic"]] += 1
        rumination_topics = [
            {"topic": topic, "risky_count": count}
            for topic, count in sorted(
                topic_counts.items(), key=lambda kv: -kv[1]
            )
        ]
        if len(risky) >= 3 or any(
            topic["risky_count"] >= 2 for topic in rumination_topics
        ):
            risk_level = "high"
        elif risky:
            risk_level = "medium"
        else:
            risk_level = "low"
        if risk_level == "high":
            advice = (
                "反刍风险高：同一件负性事件被反复调出。别再重复回放，"
                "先重评（换个角度），再借“提取后记忆可更新”的窗口"
                "改写结论（Nader 2000）。"
            )
        elif risk_level == "medium":
            advice = (
                "有反刍苗头：这条负性记忆被访问偏多。"
                "建议改为间隔复习 + 重评，而不是每次想起来就重放。"
            )
        else:
            advice = "情绪记忆访问正常：保持间隔复习即可。"
        return {
            "total_memories": len(items),
            "negative_count": negative_count,
            "risky_memories": risky,
            "rumination_topics": rumination_topics,
            "risk_level": risk_level,
            "advice": advice,
        }

    def consolidation_forecast(
        self,
        *,
        limit: int = 5,
        now: datetime | None = None,
    ) -> dict:
        """Predict which memories will benefit most from sleep.

        Sleep consolidates memory, and pre-sleep rehearsal of important
        material strengthens it (Rasch & Born, 2013). Emotional salience
        also boosts overnight consolidation (Cahill & McGaugh, 1998).
        This tool scores every memory's overnight-gain potential and
        returns tonight's review candidates with predicted gain.
        """
        items = self.store.all_active()
        rows: list[dict] = []
        for item in items:
            r = self.curve.retrievability(item, now)
            emotional = int(
                item.affect in ("positive", "negative", "arousing", "mixed")
            )
            weak_boost = 0.5 if r < 0.6 else 0.0
            score = round(
                min(
                    1.0,
                    0.4 * item.importance
                    + 0.3 * emotional
                    + 0.3 * weak_boost,
                ),
                3,
            )
            gain = round(max(0.0, 1.0 - r) * item.importance, 3)
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:36],
                    "importance": round(item.importance, 3),
                    "affect": item.affect or "neutral",
                    "retrievability": round(r, 3),
                    "consolidation_score": score,
                    "predicted_gain": gain,
                    "reason": (
                        "重要 + 情绪显著 + 需要巩固，睡眠收益最大"
                        if score >= 0.8
                        else "重要或情绪记忆，睡前过一遍可强化"
                        if score >= 0.5
                        else "巩固收益一般，按常规间隔复习即可"
                    ),
                }
            )
        rows.sort(
            key=lambda row: (
                -row["consolidation_score"],
                -row["predicted_gain"],
            )
        )
        top = rows[: max(1, int(limit))]
        return {
            "total_memories": len(items),
            "tonight_candidates": top,
            "predicted_gain_total": round(
                sum(row["predicted_gain"] for row in top), 3
            ),
            "advice": (
                "睡前把今晚候选快速过一遍，睡后巩固效果最好"
                "（Rasch & Born 2013）。"
                if top
                else "暂无高收益候选，保持常规复习即可。"
            ),
        }

    def forgetting_balance(
        self,
        *,
        imbalance_ratio: float = 3.0,
        limit: int = 10,
    ) -> dict:
        """Detect within-topic access imbalance (retrieval-induced forgetting).

        Retrieving one memory strengthens it and suppresses its
        competitors in the same category (Anderson, Bjork & Bjork, 1994).
        If one memory in a topic is retrieved far more often than its
        siblings, the siblings may be losing retrievability silently.
        """

        ratio = max(1.0, float(imbalance_ratio))
        items = self.store.all_active()
        topic_groups: defaultdict[str, list] = defaultdict(list)
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            topic_groups[topic].append(item)
        topics: list[dict] = []
        for topic, members in topic_groups.items():
            if len(members) < 2:
                continue
            total_access = sum(item.access_count for item in members)
            rows = []
            for item in members:
                rows.append(
                    {
                        "id": item.id,
                        "preview": item.content[:32],
                        "access_count": item.access_count,
                        "share": round(
                            item.access_count / max(1, total_access), 3
                        ),
                    }
                )
            rows.sort(key=lambda row: -row["access_count"])
            max_access = rows[0]["access_count"]
            min_access = rows[-1]["access_count"]
            imbalanced = bool(
                max_access >= ratio * max(1, min_access)
                and max_access >= 3
            )
            topics.append(
                {
                    "topic": topic,
                    "memories": rows,
                    "imbalanced": imbalanced,
                    "suggestion": (
                        "热门记忆被反复提取，兄弟记忆可能被压制："
                        "补练低频记忆，平衡提取（RIF，Anderson 1994）。"
                        if imbalanced
                        else "提取较均衡，无需调整。"
                    ),
                }
            )
        flagged = [topic for topic in topics if topic["imbalanced"]]
        if flagged:
            advice = (
                "发现提取失衡：同一主题里热门记忆反复被想起，"
                "低频记忆可能被偷偷压制，优先补练它们。"
            )
        else:
            advice = "各主题提取较均衡，无提取诱发遗忘风险。"
        return {
            "total_topics": len(topics),
            "flagged_count": len(flagged),
            "topics": topics[: max(1, int(limit))],
            "advice": advice,
        }

    def metacog_report(
        self,
        *,
        min_attempts: int = 3,
    ) -> dict:
        """Report confidence vs retrieval accuracy (calibration).

        Monitoring one's own knowledge (Koriat, 1997): good calibration
        means confidence matches accuracy. This tool aggregates retrieval
        attempts per topic, compares mean confidence with accuracy and
        flags overconfidence / underconfidence.
        """

        min_attempts = max(1, int(min_attempts))
        items = self.store.all_active()
        stats: defaultdict[str, dict] = defaultdict(
            lambda: {"attempts": 0, "successes": 0, "conf_sum": 0.0}
        )
        for item in items:
            attempts = item.retrieval_successes + item.retrieval_failures
            if attempts < min_attempts:
                continue
            topic = item.cues[0] if item.cues else item.content[:10]
            s = stats[topic]
            s["attempts"] += attempts
            s["successes"] += item.retrieval_successes
            s["conf_sum"] += item.confidence * attempts
        topics: list[dict] = []
        total_gap = 0.0
        for topic, s in stats.items():
            accuracy = round(s["successes"] / s["attempts"], 3)
            mean_confidence = round(s["conf_sum"] / s["attempts"], 3)
            gap = round(mean_confidence - accuracy, 3)
            total_gap += abs(gap)
            if gap >= 0.15:
                flag = "overconfident"
            elif gap <= -0.15:
                flag = "underconfident"
            else:
                flag = "well_calibrated"
            topics.append(
                {
                    "topic": topic,
                    "attempts": s["attempts"],
                    "accuracy": accuracy,
                    "mean_confidence": mean_confidence,
                    "gap": gap,
                    "flag": flag,
                }
            )
        topics.sort(key=lambda topic: -abs(topic["gap"]))
        mean_abs_gap = (
            round(total_gap / len(topics), 3) if topics else 0.0
        )
        calibration_score = round(
            max(0.0, min(1.0, 1.0 - mean_abs_gap)), 3
        )
        flagged = [topic for topic in topics if topic["flag"] != "well_calibrated"]
        if any(topic["flag"] == "overconfident" for topic in topics):
            advice = "存在过度自信主题：多练自测、用真实成绩校准置信度。"
        elif any(topic["flag"] == "underconfident" for topic in topics):
            advice = "存在自信不足主题：回忆成绩已不错，可适当上调置信度。"
        else:
            advice = "校准良好：置信度与真实回忆成绩基本一致。"
        return {
            "topics": topics,
            "mean_abs_gap": mean_abs_gap,
            "calibration_score": calibration_score,
            "flagged_count": len(flagged),
            "advice": advice,
        }

    def reconsolidation_plan(
        self,
        memory_id: str,
        *,
        now: datetime | None = None,
    ) -> dict:
        """Produce an update plan for a memory that needs revision.

        Reactivated memories become labile and can be updated, not just
        replayed (Nader et al., 2000); clinical reconsolidation updating
        follows retrieve -> prediction error -> update. This tool finds
        the target memory, gathers conflicting evidence and returns a
        concrete update plan.
        """
        item = self.backend.get(memory_id)
        if item is None:
            return {
                "found": False,
                "advice": "记忆不存在：先确认 memory_id 再生成更新计划。",
            }
        item_cues = set(item.cues)
        same_topic = [
            other
            for other in self.store.all_active()
            if other.id != item.id
            and item_cues
            and (set(other.cues) & item_cues)
        ]
        conflicts = []
        for other in same_topic:
            if other.content_hash == item.content_hash:
                continue
            if len(conflicts) >= 5:
                break
            conflicts.append(
                {
                    "id": other.id,
                    "preview": other.content[:36],
                    "confidence": round(other.confidence, 3),
                }
            )
        r = self.curve.retrievability(item, now)
        steps = [
            {
                "order": 1,
                "step": "提取：先调出这条记忆，打开可更新窗口",
                "verdict": "ok",
            },
            {
                "order": 2,
                "step": "找冲突/新证据",
                "evidence_count": len(conflicts),
                "verdict": "ok" if conflicts else "weak",
            },
            {
                "order": 3,
                "step": "更新：用 update() 改写内容/置信度，或存推理记忆",
                "verdict": "ok",
            },
            {
                "order": 4,
                "step": "再巩固：更新后拉开间隔复习，避免反复提取",
                "verdict": "ok",
            },
        ]
        return {
            "found": True,
            "memory": {
                "id": item.id,
                "preview": item.content[:40],
                "confidence": round(item.confidence, 3),
                "evidence_count": item.evidence_count,
                "revision_count": item.revision_count,
                "retrievability": round(r, 3),
            },
            "related_count": len(same_topic),
            "conflicts": conflicts,
            "steps": steps,
            "advice": (
                "有冲突待更新：先提取，再按新证据改写，"
                "更新后间隔复习（Nader 2000 再巩固流程）。"
                if conflicts
                else "暂无冲突：如需刷新内容，直接 update() 后间隔复习。"
            ),
        }

    def mastery_map(
        self,
        *,
        threshold: float = 0.5,
        min_attempts: int = 3,
        now: datetime | None = None,
    ) -> dict:
        """Estimate per-topic mastery and recommend the next topic to learn.

        Zone of proximal development (Vygotsky, 1978): learning is most
        efficient just beyond current mastery. Mastery blends retrieval
        accuracy, average retrievability and topic coverage; topics in
        the "developing" band are the next-step candidates.
        """

        min_attempts = max(1, int(min_attempts))
        items = self.store.all_active()
        stats: defaultdict[str, dict] = defaultdict(
            lambda: {
                "count": 0,
                "acc_sum": 0.0,
                "r_sum": 0.0,
            }
        )
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            s = stats[topic]
            s["count"] += 1
            attempts = item.retrieval_successes + item.retrieval_failures
            if attempts >= min_attempts:
                accuracy = item.retrieval_successes / attempts
            else:
                accuracy = item.confidence
            s["acc_sum"] += accuracy
            s["r_sum"] += self.curve.retrievability(item, now)
        topics: list[dict] = []
        for topic, s in stats.items():
            accuracy = s["acc_sum"] / s["count"]
            avg_r = s["r_sum"] / s["count"]
            coverage = min(1.0, s["count"] / 3.0)
            mastery = round(
                0.5 * accuracy + 0.3 * avg_r + 0.2 * coverage,
                3,
            )
            if mastery >= 0.7:
                flag = "mastered"
            elif mastery >= threshold:
                flag = "developing"
            else:
                flag = "new"
            topics.append(
                {
                    "topic": topic,
                    "memory_count": s["count"],
                    "accuracy": round(accuracy, 3),
                    "avg_retrievability": round(avg_r, 3),
                    "mastery": mastery,
                    "flag": flag,
                }
            )
        topics.sort(key=lambda topic: -topic["mastery"])
        developing = [
            topic for topic in topics if topic["flag"] == "developing"
        ]
        developing.sort(key=lambda topic: topic["mastery"])
        next_steps = [
            {"topic": topic["topic"], "mastery": topic["mastery"]}
            for topic in developing[:3]
        ]
        if next_steps:
            advice = (
                "下一步建议：先学“正在发展”的主题（最近发展区，Vygotsky 1978），"
                "从掌握度最低的开始，配合自测与间隔复习。"
            )
        else:
            advice = "没有正在发展的主题：要么都掌握（开始新主题），要么都是新主题（先建立基础）。"
        return {
            "topics": topics,
            "next_steps": next_steps,
            "advice": advice,
        }

    def attention_filter(
        self,
        task: str,
        *,
        top_k: int = 5,
        now: datetime | None = None,
    ) -> dict:
        """Filter memories for the current task (biased competition).

        Selective attention: task goals bias the competition so relevant
        representations win while distractors are suppressed (Desimone &
        Duncan, 1995). This tool recalls task-relevant memories and flags
        strong-but-irrelevant memories that should stay out of the prompt.
        """
        results = self.recall(task, top_k=max(1, int(top_k)), now=now)
        relevant = [
            {
                "id": result.item.id,
                "preview": result.item.content[:36],
                "score": round(result.score, 3),
            }
            for result in results
        ]
        relevant_ids = {item["id"] for item in relevant}
        suppressed: list[dict] = []
        for item in self.store.all_active():
            if item.id in relevant_ids:
                continue
            if item.strength >= 0.7 and item.importance >= 0.6:
                suppressed.append(
                    {
                        "id": item.id,
                        "preview": item.content[:32],
                        "strength": round(item.strength, 3),
                        "importance": round(item.importance, 3),
                        "reason": "很强但不相关：当前任务不要调出，避免分心",
                    }
                )
        suppressed.sort(
            key=lambda item: (-item["strength"], -item["importance"])
        )
        return {
            "task": task,
            "relevant": relevant,
            "kept_count": len(relevant),
            "suppressed": suppressed,
            "suppressed_count": len(suppressed),
            "advice": (
                "聚焦成功：保留相关记忆，把强但不相关的记忆挡在工作集外"
                "（偏向竞争，Desimone & Duncan 1995）。"
                if suppressed
                else "未发现强干扰记忆：按当前任务检索即可。"
            ),
        }

    def analogy_bridge(
        self,
        *,
        min_structure: float = 0.3,
        limit: int = 5,
    ) -> dict:
        """Find cross-topic memory pairs with shared structure (analogy).

        Analogical thinking maps systems of relations between different
        domains (structure-mapping; Gentner, 1983; Holyoak & Thagard,
        1995). This tool scores pairs from different topics by shared
        cues, shared terms and shared relation words, and suggests
        analogies that aid transfer.
        """


        relation_words = {
            "绕", "围绕", "大于", "小于", "等于", "导致", "因为",
            "所以", "依赖", "推动", "阻止", "包含", "属于", "对应",
            "orbit", "cause", "depend", "contain", "lead",
        }
        items = self.store.all_active()
        rows: list[dict] = []
        for a, b in combinations(items, 2):
            topic_a = a.cues[0] if a.cues else a.content[:10]
            topic_b = b.cues[0] if b.cues else b.content[:10]
            if topic_a == topic_b:
                continue
            cue_overlap = (
                len(set(a.cues) & set(b.cues))
                / max(1, len(set(a.cues) | set(b.cues)))
                if (a.cues or b.cues)
                else 0.0
            )
            terms_a = set(tokenize(a.content))
            terms_b = set(tokenize(b.content))
            term_overlap = (
                len(terms_a & terms_b) / max(1, len(terms_a | terms_b))
                if (terms_a or terms_b)
                else 0.0
            )
            relation_shared = int(
                any(word in a.content for word in relation_words)
                and any(word in b.content for word in relation_words)
            )
            structure = round(
                min(
                    1.0,
                    0.4 * cue_overlap
                    + 0.6 * term_overlap
                    + 0.2 * relation_shared,
                ),
                3,
            )
            if structure < min_structure:
                continue
            rows.append(
                {
                    "topic_a": topic_a,
                    "topic_b": topic_b,
                    "a_preview": a.content[:36],
                    "b_preview": b.content[:36],
                    "structure_score": structure,
                    "suggestion": (
                        f"结构相似：用「{topic_a}」理解「{topic_b}」，"
                        "关系可以迁移（结构映射）。"
                    ),
                }
            )
        rows.sort(key=lambda row: -row["structure_score"])
        return {
            "total_pairs_scanned": len(items) * (len(items) - 1) // 2,
            "analogy_count": len(rows),
            "analogies": rows[: max(1, int(limit))],
            "advice": (
                "找到类比桥：跨主题的结构相似记忆可以互相解释，"
                "迁移学习更省力（Gentner 1983）。"
                if rows
                else "暂无跨主题类比：继续积累不同领域记忆后再看。"
            ),
        }

    def next_interval(
        self,
        memory_id: str | None = None,
        *,
        now: datetime | None = None,
    ) -> dict:
        """Recommend each memory's next review interval (adaptive spacing).

        Adaptive spacing schedules intervals just long enough for
        effortful retrieval (Karpicke & Bauernschmidt, 2011; Cepeda et
        al., 2006). Base 24h grows with success streak, stretches with
        high accuracy and high retrievability, shrinks for failures,
        low retrievability and high importance.
        """
        if memory_id:
            item = self.backend.get(memory_id)
            items = [item] if item is not None else []
        else:
            items = self.store.all_active()
        rows: list[dict] = []
        for item in items:
            r = self.curve.retrievability(item, now)
            base = 24.0
            streak_mult = min(4.0, 1.5 ** item.review_streak)
            attempts = item.retrieval_successes + item.retrieval_failures
            if attempts >= 3:
                accuracy = item.retrieval_successes / attempts
                acc_mult = 1.2 if accuracy >= 0.8 else (
                    0.5 if accuracy < 0.5 else 1.0
                )
            else:
                accuracy = None
                acc_mult = 1.0
            imp_mult = 0.8 if item.importance >= 0.7 else 1.0
            if r >= 0.7:
                r_mult = 1.3
            elif r < 0.3:
                r_mult = 0.6
            else:
                r_mult = 1.0
            interval = round(
                base * streak_mult * acc_mult * imp_mult * r_mult,
                1,
            )
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:32],
                    "review_streak": item.review_streak,
                    "accuracy": accuracy,
                    "retrievability": round(r, 3),
                    "next_interval_hours": interval,
                    "reason": (
                        "连对多、准确率高、还熟练：间隔拉长"
                        if interval >= 100
                        else "失败多/快忘/重要：间隔缩短，早点复习"
                        if interval < 24
                        else "中等状态：保持当前间隔"
                    ),
                }
            )
        rows.sort(key=lambda row: -row["next_interval_hours"])
        return {
            "count": len(rows),
            "rows": rows,
            "advice": (
                "自适应间隔：按每次回忆表现调整下次复习时间，"
                "让回忆“有点难但能想起来”（Karpicke & Bauernschmidt 2011）。"
            ),
        }

    def nightly_routine(
        self,
        *,
        review_limit: int = 3,
        quiz_count: int = 3,
        now: datetime | None = None,
    ) -> dict:
        """Compose tonight's review, sleep inference and tomorrow's quiz.

        Sleep consolidates memory and pre-sleep rehearsal of important
        material strengthens it (Rasch & Born, 2013); retrieval practice
        the next day verifies and locks it in (testing effect; Roediger
        & Karpicke, 2006). This pipeline ties consolidation_forecast +
        sleep_inference + test_generator into one nightly routine.
        """
        forecast = self.consolidation_forecast(
            limit=max(1, int(review_limit)),
            now=now,
        )
        inference = self.sleep_inference(limit=1, now=now)
        quiz = self.test_generator(count=max(1, int(quiz_count)))
        tonight = [
            {
                "id": candidate["id"],
                "preview": candidate["preview"],
                "score": candidate["consolidation_score"],
            }
            for candidate in forecast["tonight_candidates"]
        ]
        return {
            "tonight_review": tonight,
            "sleep_inference_pairs": inference["ready_pairs"],
            "tomorrow_quiz": quiz["questions"],
            "advice": (
                "夜间流程：今晚复习候选 → 睡眠整合推断对 → "
                "明早自测验证（睡眠巩固 + 测试效应）。"
            ),
        }

    def cue_diversity(
        self,
        *,
        limit: int = 20,
    ) -> dict:
        """Check each memory's retrieval-cue breadth.

        Encoding specificity (Tulving & Thomson, 1973): a memory is
        reachable through cues present at encoding, and multiple distinct
        cues make retrieval more robust. Single-cue memories are fragile;
        cues shared by many memories are overloaded and weak.
        """

        items = self.store.all_active()
        cue_counts: Counter = Counter()
        for item in items:
            for cue in item.cues:
                cue_counts[cue] += 1
        rows: list[dict] = []
        for item in items:
            cue_count = len(item.cues)
            if cue_count >= 3:
                level = "robust"
            elif cue_count == 2:
                level = "ok"
            else:
                level = "fragile"
            overloaded = [
                cue for cue in item.cues if cue_counts[cue] > 4
            ]
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:32],
                    "cue_count": cue_count,
                    "cues": item.cues[:4],
                    "level": level,
                    "overloaded_cues": overloaded[:3],
                    "suggestion": (
                        "线索太窄：加 1-2 个不同角度的线索，"
                        "检索更稳（编码特异性）。"
                        if level == "fragile" or overloaded
                        else "线索足够：保持现状。"
                    ),
                }
            )
        rows.sort(key=lambda row: row["cue_count"])
        counts = defaultdict(int)
        for row in rows:
            counts[row["level"]] += 1
        fragile = [row for row in rows if row["level"] == "fragile"]
        return {
            "total_memories": len(items),
            "level_counts": dict(counts),
            "rows": rows[: max(1, int(limit))],
            "advice": (
                "有脆弱线索：单线索/超载线索记忆容易想不起来，"
                "建议补充多角度线索（Tulving & Thomson 1973）。"
                if fragile
                else "线索结构良好：记忆检索路径丰富。"
            ),
        }

    def weekly_review(
        self,
        *,
        now: datetime | None = None,
    ) -> dict:
        """Compose a weekly memory health review.

        Aggregates coverage (blind spots), forgetting risk, metacognitive
        calibration and tonight's consolidation candidates into one
        weekly summary plus a next-week plan.
        """
        coverage = self.coverage_report(now=now)
        risk = self.forgetting_risk(now=now, limit=5)
        meta = self.metacog_report()
        stats = self.stats()
        forecast = self.consolidation_forecast(limit=3, now=now)
        weak_topics = [
            {
                "topic": topic["topic"],
                "coverage": topic["coverage"],
                "status": topic["status"],
            }
            for topic in coverage["topics"]
            if topic["status"] in ("unreviewed", "partial")
        ]
        next_week_plan = [
            "先复习遗忘风险最高的 5 条（重要且快忘）",
            "补练未复习/只复习一半的主题（盲区）",
            "校准过度自信主题（多自测、用真实成绩对齐）",
            "每晚按夜间流程跑一遍（睡前复习 + 明早自测）",
        ]
        return {
            "week_summary": {
                "total_memories": stats["active"],
                "topics": coverage["total_topics"],
                "weak_topics": weak_topics,
                "avg_risk": risk["avg_risk"],
                "riskiest_ids": [
                    entry["id"] for entry in risk["riskiest"]
                ],
                "calibration_score": meta["calibration_score"],
                "tonight_candidates": len(forecast["tonight_candidates"]),
            },
            "next_week_plan": next_week_plan,
            "advice": (
                "周报生成：先补盲区和风险记忆，再校准置信度，"
                "每天用夜间流程巩固。"
            ),
        }

    def transfer_prompt(
        self,
        *,
        count: int = 3,
        min_mastery: float = 0.7,
        now: datetime | None = None,
    ) -> dict:
        """Generate cross-context application questions (far transfer).

        Transfer depends on applying knowledge in a new context (Barnett
        & Ceci, 2002). This tool picks mastered topics from mastery_map
        and builds hidden-answer prompts that apply the knowledge to a
        new scenario instead of re-asking the original fact.
        """
        mastery = self.mastery_map(now=now)
        mastered = [
            topic for topic in mastery["topics"]
            if topic["flag"] == "mastered"
            and topic["mastery"] >= min_mastery
        ]
        chosen = mastered[: max(1, int(count))]
        if not chosen:
            chosen = mastery["topics"][: max(1, int(count))]
        scenarios = [
            "一个陌生领域",
            "一次真实任务",
            "一个反例场景",
        ]
        prompts: list[dict] = []
        for index, topic in enumerate(chosen):
            items = [
                item
                for item in self.store.all_active()
                if item.cues and item.cues[0] == topic["topic"]
            ]
            for item in items[:1]:
                scenario = scenarios[index % len(scenarios)]
                prompts.append(
                    {
                        "memory_id": item.id,
                        "topic": topic["topic"],
                        "question": (
                            f"【迁移】把「{topic['topic']}」的知识用到"
                            f"{scenario}：说明怎么应用（答案隐藏）。"
                        ),
                        "hint_cues": item.cues[:3],
                        "answer_hidden": True,
                    }
                )
        return {
            "topics": [
                {"topic": topic["topic"], "mastery": topic["mastery"]}
                for topic in chosen
            ],
            "prompts": prompts,
            "advice": (
                "迁移题已生成：已掌握主题换新场景应用，"
                "检验的是真理解而不是死记（Barnett & Ceci 2002）。"
                if prompts
                else "暂无已掌握主题：先巩固基础，再练迁移。"
            ),
        }

    def curve_fit(
        self,
        memory_id: str | None = None,
        *,
        horizon_days: int = 30,
        threshold: float = 0.4,
        now: datetime | None = None,
    ) -> dict:
        """Personalize each memory's forgetting forecast.

        Forgetting rates vary across individuals and items (Murre &
        Chessa, 2011): repeated successful retrieval builds storage
        strength (Bjork & Bjork, 1992) and slows decay. This tool
        estimates a per-memory decay rate from retrieval history and
        predicts the day retrievability crosses a threshold.
        """

        threshold = max(0.05, min(0.95, float(threshold)))
        if memory_id:
            item = self.backend.get(memory_id)
            items = [item] if item is not None else []
        else:
            items = self.store.all_active()
        rows: list[dict] = []
        for item in items:
            r = self.curve.retrievability(item, now)
            attempts = item.retrieval_successes + item.retrieval_failures
            if attempts:
                success_rate = item.retrieval_successes / attempts
                history_factor = min(2.0, 0.5 + success_rate)
            else:
                history_factor = 1.0
            base_rate = self.curve.effective_decay_rate(item)
            estimated_rate = base_rate / history_factor
            if r > threshold:
                days_to = round(
                    math.log(r / threshold) / estimated_rate / 24.0,
                    1,
                )
            else:
                days_to = 0.0
            days_to = min(float(horizon_days), days_to)
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:32],
                    "retrievability": round(r, 3),
                    "attempts": attempts,
                    "success_rate": (
                        round(item.retrieval_successes / attempts, 3)
                        if attempts
                        else None
                    ),
                    "estimated_rate_per_hour": round(estimated_rate, 5),
                    "days_to_threshold": days_to,
                    "reason": (
                        "回忆成功率越高，遗忘越慢"
                        if history_factor > 1.0
                        else "暂无历史记录，按默认速率预测"
                    ),
                }
            )
        rows.sort(key=lambda row: row["days_to_threshold"])
        return {
            "count": len(rows),
            "threshold": threshold,
            "rows": rows,
            "advice": (
                "个性化遗忘曲线：用每条记忆的真实回忆记录调衰减速率，"
                "预测多久后会跌破复习阈值（Murre & Chessa 2011）。"
            ),
        }

    def affect_decay(
        self,
        *,
        limit: int = 20,
    ) -> dict:
        """Forecast emotional charge persistence for emotional memories.

        Emotional memories persist longer, but repeated successful
        processing reduces the charge (Gross, 2002; extinction-like
        regulation). Residual charge drops with the review streak (3
        consecutive successes = processed). This reports current charge,
        estimated persistence and a regulation hint.
        """

        emotional = [
            item
            for item in self.store.all_active()
            if item.affect in ("positive", "negative", "arousing", "mixed")
        ]
        rows: list[dict] = []
        for item in emotional:
            charge = round(max(0.0, 1.0 - item.review_streak / 3.0), 3)
            persistence_days = round(charge * 30.0, 1)
            if charge == 0:
                status = "processed"
            elif charge <= 0.5:
                status = "fading"
            else:
                status = "persistent"
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:32],
                    "affect": item.affect,
                    "review_streak": item.review_streak,
                    "charge": charge,
                    "persistence_days": persistence_days,
                    "status": status,
                    "hint": (
                        "情绪已处理：正常间隔复习即可"
                        if status == "processed"
                        else "情绪在消退：保持重评式复习"
                        if status == "fading"
                        else "情绪仍强：用重评+更新处理，别反复回放"
                    ),
                }
            )
        rows.sort(
            key=lambda row: (-row["charge"], row["persistence_days"])
        )
        counts = defaultdict(int)
        for row in rows:
            counts[row["status"]] += 1
        persistent = [row for row in rows if row["status"] == "persistent"]
        return {
            "total_emotional": len(emotional),
            "status_counts": dict(counts),
            "rows": rows[: max(1, int(limit))],
            "advice": (
                "仍有高情绪记忆：先重评（换个角度），再趁提取窗口更新"
                "结论（Gross 2002；Nader 2000）。"
                if persistent
                else "情绪记忆处理良好：按间隔复习保持即可。"
            ),
        }

    def goal_progress(
        self,
        goal: str,
        *,
        now: datetime | None = None,
    ) -> dict:
        """Measure progress toward a learning goal via topic mastery.

        Self-regulated learning requires setting goals and monitoring
        progress (Zimmerman; goal-monitoring research). This tool maps
        the goal to the best-matching topic in mastery_map and reports
        the mastery ratio and status.
        """
        mastery = self.mastery_map(now=now)
        goal_lower = goal.strip().lower()
        matches: list[dict] = []
        for topic in mastery["topics"]:
            if (
                goal_lower in topic["topic"].lower()
                or topic["topic"].lower() in goal_lower
            ):
                matches.append(topic)
        if not matches:
            for topic in mastery["topics"]:
                items = [
                    item
                    for item in self.store.all_active()
                    if item.cues and item.cues[0] == topic["topic"]
                ]
                if any(
                    goal_lower in item.content.lower()
                    for item in items
                ):
                    matches.append(topic)
        if matches:
            best = max(matches, key=lambda topic: topic["mastery"])
            progress_ratio = best["mastery"]
            if best["flag"] == "mastered":
                status = "mastered"
            elif best["flag"] == "developing":
                status = "in_progress"
            else:
                status = "not_started"
            matched_topic = best["topic"]
        else:
            progress_ratio = 0.0
            status = "not_started"
            matched_topic = None
        return {
            "goal": goal,
            "matched_topic": matched_topic,
            "progress_ratio": progress_ratio,
            "status": status,
            "advice": (
                "目标已有进度：继续按掌握度地图的下一步学，"
                "定期复查（自我调节学习）。"
                if status == "in_progress"
                else "目标已掌握：换迁移题检验真理解。"
                if status == "mastered"
                else "目标未开始：先积累该主题的基础记忆。"
            ),
        }

    def retrieval_snapshot(
        self,
        *,
        previous: dict | None = None,
        now: datetime | None = None,
    ) -> dict:
        """Capture a compact memory-state snapshot (longitudinal tracking).

        Knowledge tracing monitors how a learner's knowledge state
        evolves over time (knowledge-tracing literature). This captures
        key indicators; passing a previous snapshot adds a progress diff.
        """
        stats = self.stats()
        items = self.store.all_active()
        avg_r = round(
            sum(self.curve.retrievability(item, now) for item in items)
            / max(1, len(items)),
            3,
        )
        reviewed = sum(
            1
            for item in items
            if item.retrieval_successes + item.retrieval_failures > 0
        )
        risk = self.forgetting_risk(now=now)
        meta = self.metacog_report()
        snapshot = {
            "total_memories": stats["active"],
            "avg_retrievability": avg_r,
            "reviewed_ratio": round(reviewed / max(1, len(items)), 3),
            "avg_risk": risk["avg_risk"],
            "calibration_score": meta["calibration_score"],
            "topics": len(meta["topics"]),
        }
        diff: dict | None = None
        if previous and previous.get("snapshot"):
            prev = previous["snapshot"]
            diff = {}
            for key in snapshot:
                if key in prev:
                    diff[key] = round(snapshot[key] - prev[key], 3)
            progress = sum(
                1
                for key in ("avg_retrievability", "reviewed_ratio",
                            "calibration_score")
                if diff.get(key, 0) > 0
            )
            regress = sum(
                1
                for key in ("avg_retrievability", "reviewed_ratio",
                            "calibration_score")
                if diff.get(key, 0) < 0
            )
            verdict = "improving" if progress > regress else (
                "declining" if regress > progress else "stable"
            )
            diff["verdict"] = verdict
        return {
            "captured_at": (now or utcnow()).isoformat(),
            "snapshot": snapshot,
            "diff": diff,
            "advice": (
                "快照已生成：下次再拍一张对比，就能看到进步/退步"
                "（知识追踪，纵向监控）。"
                if diff is None
                else f"快照对比完成：{diff.get('verdict', 'stable')}。"
            ),
        }

    def retrieval_assist(
        self,
        query: str,
        *,
        limit: int = 8,
        now: datetime | None = None,
    ) -> dict:
        """Suggest alternative retrieval cues when a query stalls.

        Encoding specificity (Tulving & Thomson, 1973) and
        transfer-appropriate processing (Morris, Bransford & Franks,
        1977): a memory is reachable through the cues present at encoding,
        so rephrasing the question with the stored cue words recovers
        traces the original query misses. This tool mines existing cues
        and content terms that overlap the (synonym-expanded) query and
        returns them as concrete follow-up queries.
        """

        q_terms = set(tokenize(query))
        expanded = (
            expand_synonyms(q_terms) if has_cjk(query) else set(q_terms)
        )
        new_synonyms = sorted(expanded - q_terms)
        cue_counts: dict[str, int] = {}
        content_counts: dict[str, int] = {}
        for item in self.store.all_active():
            best_cue = 0
            for cue in item.cues:
                common = len(expanded & set(tokenize(cue)))
                if common > best_cue:
                    best_cue = common
            if best_cue and item.cues:
                cue_counts[item.cues[0]] = max(
                    cue_counts.get(item.cues[0], 0), best_cue
                )
            common = len(expanded & set(tokenize(item.content)))
            if common:
                for cue in item.cues[:3] or [item.content[:12]]:
                    content_counts[cue] = max(
                        content_counts.get(cue, 0), common
                    )
        suggestions: list[dict] = []
        for cue, count in sorted(
            cue_counts.items(), key=lambda kv: (-kv[1], kv[0])
        ):
            suggestions.append(
                {"cue": cue, "source": "cue", "matched_count": count}
            )
        for cue, count in sorted(
            content_counts.items(), key=lambda kv: (-kv[1], kv[0])
        ):
            if not any(s["cue"] == cue for s in suggestions):
                suggestions.append(
                    {"cue": cue, "source": "content", "matched_count": count}
                )
        suggestions = suggestions[: max(1, int(limit))]
        recall = self.recall(query, top_k=3, now=now)
        return {
            "query": query,
            "expanded_terms": sorted(expanded),
            "new_synonyms": new_synonyms,
            "suggestions": suggestions,
            "top_recall": [
                {
                    "id": r.item.id,
                    "preview": r.item.content[:40],
                    "score": round(r.score, 3),
                    "confident": r.confident,
                }
                for r in recall
            ],
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
            if memory_id not in self._suppressed_ids:
                self._suppressed_ids[memory_id] = now.isoformat()
                suppressed += 1
        return {"suppressed": suppressed}

    def unsuppress_memories(self, memory_ids: list[str]) -> dict:
        """Restore suppressed memories to normal retrieval."""
        unsuppressed = 0
        for memory_id in memory_ids:
            if memory_id in self._suppressed_ids:
                del self._suppressed_ids[memory_id]
                unsuppressed += 1
        return {"unsuppressed": unsuppressed}

    def suppressed_report(self) -> dict:
        """List currently suppressed memories with their previews."""
        out = []
        for memory_id, suppressed_at in self._suppressed_ids.items():
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

    def timeline_report(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 200,
    ) -> dict:
        """Return an autobiographical timeline of episodic memories.

        Autobiographical memory is organized hierarchically by time
        (Conway & Pleydell-Pearce, 2000): life periods contain events,
        events contain details. This report lists episodic traces in
        chronological order grouped by day, optionally bounded by a
        start/end window.
        """
        items = [
            item
            for item in self.store.all_active(MemoryKind.EPISODIC)
            if item.status is MemoryStatus.ACTIVE
        ]
        items.sort(key=lambda item: item.created_at)
        if start is not None:
            items = [item for item in items if item.created_at >= start]
        if end is not None:
            items = [item for item in items if item.created_at < end]
        items = items[: max(1, int(limit))]
        days: dict[str, list[dict]] = {}
        for item in items:
            day = item.created_at.date().isoformat()
            days.setdefault(day, []).append(
                {
                    "id": item.id,
                    "preview": item.content[:40],
                    "kind": item.kind.value,
                    "importance": round(item.importance, 3),
                    "created_at": item.created_at.isoformat(),
                }
            )
        out = [
            {"date": day, "count": len(entries), "items": entries}
            for day, entries in sorted(days.items())
        ]
        return {
            "total": len(items),
            "days": out,
            "start_date": out[0]["date"] if out else None,
            "end_date": out[-1]["date"] if out else None,
        }

    def recognition_check(
        self,
        query: str,
        memory_id: str,
    ) -> dict:
        """Classify a memory hit as recollection vs familiarity.

        Dual-process theory (Yonelinas, 2002): recognition can rest on
        recollection (specific evidence recovered) or familiarity (a
        vague "I know it" without detail). This tool checks one candidate
        memory against a query and reports which process supports it.
        """

        item = self.backend.get(memory_id)
        if item is None:
            return {"memory_id": memory_id, "verdict": "missing"}
        results = self.recall(query, top_k=10)
        entry = next(
            (r for r in results if r.item.id == memory_id), None
        )
        q_terms = set(tokenize(query))
        item_terms = set(tokenize(item.content)) | set(item.cues)
        common = len(q_terms & item_terms)
        overlap = (
            common / max(1, min(len(q_terms), len(item_terms)))
            if q_terms and item_terms
            else 0.0
        )
        if entry is None:
            verdict = "unmatched"
            score = 0.0
            reasons = []
        else:
            score = entry.score
            reasons = entry.reasons
            evidence = any(
                "overlap" in r or "semantic" in r for r in reasons
            )
            if overlap >= 0.6:
                verdict = "recollection"
            elif overlap > 0 and evidence:
                verdict = "familiarity"
            else:
                verdict = "unmatched"
        return {
            "memory_id": memory_id,
            "verdict": verdict,
            "score": round(score, 3),
            "overlap": round(overlap, 3),
            "confidence": item.confidence,
            "reasons": reasons[:5],
        }

    def interference_report(
        self,
        shared_cue_min: int = 3,
        limit: int = 20,
    ) -> dict:
        """Report cue-crowded clusters that cause interference.

        Proactive interference (Wickens, 1972): when too many memories
        hang on the same cue, they compete and get confused. This tool
        finds cues with >= shared_cue_min active memories and suggests
        differentiating them with extra cues.
        """

        cue_members: dict[str, list] = defaultdict(list)
        for item in self.store.all_active():
            for cue in item.cues:
                cue_members[cue].append(item)
        clusters = []
        for cue, members in cue_members.items():
            if len(members) < max(2, int(shared_cue_min)):
                continue
            total_overlap = 0.0
            pairs = 0
            for i in range(len(members)):
                a_terms = set(tokenize(members[i].content))
                for j in range(i + 1, len(members)):
                    b_terms = set(tokenize(members[j].content))
                    common = len(a_terms & b_terms)
                    denominator = max(
                        1, min(len(a_terms), len(b_terms))
                    )
                    total_overlap += common / denominator
                    pairs += 1
            avg_overlap = (
                round(total_overlap / pairs, 3) if pairs else 0.0
            )
            members.sort(key=lambda it: it.seq, reverse=True)
            clusters.append(
                {
                    "cue": cue,
                    "memory_count": len(members),
                    "avg_content_overlap": avg_overlap,
                    "members": [
                        {
                            "id": item.id,
                            "preview": item.content[:32],
                        }
                        for item in members[:5]
                    ],
                }
            )
        clusters.sort(
            key=lambda c: (-c["memory_count"], c["cue"])
        )
        clusters = clusters[: max(1, int(limit))]
        return {
            "total_cues": len(cue_members),
            "crowded_clusters": clusters,
            "suggestion": (
                "给同一线索下的记忆补上区别性线索（日期/对象/主题词），"
                "降低互相抢答"
            ),
        }

    def life_story(
        self,
        period_days: int = 30,
        limit: int = 20,
    ) -> dict:
        """Summarize the memory store as life periods.

        Autobiographical memory is organized into lifetime periods that
        contain events (Conway & Pleydell-Pearce, 2000). This tool groups
        episodic traces into time buckets (default 30 days) and reports
        each period's event count, top themes, average importance and
        highlights.
        """

        epoch = date(1970, 1, 1)
        items = [
            item
            for item in self.store.all_active(MemoryKind.EPISODIC)
            if item.status is MemoryStatus.ACTIVE
        ]
        items.sort(key=lambda item: item.created_at)
        buckets: dict[date, list] = defaultdict(list)
        for item in items:
            day = item.created_at.date()
            bucket = epoch + timedelta(
                days=(day - epoch).days // max(1, int(period_days))
                * max(1, int(period_days))
            )
            buckets[bucket].append(item)
        periods = []
        for bucket in sorted(buckets):
            members = buckets[bucket]
            theme_counts: dict[str, int] = defaultdict(int)
            importance_sum = 0.0
            for item in members:
                topic = item.cues[0] if item.cues else "（无标签）"
                theme_counts[topic] += 1
                importance_sum += item.importance
            highlights = sorted(
                members,
                key=lambda it: (it.importance, it.seq),
                reverse=True,
            )[:3]
            periods.append(
                {
                    "period_start": bucket.isoformat(),
                    "period_end": (
                        bucket + timedelta(days=max(1, int(period_days)) - 1)
                    ).isoformat(),
                    "event_count": len(members),
                    "top_themes": [
                        {"cue": cue, "count": count}
                        for cue, count in sorted(
                            theme_counts.items(),
                            key=lambda kv: (-kv[1], kv[0]),
                        )[:5]
                    ],
                    "avg_importance": round(
                        importance_sum / len(members), 3
                    ),
                    "highlights": [
                        {
                            "id": item.id,
                            "preview": item.content[:32],
                            "importance": round(item.importance, 3),
                        }
                        for item in highlights
                    ],
                }
            )
        periods = periods[: max(1, int(limit))]
        return {
            "period_days": max(1, int(period_days)),
            "total_events": len(items),
            "periods": periods,
        }

    def recall_reasoning(
        self,
        query: str,
        *,
        top_k: int | None = None,
        now: datetime | None = None,
    ) -> list[RecallResult]:
        """System-2 recall: assemble a reasoning premise pack.

        Fast keyword retrieval (System 1) plus a bounded boost for all
        same-dimension premises (math / compare / transitive questions), so
        the full premise set reaches the LLM context (Kahneman 2011;
        Miller & Cohen 2001).
        """

        return self.recall(
            query,
            top_k=top_k or suggested_pack_size(query),
            now=now,
            reasoning_pack=True,
        )

    def recall_steps(
        self,
        query: str,
        *,
        top_k: int = 10,
        now: datetime | None = None,
        zh_synonyms: bool = True,
        plan_reuse: bool = True,
    ) -> list[RecallResult]:
        """Chain-of-thought step retrieval for process questions.

        "怎么 / 如何 / 为什么" questions need the ordered intermediate
        steps, not a keyword soup: mental time travel (Tulving, 1985) and
        event schemas (Gilboa & Marlatte, 2017) organize episodes into a
        chronological script, and chain-of-thought reasoning (Wei et al.,
        2022) consumes those steps in order. Episodic results are sorted by
        event date; non-process questions behave exactly like
        ``recall_reasoning``.
        """


        results = self.recall(
            query,
            top_k=max(top_k * 2, 16),
            now=now,
            reasoning_pack=True,
            zh_synonyms=zh_synonyms,
        )
        if not any(marker in query for marker in (
            "怎么", "如何", "为什么", "过程", "步骤", "准备", "计划", "安排",
            "第一步", "该做什么", "怎么做", "流程", "方法", "办法", "方式",
            "想", "要", "打算", "希望",
            "how", "why", "step",
        )):
            return results[:top_k]

        def _event_date(result) -> str:
            content = result.item.content
            match = re.search(r"\d{4}-\d{2}-\d{2}", content)
            if match:
                return match.group(0)
            match = re.search(
                r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
                content,
            )
            if match:
                return (
                    f"{int(match.group(1)):04d}-"
                    f"{int(match.group(2)):02d}-"
                    f"{int(match.group(3)):02d}"
                )
            return "9999-12-31"

        episodic = [
            r for r in results
            if r.item.kind is MemoryKind.EPISODIC
            and "执行成功" not in r.item.content
            and "执行失败" not in r.item.content
        ]
        others = [
            r for r in results if r.item.kind is not MemoryKind.EPISODIC
        ]
        ref_persons: list[str] = []
        if plan_reuse:

            found = re.findall(
                r"(?:参考|参照|学|模仿|按照|像)([\u4e00-\u9fff]{2})"
                r"|和([\u4e00-\u9fff]{2})",
                query,
            )
            ref_persons = [
                (a or b) for a, b in found if (a or b)
            ]
            if ref_persons:

                query_terms = expand_synonyms(set(tokenize(query)))
                _TOPIC_STOP = {
                    "怎么", "如何", "准备", "计划", "参考", "参照", "模仿",
                    "按照", "更好", "希望", "想要", "想做", "打算", "安排",
                }
                topic_terms = [
                    t for t in query_terms
                    if t not in ref_persons
                    and t not in _TOPIC_STOP
                    and len(t) > 1
                ][:4]
                topic = " ".join(topic_terms)
                existing_ids = {r.item.id for r in episodic}
                for ref_person in ref_persons:
                    extra = self.recall(
                        f"{ref_person} {topic}".strip(),
                        top_k=8,
                        now=now,
                        kind=MemoryKind.EPISODIC,
                        reasoning_pack=True,
                        zh_synonyms=zh_synonyms,
                    )
                    for r in extra:
                        if (
                            r.item.kind is not MemoryKind.EPISODIC
                            or r.item.id in existing_ids
                            or "执行成功" in r.item.content
                            or "执行失败" in r.item.content
                        ):
                            continue
                        if (
                            ref_person not in r.item.cues
                            and ref_person not in r.item.content
                        ):
                            continue
                        episodic.append(r)
                        existing_ids.add(r.item.id)
                        if not any(
                            "\u7c7b\u6bd4\u8ba1\u5212" in reason
                            for reason in r.reasons
                        ):
                            r.reasons.append(
                                "\u7c7b\u6bd4\u8ba1\u5212(\u53c2\u8003"
                                f"{ref_person})"
                            )
            ref_persons_all = ref_persons
            if ref_persons_all:
                ref_person = ref_persons_all[0]
                for r in episodic:
                    if (
                        ref_person in r.item.cues
                        or ref_person in r.item.content
                    ):
                        r.score = round(r.score + 0.08, 4)
                        if not any(
                            "类比计划" in reason for reason in r.reasons
                        ):
                            r.reasons.append(
                                "\u7c7b\u6bd4\u8ba1\u5212(\u53c2\u8003"
                                f"{ref_person})"
                            )
        def _plan_key(result) -> tuple:
            person = (
                result.item.cues[0][:2]
                if result.item.cues
                else result.item.content[:2]
            )
            ref_priority = 0 if person in ref_persons else 1
            return (ref_priority, _event_date(result))

        episodic.sort(key=_plan_key)
        ordered = episodic + others
        for result in episodic:
            if not any("步骤" in reason for reason in result.reasons):
                result.reasons.append(
                    "\u601d\u7ef4\u94fe\u6b65\u9aa4(\u6309\u65f6\u95f4\u6392\u5e8f)"
                )
        return ordered[:top_k]

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
            match = __import__("re").search(
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
    _MATH_SYMBOLS = {
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
    _PHYSICS_RULES = {
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

    def review_consistency(
        self,
        *,
        now: datetime | None = None,
    ) -> dict:
        """Monitor adherence to the spaced-review schedule (SRL).

        Spacing only works when reviews actually happen at the scheduled
        time (Cepeda et al., 2006), and monitoring one's own study
        behavior is a core self-regulated-learning skill (Zimmerman).
        For every memory with review history this computes the next
        scheduled review from its last review, flags past-due items,
        and reports an adherence ratio with plain advice.
        """
        now = now or utcnow()
        reviewed = []
        never_reviewed = 0
        for item in self.store.all_active():
            if item.last_review_at is None:
                never_reviewed += 1
                continue
            due_at = self.scheduler.next_review_at(
                item, now=item.last_review_at
            )
            overdue = now > due_at
            lateness_days = max(0, (now - due_at).days)
            reviewed.append(
                {
                    "memory_id": item.id,
                    "preview": item.content[:32],
                    "review_streak": item.review_streak,
                    "last_review_at": item.last_review_at.isoformat(),
                    "scheduled_at": due_at.isoformat(),
                    "overdue": overdue,
                    "lateness_days": lateness_days,
                }
            )
        reviewed.sort(key=lambda row: -row["lateness_days"])
        on_time = sum(1 for row in reviewed if not row["overdue"])
        total_reviewed = len(reviewed)
        adherence_ratio = round(
            on_time / max(1, total_reviewed), 3
        )
        avg_lateness = round(
            sum(row["lateness_days"] for row in reviewed)
            / max(1, total_reviewed),
            2,
        )
        if adherence_ratio >= 0.8:
            verdict = "high"
        elif adherence_ratio >= 0.5:
            verdict = "medium"
        else:
            verdict = "low"
        if total_reviewed == 0:
            advice = (
                "还没有复习记录：间隔复习只有真复习才有用，"
                "先从到期记忆开始每天复习。"
            )
        elif verdict == "high":
            advice = (
                f"坚持度 {adherence_ratio:.0%}：复习很准时，"
                "保持这个节奏，重点看最晚到期的几条。"
            )
        elif verdict == "medium":
            advice = (
                f"坚持度 {adherence_ratio:.0%}：一半左右复习在到期后补做，"
                "把复习固定到固定时段，先清积压再上新。"
            )
        else:
            advice = (
                f"坚持度 {adherence_ratio:.0%}：积压较多，"
                "建议先只复习最危险（最重要+最晚到期）的几条，"
                "恢复节奏后再扩量。"
            )
        return {
            "total_memories": len(reviewed) + never_reviewed,
            "reviewed_count": total_reviewed,
            "on_time_count": on_time,
            "overdue_count": total_reviewed - on_time,
            "never_reviewed_count": never_reviewed,
            "adherence_ratio": adherence_ratio,
            "avg_lateness_days": avg_lateness,
            "verdict": verdict,
            "top_overdue": reviewed[:3],
            "advice": advice,
        }

    def learning_loop(
        self,
        *,
        now: datetime | None = None,
        count: int = 1,
    ) -> dict:
        """Build a ready-to-run learning loop: review -> practice -> snapshot.

        Combines three evidence-backed principles into one agent-facing
        loop: spaced-review adherence (Cepeda et al., 2006), the testing
        effect (Roediger & Karpicke, 2006) and longitudinal knowledge
        tracking (retrieval_snapshot). The returned steps say what to
        review first, which self-test question to attempt for the
        weakest topic, and which snapshot to take afterwards to measure
        progress. Read-only.
        """
        baseline = self.retrieval_snapshot(now=now)
        consistency = self.review_consistency(now=now)
        mastery = self.mastery_map(now=now)
        focus = None
        if mastery["next_steps"]:
            focus = mastery["next_steps"][0]["topic"]
        elif mastery["topics"]:
            focus = mastery["topics"][0]["topic"]
        practice = None
        if focus:
            mastered = any(
                entry["topic"] == focus and entry["flag"] == "mastered"
                for entry in mastery["topics"]
            )
            if mastered:
                generated = self.analogy_prompt(
                    topic=focus, count=max(1, int(count))
                )
                practice = {
                    "kind": "analogy",
                    "topic": focus,
                    "questions": generated["prompts"][
                        : max(1, int(count))
                    ],
                }
            else:
                generated = self.test_generator(
                    topic=focus, count=max(1, int(count))
                )
                practice = {
                    "kind": "test",
                    "topic": focus,
                    "questions": generated["questions"][
                        : max(1, int(count))
                    ],
                }
        if practice and practice["questions"]:
            practice_question = practice["questions"][0]["question"]
        else:
            practice_question = "记忆库里还没有可练的题，先积累内容。"
        steps = [
            {
                "order": 1,
                "step": "清积压",
                "detail": (
                    f"先复习 {consistency['overdue_count']} 条过期记忆；"
                    "从最重要+最晚到期的开始。"
                ),
            },
            {
                "order": 2,
                "step": "做练习",
                "detail": practice_question,
            },
            {
                "order": 3,
                "step": "拍快照",
                "detail": (
                    "学完后再拍一张记忆快照，对比本次 baseline"
                    "看进步/退步。"
                ),
            },
        ]
        verdict = "empty" if not mastery["topics"] else "ready"
        if verdict == "empty":
            advice = (
                "记忆库还是空的：先存入学习内容，才能形成"
                "复习→练习→快照的闭环。"
            )
        else:
            advice = (
                f"学习闭环已生成：先清 {consistency['overdue_count']} 条"
                "积压，再做练习，最后拍快照对比——按顺序执行就能看到进步。"
            )
        return {
            "baseline": baseline["snapshot"],
            "review": {
                "overdue_count": consistency["overdue_count"],
                "never_reviewed_count": consistency["never_reviewed_count"],
                "adherence_ratio": consistency["adherence_ratio"],
            },
            "focus_topic": focus,
            "practice": practice,
            "steps": steps,
            "verdict": verdict,
            "advice": advice,
        }

    def agent_learning_session(
        self,
        answers: list[dict] | None = None,
        *,
        now: datetime | None = None,
        count: int = 1,
    ) -> dict:
        """Run one end-to-end agent learning session (study + measure + plan).

        Executes the learning loop with real scoring: each attempt goes
        through practice_answer (testing effect; Roediger & Karpicke,
        2006), review consistency is re-checked, a second snapshot is
        diffed against the baseline (knowledge tracing), and the next
        loop is planned. Answers are ``{"id": memory_id, "attempt": str}``.
        """
        loop = self.learning_loop(now=now, count=count)
        baseline = loop["baseline"]
        scored: list[dict] = []
        if answers:
            for entry in answers:
                try:
                    result = self.practice_answer(
                        entry["id"],
                        entry.get("attempt", ""),
                        now=now,
                    )
                    scored.append(
                        {
                            "memory_id": entry["id"],
                            "success": bool(result["success"]),
                            "retrievability_after": result["retrievability"],
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    scored.append(
                        {
                            "memory_id": entry.get("id"),
                            "success": False,
                            "error": str(exc)[:40],
                        }
                    )
        after = self.retrieval_snapshot(
            previous={"snapshot": baseline}, now=now
        )
        consistency = self.review_consistency(now=now)
        next_loop = self.learning_loop(now=now, count=count)
        attempted = len(scored)
        correct = sum(1 for item in scored if item["success"])
        verdict = "empty" if not loop["practice"] else "ready"
        if verdict == "empty":
            advice = (
                "记忆库还是空的：先存入学习内容，再开学习会话。"
            )
        elif attempted:
            advice = (
                f"本次答对 {correct}/{attempted}，"
                f"快照结论：{after['diff']['verdict']}。"
                "下一轮计划已生成，按顺序继续。"
            )
        else:
            advice = (
                "本次没有答题记录：先做练习，再回来拍快照对比。"
            )
        return {
            "baseline": baseline,
            "practice": loop["practice"],
            "scored": scored,
            "session_result": {
                "attempted": attempted,
                "correct": correct,
                "success_rate": (
                    round(correct / max(1, attempted), 3)
                    if attempted
                    else None
                ),
            },
            "snapshot_after": {
                "diff": after["diff"],
                "advice": after["advice"],
            },
            "review_after": {
                "overdue_count": consistency["overdue_count"],
                "adherence_ratio": consistency["adherence_ratio"],
            },
            "next_loop": {
                "focus_topic": next_loop["focus_topic"],
                "steps": next_loop["steps"],
                "verdict": next_loop["verdict"],
            },
            "verdict": verdict,
            "advice": advice,
        }

    def sleep_replay(self, now: datetime | None = None) -> dict:
        """Sleep replay: strengthen surprising events, consolidate experience.

        Hippocampal replay (Wilson & McNaughton, 1994) preferentially
        replays salient waking events; sleep-dependent consolidation
        (Stickgold & Walker, 2013) stabilizes them. Prediction-error marked
        records ("意外") get a small strength boost, and each step's outcome
        history is consolidated into a semantic "历史成功率" summary.
        """
        _ACTION_PREFIXES = "订买卖打包收拾请找定学搬选入"
        steps: dict[str, list[int]] = {}
        replayed = 0
        for item in self.backend.list(kind=MemoryKind.EPISODIC):
            if "执行成功" not in item.content and "执行失败" not in item.content:
                continue
            if len(item.cues) < 3:
                continue
            step_cue = item.cues[1]
            noun = step_cue.lstrip(_ACTION_PREFIXES) or step_cue
            steps.setdefault(noun, [0, 0])
            if "执行成功" in item.content:
                steps[noun][0] += max(1, item.evidence_count)
            else:
                steps[noun][1] += max(1, item.evidence_count)
            if "意外" in item.cues:
                item.retrieval_successes += 1
                if item.strength < 1.0:
                    item.strength = round(min(1.0, item.strength + 0.05), 4)
                self.backend.update(item)
                replayed += 1

        consolidated = 0
        source = SourceRecord(origin=SourceType.INFERENCE)
        for noun, (success, failure) in steps.items():
            total = success + failure
            if total < 2:
                continue
            self.remember(
                f"步骤“{noun}”的历史成功率：{success}/{total}。",
                kind=MemoryKind.SEMANTIC,
                source=source,
                cues=[noun, "成功率"],
                importance=0.5,
                evidence_count=total,
                created_at=now,
            )
            consolidated += 1
        return {
            "replayed_surprising": replayed,
            "consolidated_steps": consolidated,
        }

    def practice_due(
        self,
        limit: int = 5,
        now: datetime | None = None,
        *,
        kind: MemoryKind | None = None,
        desirable_difficulty: bool = True,
        min_gap_hours: float = 24.0,
        adaptive_gap: bool = True,
        interleave: bool = True,
        vary_cues: bool = True,
        arousal_priority: bool = True,
        fresh_priority: bool = False,
        fresh_window_hours: float = 6.0,
        review_score_priority: bool = False,
    ) -> list[dict]:
        """Active retrieval practice: due memories shown as cues only.

        Testing effect (Roediger & Karpicke, 2006): attempting retrieval
        and then receiving feedback strengthens a memory more than passive
        re-reading. Spacing effect (Cepeda et al., 2006): practice must be
        spaced - ``min_gap_hours`` prevents massed re-practice of the same
        item. Interleaving (Rohrer & Taylor, 2007): cards from different
        categories are mixed so consecutive cards rarely repeat a category.
        The agent sees only the cues (no content) and must recall the answer
        before it is revealed. Transfer-appropriate processing (Morris,
        Bransford & Franks, 1977): practice in the same kind/format as the
        upcoming test transfers best, so ``kind`` puts that kind of memory
        first in the session. Encoding variability (Martin, 1968):
        practising through different cues each session makes the memory
        robust across query phrasings, so ``vary_cues`` rotates the shown
        cue. Arousal-biased competition (Mather & Sutherland, 2011):
        emotionally arousing memories compete harder for consolidation, so
        ``arousal_priority`` rehearses them first within the quota. Early
        consolidation window (Gais et al., 2006): traces encoded within the
        last few hours are preferentially rehearsed, so ``fresh_priority``
        puts them first while they are still consolidating.
        Review score (importance x forgetting): when enabled, due items are
        ordered by how much they *need* review - important AND fading
        traces first - instead of importance-first alone.
        """
        now = now or utcnow()
        items = self.review_due(
            limit=max(limit * 2, 12),
            now=now,
            desirable_difficulty=desirable_difficulty,
        )
        if arousal_priority:
            # Arousal-biased competition (Mather & Sutherland, 2011):
            # arousing traces compete harder for rehearsal, so they enter
            # the practice queue at a higher retrievability threshold
            # (0.65 instead of 0.5).
            extra = self.review_due(
                limit=max(limit * 2, 12),
                now=now,
                desirable_difficulty=desirable_difficulty,
                due_threshold=0.65,
            )
            extra_ids = {item.id for item in items}
            extra_cap = max(1, limit // 2)
            items = items + [
                item
                for item in extra
                if (
                    item.id not in extra_ids
                    and item.affect in ("positive", "negative", "arousing")
                )
            ][:extra_cap]
        if fresh_priority:
            fresh_extra = self.review_due(
                limit=max(limit * 2, 12),
                now=now,
                desirable_difficulty=desirable_difficulty,
                due_threshold=0.65,
            )
            existing = {item.id for item in items}
            fresh_items = [
                item
                for item in fresh_extra
                if (
                    item.id not in existing
                    and (now - item.created_at).total_seconds()
                    < fresh_window_hours * 3600
                )
            ]
            extra_cap = max(1, limit // 2)
            items = fresh_items[:extra_cap] + items
        if min_gap_hours > 0:
            kept = []
            for item in items:
                gap = min_gap_hours
                if adaptive_gap:
                    rate = self._success_rate(item)
                    total = item.retrieval_successes + item.retrieval_failures
                    if total > 0 and rate < 0.5:
                        # struggling memory: practise again sooner
                        gap *= 0.6
                    elif total > 0 and rate >= 0.9:
                        gap *= 1.3
                is_fresh = (
                    fresh_priority
                    and (now - item.created_at).total_seconds()
                    < fresh_window_hours * 3600
                )
                if (
                    is_fresh
                    or self.curve.hours_since_last_access(item, now) >= gap
                ):
                    kept.append(item)
            if (
                kind is not None
                or arousal_priority
                or review_score_priority
            ):
                def _practice_key(item: MemoryItem) -> tuple:
                    fresh = (
                        (now - item.created_at).total_seconds()
                        < fresh_window_hours * 3600
                        if fresh_priority
                        else False
                    )
                    kind_mismatch = (
                        item.kind is not kind if kind is not None else 0
                    )
                    arousal_mismatch = (
                        item.affect not in ("positive", "negative", "arousing")
                        if arousal_priority
                        else 0
                    )
                    if review_score_priority:
                        need = item.importance * (
                            1.0 - self.curve.retrievability(item, now)
                        )
                        return (
                            -need,
                            kind_mismatch,
                            arousal_mismatch,
                        )
                    return (
                        0 if fresh else 1,
                        kind_mismatch,
                        arousal_mismatch,
                    )

                kept.sort(key=_practice_key)
            items = kept[:limit]
        else:
            if (
                kind is not None
                or arousal_priority
                or review_score_priority
            ):
                def _practice_key2(item: MemoryItem) -> tuple:
                    fresh = (
                        (now - item.created_at).total_seconds()
                        < fresh_window_hours * 3600
                        if fresh_priority
                        else False
                    )
                    kind_mismatch = (
                        item.kind is not kind if kind is not None else 0
                    )
                    arousal_mismatch = (
                        item.affect not in ("positive", "negative", "arousing")
                        if arousal_priority
                        else 0
                    )
                    if review_score_priority:
                        need = item.importance * (
                            1.0 - self.curve.retrievability(item, now)
                        )
                        return (
                            -need,
                            kind_mismatch,
                            arousal_mismatch,
                        )
                    return (
                        0 if fresh else 1,
                        kind_mismatch,
                        arousal_mismatch,
                    )

                items = sorted(items, key=_practice_key2)
            items = items[:limit]
        if interleave and len(items) > 1:
            items = self._interleave(items)
        out = []
        for item in items:
            if vary_cues and len(item.cues) >= 3:
                total_reviews = (
                    item.retrieval_successes + item.retrieval_failures
                )
                start = total_reviews % len(item.cues)
                window = item.cues[start:start + 2]
                if len(window) < 2:
                    window = window + item.cues[:2 - len(window)]
                cue = " / ".join(window)
            else:
                cue = (
                    " / ".join(item.cues[:2])
                    if item.cues
                    else item.content[:12]
                )
            out.append({"id": item.id, "cue": cue})
        return out

    def _interleave(self, items: list[MemoryItem]) -> list[MemoryItem]:
        """Order items so adjacent cards avoid the same category (cue)."""
        buckets: dict[str, list[MemoryItem]] = {}
        for item in items:
            cat = item.cues[0] if item.cues else item.id
            buckets.setdefault(cat, []).append(item)
        out: list[MemoryItem] = []
        last_cat = None
        while buckets:
            candidates = [
                cat for cat in buckets
                if cat != last_cat and buckets[cat]
            ]
            if not candidates:
                candidates = [cat for cat in buckets if buckets[cat]]
            if not candidates:
                break
            cat = candidates[0]
            out.append(buckets[cat].pop(0))
            if not buckets[cat]:
                del buckets[cat]
            last_cat = cat
        return out

    def _success_rate(self, item: MemoryItem) -> float:
        total = item.retrieval_successes + item.retrieval_failures
        if total == 0:
            return 0.5
        return item.retrieval_successes / total

    def practice_answer(
        self,
        memory_id: str,
        attempt: str,
        now: datetime | None = None,
        *,
        suppress_competitors: bool = True,
        suppression_factor: float = 0.97,
        generation_bonus: bool = True,
    ) -> dict:
        """Score a retrieval attempt and apply testing-effect reinforcement.

        A successful recall applies effort-scaled reinforcement (the harder
        the retrieval, the stronger the gain); a failure resets the review
        streak so the item is practised again soon. On success, competing
        memories sharing the item's primary cue are gently suppressed
        (Anderson, Bjork & Bjork, 1994 retrieval-induced forgetting):
        lowering the competing items' accessibility makes the practised
        target easier to discriminate later. Only the primary cue is used
        so auto-extracted content bigrams never misfire suppression.
        Generation effect (Slamecka & Graf, 1978): a successful recall
        phrased in the agent's own words ("generated") strengthens more
        than copying the stored sentence verbatim, so a small extra
        reinforcement is applied unless disabled. Emotionally enhanced
        """
        item = self.backend.get(memory_id)
        if item is None:
            raise ValueError(f"no memory with id {memory_id}")
        now = now or utcnow()
        norm_attempt = "".join(str(attempt or "").split())
        norm_content = "".join(str(item.content).split())
        attempt_chars = set(norm_attempt)
        shared = len(attempt_chars & set(norm_content))
        success = bool(
            norm_attempt
            and (
                norm_attempt in norm_content
                or norm_content in norm_attempt
                or (
                    len(norm_attempt) >= 2
                    and shared >= 2
                    and shared / max(len(attempt_chars), 1) >= 0.6
                )
            )
        )
        generated = success and norm_attempt != norm_content
        if success:
            retrievability = self.curve.retrievability(item, now)
            effort = max(0.0, min(1.0, 1.0 - retrievability))
            delta = 0.12
            if generation_bonus and generated:
                delta *= 1.15
            self.curve.reinforce_review(
                item, delta=delta, now=now, effort=effort
            )
            self.scheduler.record_outcome(item, True, now)
            suppressed = 0
            if suppress_competitors:
                seen = {item.id}
                primary = item.cues[0] if item.cues else ""
                if primary:
                    for rival in self.backend.find_by_cue(primary):
                        if (
                            rival.id in seen
                            or rival.status is not MemoryStatus.ACTIVE
                        ):
                            continue
                        seen.add(rival.id)
                        rival.strength = max(
                            0.05, rival.strength * suppression_factor
                        )
                        self.backend.update(rival)
                        suppressed += 1
        else:
            # Feedback effect: even a failed retrieval attempt with feedback
            # produces a small, plain reinforcement (no effort gain).
            self.curve.reinforce(item, delta=0.05, now=now)
            self.scheduler.record_outcome(item, False, now)
        self.backend.update(item)
        result = {
            "id": item.id,
            "success": success,
            "content": item.content,
            "retrievability": round(
                self.curve.retrievability(item, now), 3
            ),
        }
        if success:
            result["suppressed"] = suppressed
            result["generated"] = generated
        return result

    def practice_report(
        self,
        answers: list[dict],
        now: datetime | None = None,
    ) -> dict:
        """Score a whole practice round and return a session report.

        Each answer is ``{"id": memory_id, "attempt": str}``; results are
        aggregated so the agent gets one summary (success rate, per-card
        feedback) instead of calling ``practice_answer`` card by card.
        """
        details = [
            self.practice_answer(a["id"], a.get("attempt", ""), now=now)
            for a in answers
        ]
        now = now or utcnow()
        for detail in details:
            item = self.backend.get(detail["id"])
            if item is None:
                continue
            next_review = self.scheduler.next_review_at(item, now)
            detail["next_review_at"] = next_review.isoformat()
            detail["retry_hours"] = round(
                (next_review - now).total_seconds() / 3600.0, 1
            )
        retrievabilities = []
        for detail in details:
            item = self.backend.get(detail["id"])
            if item is not None:
                retrievabilities.append(
                    self.curve.retrievability(item, now)
                )
        successes = sum(1 for d in details if d["success"])
        difficulty = None
        if retrievabilities:
            mean_ret = sum(retrievabilities) / len(retrievabilities)
            difficulty = {
                "n": len(retrievabilities),
                "mean_retrievability": round(mean_ret, 3),
                "mean_difficulty": round(1.0 - mean_ret, 3),
                "min_retrievability": round(min(retrievabilities), 3),
                "max_retrievability": round(max(retrievabilities), 3),
            }
        return {
            "n": len(details),
            "successes": successes,
            "failures": len(details) - successes,
            "success_rate": round(
                successes / len(details), 3
            ) if details else 0.0,
            "difficulty": difficulty,
            "details": details,
        }

    def practice_plan(
        self,
        limit: int = 5,
        now: datetime | None = None,
    ) -> list[dict]:
        """Return the next practice session as a review plan.

        The agent gets, for every card in the coming session, the scheduled
        next review time (Smolen et al., 2016 adaptive spacing), current
        retrievability, and historical success rate - so it can plan around
        the memory system instead of treating practice as a black box.
        """
        now = now or utcnow()
        cards = self.practice_due(limit=limit, now=now)
        plan = []
        for card in cards:
            item = self.backend.get(card["id"])
            if item is None:
                continue
            next_review = self.scheduler.next_review_at(item, now)
            plan.append(
                {
                    "id": item.id,
                    "cue": card["cue"],
                    "next_review_at": next_review.isoformat(),
                    "overdue": next_review < now,
                    "retrievability": round(
                        self.curve.retrievability(item, now), 3
                    ),
                    "success_rate": round(
                        self._success_rate(item), 3
                    ),
                    "kind": item.kind.value,
                }
            )
        return plan

    def practice_forecast(
        self,
        days: int = 7,
        now: datetime | None = None,
    ) -> list[dict]:
        """Forecast which memories are due within the next ``days``.

        Extends practice_plan into a calendar (Smolen et al., 2016
        adaptive spacing): every active trace whose scheduled next review
        falls inside the window is returned with its due time, so agents
        can plan a week of reviews ahead of time.
        """

        now = now or utcnow()
        horizon = now + timedelta(days=max(1, int(days)))
        forecast = []
        for item in self.store.all_active():
            next_review = self.scheduler.next_review_at(item, now)
            if not (next_review <= horizon):
                continue
            forecast.append(
                {
                    "id": item.id,
                    "cue": (
                        " / ".join(item.cues[:2])
                        if item.cues
                        else item.content[:12]
                    ),
                    "due_at": next_review.isoformat(),
                    "overdue": next_review < now,
                    "retrievability": round(
                        self.curve.retrievability(item, now), 3
                    ),
                    "success_rate": round(
                        self._success_rate(item), 3
                    ),
                    "kind": item.kind.value,
                }
            )
        forecast.sort(key=lambda entry: entry["due_at"])
        return forecast

    def memory_status(self, now: datetime | None = None) -> dict:
        """Return a compact memory-health snapshot.

        Gives agents the same numbers a human would check: how many
        memories (by kind), average strength/importance, how many are due
        right now, and how many conflicts exist.
        """
        now = now or utcnow()
        stats = self.backend.stats()
        due = len(
            self.scheduler.due_items(
                self.store.all_active(),
                now=now,
                limit=10**6,
            )
        )
        conflicts = len(self.consolidator.detect_conflicts())
        return {
            "stats": stats,
            "due_now": due,
            "conflicts": conflicts,
        }

    def review_batch(
        self,
        answers: list[dict],
        now: datetime | None = None,
    ) -> dict:
        """Apply a batch of spaced-repetition outcomes.

        Each answer is ``{"id": memory_id, "success": bool}``; results are
        aggregated with the adaptive scheduler state (review streak, next
        review time) so agents can drive review loops in bulk (Smolen et
        al., 2016).
        """
        now = now or utcnow()
        details = []
        for answer in answers:
            item = self.review(
                answer["id"],
                success=bool(answer.get("success", False)),
                now=now,
            )
            if item is None:
                continue
            next_review = self.scheduler.next_review_at(item, now)
            details.append(
                {
                    "id": item.id,
                    "success": bool(answer.get("success", False)),
                    "review_streak": item.review_streak,
                    "retrievability": round(
                        self.curve.retrievability(item, now), 3
                    ),
                    "next_review_at": next_review.isoformat(),
                    "retry_hours": round(
                        (next_review - now).total_seconds() / 3600.0, 1
                    ),
                }
            )
        successes = sum(1 for d in details if d["success"])
        return {
            "n": len(details),
            "successes": successes,
            "failures": len(details) - successes,
            "success_rate": round(
                successes / len(details), 3
            ) if details else 0.0,
            "details": details,
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
            "intents": [dict(r) for r in self._intents.values()],
            "suppressed_ids": dict(self._suppressed_ids),
        }

    def import_memories(self, payload: dict) -> int:
        """Import memories from an export payload (round 106).

        Rebuilds each MemoryItem from its dict and adds it back into the
        store with cues and associations. Ids are preserved for portability;
        importing the same payload twice creates duplicates.
        """

        imported = 0
        for data in payload.get("memories", []):
            item = MemoryItem.from_dict(data)
            self.backend.add(item)
            self.backend.add_cues(item.id, item.cues)
            self.associations.index(item)
            self.associations.link_related(item)
            imported += 1
        for record in payload.get("intents", []):
            record = dict(record)
            if record.get("id"):
                self._intents[record["id"]] = record
        for memory_id, suppressed_at in payload.get(
            "suppressed_ids", {}
        ).items():
            if self.backend.get(memory_id) is not None:
                self._suppressed_ids[memory_id] = suppressed_at
        return imported

    def practice_session(
        self,
        answers: list[dict],
        limit: int = 5,
        now: datetime | None = None,
    ) -> dict:
        """Run one complete practice session: plan + scored report.

        Returns the coming session's plan and the report for the answers
        just processed (difficulty, next-review suggestions), so agents
        can run a full review loop in one call.
        """
        now = now or utcnow()
        plan = self.practice_plan(limit=limit, now=now)
        report = self.practice_report(answers, now=now)
        return {"plan": plan, "report": report}

    def sleep_and_plan(
        self,
        days: int = 7,
        now: datetime | None = None,
        summarizer=None,
    ) -> dict:
        """Sleep consolidation + refreshed review plan in one call.

        Runs the full sleep cycle, then returns the consolidation summary,
        how many weak-important traces were replayed, and the refreshed
        practice plan/forecast (Stickgold & Walker, 2013; Smolen et al.,
        2016).
        """
        now = now or utcnow()
        report = self.sleep(now=now, summarizer=summarizer)
        plan = self.practice_plan(limit=10, now=now)
        forecast = self.practice_forecast(days=days, now=now)
        return {
            "sleep_summary": report.summary(),
            "weak_replayed": report.weak_replayed,
            "plan": plan,
            "forecast": forecast,
        }

    def memory_audit(self, now: datetime | None = None) -> dict:
        """Deep lifecycle audit beyond the quick status snapshot.

        Adds recycled count, revised traces, emotional traces, average
        retrievability, due and conflict counts - the numbers a maintainer
        would review before deciding what to keep, fix or rehearse.
        """
        now = now or utcnow()
        stats = self.backend.stats()
        items = self.store.all_active()
        retrievabilities = [
            self.curve.retrievability(item, now) for item in items
        ]
        recycled = len(
            self.backend.list(status=MemoryStatus.RECYCLED)
        )
        return {
            "active": len(items),
            "recycled": recycled,
            "semantic": stats["semantic"],
            "episodic": stats["episodic"],
            "revised": sum(1 for i in items if i.revision_count > 0),
            "emotional": sum(1 for i in items if i.affect),
            "conflicts": len(self.consolidator.detect_conflicts()),
            "due_now": len(
                self.scheduler.due_items(items, now=now, limit=10**6)
            ),
            "avg_retrievability": round(
                sum(retrievabilities) / len(retrievabilities), 3
            ) if retrievabilities else 0.0,
            "avg_importance": stats["avg_importance"],
        }

    def dedupe_memories(self, now: datetime | None = None) -> int:
        """Merge near-duplicate traces on demand.

        Complementary learning systems (McClelland et al., 1995): repeated
        episodes collapse into one strengthened trace. Exposes the sleep
        merge pass as an on-demand maintenance tool.
        """
        now = now or utcnow()
        return self.consolidator._merge_duplicates(now)

    def resolve_conflicts(self, now: datetime | None = None) -> dict:
        """Resolve memory conflicts on demand.

        Runs the same accommodation (lopsided evidence retires the stale
        trace) and REM-style resolution (balanced conflicts lose
        confidence) that sleep uses, without waiting for the sleep cycle
        (Nader et al., 2000 reconsolidation; Walker & Stickgold, 2004).
        """
        now = now or utcnow()
        accommodated = self.consolidator._accommodation_phase(now)
        rem_links, rem_resolved = self.consolidator._rem_phase(now)
        remaining = len(self.consolidator.detect_conflicts())
        return {
            "accommodated": accommodated,
            "rem_resolved": rem_resolved,
            "rem_links": rem_links,
            "remaining": remaining,
        }

    def review_load(
        self,
        days: int = 7,
        now: datetime | None = None,
    ) -> dict:
        """Estimate the upcoming review pressure.

        Returns how many traces are due right now, how many are overdue,
        how many will become due within ``days``, and how many are weak
        (retrievability < 0.3). A weighted load index (overdue x2) tells
        agents whether today needs a bigger quota.
        """

        now = now or utcnow()
        items = self.store.all_active()
        due_now = 0
        overdue = 0
        due_soon = 0
        weak = 0
        horizon = now + timedelta(days=max(1, int(days)))
        for item in items:
            retrievability = self.curve.retrievability(item, now)
            if retrievability < 0.3:
                weak += 1
            next_review = self.scheduler.next_review_at(item, now)
            if next_review <= horizon:
                due_soon += 1
            if next_review < now:
                overdue += 1
            if retrievability < 0.5:
                due_now += 1
        return {
            "due_now": due_now,
            "overdue": overdue,
            "due_within_days": due_soon - overdue,
            "weak": weak,
            "load_index": due_soon + overdue,
        }

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
        for memory_id in memory_ids:
            item = self.backend.get(memory_id)
            if item is None:
                continue
            cues = set(item.cues)
            if action == "add":
                added += len(new_tags - cues)
                cues |= new_tags
            else:
                removed += len(cues & new_tags)
                cues -= new_tags
            item.cues = normalize_cues(list(cues))
            self.backend.update(item)
            self.backend.add_cues(item.id, item.cues)
            updated += 1
        return {"updated": updated, "added": added, "removed": removed}

    def cleanup_preview(
        self,
        now: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Preview which traces the sleep prune pass would recycle.

        Episodic traces that are unimportant, never accessed and old are
        prune candidates. This returns them without deleting anything, so
        agents can review before committing.
        """
        now = now or utcnow()
        preview = []
        for item in self.store.all_active(MemoryKind.EPISODIC):
            age_days = (
                now - item.created_at
            ).total_seconds() / 86400.0
            if (
                item.importance < self.consolidator.prune_importance
                and item.access_count == 0
                and age_days >= self.consolidator.prune_age_days
            ):
                preview.append(
                    {
                        "id": item.id,
                        "preview": item.content[:60],
                        "importance": round(item.importance, 3),
                        "age_days": round(age_days, 1),
                    }
                )
                if len(preview) >= max(1, int(limit)):
                    break
        return preview

    def similarity_report(
        self,
        threshold: float = 0.6,
        limit: int = 20,
    ) -> list[dict]:
        """Find confusable memory pairs by content-token overlap.

        Helps agents spot near-duplicates that dedupe may have missed or
        pairs that need better separation (pattern separation; Yassa &
        Stark, 2011).
        """

        items = self.store.all_active()
        pairs = []
        for i in range(len(items)):
            a = items[i]
            a_terms = set(tokenize(a.content))
            for j in range(i + 1, len(items)):
                b = items[j]
                b_terms = set(tokenize(b.content))
                common = len(a_terms & b_terms)
                denominator = max(1, min(len(a_terms), len(b_terms)))
                overlap = common / denominator
                if overlap >= threshold:
                    pairs.append(
                        {
                            "a_id": a.id,
                            "b_id": b.id,
                            "overlap": round(overlap, 3),
                            "a_preview": a.content[:40],
                            "b_preview": b.content[:40],
                        }
                    )
        pairs.sort(key=lambda p: p["overlap"], reverse=True)
        return pairs[: max(1, int(limit))]

    def association_report(self, limit: int = 10) -> dict:
        """Summarize the memory association network.

        Reports how well memories are interlinked (spreading activation;
        Collins & Loftus, 1975): total links, connected vs isolated
        memories, average degree, and the most-connected memories.
        """
        items = {item.id: item for item in self.store.all_active()}
        links = self.backend.all_links()
        degree: dict[str, int] = {mid: 0 for mid in items}
        unique_pairs: set[frozenset[str]] = set()
        directed = 0
        for src, dst, _weight in links:
            if src in items and dst in items:
                directed += 1
                degree[src] += 1
                degree[dst] += 1
                unique_pairs.add(frozenset((src, dst)))
        connected = sum(1 for d in degree.values() if d > 0)
        top = sorted(
            degree.items(), key=lambda kv: (-kv[1], kv[0])
        )[: max(1, int(limit))]
        top_connected = [
            {
                "id": mid,
                "preview": items[mid].content[:40],
                "link_count": degree[mid],
                "kind": items[mid].kind.value,
            }
            for mid, _count in top
            if degree[mid] > 0
        ]
        return {
            "memory_count": len(items),
            "directed_links": directed,
            "unique_pairs": len(unique_pairs),
            "connected_count": connected,
            "isolated_count": len(items) - connected,
            "avg_links": round(
                sum(degree.values()) / max(1, len(items)), 3
            ),
            "top_connected": top_connected,
        }

    # -- sleep cycle ----------------------------------------------------------

    def sleep(
        self,
        now: datetime | None = None,
        summarizer=None,
    ) -> ConsolidationReport:
        return self.consolidator.sleep(now, summarizer=summarizer)

    def reflect(self, summarizer=None, now: datetime | None = None) -> list[MemoryItem]:
        """Rewrite evidence-backed semantic facts as an abstraction of their
        supporting episodes (reflection; Park et al., 2023)."""
        return self.consolidator.reflect(summarizer, now)

    # -- active forgetting ----------------------------------------------------

    def forget(self, memory_id: str) -> bool:
        return self.recycle.trash(memory_id)

    def restore(self, memory_id: str) -> bool:
        return self.recycle.restore(memory_id)

    def purge(self, before: datetime | None = None, limit: int = 1000) -> int:
        return self.recycle.purge(before=before, limit=limit)

    def review_due(
        self,
        limit: int = 10,
        now: datetime | None = None,
        importance_first: bool = True,
        desirable_difficulty: bool = False,
        difficulty_target: float = 0.45,
        due_threshold: float = 0.5,
    ) -> list[MemoryItem]:
        return self.scheduler.due_items(
            self.store.all_active(),
            now=now,
            limit=limit,
            importance_first=importance_first,
            desirable_difficulty=desirable_difficulty,
            difficulty_target=difficulty_target,
            due_threshold=due_threshold,
        )

    def review(
        self,
        memory_id: str,
        *,
        success: bool,
        now: datetime | None = None,
        confidence_aware: bool = True,
    ) -> MemoryItem | None:
        """Record a spaced-repetition outcome for a memory.

        Spacing effect (Cepeda et al., 2006) + adaptive scheduling (Smolen
        et al., 2016): a successful review extends the streak and grows the
        next interval; a failed review resets the streak so the trace is
        re-presented sooner. Call this from the agent loop whenever the agent
        can judge whether the recalled content was actually correct.

        With ``confidence_aware`` (default on), a successful review of a
        memory the system is *not confident* about keeps the next interval
        shorter (more practice), mirroring the desirable-difficulty benefit:
        low-confidence-but-correct retrievals deserve more rehearsal
        (Bjork & Kroll, 2015; Koriat & Goldsmith, 1996).
        """
        item = self.backend.get(memory_id)
        if item is None:
            return None
        now = now or utcnow()
        self.scheduler.record_outcome(item, success=success, now=now)
        if success:
            self.curve.reinforce_review(item, delta=0.1, now=now)
            if confidence_aware:
                label, _ = self.calibrated_confidence(item, now)
                if label is not ConfidenceLabel.HIGH:
                    # practice sooner: cut the streak gain in half
                    item.review_streak = max(0.0, item.review_streak - 0.5)
        else:
            # failure slightly weakens retrieval strength: the trace was not
            # retrievable, so the forgetting curve reflects it.
            item.strength = max(0.3, item.strength - 0.05)
        self.backend.update(item)
        return item

    def working_set(self, limit: int = 8) -> list[MemoryItem]:
        """Recently used memories, newest first (working memory).

        Atkinson & Shiffrin (1968); CoALA working memory (Sumers et al., 2023):
        the working set is what should be injected into the agent's prompt.
        """
        touched = [
            item
            for item in self.backend.list()
            if item.last_access_at is not None
        ]
        touched.sort(key=lambda item: item.last_access_at, reverse=True)
        return touched[:limit]

    def working_set_budget(
        self,
        *,
        limit: int = 8,
        capacity: int = 7,
        optimal: int = 4,
    ) -> dict:
        """Check whether the working set fits the agent's working memory.

        Working memory is limited to roughly 7±2 chunks (Miller, 1956),
        with a more realistic focus of 4±1 (Cowan, 2001); cognitive load
        theory says overload hurts learning and planning (Sweller, 1988).
        This tool compares the current working set against capacity and
        recommends chunking by topic when overloaded.
        """

        items = self.working_set(limit=max(1, int(limit)))
        count = len(items)
        capacity = max(1, int(capacity))
        optimal = min(max(1, int(optimal)), capacity)
        load_ratio = round(count / capacity, 3)
        if count > capacity:
            verdict = "overloaded"
        elif count > optimal:
            verdict = "optimal"
        else:
            verdict = "underutilized"
        topic_chunks: dict[str, list[str]] = defaultdict(list)
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            topic_chunks[topic].append(item.id)
        chunks = [
            {
                "topic": topic,
                "count": len(memory_ids),
                "memory_ids": memory_ids,
            }
            for topic, memory_ids in topic_chunks.items()
        ]
        chunks.sort(key=lambda chunk: -chunk["count"])
        if verdict == "overloaded":
            advice = (
                "一次装不下：按主题分批（每批不超过 4 条），"
                "先处理最重要的主题，降低认知负荷。"
            )
        elif verdict == "optimal":
            advice = "负载合适：保持当前节奏，先做最重要主题即可。"
        else:
            advice = "负载偏低：可以把最相关的记忆也放进工作集，充分用满。"
        return {
            "count": count,
            "capacity": capacity,
            "optimal": optimal,
            "load_ratio": load_ratio,
            "verdict": verdict,
            "chunks": chunks,
            "advice": advice,
        }

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

    def close(self) -> None:
        if hasattr(self.backend, "close"):
            self.backend.close()


__all__ = ["MemoryEngine"]
