from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Inject mock motor modules before importing the module under test
# to handle environments where motor is not installed
if "motor" not in sys.modules:
    motor_mock = MagicMock()
    sys.modules["motor"] = motor_mock
    sys.modules["motor.core"] = MagicMock()

import pytest

from fastapi_pagination import Page, Params, set_page, set_params
from fastapi_pagination.ext.motor import apaginate, apaginate_aggregate, paginate, paginate_aggregate


def make_mock_collection(items=None, total=10):
    if items is None:
        items = [{"_id": i, "name": f"item{i}"} for i in range(3)]

    collection = MagicMock()

    # Mock count_documents as a coroutine
    collection.count_documents = AsyncMock(return_value=total)

    # Mock cursor returned by find
    cursor = MagicMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=items)
    collection.find = MagicMock(return_value=cursor)

    # Mock aggregate cursor
    agg_cursor = MagicMock()
    agg_data = {"data": items, "metadata": [{"total": total}]}
    agg_cursor.to_list = AsyncMock(return_value=[agg_data])
    collection.aggregate = MagicMock(return_value=agg_cursor)

    return collection, cursor


@pytest.fixture
def pagination_ctx():
    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            yield


@pytest.mark.asyncio
async def test_apaginate_basic(pagination_ctx):
    items = [{"_id": 1}, {"_id": 2}]
    collection, _ = make_mock_collection(items=items, total=2)

    result = await apaginate(collection)

    assert result.total == 2
    assert list(result.items) == items
    collection.count_documents.assert_called_once_with({})
    collection.find.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_with_query_filter(pagination_ctx):
    items = [{"_id": 1}]
    collection, _ = make_mock_collection(items=items, total=1)
    query_filter = {"name": "test"}

    result = await apaginate(collection, query_filter=query_filter)

    assert result.total == 1
    collection.count_documents.assert_called_once_with(query_filter)
    collection.find.assert_called_once_with(query_filter, skip=0, limit=10)


@pytest.mark.asyncio
async def test_apaginate_with_sort_tuple(pagination_ctx):
    items = [{"_id": 1}]
    collection, cursor = make_mock_collection(items=items, total=1)
    sort = ("name", 1)

    await apaginate(collection, sort=sort)

    cursor.sort.assert_called_once_with("name", 1)


@pytest.mark.asyncio
async def test_apaginate_with_sort_non_tuple(pagination_ctx):
    items = [{"_id": 1}]
    collection, cursor = make_mock_collection(items=items, total=1)
    sort = [("name", 1)]

    await apaginate(collection, sort=sort)

    cursor.sort.assert_called_once_with(sort)


@pytest.mark.asyncio
async def test_apaginate_with_transformer(pagination_ctx):
    items = [{"_id": 1}]
    collection, _ = make_mock_collection(items=items, total=1)

    async def transformer(items):
        return [{"transformed": True}]

    result = await apaginate(collection, transformer=transformer)

    assert list(result.items) == [{"transformed": True}]


@pytest.mark.asyncio
async def test_apaginate_with_additional_data(pagination_ctx):
    items = [{"_id": 1}]
    collection, _ = make_mock_collection(items=items, total=1)

    result = await apaginate(collection, additional_data={})

    assert result is not None


@pytest.mark.asyncio
async def test_apaginate_aggregate_basic(pagination_ctx):
    items = [{"_id": 1}, {"_id": 2}]
    collection, _ = make_mock_collection(items=items, total=2)

    result = await apaginate_aggregate(collection)

    assert result.total == 2
    assert list(result.items) == items
    collection.aggregate.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_pipeline(pagination_ctx):
    items = [{"_id": 1}]
    collection, _ = make_mock_collection(items=items, total=1)
    pipeline = [{"$match": {"active": True}}]

    result = await apaginate_aggregate(collection, aggregate_pipeline=pipeline)

    assert result.total == 1
    assert list(result.items) == items


@pytest.mark.asyncio
async def test_apaginate_aggregate_empty_metadata(pagination_ctx):
    items = []
    collection = MagicMock()
    agg_data = {"data": items, "metadata": []}
    agg_cursor = MagicMock()
    agg_cursor.to_list = AsyncMock(return_value=[agg_data])
    collection.aggregate = MagicMock(return_value=agg_cursor)

    result = await apaginate_aggregate(collection)

    assert result.total == 0
    assert list(result.items) == []


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_aggregation_filter_end_int(pagination_ctx):
    items = [{"_id": 1}]
    collection, _ = make_mock_collection(items=items, total=1)
    pipeline = [{"$match": {"x": 1}}, {"$project": {"name": 1}}]

    result = await apaginate_aggregate(
        collection,
        aggregate_pipeline=pipeline,
        aggregation_filter_end=1,
    )

    assert result is not None


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_aggregation_filter_end_auto(pagination_ctx):
    items = [{"_id": 1}]
    collection, _ = make_mock_collection(items=items, total=1)
    pipeline = [{"$match": {"x": 1}}, {"$project": {"name": 1}}]

    result = await apaginate_aggregate(
        collection,
        aggregate_pipeline=pipeline,
        aggregation_filter_end="auto",
    )

    assert result is not None


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_pipeline_transformer(pagination_ctx):
    items = [{"_id": 1}]
    collection, _ = make_mock_collection(items=items, total=1)

    def pipeline_transformer(pipeline):
        return pipeline  # identity

    result = await apaginate_aggregate(
        collection,
        aggregation_pipeline_transformer=pipeline_transformer,
    )

    assert result is not None


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_transformer(pagination_ctx):
    items = [{"_id": 1}]
    collection, _ = make_mock_collection(items=items, total=1)

    async def transformer(items):
        return [{"transformed": True}]

    result = await apaginate_aggregate(collection, transformer=transformer)

    assert list(result.items) == [{"transformed": True}]


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate(pagination_ctx):
    items = [{"_id": 1}]
    collection, _ = make_mock_collection(items=items, total=1)

    result = await paginate(collection)

    assert result is not None
    assert result.total == 1


@pytest.mark.asyncio
async def test_paginate_aggregate_delegates_to_apaginate_aggregate(pagination_ctx):
    items = [{"_id": 1}]
    collection, _ = make_mock_collection(items=items, total=1)

    result = await paginate_aggregate(collection)

    assert result is not None
    assert result.total == 1
