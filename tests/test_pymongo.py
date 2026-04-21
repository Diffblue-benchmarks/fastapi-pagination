from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.pymongo import apaginate, apaginate_aggregate, paginate, paginate_aggregate


@pytest.fixture
def params():
    return Params(page=1, size=10)


@pytest.fixture
def sync_collection():
    collection = MagicMock()
    items = [{"_id": i, "name": f"item{i}"} for i in range(3)]
    collection.count_documents.return_value = 3
    collection.find.return_value.to_list.return_value = items
    return collection


@pytest.fixture
def async_collection():
    collection = MagicMock()
    items = [{"_id": i, "name": f"item{i}"} for i in range(3)]
    collection.count_documents = AsyncMock(return_value=3)
    collection.find.return_value.to_list = AsyncMock(return_value=items)
    return collection


@pytest.fixture
def sync_agg_collection():
    collection = MagicMock()
    cursor = MagicMock()
    data = [{"data": [{"_id": 1}, {"_id": 2}], "metadata": [{"total": 2}]}]
    cursor.to_list.return_value = data
    collection.aggregate.return_value = cursor
    return collection


@pytest.fixture
def async_agg_collection():
    collection = MagicMock()
    cursor = MagicMock()
    data = [{"data": [{"_id": 1}, {"_id": 2}], "metadata": [{"total": 2}]}]
    cursor.to_list = AsyncMock(return_value=data)
    collection.aggregate.return_value = cursor
    return collection


def test_paginate_basic(sync_collection, params):
    result = paginate(sync_collection, params=params)
    assert isinstance(result, Page)
    assert result.total == 3
    assert len(result.items) == 3


def test_paginate_query_filter_none_defaults_to_empty(sync_collection, params):
    paginate(sync_collection, query_filter=None, params=params)
    sync_collection.count_documents.assert_called_once_with({})


def test_paginate_with_query_filter(sync_collection, params):
    paginate(sync_collection, query_filter={"active": True}, params=params)
    sync_collection.count_documents.assert_called_once_with({"active": True})


def test_paginate_with_filter_fields(sync_collection, params):
    result = paginate(sync_collection, filter_fields={"name": 1}, params=params)
    assert isinstance(result, Page)
    call_args = sync_collection.find.call_args
    assert call_args[0][1] == {"name": 1}


@pytest.mark.asyncio
async def test_apaginate_basic(async_collection, params):
    result = await apaginate(async_collection, params=params)
    assert isinstance(result, Page)
    assert result.total == 3
    assert len(result.items) == 3


@pytest.mark.asyncio
async def test_apaginate_query_filter_none_defaults_to_empty(async_collection, params):
    await apaginate(async_collection, query_filter=None, params=params)
    async_collection.count_documents.assert_called_once_with({})


@pytest.mark.asyncio
async def test_apaginate_with_query_filter(async_collection, params):
    await apaginate(async_collection, query_filter={"status": "active"}, params=params)
    async_collection.count_documents.assert_called_once_with({"status": "active"})


@pytest.mark.asyncio
async def test_apaginate_with_filter_fields(async_collection, params):
    result = await apaginate(async_collection, filter_fields={"name": 1}, params=params)
    assert isinstance(result, Page)
    call_args = async_collection.find.call_args
    assert call_args[0][1] == {"name": 1}


def test_paginate_aggregate_basic(sync_agg_collection, params):
    result = paginate_aggregate(sync_agg_collection, params=params)
    assert isinstance(result, Page)
    assert result.total == 2
    assert len(result.items) == 2


def test_paginate_aggregate_with_pipeline(sync_agg_collection, params):
    pipeline = [{"$match": {"active": True}}]
    result = paginate_aggregate(sync_agg_collection, aggregate_pipeline=pipeline, params=params)
    assert isinstance(result, Page)
    called_pipeline = sync_agg_collection.aggregate.call_args[0][0]
    assert any("$facet" in stage for stage in called_pipeline)


def test_paginate_aggregate_empty_metadata(params):
    collection = MagicMock()
    cursor = MagicMock()
    cursor.to_list.return_value = [{"data": [], "metadata": []}]
    collection.aggregate.return_value = cursor
    result = paginate_aggregate(collection, params=params)
    assert result.total == 0


def test_paginate_aggregate_with_aggregation_filter_end(params):
    collection = MagicMock()
    cursor = MagicMock()
    data = [{"data": [{"_id": 1}], "metadata": [{"total": 1}]}]
    cursor.to_list.return_value = data
    collection.aggregate.return_value = cursor
    pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]
    result = paginate_aggregate(collection, aggregate_pipeline=pipeline, aggregation_filter_end=1, params=params)
    assert isinstance(result, Page)


def test_paginate_aggregate_with_aggregation_filter_end_auto(params):
    collection = MagicMock()
    cursor = MagicMock()
    data = [{"data": [{"_id": 1}], "metadata": [{"total": 1}]}]
    cursor.to_list.return_value = data
    collection.aggregate.return_value = cursor
    pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]
    result = paginate_aggregate(collection, aggregate_pipeline=pipeline, aggregation_filter_end="auto", params=params)
    assert isinstance(result, Page)


def test_paginate_aggregate_with_pipeline_transformer(sync_agg_collection, params):
    def transformer(pipeline):
        return pipeline

    result = paginate_aggregate(sync_agg_collection, aggregation_pipeline_transformer=transformer, params=params)
    assert isinstance(result, Page)


@pytest.mark.asyncio
async def test_apaginate_aggregate_basic(async_agg_collection, params):
    result = await apaginate_aggregate(async_agg_collection, params=params)
    assert isinstance(result, Page)
    assert result.total == 2
    assert len(result.items) == 2


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_pipeline(async_agg_collection, params):
    pipeline = [{"$match": {"active": True}}]
    result = await apaginate_aggregate(async_agg_collection, aggregate_pipeline=pipeline, params=params)
    assert isinstance(result, Page)
    called_pipeline = async_agg_collection.aggregate.call_args[0][0]
    assert any("$facet" in stage for stage in called_pipeline)


@pytest.mark.asyncio
async def test_apaginate_aggregate_empty_metadata(params):
    collection = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[{"data": [], "metadata": []}])
    collection.aggregate.return_value = cursor
    result = await apaginate_aggregate(collection, params=params)
    assert result.total == 0


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_aggregation_filter_end(params):
    collection = MagicMock()
    cursor = MagicMock()
    data = [{"data": [{"_id": 1}], "metadata": [{"total": 1}]}]
    cursor.to_list = AsyncMock(return_value=data)
    collection.aggregate.return_value = cursor
    pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]
    result = await apaginate_aggregate(collection, aggregate_pipeline=pipeline, aggregation_filter_end=1, params=params)
    assert isinstance(result, Page)


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_aggregation_filter_end_auto(params):
    collection = MagicMock()
    cursor = MagicMock()
    data = [{"data": [{"_id": 1}], "metadata": [{"total": 1}]}]
    cursor.to_list = AsyncMock(return_value=data)
    collection.aggregate.return_value = cursor
    pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]
    result = await apaginate_aggregate(
        collection, aggregate_pipeline=pipeline, aggregation_filter_end="auto", params=params
    )
    assert isinstance(result, Page)


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_pipeline_transformer(async_agg_collection, params):
    def transformer(pipeline):
        return pipeline

    result = await apaginate_aggregate(
        async_agg_collection, aggregation_pipeline_transformer=transformer, params=params
    )
    assert isinstance(result, Page)
