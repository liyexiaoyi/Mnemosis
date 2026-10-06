"""NumPy Top-k parity including its historical unstable tie ordering."""
import os
import unittest
from unittest.mock import patch
import pytest
try:
    import numpy as np
except ImportError:
    if os.environ.get('MNEMOSIS_TEST_NUMPY') == '1':
        raise
    # unittest discovery and pytest both recognize the standard SkipTest.
    raise unittest.SkipTest('optional NumPy is not installed')
from mnemosis.vector_index import VectorIndex
import mnemosis.vector_index as module


def test_cached_unique_top5_sorts_only_selected_candidates():
    n=4096
    scores=np.random.default_rng(42).permutation(np.arange(n,dtype=np.float32))
    matrix=np.column_stack((scores,np.zeros(n,dtype=np.float32)))
    ids=[str(i) for i in range(n)]
    expected=np.argsort(-scores)[:5]
    e=VectorIndex(dim=2)
    try:
        with patch.object(np,'argsort',wraps=np.argsort) as sort:
            actual=e._rerank_matrix(ids,matrix,np.ones(n,dtype=np.float32),[1.,0.],5)
        assert [i for i,_ in actual]==[ids[i] for i in expected]
        assert max(len(c.args[0]) for c in sort.call_args_list)<=5
    finally:e.close()

@pytest.mark.parametrize('dtype',[np.float32,np.float64])
@pytest.mark.parametrize('top_k',[-3,0,1,5,20,1024,4096,5000])
@pytest.mark.parametrize('case',['random','cutoff_tie','selected_tie','all_equal','nan','infinity','signed_zero'])
def test_topk_indices_exactly_match_historical_argsort(dtype,top_k,case):
    scores=np.random.default_rng(20261006).normal(size=4096).astype(dtype)
    if case=='cutoff_tie':
        scores[:24]=10
    elif case=='selected_tie':
        scores[:2]=10
    elif case=='all_equal':scores[:]=1
    elif case=='nan':scores[3]=np.nan
    elif case=='infinity':scores[:2]=[np.inf,-np.inf]
    elif case=='signed_zero':scores[:]=0;scores[::2]=-0.
    expected=np.argsort(-scores)[:top_k]
    actual=module._top_score_indices(np,scores,top_k)
    np.testing.assert_array_equal(actual,expected)

@pytest.mark.parametrize('dtype',[np.float32,np.float64])
@pytest.mark.parametrize('n',[0,1,32,1023])
def test_small_scores_keep_original_sorting(dtype,n):
    scores=np.random.default_rng(43).normal(size=n).astype(dtype)
    np.testing.assert_array_equal(module._top_score_indices(np,scores,5),np.argsort(-scores)[:5])
