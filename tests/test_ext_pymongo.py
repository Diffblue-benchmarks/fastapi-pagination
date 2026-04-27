from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from fastapi_pagination import Params
from fastapi_pagination.api import set_params
from fastapi_pagination.ext.pymongo import apaginate, apaginate_aggregate, paginate, paginate_aggregate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_sync_collection(
    count: int = 0,
    items: list[Any] | None = None,
) -> MagicMock:
    """Return a mock pymongo Collection."""
    if items is None:
        items = []
    mock_col = MagicMock()
    mock_col.count_documents.return_value = count
    mock_cursor = MagicMock()
    mock_cursor.to_list.return_value = items
    mock_col.find.return_value = mock_cursor
    return mock_col


def make_async_collection(
    count: int = 0,
    items: list[Any] | None = None,
) -> MagicMock:
    """Return a mock pymongo AsyncCollection."""
    if items is None:
        items = []
    mock_col = MagicMock()
    mock_col.count_documents = AsyncMock(return_value=count)
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=items)
    mock_col.find.return_value = mock_cursor
    return mock_col


def make_aggregate_collection(
    data: list[Any] | None = None,
    metadata: list[Any] | None = None,
) -> MagicMock:
    """Return a sync mock collection suitable for aggregate tests."""
    if data is None:
        data = []
    if metadata is None:
        metadata = [{"total": len(data)}] if data else []
    mock_col = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.to_list.return_value = [{"data": data, "metadata": metadata}]
    mock_col.aggregate.return_value = mock_cursor
    return mock_col


async def make_async_aggregate_collection(
    data: list[Any] | None = None,
    metadata: list[Any] | None = None,
) -> MagicMock:
    """Return an async mock collection suitable for aggregate tests."""
    if data is None:
        data = []
    if metadata is None:
        metadata = [{"total": len(data)}] if data else []
    mock_col = MagicMock()
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[{"data": data, "metadata": metadata}])
    mock_col.aggregate = AsyncMock(return_value=mock_cursor)
    return mock_col


# ---------------------------------------------------------------------------
# paginate tests
# ---------------------------------------------------------------------------


def test_paginate_returns_page_with_items():
    items = [{"name": "alice"}, {"name": "bob"}]
    mock_col = make_sync_collection(count=2, items=items)

    with set_params(Params(page=1, size=10)):
        result = paginate(mock_col)

    assert result.total == 2
    assert result.items == items


def test_paginate_with_none_query_filter_defaults_to_empty_dict():
    """query_filter=None should be treated as {} (line 41)."""
    mock_col = make_sync_collection(count=1, items=[{"x": 1}])

    with set_params(Params(page=1, size=10)):
        result = paginate(mock_col, query_filter=None)

    mock_col.count_documents.assert_called_once_with({})
    assert result.total == 1


def test_paginate_with_explicit_query_filter():
    items = [{"status": "active"}]
    mock_col = make_sync_collection(count=1, items=items)
    query_filter = {"status": "active"}

    with set_params(Params(page=1, size=5)):
        result = paginate(mock_col, query_filter=query_filter)

    mock_col.count_documents.assert_called_once_with(query_filter)
    assert result.total == 1
    assert result.items == items


def test_paginate_with_filter_fields_and_sort():
    items = [{"name": "alice"}]
    mock_col = make_sync_collection(count=1, items=items)
    filter_fields = {"name": 1}
    sort = [("name", 1)]

    with set_params(Params(page=1, size=10)):
        result = paginate(mock_col, filter_fields=filter_fields, sort=sort)

    call_kwargs = mock_col.find.call_args
    assert call_kwargs.kwargs.get("sort") == sort
    assert result.total == 1


def test_paginate_empty_collection():
    mock_col = make_sync_collection(count=0, items=[])

    with set_params(Params(page=1, size=10)):
        result = paginate(mock_col)

    assert result.total == 0
    assert result.items == []


def test_paginate_with_explicit_params():
    items = [{"id": i} for i in range(5)]
    mock_col = make_sync_collection(count=5, items=items)

    result = paginate(mock_col, params=Params(page=1, size=5))

    assert result.total == 5
    assert len(result.items) == 5


# ---------------------------------------------------------------------------
# apaginate tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_returns_page_with_items():
    items = [{"name": "charlie"}]
    mock_col = make_async_collection(count=1, items=items)

    with set_params(Params(page=1, size=10)):
        result = await apaginate(mock_col)

    assert result.total == 1
    assert result.items == items


@pytest.mark.asyncio
async def test_apaginate_with_none_query_filter_defaults_to_empty_dict():
    """query_filter=None should be treated as {} (line 76)."""
    mock_col = make_async_collection(count=0, items=[])

    with set_params(Params(page=1, size=10)):
        result = await apaginate(mock_col, query_filter=None)

    mock_col.count_documents.assert_called_once_with({})
    assert result.total == 0


@pytest.mark.asyncio
async def test_apaginate_with_explicit_query_filter():
    items = [{"active": True}]
    mock_col = make_async_collection(count=1, items=items)
    query_filter = {"active": True}

    with set_params(Params(page=1, size=10)):
        result = await apaginate(mock_col, query_filter=query_filter)

    mock_col.count_documents.assert_called_once_with(query_filter)
    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_with_explicit_params():
    items = [{"id": 1}]
    mock_col = make_async_collection(count=1, items=items)

    result = await apaginate(mock_col, params=Params(page=1, size=10))

    assert result.total == 1
    assert result.items == items


# ---------------------------------------------------------------------------
# paginate_aggregate tests
# ---------------------------------------------------------------------------


def test_paginate_aggregate_basic():
    data = [{"_id": 1, "name": "alice"}]
    mock_col = make_aggregate_collection(data=data)

    with set_params(Params(page=1, size=10)):
        result = paginate_aggregate(mock_col)

    assert result.total == 1
    assert result.items == data


def test_paginate_aggregate_empty_metadata_gives_zero_total():
    """When metadata is empty, total should fall back to 0 (IndexError path)."""
    mock_col = make_aggregate_collection(data=[], metadata=[])

    with set_params(Params(page=1, size=10)):
        result = paginate_aggregate(mock_col)

    assert result.total == 0
    assert result.items == []


def test_paginate_aggregate_with_pipeline():
    data = [{"value": 42}]
    mock_col = make_aggregate_collection(data=data)
    pipeline = [{"$match": {"active": True}}]

    with set_params(Params(page=1, size=10)):
        result = paginate_aggregate(mock_col, aggregate_pipeline=pipeline)

    assert result.total == 1
    assert result.items == data
    # Verify the pipeline was actually passed to aggregate
    passed_pipeline = mock_col.aggregate.call_args[0][0]
    assert any("$facet" in stage for stage in passed_pipeline)


def test_paginate_aggregate_with_none_pipeline():
    """aggregate_pipeline=None should be treated as [] (line 113)."""
    mock_col = make_aggregate_collection(data=[{"x": 1}])

    with set_params(Params(page=1, size=10)):
        result = paginate_aggregate(mock_col, aggregate_pipeline=None)

    assert result.total == 1


def test_paginate_aggregate_with_aggregation_filter_end_integer():
    data = [{"name": "test"}]
    mock_col = make_aggregate_collection(data=data)
    pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]

    with set_params(Params(page=1, size=10)):
        result = paginate_aggregate(mock_col, aggregate_pipeline=pipeline, aggregation_filter_end=1)

    assert result.total == 1
    assert result.items == data


def test_paginate_aggregate_with_aggregation_filter_end_auto():
    data = [{"name": "test"}]
    mock_col = make_aggregate_collection(data=data)
    pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]

    with set_params(Params(page=1, size=10)):
        result = paginate_aggregate(mock_col, aggregate_pipeline=pipeline, aggregation_filter_end="auto")

    assert result.total == 1
    assert result.items == data


def test_paginate_aggregate_with_pipeline_transformer():
    data = [{"name": "transformed"}]
    mock_col = make_aggregate_collection(data=data)

    def my_transformer(pipeline: list) -> list:
        return pipeline

    with set_params(Params(page=1, size=10)):
        result = paginate_aggregate(mock_col, aggregation_pipeline_transformer=my_transformer)

    assert result.total == 1
    assert result.items == data


def test_paginate_aggregate_with_explicit_params():
    data = [{"id": 99}]
    mock_col = make_aggregate_collection(data=data)

    result = paginate_aggregate(mock_col, params=Params(page=1, size=10))

    assert result.total == 1
    assert result.items == data


# ---------------------------------------------------------------------------
# apaginate_aggregate tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_aggregate_basic():
    data = [{"_id": 1, "value": "foo"}]
    mock_col = await make_async_aggregate_collection(data=data)

    with set_params(Params(page=1, size=10)):
        result = await apaginate_aggregate(mock_col)

    assert result.total == 1
    assert result.items == data


@pytest.mark.asyncio
async def test_apaginate_aggregate_empty_metadata_gives_zero_total():
    """When metadata is empty, total should fall back to 0."""
    mock_col = await make_async_aggregate_collection(data=[], metadata=[])

    with set_params(Params(page=1, size=10)):
        result = await apaginate_aggregate(mock_col)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_pipeline():
    data = [{"name": "async_test"}]
    mock_col = await make_async_aggregate_collection(data=data)
    pipeline = [{"$match": {"active": True}}]

    with set_params(Params(page=1, size=10)):
        result = await apaginate_aggregate(mock_col, aggregate_pipeline=pipeline)

    assert result.total == 1
    assert result.items == data


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_none_pipeline():
    """aggregate_pipeline=None should be treated as []."""
    mock_col = await make_async_aggregate_collection(data=[{"x": 2}])

    with set_params(Params(page=1, size=10)):
        result = await apaginate_aggregate(mock_col, aggregate_pipeline=None)

    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_explicit_params():
    data = [{"id": 10}]
    mock_col = await make_async_aggregate_collection(data=data)

    result = await apaginate_aggregate(mock_col, params=Params(page=1, size=10))

    assert result.total == 1
    assert result.items == data


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_aggregation_filter_end_auto():
    data = [{"name": "result"}]
    mock_col = await make_async_aggregate_collection(data=data)
    pipeline = [{"$match": {"status": "ok"}}, {"$project": {"name": 1}}]

    with set_params(Params(page=1, size=10)):
        result = await apaginate_aggregate(mock_col, aggregate_pipeline=pipeline, aggregation_filter_end="auto")

    assert result.total == 1
    assert result.items == data
