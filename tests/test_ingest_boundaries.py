"""Bulk import graph equivalence, bounded duplicate writes and failure boundaries."""
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from mnemosis import MemoryEngine
from mnemosis.backend import SQLiteBackend
from mnemosis.vector_index import VectorIndex

NOW = datetime(2026, 10, 6, tzinfo=timezone.utc)

def records(n=6):
    return [dict(content=f'needle{i} shared event', cues=['shared'], created_at=NOW,
                 importance=.5) for i in range(n)]

@pytest.mark.parametrize('path', ['dict', 'sqlite'])
@pytest.mark.parametrize('method', ['batch', 'chunked'])
@pytest.mark.parametrize('delta', [-1, 1])
def test_wrong_vector_count_leaves_failed_batch_unwritten(tmp_path, path, method, delta):
    class WrongCount:
        def embed_many(self, texts):
            return [[1., 0., 0.] for _ in range(len(texts) + delta)]
    e = MemoryEngine(str(tmp_path/'mem.sqlite') if path=='sqlite' else None,
                     vector_index=VectorIndex(dim=3), index_embedder=WrongCount(), auto_warmup=False)
    try:
        with pytest.raises(RuntimeError, match='embedder returned'):
            if method=='batch': e.remember_many(records(), auto_cues=False)
            else: e.remember_many_chunked(records(), chunk_size=2, auto_cues=False)
        assert e.backend.count() == 0
        assert e.vector_index.size == 0
    finally: e.close()

@pytest.mark.parametrize('path', ['dict', 'sqlite'])
def test_later_failed_chunk_preserves_prefix_and_suffix_retry(tmp_path, path):
    class Flaky:
        calls = 0
        fail = True
        def embed_many(self, texts):
            self.calls += 1
            n = len(texts)-1 if self.fail and self.calls==2 else len(texts)
            return [[1., 0., 0.] for _ in range(n)]
    embed = Flaky()
    e = MemoryEngine(str(tmp_path/'mem.sqlite') if path=='sqlite' else None,
                     vector_index=VectorIndex(dim=3), index_embedder=embed, auto_warmup=False)
    try:
        with pytest.raises(RuntimeError, match='embedder returned'):
            e.remember_many_chunked(records(), chunk_size=2, auto_cues=False)
        assert e.backend.count()==2
        assert e.vector_index.size==2
        assert not e.associations._batch_pool
        if path=='sqlite':
            assert not e.backend._bulk_terms_index_deferred
            assert e.backend._conn.execute('PRAGMA synchronous').fetchone()[0]==1
        embed.fail=False
        e.remember_many_chunked(records()[2:], chunk_size=2, auto_cues=False)
        assert e.backend.count()==6
        assert e.vector_index.size==6
        assert sorted(i.content for i in e.store.all_active())==sorted(r['content'] for r in records())
        assert e.recall_bm25('needle5',top_k=1)[0].item.content==records()[5]['content']
    finally: e.close()

def test_bulk_links_do_not_stage_identical_reverse_twice():
    b = SQLiteBackend(':memory:')
    try:
        b.begin_bulk_mode()
        b.add_links_many(iter([('a','b',.4),('b','a',.4),('a','b',.9),('b','a',.9),('c','c',1.)]))
        assert b._conn.execute('SELECT COUNT(*) FROM links_bulk').fetchone()[0]==2
        b.end_bulk_mode()
        assert b.link_weight('a','b')==.9
        assert set(b.all_links())=={('a','b',.9),('b','a',.9)}
    finally:
        if b._bulk_terms_index_deferred: b.end_bulk_mode()
        b.close()

def test_incremental_graph_stages_one_row_per_canonical_edge(tmp_path):
    e=MemoryEngine(str(tmp_path/'mem.sqlite'),auto_warmup=False)
    staged=[]
    end=e.backend.end_bulk_mode
    def capture():
        staged.append(e.backend._conn.execute('SELECT COUNT(*) FROM links_bulk').fetchone()[0])
        end()
    try:
        with patch.object(e.backend,'end_bulk_mode',capture):
            e.remember_many_chunked(records(12),chunk_size=12,auto_cues=False,max_links=32)
        actual=e.backend._conn.execute('SELECT COUNT(*) FROM links').fetchone()[0]
        assert actual==66
        assert staged==[actual]
        assert len(e.backend.all_links())==132
    finally:e.close()

def test_cleanup_failure_still_releases_association_pool(tmp_path):
    e=MemoryEngine(str(tmp_path/'mem.sqlite'),auto_warmup=False)
    end=e.backend.end_bulk_mode
    def fail_after_restore():
        end()
        raise RuntimeError('end import failed')
    try:
        with patch.object(e.backend,'end_bulk_mode',fail_after_restore), pytest.raises(RuntimeError,match='end import failed'):
            e.remember_many_chunked(records(),chunk_size=2,auto_cues=False)
        assert e.backend.count()==6
        assert not e.associations._batch_pool
        assert not e.backend._bulk_terms_index_deferred
        assert e.backend._conn.execute('PRAGMA synchronous').fetchone()[0]==1
    finally:e.close()

@pytest.mark.parametrize('bulk', [False, True])
def test_weight_max_distant_duplicates_and_generator_rollback(bulk):
    b=SQLiteBackend(':memory:')
    try:
        if bulk: b.begin_bulk_mode()
        b.add_links_many(iter([('a','b',.2),('x','y',.4),('b','a',.9),('a','b',.1)]))
        def broken():
            yield 'p','q',.8
            yield 'q','p',.8
            raise ValueError('bad link input')
        with pytest.raises(ValueError,match='bad link input'): b.add_links_many(broken())
        if bulk: b.end_bulk_mode()
        assert b.link_weight('a','b')==.9
        assert b.link_weight('x','y')==.4
        assert b.link_weight('p','q')==0
    finally:
        if b._bulk_terms_index_deferred: b.end_bulk_mode()
        b.close()
