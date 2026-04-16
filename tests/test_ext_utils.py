from __future__ import annotations

import pytest

from fastapi_pagination.bases import RawParams
from fastapi_pagination.ext.utils import (
    generic_query_apply_params,
    get_mongo_pipeline_filter_end,
    len_or_none,
    unwrap_scalars,
    wrap_scalars,
)


# len_or_none tests

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


# unwrap_scalars tests

def test_unwrap_scalars_single_element_items():
    result = unwrap_scalars([[1], [2], [3]])
    assert result == [1, 2, 3]


def test_unwrap_scalars_multi_element_items():
    result = unwrap_scalars([[1, 2], [3, 4]])
    assert result == [[1, 2], [3, 4]]


def test_unwrap_scalars_force_unwrap():
    result = unwrap_scalars([[1, 2], [3, 4]], force_unwrap=True)
    assert result == [1, 3]


def test_unwrap_scalars_mixed():
    result = unwrap_scalars([[1], [2, 3]])
    assert result == [1, [2, 3]]


# wrap_scalars tests

def test_wrap_scalars_with_non_sequence():
    result = wrap_scalars([1, 2, 3])
    assert result == [[1], [2], [3]]


def test_wrap_scalars_with_sequence_items():
    result = wrap_scalars([[1, 2], [3]])
    assert result == [[1, 2], [3]]


def test_wrap_scalars_mixed():
    result = wrap_scalars([1, [2, 3]])
    assert result == [[1], [2, 3]]


# generic_query_apply_params tests

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


def test_generic_query_apply_params_with_limit_and_offset():
    q = MockQuery()
    params = RawParams(limit=10, offset=5)
    result = generic_query_apply_params(q, params)

    assert result._limit == 10
    assert result._offset == 5


def test_generic_query_apply_params_limit_none():
    q = MockQuery()
    params = RawParams(limit=None, offset=20)
    result = generic_query_apply_params(q, params)

    assert result._limit is None
    assert result._offset == 20


def test_generic_query_apply_params_offset_none():
    q = MockQuery()
    params = RawParams(limit=5, offset=None)
    result = generic_query_apply_params(q, params)

    assert result._limit == 5
    assert result._offset is None


def test_generic_query_apply_params_both_none():
    q = MockQuery()
    params = RawParams(limit=None, offset=None)
    result = generic_query_apply_params(q, params)

    assert result._limit is None
    assert result._offset is None


# get_mongo_pipeline_filter_end tests

def test_get_mongo_pipeline_filter_end_empty():
    result = get_mongo_pipeline_filter_end([])
    assert result == 0


def test_get_mongo_pipeline_filter_end_all_transform():
    pipeline = [
        {"$project": {"name": 1}},
        {"$addFields": {"x": 1}},
        {"$set": {"y": 2}},
    ]
    result = get_mongo_pipeline_filter_end(pipeline)
    assert result == 0


def test_get_mongo_pipeline_filter_end_non_transform_at_end():
    pipeline = [
        {"$match": {"status": "active"}},
        {"$project": {"name": 1}},
    ]
    result = get_mongo_pipeline_filter_end(pipeline)
    assert result == 1


def test_get_mongo_pipeline_filter_end_non_transform_only():
    pipeline = [
        {"$match": {"status": "active"}},
        {"$sort": {"name": 1}},
    ]
    result = get_mongo_pipeline_filter_end(pipeline)
    assert result == 2


def test_get_mongo_pipeline_filter_end_mixed():
    pipeline = [
        {"$match": {"status": "active"}},
        {"$project": {"name": 1}},
        {"$addFields": {"x": 1}},
    ]
    result = get_mongo_pipeline_filter_end(pipeline)
    assert result == 1
