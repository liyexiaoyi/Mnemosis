"""Exact historical token parity and a structural no-useless-scans contract."""
import cProfile
import importlib.util
from pathlib import Path
import random
from unittest.mock import patch
import pytest
from mnemosis import types

spec = importlib.util.spec_from_file_location('tokenize_reference', Path(__file__).parent/'fixtures/tokenize_a2199c2.py')
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)

TEXTS = [
    '', 'Tea tea COFFEE foo-bar_a -- -a _b 2026-10-05',
    '2026年3月1日 2026 年 13 月 00 日 2026年五月二日',
    '2026年五月二日和2027年五月二日，另提五月二日',
    '五月二日 before 2026年五月二日 2026年十三月三十二日',
    '２０２６年０３月０１日 ٢٠٢٦年٣月١日 2026年零月零日',
    '三百元 三本 两千元 二十杯 三 元 五\n本 十张 零个',
    '请问阿丽最喜欢的颜色是什么？阿丽喜欢颜色',
    'a中b文c，的了，是在；foo_bar中文 foo-bar 2-3 x_y_z',
    'İ Σ ΟΣ ẞ K ＡＡ café é 𠮷 😀 \ud800 \x00 Straße',
    '金额10元\t\n第二次，2026\t年\n3 月 1\r日',
    '阿丽喜欢旅行，阿丽喜欢旅行，tea tea tea',
]

@pytest.mark.parametrize('normalize', [True, False])
def test_matches_frozen_tokens_counts_order_and_dynamic_stopwords(normalize):
    rng = random.Random(20261005)
    fragments = TEXTS + ['零', '二', '十', '年', '月', '日', '元', '本', '台', '-', '_', ' ', '\n', '99', '２０２６', 'İ', '的', '中']
    corpus = TEXTS + [''.join(rng.choices(fragments, k=rng.randrange(1, 12))) for _ in range(1500)]
    for stopwords in (types.STOPWORDS, types.STOPWORDS | {'tea', 'foo-bar_a', '旅行'}):
        for cjk_stopwords in (types.CJK_STOPWORDS, types.CJK_STOPWORDS | {'丽', '中'}):
            with patch.object(types, 'ZH_DATE_NORMALIZE', normalize), patch.object(reference, 'ZH_DATE_NORMALIZE', normalize), patch.object(types, 'STOPWORDS', stopwords), patch.object(reference, 'STOPWORDS', stopwords), patch.object(types, 'CJK_STOPWORDS', cjk_stopwords), patch.object(reference, 'CJK_STOPWORDS', cjk_stopwords):
                for text in corpus:
                    assert types.tokenize(text) == reference.tokenize(text), repr(text)

def test_plain_text_avoids_impossible_compound_and_date_scans():
    text = 'travel tea coffee meeting '*8 + '私教课练腿记录，计划复盘与记忆检索。'
    profile = cProfile.Profile()
    actual = profile.runcall(types.tokenize, text)
    scans = sum(entry.callcount for entry in profile.getstats()
                if isinstance(entry.code, str) and 're.Pattern' in entry.code
                and any(f"'{name}'" in entry.code for name in ('findall','sub','search','match','fullmatch','finditer')))
    assert actual == reference.tokenize(text)
    # Compounds require '-' or '_'; Chinese dates require '年'. Only word,
    # numeral-unit and CJK extraction can match this plain-text input.
    assert scans <= 3, f'{scans} regex scans despite absent required markers'
