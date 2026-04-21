import pytest

from fastapi_pagination.ext.utils import (
    generic_query_apply_params,
    get_mongo_pipeline_filter_end,
    len_or_none,
    unwrap_scalars,
    wrap_scalars,
)
from fastapi_pagination.bases import RawParams


# --- len_or_none ---

def test_len_or_none_with_list():
    assert len_or_none([1, 2, 3]) == 3


def test_len_or_none_with_empty_list():
    assert len_or_none([]) == 0


def test_len_or_none_with_string():
    assert len_or_none("hello") == 5


def test_len_or_none_with_no_len():
    assert len_or_none(42) is None


def test_len_or_none_with_none():
    assert len_or_none(None) is None


# --- unwrap_scalars ---

def test_unwrap_scalars_single_item_sequences():
    result = unwrap_scalars([[1], [2], [3]])
    assert result == [1, 2, 3]


def test_unwrap_scalars_multi_item_sequences():
    result = unwrap_scalars([[1, 2], [3, 4]])
    assert result == [[1, 2], [3, 4]]


def test_unwrap_scalars_force_unwrap():
    result = unwrap_scalars([[1, 2], [3, 4]], force_unwrap=True)
    assert result == [1, 3]


def test_unwrap_scalars_mixed():
    result = unwrap_scalars([[1], [2, 3]])
    assert result == [1, [2, 3]]


# --- wrap_scalars ---

def test_wrap_scalars_with_sequences():
    result = wrap_scalars([[1, 2], [3, 4]])
    assert result == [[1, 2], [3, 4]]


def test_wrap_scalars_with_non_sequences():
    result = wrap_scalars([1, 2, 3])
    assert result == [[1], [2], [3]]


def test_wrap_scalars_mixed():
    result = wrap_scalars([[1, 2], 3])
    assert result == [[1, 2], [3]]


# --- generic_query_apply_params ---

class MockQuery:
    def __init__(self):
        self._limit = None
        self._offset = None

    def limit(self, val):
        self._limit = val
        return self

    def offset(self, val):
        self._offset = val
        return self


def test_generic_query_apply_params_both():
    q = MockQuery()
    params = RawParams(limit=10, offset=5)
    result = generic_query_apply_params(q, params)
    assert result._limit == 10
    assert result._offset == 5


def test_generic_query_apply_params_limit_only():
    q = MockQuery()
    params = RawParams(limit=10, offset=None)
    result = generic_query_apply_params(q, params)
    assert result._limit == 10
    assert result._offset is None


def test_generic_query_apply_params_offset_only():
    q = MockQuery()
    params = RawParams(limit=None, offset=5)
    result = generic_query_apply_params(q, params)
    assert result._limit is None
    assert result._offset == 5


def test_generic_query_apply_params_none():
    q = MockQuery()
    params = RawParams(limit=None, offset=None)
    result = generic_query_apply_params(q, params)
    assert result._limit is None
    assert result._offset is None


# --- get_mongo_pipeline_filter_end ---

def test_get_mongo_pipeline_filter_end_empty():
    assert get_mongo_pipeline_filter_end([]) == 0


def test_get_mongo_pipeline_filter_end_all_transform():
    pipeline = [
        {"$project": {"name": 1}},
        {"$addFields": {"x": 1}},
        {"$set": {"y": 2}},
    ]
    assert get_mongo_pipeline_filter_end(pipeline) == 0


def test_get_mongo_pipeline_filter_end_non_transform_at_end():
    pipeline = [
        {"$match": {"status": "active"}},
        {"$project": {"name": 1}},
    ]
    # $project is transform, $match is not; reversed traversal hits $project first (transform),
    # then $match (not transform) -> returns len - 1 = 1
    assert get_mongo_pipeline_filter_end(pipeline) == 1


def test_get_mongo_pipeline_filter_end_non_transform_only():
    pipeline = [
        {"$match": {"status": "active"}},
    ]
    assert get_mongo_pipeline_filter_end(pipeline) == 1


def test_get_mongo_pipeline_filter_end_mixed():
    pipeline = [
        {"$match": {"status": "active"}},
        {"$sort": {"name": 1}},
        {"$project": {"name": 1}},
        {"$addFields": {"x": 1}},
    ]
    # Reversed: $addFields (transform), $project (transform), $sort (not transform) -> index 2 from end
    # len=4, i=2 -> 4-2 = 2
    assert get_mongo_pipeline_filter_end(pipeline) == 2
