"""Minimum-displacement reranking: independent enumeration and live recall."""
from importlib.util import find_spec
from itertools import combinations
import random
import pytest
from test_candidate_admission import engine, remember, state, attach, SemanticEmbedder, IndexStub, NOW

def choose(primary, semantic, limit=64):
    assert find_spec('mnemosis.rerank_budget') is not None, 'rerank budget model missing'
    from mnemosis.rerank_budget import reserve_semantic
    return reserve_semantic(primary, semantic, limit=limit)

def recall(engine, query, **kwargs):
    try:
        return engine.recall(query, candidate_policy='quota', rerank_policy='semantic_reserve', now=NOW, read_only=True, **kwargs)
    except TypeError as exc:
        if "unexpected keyword argument 'rerank_policy'" in str(exc):
            pytest.fail('live recall does not support semantic reserve')
        raise

def test_disjoint_channels_keep_primary28_and_all_semantic36():
    primary = [f'P{i}' for i in range(64)]
    semantic = [f'D{i}' for i in range(36)]
    out = choose(primary, semantic)
    assert len(out) == 64 and set(primary[:28]) | set(semantic) == set(out)

def test_overlap_never_spends_an_extra_slot():
    primary = [f'P{i}' for i in range(64)]
    semantic = primary[:30] + [f'D{i}' for i in range(6)]
    out = choose(primary, semantic)
    assert len(out) == 64 and set(primary[:58]) | set(semantic) == set(out)

def test_empty_semantic_keeps_exact_primary_order():
    assert choose(['A', 'B'], []) == ('A', 'B')
    assert choose([], []) == ()
    assert choose([], ['A'], 0) == ()

def test_underfilled_primary_is_not_padded_with_unrequested_candidates():
    assert set(choose(['A'], ['B'])) == {'A', 'B'}

def test_small_budget_protects_only_available_semantic_prefix():
    assert set(choose(['P0', 'P1'], ['D0', 'D1', 'D2'], 2)) == {'D0', 'D1'}

def test_enumeration_proves_max_retention_and_priority_ties():
    rng = random.Random(20261007)
    for _ in range(200):
        universe = [str(i) for i in range(8)]
        limit = rng.randrange(7)
        primary = rng.sample(universe, rng.randrange(limit + 1))
        semantic = rng.sample(universe, rng.randrange(7))
        left = primary[:]
        right = semantic[:]
        out = choose(primary, semantic, limit)
        protected = set(semantic[:limit])
        allowed = set(primary) | protected
        feasible = []
        for size in range(min(limit, len(allowed)) + 1):
            for subset in combinations(sorted(allowed), size):
                selected = set(subset)
                if protected <= selected:
                    feasible.append((len(selected & set(primary)), tuple((i in selected for i in primary)), selected))
        optimum = max(((retention, ties) for retention, ties, _ in feasible))
        assert (len(set(out) & set(primary)), tuple((i in out for i in primary))) == optimum
        assert len(out) == len(set(out)) <= limit and protected <= set(out) <= allowed
        assert primary == left and semantic == right
        dropped = len(set(primary) - set(out))
        assert dropped == max(0, len(set(primary) | protected) - limit)

@pytest.mark.parametrize('primary,semantic,limit,error', [(None, [], 64, TypeError), ('A', [], 64, TypeError), (['A', 'A'], [], 64, ValueError), ([], ['A', 'A'], 64, ValueError), ([''], [], 64, ValueError), ([], [1], 64, TypeError), (['A', 'B'], [], 1, ValueError), ([], [], True, TypeError), ([], [], 1.5, TypeError), ([], [], -1, ValueError), ([], [], 65, ValueError), ([], [str(i) for i in range(37)], 64, ValueError)])
def test_invalid_constraints_are_rejected(primary, semantic, limit, error):
    with pytest.raises(error):
        choose(primary, semantic, limit)

@pytest.mark.parametrize('budget', [1, 4, 36, 64, 128])
def test_live_semantic_reserve_is_bounded_and_searches_index_once(engine, budget):
    semantic = [remember(engine, f'jade archive {i}') for i in range(36)]
    for i in range(120):
        remember(engine, f'alpha notice {i}')
    embedder = SemanticEmbedder()
    index = IndexStub([(m.id, 1.0) for m in semantic])
    attach(engine, embedder, index)
    engine.store.dense_rerank_candidates = budget
    before = state(engine)
    result = recall(engine, 'alpha lock')
    texts = [t for batch in embedder.batches for t in batch]
    assert len(texts) == len(set(texts)) <= min(budget, 64)
    assert set((m.content for m in semantic[:min(budget, 36)])) <= set(texts)
    assert index.requests == [100] and embedder.seen == ['alpha lock']
    assert len(result) <= 5 and state(engine) == before

def test_legacy_rerank_flag_keeps_existing_quota_results(engine):
    remember(engine, 'alpha jade room')
    embedder = SemanticEmbedder()
    attach(engine, embedder, IndexStub())
    base = engine.recall('alpha lock', now=NOW, read_only=True, candidate_policy='quota')
    try:
        explicit = engine.recall('alpha lock', now=NOW, read_only=True, candidate_policy='quota', rerank_policy='legacy')
    except TypeError:
        pytest.fail('rerank policy missing')
    raw = lambda rs: [(r.item.id, r.score, r.reasons, r.confident) for r in rs]
    assert raw(base) == raw(explicit)

def test_same_membership_keeps_exact_scores_and_completion(engine):
    remember(engine, 'alpha jade room')
    remember(engine, 'alpha note')
    emb = SemanticEmbedder()
    attach(engine, emb, IndexStub())
    old = engine.recall('alpha lock', now=NOW, read_only=True, candidate_policy='quota')
    new = recall(engine, 'alpha lock')
    raw = lambda rs: [(r.item.id, r.score, r.reasons, r.confident) for r in rs]
    assert raw(old) == raw(new)

@pytest.mark.parametrize('candidate,rerank', [('legacy', 'semantic_reserve'), ('quota', 'bad')])
def test_invalid_rerank_configuration_rejected_before_index(engine, candidate, rerank):
    emb = SemanticEmbedder()
    idx = IndexStub(error=AssertionError('should not search'))
    attach(engine, emb, idx)
    try:
        with pytest.raises(ValueError, match='rerank|quota'):
            engine.recall('alpha', candidate_policy=candidate, rerank_policy=rerank, read_only=True, now=NOW)
    except TypeError:
        pytest.fail('rerank policy validation missing')
    assert not idx.requests
