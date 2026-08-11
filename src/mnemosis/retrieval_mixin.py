"""Retrieval mixin: multi-pass recall, anchors and temporal hints."""

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



class RetrievalMixin:
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
        with self._lock:
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
        with self._lock:
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
    def recall_fused(
        self,
        query: str,
        *,
        kind: MemoryKind | None = None,
        top_k: int = 5,
        now: datetime | None = None,
        pass_k: int = 24,
        rrf_k: int = 60,
        kw_weight: float = 1.0,
        ng_weight: float = 1.0,
        dense_embedder=None,
        dense_weight: float = 1.6,
        vector_index=None,
        recency_weight: float = 0.08,
        cue_weight: float = 0.12,
        date_weight: float = 0.28,
        expansion: bool = True,
    ) -> list[RecallResult]:
        """Fused multi-path recall.

        Combines keyword and character n-gram rankings with reciprocal rank
        fusion, then adds light signals from recency direction, stored cues
        and query date hints (LongMemEval-style time-aware retrieval).
        """
        from .hybrid import fused_recall

        return fused_recall(
            self,
            query,
            kind=kind,
            top_k=top_k,
            now=now,
            pass_k=pass_k,
            rrf_k=rrf_k,
            kw_weight=kw_weight,
            ng_weight=ng_weight,
            dense_embedder=dense_embedder,
            dense_weight=dense_weight,
            vector_index=vector_index,
            recency_weight=recency_weight,
            cue_weight=cue_weight,
            date_weight=date_weight,
            expansion=expansion,
        )
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
            "一个", "那个", "这个", "还有",
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
        with self._lock:
            entries = list(self._recall_log)
        return entries[-max(1, int(limit)):]
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
