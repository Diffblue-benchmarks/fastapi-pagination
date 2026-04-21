import pytest
from unittest.mock import MagicMock

from fastapi_pagination.ext.utils import (
    len_or_none,
    unwrap_scalars,
    wrap_scalars,
    generic_query_apply_params,
    get_mongo_pipeline_filter_end,
)
from fastapi_pagination.bases import RawParams


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


# wrap_scalars tests

def test_wrap_scalars_wraps_non_sequences():
    result = wrap_scalars([1, 2, 3])
    assert result == [[1], [2], [3]]


def test_wrap_scalars_keeps_sequences():
    result = wrap_scalars([[1, 2], [3, 4]])
    assert result == [[1, 2], [3, 4]]


def test_wrap_scalars_mixed():
    result = wrap_scalars([1, [2, 3]])
    assert result == [[1], [2, 3]]


# generic_query_apply_params tests

def test_generic_query_apply_params_with_limit_and_offset():
    query = MagicMock()
    query.limit.return_value = query
    query.offset.return_value = query
    params = RawParams(limit=10, offset=5)
    result = generic_query_apply_params(query, params)
    query.limit.assert_called_once_with(10)
    query.offset.assert_called_once_with(5)
    assert result is query


def test_generic_query_apply_params_with_limit_only():
    query = MagicMock()
    query.limit.return_value = query
    params = RawParams(limit=10, offset=None)
    result = generic_query_apply_params(query, params)
    query.limit.assert_called_once_with(10)
    query.offset.assert_not_called()
    assert result is query


def test_generic_query_apply_params_with_offset_only():
    query = MagicMock()
    query.offset.return_value = query
    params = RawParams(limit=None, offset=5)
    result = generic_query_apply_params(query, params)
    query.limit.assert_not_called()
    query.offset.assert_called_once_with(5)
    assert result is query


def test_generic_query_apply_params_no_limit_no_offset():
    query = MagicMock()
    params = RawParams(limit=None, offset=None)
    result = generic_query_apply_params(query, params)
    query.limit.assert_not_called()
    query.offset.assert_not_called()
    assert result is query


# get_mongo_pipeline_filter_end tests

def test_get_mongo_pipeline_filter_end_empty_pipeline():
    assert get_mongo_pipeline_filter_end([]) == 0


def test_get_mongo_pipeline_filter_end_all_transform_stages():
    pipeline = [
        {"$addFields": {"x": 1}},
        {"$project": {"_id": 0}},
    ]
    assert get_mongo_pipeline_filter_end(pipeline) == 0


def test_get_mongo_pipeline_filter_end_match_at_end():
    pipeline = [
        {"$addFields": {"x": 1}},
        {"$match": {"status": "active"}},
    ]
    assert get_mongo_pipeline_filter_end(pipeline) == 2


def test_get_mongo_pipeline_filter_end_match_in_middle():
    pipeline = [
        {"$match": {"status": "active"}},
        {"$project": {"_id": 0}},
        {"$addFields": {"x": 1}},
    ]
    assert get_mongo_pipeline_filter_end(pipeline) == 1


def test_get_mongo_pipeline_filter_end_only_match():
    pipeline = [{"$match": {"status": "active"}}]
    assert get_mongo_pipeline_filter_end(pipeline) == 1
