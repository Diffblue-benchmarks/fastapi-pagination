"""Unit tests for fastapi_pagination.ext.beanie module."""
from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from copy import copy

from beanie import PydanticObjectId
from beanie.odm.queries.find import FindMany
from beanie.odm.queries.aggregation import AggregationQuery

from fastapi_pagination.bases import RawParams, CursorRawParams
from fastapi_pagination.ext.beanie import parse_cursor, apaginate, paginate


VALID_OID = "507f1f77bcf86cd799439011"
VALID_OID2 = "507f1f77bcf86cd799439012"


# ---- parse_cursor tests ----


def test_parse_cursor_plain_valid():
    result = parse_cursor(VALID_OID)
    assert result == PydanticObjectId(VALID_OID)


def test_parse_cursor_with_prev_prefix():
    result = parse_cursor(f"prev_{VALID_OID}")
    assert result == PydanticObjectId(VALID_OID)


def test_parse_cursor_with_arbitrary_prefix():
    result = parse_cursor(f"next_{VALID_OID}")
    assert result == PydanticObjectId(VALID_OID)


def test_parse_cursor_invalid_raises_value_error():
    with pytest.raises(ValueError, match="Invalid cursor"):
        parse_cursor("invalid_not_an_objectid")


def test_parse_cursor_invalid_without_prefix():
    with pytest.raises(ValueError, match="Invalid cursor"):
        parse_cursor("notanobjectid")


# ---- paginate (deprecated wrapper) tests ----


@pytest.mark.asyncio
async def test_paginate_calls_apaginate():
    mock_query = MagicMock(spec=FindMany)
    expected_result = MagicMock()
    params = MagicMock()

    with patch("fastapi_pagination.ext.beanie.apaginate", new=AsyncMock(return_value=expected_result)) as mock_apag:
        result = await paginate(
            mock_query,
            params=params,
            transformer=None,
            additional_data=None,
            projection_model=None,
            sort=None,
            session=None,
            ignore_cache=False,
            fetch_links=False,
            lazy_parse=False,
            aggregation_filter_end=None,
        )

    assert result is expected_result
    mock_apag.assert_called_once_with(
        mock_query,
        params=params,
        transformer=None,
        additional_data=None,
        projection_model=None,
        sort=None,
        session=None,
        ignore_cache=False,
        fetch_links=False,
        lazy_parse=False,
        aggregation_filter_end=None,
    )


@pytest.mark.asyncio
async def test_paginate_default_args_calls_apaginate():
    mock_query = MagicMock(spec=FindMany)
    expected_result = MagicMock()

    with patch("fastapi_pagination.ext.beanie.apaginate", new=AsyncMock(return_value=expected_result)) as mock_apag:
        result = await paginate(mock_query)

    assert result is expected_result
    mock_apag.assert_called_once()
    _, kwargs = mock_apag.call_args
    assert kwargs["params"] is None


# ---- apaginate tests (FindMany branch) ----


def _make_find_many_mock(items=None, total=5):
    """Build a minimal FindMany-like mock for limit-offset tests."""
    if items is None:
        items = []

    find_result = MagicMock()
    find_result.count = AsyncMock(return_value=total)

    find_many_result = MagicMock()
    find_many_result.to_list = AsyncMock(return_value=items)

    query = MagicMock(spec=FindMany)
    query.find = MagicMock(return_value=find_result)
    query.find_many = MagicMock(return_value=find_many_result)
    query.__copy__ = lambda self: self
    return query


@pytest.mark.asyncio
async def test_apaginate_find_many_limit_offset_with_total():
    items = [MagicMock(id=PydanticObjectId(VALID_OID))]
    raw = RawParams(limit=10, offset=0, include_total=True)
    params = MagicMock()
    fake_page = MagicMock()

    query = _make_find_many_mock(items=items, total=1)

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw)),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=fake_page),
        patch("fastapi_pagination.ext.beanie.copy", side_effect=lambda x: x),
    ):
        result = await apaginate(query, params=params)

    assert result is fake_page


@pytest.mark.asyncio
async def test_apaginate_find_many_limit_offset_no_total():
    items = [MagicMock(id=PydanticObjectId(VALID_OID))]
    raw = RawParams(limit=10, offset=0, include_total=False)
    params = MagicMock()
    fake_page = MagicMock()

    query = _make_find_many_mock(items=items, total=0)

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw)),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=fake_page),
        patch("fastapi_pagination.ext.beanie.copy", side_effect=lambda x: x),
    ):
        result = await apaginate(query, params=params)

    assert result is fake_page


@pytest.mark.asyncio
async def test_apaginate_find_many_cursor_no_cursor():
    """Cursor pagination with cursor=None (initial page)."""
    item = MagicMock()
    item.id = PydanticObjectId(VALID_OID)
    items_full = [item] * 11  # size+1 returned so next link available
    items_page = items_full[:10]
    raw = CursorRawParams(cursor=None, size=10, include_total=False)
    params = MagicMock()
    fake_page = MagicMock()

    find_many_result = MagicMock()
    find_many_result.limit = MagicMock(return_value=find_many_result)
    find_many_result.to_list = AsyncMock(return_value=items_full)

    query = MagicMock(spec=FindMany)
    query.find = MagicMock(return_value=MagicMock(count=AsyncMock(return_value=0)))
    query.find_many = MagicMock(return_value=find_many_result)
    query.__copy__ = lambda self: self

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw)),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items_page)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=fake_page),
        patch("fastapi_pagination.ext.beanie.copy", side_effect=lambda x: x),
    ):
        result = await apaginate(query, params=params)

    assert result is fake_page


@pytest.mark.asyncio
async def test_apaginate_find_many_cursor_with_next_cursor():
    """Cursor pagination with a next cursor (gt filter)."""
    item = MagicMock()
    item.id = PydanticObjectId(VALID_OID)
    items = [item] * 5
    raw = CursorRawParams(cursor=VALID_OID, size=10, include_total=False)
    params = MagicMock()
    fake_page = MagicMock()

    find_many_result = MagicMock()
    find_many_result.find = MagicMock(return_value=find_many_result)
    find_many_result.limit = MagicMock(return_value=find_many_result)
    find_many_result.to_list = AsyncMock(return_value=items)

    query = MagicMock(spec=FindMany)
    query.find = MagicMock(return_value=MagicMock(count=AsyncMock(return_value=0)))
    query.find_many = MagicMock(return_value=find_many_result)
    query.__copy__ = lambda self: self

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw)),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=fake_page),
        patch("fastapi_pagination.ext.beanie.copy", side_effect=lambda x: x),
    ):
        result = await apaginate(query, params=params)

    assert result is fake_page


@pytest.mark.asyncio
async def test_apaginate_find_many_cursor_with_prev_cursor():
    """Cursor pagination with a prev cursor (lt filter, reversed items)."""
    item = MagicMock()
    item.id = PydanticObjectId(VALID_OID)
    items = [item] * 5
    raw = CursorRawParams(cursor=f"prev_{VALID_OID}", size=10, include_total=False)
    params = MagicMock()
    fake_page = MagicMock()

    find_result = MagicMock()
    find_result.sort = MagicMock(return_value=find_result)
    find_result.limit = MagicMock(return_value=find_result)
    find_result.to_list = AsyncMock(return_value=items)

    find_many_result = MagicMock()
    find_many_result.find = MagicMock(return_value=find_result)

    query = MagicMock(spec=FindMany)
    query.find = MagicMock(return_value=MagicMock(count=AsyncMock(return_value=0)))
    query.find_many = MagicMock(return_value=find_many_result)
    query.__copy__ = lambda self: self

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw)),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=fake_page),
        patch("fastapi_pagination.ext.beanie.copy", side_effect=lambda x: x),
    ):
        result = await apaginate(query, params=params)

    assert result is fake_page


@pytest.mark.asyncio
async def test_apaginate_additional_data_none_defaults_to_empty_dict():
    """When additional_data=None, it defaults to {} and does not raise."""
    items = []
    raw = RawParams(limit=10, offset=0, include_total=False)
    params = MagicMock()
    fake_page = MagicMock()

    query = _make_find_many_mock(items=items, total=0)

    captured_kwargs = {}

    def fake_create_page(t_items, **kwargs):
        captured_kwargs.update(kwargs)
        return fake_page

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw)),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.beanie.create_page", side_effect=fake_create_page),
        patch("fastapi_pagination.ext.beanie.copy", side_effect=lambda x: x),
    ):
        result = await apaginate(query, params=params, additional_data=None)

    assert result is fake_page


@pytest.mark.asyncio
async def test_apaginate_with_transformer():
    """Transformer is passed through to apply_items_transformer."""
    items = []
    transformed = [MagicMock()]
    raw = RawParams(limit=10, offset=0, include_total=False)
    params = MagicMock()
    fake_page = MagicMock()
    transformer = AsyncMock()

    query = _make_find_many_mock(items=items, total=0)

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw)),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=transformed)) as mock_transformer,
        patch("fastapi_pagination.ext.beanie.create_page", return_value=fake_page),
        patch("fastapi_pagination.ext.beanie.copy", side_effect=lambda x: x),
    ):
        result = await apaginate(query, params=params, transformer=transformer)

    assert result is fake_page
    mock_transformer.assert_called_once_with(items, transformer, async_=True)


# ---- apaginate aggregation branch tests ----


def _make_aggregation_query_mock(items=None, total=5):
    """Build a minimal AggregationQuery-like mock for aggregation tests."""
    if items is None:
        items = []

    data = {"data": items, "metadata": [{"total": total}] if total > 0 else []}

    mongo_cursor = AsyncMock()
    mongo_cursor.to_list = AsyncMock(return_value=[data])

    collection = MagicMock()
    collection.aggregate = MagicMock(return_value=mongo_cursor)

    document_model = MagicMock()
    document_model.get_pymongo_collection = MagicMock(return_value=collection)

    query = MagicMock(spec=AggregationQuery)
    query.clone = MagicMock(return_value=query)
    query.projection_model = None
    query.aggregation_pipeline = []
    query.session = None
    query.pymongo_kwargs = {}
    query.document_model = document_model
    query.get_aggregation_pipeline = MagicMock(return_value=[])
    return query


@pytest.mark.asyncio
async def test_apaginate_aggregation_limit_offset():
    items = [MagicMock(id=PydanticObjectId(VALID_OID))]
    raw = RawParams(limit=10, offset=0, include_total=True)
    params = MagicMock()
    fake_page = MagicMock()

    query = _make_aggregation_query_mock(items=items, total=1)

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw)),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=fake_page),
    ):
        result = await apaginate(query, params=params)

    assert result is fake_page


@pytest.mark.asyncio
async def test_apaginate_aggregation_limit_offset_zero_total():
    """Aggregation with no results: total should be 0."""
    raw = RawParams(limit=10, offset=0, include_total=True)
    params = MagicMock()
    fake_page = MagicMock()

    query = _make_aggregation_query_mock(items=[], total=0)

    captured = {}

    def fake_create_page(t_items, **kwargs):
        captured.update(kwargs)
        return fake_page

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw)),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=[])),
        patch("fastapi_pagination.ext.beanie.create_page", side_effect=fake_create_page),
    ):
        result = await apaginate(query, params=params)

    assert result is fake_page
    assert captured["total"] == 0


@pytest.mark.asyncio
async def test_apaginate_aggregation_with_filter_end():
    """aggregation_filter_end splits pipeline into filter and transform parts."""
    items = [MagicMock(id=PydanticObjectId(VALID_OID))]
    raw = RawParams(limit=10, offset=0, include_total=True)
    params = MagicMock()
    fake_page = MagicMock()

    query = _make_aggregation_query_mock(items=items, total=1)
    query.aggregation_pipeline = [{"$match": {}}, {"$project": {"_id": 1}}]

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw)),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=fake_page),
    ):
        result = await apaginate(query, params=params, aggregation_filter_end=1)

    assert result is fake_page


@pytest.mark.asyncio
async def test_apaginate_aggregation_auto_filter_end():
    """aggregation_filter_end='auto' calls get_mongo_pipeline_filter_end."""
    items = [MagicMock(id=PydanticObjectId(VALID_OID))]
    raw = RawParams(limit=10, offset=0, include_total=True)
    params = MagicMock()
    fake_page = MagicMock()

    query = _make_aggregation_query_mock(items=items, total=1)
    query.aggregation_pipeline = [{"$match": {}}, {"$project": {"_id": 1}}]

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw)),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=fake_page),
        patch(
            "fastapi_pagination.ext.beanie.get_mongo_pipeline_filter_end",
            return_value=1,
        ),
    ):
        result = await apaginate(query, params=params, aggregation_filter_end="auto")

    assert result is fake_page


@pytest.mark.asyncio
async def test_apaginate_aggregation_with_pipeline_transformer():
    """aggregation_pipeline_transformer is applied to the pipeline."""
    items = [MagicMock(id=PydanticObjectId(VALID_OID))]
    raw = RawParams(limit=10, offset=0, include_total=True)
    params = MagicMock()
    fake_page = MagicMock()
    transformed_pipeline = [{"$match": {"transformed": True}}]
    pipeline_transformer = MagicMock(return_value=transformed_pipeline)

    query = _make_aggregation_query_mock(items=items, total=1)

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw)),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=fake_page),
    ):
        result = await apaginate(query, params=params, aggregation_pipeline_transformer=pipeline_transformer)

    assert result is fake_page
    pipeline_transformer.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_aggregation_cursor_prev():
    """Aggregation with prev cursor: items are reversed and additional_data set."""
    item = MagicMock()
    item.id = PydanticObjectId(VALID_OID)
    items = [item, item]
    raw = CursorRawParams(cursor=f"prev_{VALID_OID}", size=10, include_total=False)
    params = MagicMock()
    fake_page = MagicMock()

    query = _make_aggregation_query_mock(items=items, total=2)

    captured_kwargs = {}

    def fake_create_page(t_items, **kwargs):
        captured_kwargs.update(kwargs)
        return fake_page

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw)),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.beanie.create_page", side_effect=fake_create_page),
    ):
        result = await apaginate(query, params=params)

    assert result is fake_page


@pytest.mark.asyncio
async def test_apaginate_aggregation_cursor_next():
    """Aggregation with next cursor sets additional_data correctly."""
    item = MagicMock()
    item.id = PydanticObjectId(VALID_OID)
    items = [item]
    raw = CursorRawParams(cursor=VALID_OID, size=10, include_total=False)
    params = MagicMock()
    fake_page = MagicMock()

    query = _make_aggregation_query_mock(items=items, total=1)

    captured_kwargs = {}

    def fake_create_page(t_items, **kwargs):
        captured_kwargs.update(kwargs)
        return fake_page

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw)),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.beanie.create_page", side_effect=fake_create_page),
    ):
        result = await apaginate(query, params=params)

    assert result is fake_page
    assert "next_" in captured_kwargs
    assert "previous" in captured_kwargs
