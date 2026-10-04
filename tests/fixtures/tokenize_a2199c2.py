"""Frozen tokenization oracle from commit a2199c2; never update to match optimizations."""
import re

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "you", "your",
    "they", "them", "what", "when", "where", "how", "was", "were", "are",
    "have", "has", "had", "will", "would", "can", "could", "should", "about",
    "into", "over", "after", "before", "during", "because", "been", "being",
    "not", "but", "his", "her", "its", "our", "their", "there", "here",
    "then", "than", "also", "very", "just", "only", "some", "such",
    "a", "an", "of", "on", "in", "at", "to", "by", "as", "or", "if",
    "else", "while", "until", "since", "so",
    "which", "who", "whom", "whose", "why", "these", "those",
    "i", "me", "my", "we", "us", "he", "she", "it", "much", "many",
    "more", "most", "less", "few", "own", "same", "other", "each",
}

CJK_STOPWORDS = frozenset(
    "的了是在与和或我你他她它也都有没不就都把被对从到请问说吗呢吧啊呀这那"
    "很真最更又再却曾已什怎么"
)

ZH_DATE_NORMALIZE = True

def tokenize(text: str) -> list[str]:
    """Tokenize for keyword recall.

    Dates and hyphenated compounds stay atomic ("2026-02-01" is one token),
    then latin words (stopword-filtered) + CJK content chars and bigrams.
    Chinese function words/particles are filtered so "请问阿丽最喜欢的颜色
    是什么？" and "阿丽喜欢颜色" match the same memory (zh noise reduction).
    """
    lowered = text.lower()
    tokens: list[str] = []
    compound_pattern = r"[a-z0-9]+(?:[-_][a-z0-9]+)+"
    for token in re.findall(compound_pattern, lowered):
        if token not in STOPWORDS:
            tokens.append(token)
    # Chinese dates "2026年3月1日" also emit the canonical ISO token so
    # "2026-03-01" queries match Chinese-dated memories and vice versa.
    if ZH_DATE_NORMALIZE:
        # Chinese numeral dates: "2026年五月二日" -> "2026-05-02"
        for zh_date in re.findall(
            r"(\d{4})年([一二三四五六七八九十零]+)月"
            r"([一二三四五六七八九十零]+)日",
            lowered,
        ):
            year, zh_m, zh_d = zh_date
            month = _zh_numeral(zh_m)
            day = _zh_numeral(zh_d)
            if 1 <= month <= 12 and 1 <= day <= 31:
                tokens.append(f"{int(year):04d}-{month:02d}-{day:02d}")
                lowered = re.sub(
                    re.escape(zh_date[1] + "月" + zh_date[2] + "日"),
                    " ",
                    lowered,
                    count=1,
                )
        zh_dates = re.findall(
            r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", lowered
        )
        for y, m, d in zh_dates:
            tokens.append(f"{int(y):04d}-{int(m):02d}-{int(d):02d}")
        # Remove the matched Chinese-date spans (年月日 chars) from the CJK
        # stream: the normalized ISO token carries the date, and the bare
        # 年/月/日 chars would otherwise make ANY zh-dated memory match any
        # zh-date query regardless of the actual day.
        lowered = re.sub(
            r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日",
            lambda m: " " * len(m.group(0)),
            lowered,
        )
    # Chinese numeral + money/measure unit: "三百元" also emits "300元",
    # "三本" also emits "3本" (numeric normalization for zh content).
    for zh_num, unit in re.findall(
        r"([一二三四五六七八九十零两]+)(元|块|本|个|台|条|张|件|杯|瓶)",
        lowered,
    ):
        value = _zh_numeral(zh_num)
        if value:
            tokens.append(f"{value}{unit}")
    rest = re.sub(compound_pattern, " ", lowered)
    for word in re.findall(r"[a-z0-9]+", rest):
        if len(word) > 1 and word not in STOPWORDS:
            tokens.append(word)
    cjk = "".join(re.findall(r"[\u4e00-\u9fff]", lowered))
    for ch in cjk:
        if ch not in CJK_STOPWORDS:
            tokens.append(ch)
    for i in range(len(cjk) - 1):
        bigram = cjk[i : i + 2]
        if (
            bigram[0] not in CJK_STOPWORDS
            and bigram[1] not in CJK_STOPWORDS
        ):
            tokens.append(bigram)
    return tokens

def _zh_numeral(text: str) -> int:
    """Convert Chinese numerals (1..99,999,999) to an int.

    Handles 十/百/千/万/亿 and 两 (e.g. 三百 -> 300, 两千五百 -> 2500,
    一万二千 -> 12000, 一亿五千万 -> 150000000). Returns 0 on malformed
    input so callers can safely skip the normalization.
    """
    digits = {
        "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
        "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    }
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000, "亿": 100000000}
    total = 0      # completed 万/亿 sections
    section = 0    # current section value
    number = 0     # pending digit
    for char in text:
        if char in digits:
            number = digits[char]
            continue
        unit = units.get(char)
        if unit is None:
            return 0
        if unit >= 10000:
            section = (section + number) * unit
            total += section
            section = 0
            number = 0
        else:
            section += (number or 1) * unit
            number = 0
    return total + section + number
