import pytest

from fastapi_pagination.bases import RawParams
from fastapi_pagination.ext.utils import (
    generic_query_apply_params,
    get_mongo_pipeline_filter_end,
    len_or_none,
    unwrap_scalars,
    wrap_scalars,
)


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

def test_unwrap_scalars_single_element_items():
    result = unwrap_scalars([[1], [2], [3]])
    assert result == [1, 2, 3]


def test_unwrap_scalars_multi_element_items():
    result = unwrap_scalars([[1, 2], [3, 4]])
    assert result == [[1, 2], [3, 4]]


def test_unwrap_scalars_force_unwrap():
    result = unwrap_scalars([[1, 2], [3, 4]], force_unwrap=True)
    assert result == [1, 3]


def test_unwrap_scalars_empty():
    result = unwrap_scalars([])
    assert result == []


# --- wrap_scalars ---

def test_wrap_scalars_with_lists():
    result = wrap_scalars([[1, 2], [3]])
    assert result == [[1, 2], [3]]


def test_wrap_scalars_with_non_sequence_items():
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

    def limit(self, value):
        self._limit = value
        return self

    def offset(self, value):
        self._offset = value
        return self


def test_generic_query_apply_params_with_limit_and_offset():
    q = MockQuery()
    params = RawParams(limit=10, offset=5)
    result = generic_query_apply_params(q, params)
    assert result._limit == 10
    assert result._offset == 5


def test_generic_query_apply_params_no_limit_no_offset():
    q = MockQuery()
    params = RawParams(limit=None, offset=None)
    result = generic_query_apply_params(q, params)
    assert result._limit is None
    assert result._offset is None


def test_generic_query_apply_params_only_limit():
    q = MockQuery()
    params = RawParams(limit=20, offset=None)
    result = generic_query_apply_params(q, params)
    assert result._limit == 20
    assert result._offset is None


def test_generic_query_apply_params_only_offset():
    q = MockQuery()
    params = RawParams(limit=None, offset=10)
    result = generic_query_apply_params(q, params)
    assert result._limit is None
    assert result._offset == 10


# --- get_mongo_pipeline_filter_end ---

def test_get_mongo_pipeline_filter_end_empty():
    assert get_mongo_pipeline_filter_end([]) == 0


def test_get_mongo_pipeline_filter_end_all_transform_stages():
    pipeline = [
        {"$addFields": {"x": 1}},
        {"$project": {"x": 1}},
    ]
    assert get_mongo_pipeline_filter_end(pipeline) == 0


def test_get_mongo_pipeline_filter_end_non_transform_at_end():
    pipeline = [
        {"$match": {"x": 1}},
        {"$project": {"x": 1}},
    ]
    # $match is not a transform stage, but it's at index 0 (reversed index 1)
    # The last non-transform stage is $match at index 0
    # reversed: [$project (i=0), $match (i=1)]
    # $project is transform, $match is not => return len(pipeline) - 1 = 1
    assert get_mongo_pipeline_filter_end(pipeline) == 1


def test_get_mongo_pipeline_filter_end_non_transform_only():
    pipeline = [
        {"$match": {"x": 1}},
    ]
    assert get_mongo_pipeline_filter_end(pipeline) == 1


def test_get_mongo_pipeline_filter_end_transform_after_non_transform():
    pipeline = [
        {"$project": {"x": 1}},
        {"$match": {"x": 1}},
        {"$addFields": {"y": 2}},
    ]
    # reversed: [$addFields (i=0), $match (i=1), $project (i=2)]
    # $addFields is transform -> continue
    # $match is not transform -> return len(3) - 1 = 2
    assert get_mongo_pipeline_filter_end(pipeline) == 2
