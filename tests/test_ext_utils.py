from unittest.mock import MagicMock

import pytest

from fastapi_pagination.ext.utils import (
    generic_query_apply_params,
    get_mongo_pipeline_filter_end,
    len_or_none,
    unwrap_scalars,
    wrap_scalars,
)
from fastapi_pagination.bases import RawParams


# len_or_none


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


# unwrap_scalars


def test_unwrap_scalars_single_element_items():
    items = [[1], [2], [3]]
    result = unwrap_scalars(items)
    assert list(result) == [1, 2, 3]


def test_unwrap_scalars_multi_element_items():
    items = [[1, 2], [3, 4]]
    result = unwrap_scalars(items)
    assert list(result) == [[1, 2], [3, 4]]


def test_unwrap_scalars_force_unwrap():
    items = [[1, 2], [3, 4]]
    result = unwrap_scalars(items, force_unwrap=True)
    assert list(result) == [1, 3]


def test_unwrap_scalars_mixed():
    items = [[1], [2, 3]]
    result = unwrap_scalars(items)
    assert list(result) == [1, [2, 3]]


# wrap_scalars


def test_wrap_scalars_with_sequences():
    items = [[1, 2], [3, 4]]
    result = wrap_scalars(items)
    assert list(result) == [[1, 2], [3, 4]]


def test_wrap_scalars_with_non_sequences():
    items = [1, 2, 3]
    result = wrap_scalars(items)
    assert list(result) == [[1], [2], [3]]


def test_wrap_scalars_mixed():
    items = [[1, 2], 3]
    result = wrap_scalars(items)
    assert list(result) == [[1, 2], [3]]


# generic_query_apply_params


def test_generic_query_apply_params_with_limit_and_offset():
    q = MagicMock()
    q.limit.return_value = q
    q.offset.return_value = q
    params = RawParams(limit=10, offset=5)
    result = generic_query_apply_params(q, params)
    q.limit.assert_called_once_with(10)
    q.offset.assert_called_once_with(5)
    assert result is q


def test_generic_query_apply_params_with_limit_only():
    q = MagicMock()
    q.limit.return_value = q
    params = RawParams(limit=10, offset=None)
    result = generic_query_apply_params(q, params)
    q.limit.assert_called_once_with(10)
    q.offset.assert_not_called()
    assert result is q


def test_generic_query_apply_params_with_offset_only():
    q = MagicMock()
    q.offset.return_value = q
    params = RawParams(limit=None, offset=5)
    result = generic_query_apply_params(q, params)
    q.limit.assert_not_called()
    q.offset.assert_called_once_with(5)
    assert result is q


def test_generic_query_apply_params_with_no_limit_no_offset():
    q = MagicMock()
    params = RawParams(limit=None, offset=None)
    result = generic_query_apply_params(q, params)
    q.limit.assert_not_called()
    q.offset.assert_not_called()
    assert result is q


# get_mongo_pipeline_filter_end


def test_get_mongo_pipeline_filter_end_empty_pipeline():
    assert get_mongo_pipeline_filter_end([]) == 0


def test_get_mongo_pipeline_filter_end_all_transform_stages():
    pipeline = [
        {"$addFields": {"x": 1}},
        {"$project": {"y": 1}},
        {"$set": {"z": 1}},
    ]
    assert get_mongo_pipeline_filter_end(pipeline) == 0


def test_get_mongo_pipeline_filter_end_non_transform_at_end():
    pipeline = [
        {"$match": {"status": "active"}},
    ]
    assert get_mongo_pipeline_filter_end(pipeline) == 1


def test_get_mongo_pipeline_filter_end_non_transform_followed_by_transform():
    pipeline = [
        {"$match": {"status": "active"}},
        {"$project": {"name": 1}},
        {"$set": {"extra": 1}},
    ]
    assert get_mongo_pipeline_filter_end(pipeline) == 1


def test_get_mongo_pipeline_filter_end_multiple_non_transform_stages():
    pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$type"}},
        {"$project": {"name": 1}},
    ]
    assert get_mongo_pipeline_filter_end(pipeline) == 2


def test_get_mongo_pipeline_filter_end_only_non_transform():
    pipeline = [
        {"$match": {"a": 1}},
        {"$group": {"_id": "$b"}},
    ]
    assert get_mongo_pipeline_filter_end(pipeline) == 2
