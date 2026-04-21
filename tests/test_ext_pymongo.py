from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.pymongo import apaginate, apaginate_aggregate, paginate, paginate_aggregate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_sync_collection(items, total):
    col = MagicMock()
    col.count_documents.return_value = total
    cursor = MagicMock()
    cursor.to_list.return_value = list(items)
    col.find.return_value = cursor
    return col


def make_async_collection(items, total):
    col = MagicMock()
    col.count_documents = AsyncMock(return_value=total)
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=list(items))
    col.find.return_value = cursor
    return col


def make_sync_agg_collection(data, total):
    col = MagicMock()
    cursor = MagicMock()
    cursor.to_list.return_value = [{"data": list(data), "metadata": [{"total": total}]}]
    col.aggregate.return_value = cursor
    return col


def make_async_agg_collection(data, total):
    col = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[{"data": list(data), "metadata": [{"total": total}]}])
    col.aggregate = AsyncMock(return_value=cursor)
    return col


# ---------------------------------------------------------------------------
# paginate
# ---------------------------------------------------------------------------


def test_paginate_returns_page_with_items():
    items = [{"_id": i, "name": f"item{i}"} for i in range(3)]
    col = make_sync_collection(items, total=3)
    params = Params(page=1, size=10)

    result = paginate(col, params=params)

    assert result.total == 3
    assert len(result.items) == 3
    assert result.items == items


def test_paginate_with_query_filter():
    items = [{"_id": 1, "active": True}]
    col = make_sync_collection(items, total=1)
    params = Params(page=1, size=10)

    result = paginate(col, query_filter={"active": True}, params=params)

    col.count_documents.assert_called_once_with({"active": True})
    assert result.total == 1


def test_paginate_none_query_filter_defaults_to_empty_dict():
    items = []
    col = make_sync_collection(items, total=0)
    params = Params(page=1, size=10)

    result = paginate(col, query_filter=None, params=params)

    col.count_documents.assert_called_once_with({})
    assert result.total == 0


def test_paginate_empty_collection():
    col = make_sync_collection([], total=0)
    params = Params(page=1, size=10)

    result = paginate(col, params=params)

    assert result.total == 0
    assert result.items == []


def test_paginate_second_page():
    items = [{"_id": 11}]
    col = make_sync_collection(items, total=11)
    params = Params(page=2, size=10)

    result = paginate(col, params=params)

    assert result.total == 11
    assert result.page == 2


def test_paginate_returns_page_instance():
    col = make_sync_collection([{"_id": 1}], total=1)
    params = Params(page=1, size=10)

    result = paginate(col, params=params)

    assert isinstance(result, Page)


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_returns_page_with_items():
    items = [{"_id": i} for i in range(3)]
    col = make_async_collection(items, total=3)
    params = Params(page=1, size=10)

    result = await apaginate(col, params=params)

    assert result.total == 3
    assert len(result.items) == 3


@pytest.mark.asyncio
async def test_apaginate_with_query_filter():
    items = [{"_id": 1}]
    col = make_async_collection(items, total=1)
    params = Params(page=1, size=10)

    result = await apaginate(col, query_filter={"active": True}, params=params)

    col.count_documents.assert_called_once_with({"active": True})
    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_none_query_filter_defaults_to_empty_dict():
    items = []
    col = make_async_collection(items, total=0)
    params = Params(page=1, size=10)

    result = await apaginate(col, query_filter=None, params=params)

    col.count_documents.assert_called_once_with({})
    assert result.total == 0


@pytest.mark.asyncio
async def test_apaginate_empty_collection():
    col = make_async_collection([], total=0)
    params = Params(page=1, size=10)

    result = await apaginate(col, params=params)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_returns_page_instance():
    col = make_async_collection([{"_id": 1}], total=1)
    params = Params(page=1, size=10)

    result = await apaginate(col, params=params)

    assert isinstance(result, Page)


# ---------------------------------------------------------------------------
# paginate_aggregate
# ---------------------------------------------------------------------------


def test_paginate_aggregate_basic():
    data = [{"_id": 1, "value": 10}]
    col = make_sync_agg_collection(data, total=1)
    params = Params(page=1, size=10)

    result = paginate_aggregate(col, params=params)

    assert result.total == 1
    assert len(result.items) == 1


def test_paginate_aggregate_with_pipeline():
    data = [{"_id": 1}]
    col = make_sync_agg_collection(data, total=1)
    params = Params(page=1, size=10)

    result = paginate_aggregate(col, aggregate_pipeline=[{"$match": {"active": True}}], params=params)

    col.aggregate.assert_called_once()
    assert result.total == 1


def test_paginate_aggregate_empty_metadata_gives_zero_total():
    col = MagicMock()
    cursor = MagicMock()
    cursor.to_list.return_value = [{"data": [], "metadata": []}]
    col.aggregate.return_value = cursor
    params = Params(page=1, size=10)

    result = paginate_aggregate(col, params=params)

    assert result.total == 0
    assert result.items == []


def test_paginate_aggregate_none_pipeline_defaults_to_empty():
    data = [{"_id": 1}]
    col = make_sync_agg_collection(data, total=1)
    params = Params(page=1, size=10)

    result = paginate_aggregate(col, aggregate_pipeline=None, params=params)

    col.aggregate.assert_called_once()
    assert result.total == 1


def test_paginate_aggregate_with_integer_filter_end():
    data = [{"_id": 1}]
    col = make_sync_agg_collection(data, total=1)
    params = Params(page=1, size=10)

    result = paginate_aggregate(
        col,
        aggregate_pipeline=[{"$match": {}}, {"$project": {"name": 1}}],
        aggregation_filter_end=1,
        params=params,
    )

    col.aggregate.assert_called_once()
    assert result.total == 1


def test_paginate_aggregate_with_auto_filter_end():
    data = [{"_id": 1}]
    col = make_sync_agg_collection(data, total=1)
    params = Params(page=1, size=10)

    result = paginate_aggregate(
        col,
        aggregate_pipeline=[{"$match": {}}, {"$project": {"name": 1}}],
        aggregation_filter_end="auto",
        params=params,
    )

    col.aggregate.assert_called_once()
    assert result.total == 1


def test_paginate_aggregate_with_pipeline_transformer():
    data = [{"_id": 1}]
    col = make_sync_agg_collection(data, total=1)
    params = Params(page=1, size=10)

    called = []

    def transform_pipeline(pipeline):
        called.append(pipeline)
        return pipeline

    result = paginate_aggregate(
        col,
        aggregate_pipeline=[{"$match": {"x": 1}}],
        aggregation_pipeline_transformer=transform_pipeline,
        params=params,
    )

    assert len(called) == 1
    assert result.total == 1


def test_paginate_aggregate_multiple_items():
    data = [{"_id": i} for i in range(5)]
    col = make_sync_agg_collection(data, total=5)
    params = Params(page=1, size=10)

    result = paginate_aggregate(col, params=params)

    assert result.total == 5
    assert len(result.items) == 5


# ---------------------------------------------------------------------------
# apaginate_aggregate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_aggregate_basic():
    data = [{"_id": 1}]
    col = make_async_agg_collection(data, total=1)
    params = Params(page=1, size=10)

    result = await apaginate_aggregate(col, params=params)

    assert result.total == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_pipeline():
    data = [{"_id": 1}]
    col = make_async_agg_collection(data, total=1)
    params = Params(page=1, size=10)

    result = await apaginate_aggregate(col, aggregate_pipeline=[{"$match": {"x": 1}}], params=params)

    col.aggregate.assert_called_once()
    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_aggregate_empty_metadata_gives_zero_total():
    col = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[{"data": [], "metadata": []}])
    col.aggregate = AsyncMock(return_value=cursor)
    params = Params(page=1, size=10)

    result = await apaginate_aggregate(col, params=params)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_aggregate_none_pipeline_defaults_to_empty():
    data = [{"_id": 2}]
    col = make_async_agg_collection(data, total=1)
    params = Params(page=1, size=10)

    result = await apaginate_aggregate(col, aggregate_pipeline=None, params=params)

    col.aggregate.assert_called_once()
    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_integer_filter_end():
    data = [{"_id": 1}]
    col = make_async_agg_collection(data, total=1)
    params = Params(page=1, size=10)

    result = await apaginate_aggregate(
        col,
        aggregate_pipeline=[{"$match": {}}, {"$project": {"name": 1}}],
        aggregation_filter_end=1,
        params=params,
    )

    col.aggregate.assert_called_once()
    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_pipeline_transformer():
    data = [{"_id": 1}]
    col = make_async_agg_collection(data, total=1)
    params = Params(page=1, size=10)

    called = []

    def transform_pipeline(pipeline):
        called.append(pipeline)
        return pipeline

    result = await apaginate_aggregate(
        col,
        aggregate_pipeline=[{"$match": {"x": 1}}],
        aggregation_pipeline_transformer=transform_pipeline,
        params=params,
    )

    assert len(called) == 1
    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_aggregate_multiple_items():
    data = [{"_id": i} for i in range(4)]
    col = make_async_agg_collection(data, total=4)
    params = Params(page=1, size=10)

    result = await apaginate_aggregate(col, params=params)

    assert result.total == 4
    assert len(result.items) == 4
