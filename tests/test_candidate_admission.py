"""Quota invariants and real recall boundaries for opt-in candidate admission."""
from datetime import datetime, timezone
from importlib.util import find_spec
from pathlib import Path
import random, tempfile
import pytest
from mnemosis import MemoryEngine, MemoryKind, SourceRecord, SourceType
from mnemosis.embedding import Embedder
from mnemosis.vector_index import VectorIndex
NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)

def choose(lexical, dense):
    assert find_spec('mnemosis.candidate_admission') is not None, 'quota admission module is not implemented'
    from mnemosis.candidate_admission import quota_admission
    return quota_admission(lexical, dense)

def recall_quota(engine, query, **kwargs):
    try:
        return engine.recall(query, now=NOW, read_only=True, candidate_policy='quota', **kwargs)
    except TypeError as exc:
        if "unexpected keyword argument 'candidate_policy'" in str(exc):
            pytest.fail('real recall does not implement quota admission')
        raise

class SemanticEmbedder(Embedder):

    def __init__(self):
        self.seen = []
        self.batches = []

    def embed(self, text):
        self.seen.append(text)
        return [1.0, 0.0] if 'jade' in text or text == 'alpha lock' else [-1.0, 0.0]

    def embed_many(self, texts):
        self.batches.append(list(texts))
        return [[1.0, 0.0] if 'jade' in t else [-1.0, 0.0] for t in texts]

class IndexStub:

    def __init__(self, hits=None, error=None):
        self.hits = hits or []
        self.error = error
        self.requests = []

    def search(self, vector, *, top_k):
        self.requests.append(top_k)
        if self.error:
            raise self.error
        return self.hits

    def close(self):
        pass

@pytest.fixture(params=['dict', 'sqlite'])
def engine(request):
    with tempfile.TemporaryDirectory() as tmp:
        e = MemoryEngine(None if request.param == 'dict' else str(Path(tmp) / 'memory.sqlite'), auto_warmup=False)
        yield e
        e.close()

def remember(engine, text, **kwargs):
    return engine.remember(text, source=SourceRecord(SourceType.USER), cues=[], auto_cues=False, auto_context=False, importance=0.5, created_at=NOW, **kwargs)

def state(engine):
    return ([i.to_dict() for i in engine.store.all_active()], sorted(engine.backend.all_links()), engine.get_recall_log(), list(engine.backend._conn.iterdump()) if hasattr(engine.backend, '_conn') else None)

def attach(engine, embedder, index):
    engine.embedder = embedder
    engine.index_embedder = embedder
    engine.vector_index = index

def test_protects_lexical64_and_all_semantic36_at_full_budget():
    lexical = [f'L{i}' for i in range(100)]
    dense = [f'D{i}' for i in range(36)]
    out = choose(lexical, dense)
    assert len(out) == len(set(out)) == 100
    assert set(lexical[:64]) <= set(out) and set(dense) <= set(out)
    assert not set(lexical[64:]) & set(out)

def test_overlap_replenishes_lexical_capacity_without_extra_slots():
    lexical = [f'L{i}' for i in range(100)]
    out = choose(lexical, lexical[:30] + [f'D{i}' for i in range(6)])
    assert len(out) == 100 and set(lexical[:94]) <= set(out)
    assert all((f'D{i}' in out for i in range(6)))

def test_empty_dense_channel_preserves_every_lexical_candidate():
    lexical = [f'L{i}' for i in range(100)]
    assert choose(lexical, []) == tuple(lexical)

def test_empty_lexical_channel_admits_dense_without_fabricated_padding():
    assert choose([], ['D']) == ('D',)
    assert choose([], []) == ()

def test_sequences_are_not_mutated_and_identifiers_are_exact():
    lexical = ['A', 'a']
    dense = ['A', 'é', 'é']
    left = lexical[:]
    right = dense[:]
    assert set(choose(lexical, dense)) == {'A', 'a', 'é', 'é'}
    assert lexical == left and dense == right

@pytest.mark.parametrize('lexical,dense,error', [(None, [], TypeError), ('A', [], TypeError), ((x for x in ['A']), [], TypeError), (['A', 'A'], [], ValueError), ([], ['A', 'A'], ValueError), ([''], [], ValueError), ([' A'], [], ValueError), ([1], [], TypeError), ([f'L{i}' for i in range(101)], [], ValueError), ([], [f'D{i}' for i in range(37)], ValueError)])
def test_invalid_rankings_are_rejected(lexical, dense, error):
    with pytest.raises(error):
        choose(lexical, dense)

def test_budget_and_protected_prefix_hold_for_adversarial_overlaps():
    rng = random.Random(20261006)
    for _ in range(250):
        lexical = [f'I{i}' for i in rng.sample(range(150), rng.randrange(101))]
        dense = [f'I{i}' for i in rng.sample(range(150), rng.randrange(37))]
        out = choose(lexical, dense)
        assert len(out) == min(100, len(set(lexical) | set(dense)))
        assert set(lexical[:64]) | set(dense) <= set(out)
        assert set(out) <= set(lexical) | set(dense)
        assert choose(lexical, dense) == out

def test_independent_semantic_trace_can_bypass_lexical_gate(engine):
    wanted = remember(engine, 'spare instrument lodged in jade cupboard')
    for i in range(120):
        remember(engine, f'alpha notice number {i}')
    embedder = SemanticEmbedder()
    index = VectorIndex(dim=2)
    for item in engine.store.all_active():
        index.add(item.id, embedder.embed(item.content))
    attach(engine, embedder, index)
    before = state(engine)
    index_before = list(index._conn.iterdump())
    legacy = engine.recall('alpha lock', now=NOW, read_only=True)
    assert wanted.id not in {r.item.id for r in legacy}
    embedder.seen.clear()
    embedder.batches.clear()
    quota = recall_quota(engine, 'alpha lock')
    assert wanted.id in {r.item.id for r in quota}
    assert embedder.seen == ['alpha lock']
    assert sum(map(len, embedder.batches)) <= 64
    assert state(engine) == before and list(index._conn.iterdump()) == index_before

def test_same_candidate_set_keeps_scores_reasons_and_completion(engine):
    for text in ['alpha jade room', 'alpha note']:
        remember(engine, text)
    embedder = SemanticEmbedder()
    index = VectorIndex(dim=2)
    for item in engine.store.all_active():
        index.add(item.id, embedder.embed(item.content))
    attach(engine, embedder, index)
    before = state(engine)
    legacy = engine.recall('alpha lock', now=NOW, read_only=True)
    quota = recall_quota(engine, 'alpha lock')
    raw = lambda rs: [(r.item.id, r.score, r.reasons, r.confident) for r in rs]
    assert raw(legacy) == raw(quota) and state(engine) == before

def test_default_never_calls_independent_index(engine):
    remember(engine, 'alpha jade room')
    embedder = SemanticEmbedder()
    index = IndexStub(error=AssertionError('default read index'))
    attach(engine, embedder, index)
    default = engine.recall('alpha lock', now=NOW, read_only=True)
    explicit = engine.recall('alpha lock', now=NOW, read_only=True, candidate_policy='legacy')
    assert [r.item.id for r in default] == [r.item.id for r in explicit] and (not index.requests)

def test_index_boundary_filters_before_admission(engine):
    valid = remember(engine, 'jade valid record', kind=MemoryKind.EPISODIC)
    excluded = remember(engine, 'jade excluded record', kind=MemoryKind.EPISODIC)
    suppressed = remember(engine, 'jade suppressed record', kind=MemoryKind.EPISODIC)
    wrong = remember(engine, 'jade other kind', kind=MemoryKind.SEMANTIC)
    recycled = remember(engine, 'jade recycled record', kind=MemoryKind.EPISODIC)
    engine.forget(recycled.id)
    engine._suppressed_ids[suppressed.id] = 'test'
    embedder = SemanticEmbedder()
    index = IndexStub([(i, 0.9) for i in ['missing', recycled.id, wrong.id, excluded.id, suppressed.id, valid.id, valid.id]])
    attach(engine, embedder, index)
    before = state(engine)
    results = recall_quota(engine, 'alpha lock', kind=MemoryKind.EPISODIC, exclude_ids={excluded.id})
    assert {r.item.id for r in results} == {valid.id}
    assert index.requests == [100] and state(engine) == before

@pytest.mark.parametrize('setup', ['no_index', 'no_embedder', 'different_index_embedder', 'disabled_default_embedder'])
def test_quota_requires_matching_index_configuration(engine, setup):
    remember(engine, 'alpha room')
    embedder = SemanticEmbedder()
    index = IndexStub()
    attach(engine, embedder, index)
    kwargs = {}
    if setup == 'no_index':
        engine.vector_index = None
    elif setup == 'no_embedder':
        engine.embedder = None
    elif setup == 'different_index_embedder':
        engine.index_embedder = SemanticEmbedder()
    else:
        kwargs['use_default_embedder'] = False
    with pytest.raises(ValueError, match='index|embedder'):
        recall_quota(engine, 'alpha lock', **kwargs)
    assert not index.requests

@pytest.mark.parametrize('hits,error', [([('A', float('nan'))], ValueError), ([('A', float('inf'))], ValueError), ([('A', True)], TypeError), ([('A', 'score')], TypeError), ([('A', 0.2, 'extra')], ValueError), ([('', 0.2)], ValueError), ([(str(i), 0.2) for i in range(101)], ValueError)])
def test_malformed_index_hits_are_rejected(engine, hits, error):
    attach(engine, SemanticEmbedder(), IndexStub(hits))
    with pytest.raises(error):
        recall_quota(engine, 'alpha lock')

def test_index_failure_is_not_silently_treated_as_empty(engine):
    attach(engine, SemanticEmbedder(), IndexStub(error=RuntimeError('index offline')))
    with pytest.raises(RuntimeError, match='index offline'):
        recall_quota(engine, 'alpha lock')

@pytest.mark.parametrize('dense_limit', [4, 64, 128])
def test_zero_lexical_hit_respects_initial_and_rerank_budgets(engine, dense_limit):
    for i in range(155):
        remember(engine, f'jade archive {i}')
    embedder = SemanticEmbedder()
    index = VectorIndex(dim=2)
    for item in engine.store.all_active():
        index.add(item.id, embedder.embed(item.content))
    attach(engine, embedder, index)
    engine.store.dense_rerank_candidates = dense_limit
    embedder.seen.clear()
    embedder.batches.clear()
    before = state(engine)
    results = recall_quota(engine, 'unseenword', top_k=5)
    assert len(results) <= 5 and sum(map(len, embedder.batches)) <= min(dense_limit, 64)
    assert embedder.seen == ['unseenword'] and state(engine) == before

def test_unknown_policy_rejected_even_without_candidates(engine):
    with pytest.raises(ValueError, match='candidate_policy'):
        engine.recall('missing', candidate_policy='unknown', now=NOW, read_only=True)

def test_strongest_kind_filter_precedes_order_and_limit(engine):
    from mnemosis.types import MemoryStatus
    wanted = remember(engine, 'episodic target', kind=MemoryKind.EPISODIC)
    remember(engine, 'semantic decoy', kind=MemoryKind.SEMANTIC)
    forgotten = remember(engine, 'inactive target', kind=MemoryKind.EPISODIC)
    engine.forget(forgotten.id)
    before = state(engine)
    found = engine.backend.list_strongest(kind=MemoryKind.EPISODIC, status=MemoryStatus.ACTIVE, limit=1)
    assert [item.id for item in found] == [wanted.id]
    assert engine.backend.list_strongest(kind=MemoryKind.EPISODIC, limit=0) == []
    assert state(engine) == before
