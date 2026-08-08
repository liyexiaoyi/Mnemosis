"""Chinese synonym expansion for recall (round 31, 中文专项优化).

Chinese questions often use different words than the stored memory
("怎么筹备去京都旅游" vs stored "准备去京都旅行"). A small, curated
synonym map expands the query terms so recall matches both sides. The
groups are intentionally conservative (common near-synonyms only) and the
expansion only fires for CJK queries, so English/latin recall is untouched.
"""

from __future__ import annotations

import re


_SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"旅游", "旅行"}),
    frozenset({"准备", "筹备", "安排"}),
    frozenset({"买", "购买", "购置"}),
    frozenset({"花", "花费"}),
    frozenset({"喜欢", "喜爱"}),
    frozenset({"城市", "都市"}),
    frozenset({"颜色", "色彩"}),
    frozenset({"食物", "美食"}),
    frozenset({"运动", "锻炼", "健身"}),
    frozenset({"歌手", "歌星"}),
    frozenset({"搬家", "迁居"}),
    frozenset({"学习", "学会"}),
    frozenset({"开始", "坚持"}),
    frozenset({"餐厅", "饭馆", "饭店"}),
    frozenset({"酒店", "宾馆"}),
    frozenset({"礼物", "礼品"}),
    frozenset({"相机", "照相机"}),
    frozenset({"手机", "电话"}),
    frozenset({"电脑", "计算机"}),
    frozenset({"背包", "书包"}),
    frozenset({"唱歌", "演唱"}),
    frozenset({"画画", "绘画"}),
    frozenset({"跑步", "慢跑"}),
    frozenset({"写字", "书写"}),
    frozenset({"高兴", "开心"}),
    frozenset({"美丽", "漂亮"}),
    frozenset({"便宜", "廉价"}),
    frozenset({"做饭", "做菜", "烹饪"}),
    frozenset({"早晨", "早上"}),
    frozenset({"晚上", "夜晚"}),
    frozenset({"贵", "昂贵"}),
    frozenset({"便宜", "廉价"}),
)

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def has_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text))


def expand_synonyms(terms: set[str]) -> set[str]:
    """Add same-group synonyms for any term already present."""
    if not terms:
        return terms
    out = set(terms)
    for group in _SYNONYM_GROUPS:
        if terms & group:
            out |= group
    return out


__all__ = ["has_cjk", "expand_synonyms"]
