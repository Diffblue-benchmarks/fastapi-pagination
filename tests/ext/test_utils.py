import pytest
from unittest.mock import MagicMock

from fastapi_pagination.bases import RawParams
from fastapi_pagination.ext.utils import (
    generic_query_apply_params,
    get_mongo_pipeline_filter_end,
    len_or_none,
    unwrap_scalars,
    wrap_scalars,
)


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


def test_unwrap_scalars_single_element_sequences():
    items = [[1], [2], [3]]
    result = unwrap_scalars(items)
    assert result == [1, 2, 3]


def test_unwrap_scalars_multi_element_sequences():
    items = [[1, 2], [3, 4]]
    result = unwrap_scalars(items)
    assert result == [[1, 2], [3, 4]]


def test_unwrap_scalars_force_unwrap():
    items = [[1, 2], [3, 4]]
    result = unwrap_scalars(items, force_unwrap=True)
    assert result == [1, 3]


def test_unwrap_scalars_mixed():
    items = [[1], [2, 3]]
    result = unwrap_scalars(items)
    assert result == [1, [2, 3]]


def test_wrap_scalars_with_sequences():
    items = [[1, 2], [3, 4]]
    result = wrap_scalars(items)
    assert result == [[1, 2], [3, 4]]


def test_wrap_scalars_with_scalars():
    items = [1, 2, 3]
    result = wrap_scalars(items)
    assert result == [[1], [2], [3]]


def test_wrap_scalars_with_mixed():
    items = [1, [2, 3]]
    result = wrap_scalars(items)
    assert result == [[1], [2, 3]]


def test_generic_query_apply_params_with_limit_and_offset():
    mock_query = MagicMock()
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query

    params = RawParams(limit=10, offset=5)
    result = generic_query_apply_params(mock_query, params)

    mock_query.limit.assert_called_once_with(10)
    mock_query.offset.assert_called_once_with(5)
    assert result == mock_query


def test_generic_query_apply_params_no_limit():
    mock_query = MagicMock()
    mock_query.offset.return_value = mock_query

    params = RawParams(limit=None, offset=5)
    result = generic_query_apply_params(mock_query, params)

    mock_query.limit.assert_not_called()
    mock_query.offset.assert_called_once_with(5)
    assert result == mock_query


def test_generic_query_apply_params_no_offset():
    mock_query = MagicMock()
    mock_query.limit.return_value = mock_query

    params = RawParams(limit=10, offset=None)
    result = generic_query_apply_params(mock_query, params)

    mock_query.limit.assert_called_once_with(10)
    mock_query.offset.assert_not_called()
    assert result == mock_query


def test_generic_query_apply_params_neither():
    mock_query = MagicMock()

    params = RawParams(limit=None, offset=None)
    result = generic_query_apply_params(mock_query, params)

    mock_query.limit.assert_not_called()
    mock_query.offset.assert_not_called()
    assert result == mock_query


def test_get_mongo_pipeline_filter_end_empty_pipeline():
    result = get_mongo_pipeline_filter_end([])
    assert result == 0


def test_get_mongo_pipeline_filter_end_all_transform_stages():
    pipeline = [
        {"$addFields": {"field": 1}},
        {"$project": {"field": 1}},
        {"$set": {"field": 1}},
    ]
    result = get_mongo_pipeline_filter_end(pipeline)
    assert result == 0


def test_get_mongo_pipeline_filter_end_with_filter_stage():
    pipeline = [
        {"$match": {"field": "value"}},
        {"$project": {"field": 1}},
    ]
    result = get_mongo_pipeline_filter_end(pipeline)
    assert result == 1


def test_get_mongo_pipeline_filter_end_filter_at_end():
    pipeline = [
        {"$project": {"field": 1}},
        {"$match": {"field": "value"}},
    ]
    result = get_mongo_pipeline_filter_end(pipeline)
    assert result == 2


def test_get_mongo_pipeline_filter_end_single_non_transform():
    pipeline = [{"$sort": {"field": 1}}]
    result = get_mongo_pipeline_filter_end(pipeline)
    assert result == 1


def test_get_mongo_pipeline_filter_end_transforms_after_filter():
    pipeline = [
        {"$match": {"status": "active"}},
        {"$addFields": {"newField": 1}},
        {"$project": {"field": 1}},
    ]
    result = get_mongo_pipeline_filter_end(pipeline)
    assert result == 1
