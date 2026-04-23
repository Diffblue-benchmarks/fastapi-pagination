"""Unit tests for fastapi_pagination.ext.motor."""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock

# motor is an optional dependency not installed in this environment;
# provide a minimal stub so the extension module can be imported.
if "motor" not in sys.modules:
    _motor_stub = MagicMock()
    sys.modules["motor"] = _motor_stub
    sys.modules["motor.core"] = _motor_stub

from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.motor import apaginate, apaginate_aggregate, paginate, paginate_aggregate


def make_cursor(items=None):
    """Return a mock Motor cursor with async to_list and chainable sort."""
    if items is None:
        items = []
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=items)
    cursor.sort = MagicMock(return_value=cursor)
    return cursor


def make_collection(items=None, total=10):
    """Return a mock AgnosticCollection."""
    if items is None:
        items = [{"_id": i} for i in range(3)]
    cursor = make_cursor(items)
    collection = MagicMock()
    collection.count_documents = AsyncMock(return_value=total)
    collection.find = MagicMock(return_value=cursor)
    collection.aggregate = MagicMock(return_value=cursor)
    return collection, cursor


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_returns_page():
    items = [{"_id": 1}, {"_id": 2}]
    collection, cursor = make_collection(items=items, total=10)
    params = Params(page=1, size=10)

    result = await apaginate(collection, params=params)

    assert list(result.items) == items
    assert result.total == 10


@pytest.mark.asyncio
async def test_apaginate_calls_count_documents_and_find():
    items = [{"_id": 1}]
    collection, cursor = make_collection(items=items, total=5)
    params = Params(page=1, size=10)

    await apaginate(collection, params=params)

    collection.count_documents.assert_called_once_with({})
    collection.find.assert_called_once_with({}, skip=0, limit=10)
    cursor.to_list.assert_called_once_with(length=10)


@pytest.mark.asyncio
async def test_apaginate_with_query_filter():
    items = [{"_id": 1}]
    collection, cursor = make_collection(items=items, total=5)
    params = Params(page=1, size=10)
    query_filter = {"active": True}

    await apaginate(collection, query_filter=query_filter, params=params)

    collection.count_documents.assert_called_once_with(query_filter)
    collection.find.assert_called_once_with(query_filter, skip=0, limit=10)


@pytest.mark.asyncio
async def test_apaginate_with_sort_tuple():
    items = [{"_id": 1}]
    collection, cursor = make_collection(items=items, total=1)
    params = Params(page=1, size=10)

    await apaginate(collection, params=params, sort=("name", 1))

    cursor.sort.assert_called_once_with("name", 1)


@pytest.mark.asyncio
async def test_apaginate_with_sort_non_tuple():
    items = [{"_id": 1}]
    collection, cursor = make_collection(items=items, total=1)
    params = Params(page=1, size=10)
    sort_spec = [("name", 1)]

    await apaginate(collection, params=params, sort=sort_spec)

    cursor.sort.assert_called_once_with(sort_spec)


@pytest.mark.asyncio
async def test_apaginate_without_sort():
    items = [{"_id": 1}]
    collection, cursor = make_collection(items=items, total=1)
    params = Params(page=1, size=10)

    await apaginate(collection, params=params)

    cursor.sort.assert_not_called()


@pytest.mark.asyncio
async def test_apaginate_pagination_offset():
    items = [{"_id": 10}, {"_id": 11}]
    collection, cursor = make_collection(items=items, total=20)
    params = Params(page=2, size=10)

    result = await apaginate(collection, params=params)

    collection.find.assert_called_once_with({}, skip=10, limit=10)
    assert list(result.items) == items
    assert result.total == 20


@pytest.mark.asyncio
async def test_apaginate_with_async_transformer():
    items = [{"_id": 1}, {"_id": 2}]
    collection, _ = make_collection(items=items, total=2)
    params = Params(page=1, size=10)

    async def transformer(items):
        return [{"id": item["_id"]} for item in items]

    result = await apaginate(collection, params=params, transformer=transformer)

    assert list(result.items) == [{"id": 1}, {"id": 2}]


@pytest.mark.asyncio
async def test_apaginate_with_empty_items():
    collection, _ = make_collection(items=[], total=0)
    params = Params(page=1, size=10)

    result = await apaginate(collection, params=params)

    assert list(result.items) == []
    assert result.total == 0


# ---------------------------------------------------------------------------
# apaginate_aggregate
# ---------------------------------------------------------------------------


def make_aggregate_collection(items=None, total=10):
    """Return a mock collection for aggregate queries."""
    if items is None:
        items = [{"_id": i} for i in range(3)]
    agg_result = [{"data": items, "metadata": [{"total": total}]}]
    cursor = make_cursor(items=agg_result)
    collection = MagicMock()
    collection.aggregate = MagicMock(return_value=cursor)
    return collection, cursor


@pytest.mark.asyncio
async def test_apaginate_aggregate_basic():
    items = [{"_id": 1}, {"_id": 2}]
    collection, cursor = make_aggregate_collection(items=items, total=5)
    params = Params(page=1, size=10)

    result = await apaginate_aggregate(collection, params=params)

    assert list(result.items) == items
    assert result.total == 5
    cursor.to_list.assert_called_once_with(length=None)


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_pipeline():
    items = [{"_id": 1}]
    collection, cursor = make_aggregate_collection(items=items, total=1)
    params = Params(page=1, size=10)
    pipeline = [{"$match": {"active": True}}]

    await apaginate_aggregate(collection, aggregate_pipeline=pipeline, params=params)

    call_args = collection.aggregate.call_args
    passed_pipeline = call_args[0][0]
    assert {"$match": {"active": True}} in passed_pipeline


@pytest.mark.asyncio
async def test_apaginate_aggregate_empty_metadata_returns_zero_total():
    items = [{"_id": 1}]
    agg_result = [{"data": items, "metadata": []}]
    cursor = make_cursor(items=agg_result)
    collection = MagicMock()
    collection.aggregate = MagicMock(return_value=cursor)
    params = Params(page=1, size=10)

    result = await apaginate_aggregate(collection, params=params)

    assert result.total == 0
    assert list(result.items) == items


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_aggregation_filter_end_int():
    items = [{"_id": 1}]
    collection, cursor = make_aggregate_collection(items=items, total=1)
    params = Params(page=1, size=10)
    pipeline = [{"$match": {"x": 1}}, {"$project": {"name": 1}}]

    await apaginate_aggregate(
        collection,
        aggregate_pipeline=pipeline,
        params=params,
        aggregation_filter_end=1,
    )

    call_args = collection.aggregate.call_args
    passed_pipeline = call_args[0][0]
    # The transform_part ([:1] = [{"$match": ...}]) should be in paginate_data
    # so $facet data should contain it
    facet_stage = next(s for s in passed_pipeline if "$facet" in s)
    assert facet_stage is not None


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_aggregation_filter_end_auto():
    items = [{"_id": 1}]
    collection, cursor = make_aggregate_collection(items=items, total=1)
    params = Params(page=1, size=10)
    pipeline = [{"$match": {"x": 1}}, {"$project": {"name": 1}}]

    result = await apaginate_aggregate(
        collection,
        aggregate_pipeline=pipeline,
        params=params,
        aggregation_filter_end="auto",
    )

    assert list(result.items) == items


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_pipeline_transformer():
    items = [{"_id": 1}]
    collection, cursor = make_aggregate_collection(items=items, total=1)
    params = Params(page=1, size=10)

    transformed_pipelines = []

    def pipeline_transformer(pipeline):
        transformed_pipelines.append(pipeline)
        return pipeline

    await apaginate_aggregate(
        collection,
        params=params,
        aggregation_pipeline_transformer=pipeline_transformer,
    )

    assert len(transformed_pipelines) == 1


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_async_transformer():
    items = [{"_id": 1}, {"_id": 2}]
    collection, _ = make_aggregate_collection(items=items, total=2)
    params = Params(page=1, size=10)

    async def transformer(items):
        return [item["_id"] for item in items]

    result = await apaginate_aggregate(collection, params=params, transformer=transformer)

    assert list(result.items) == [1, 2]


@pytest.mark.asyncio
async def test_apaginate_aggregate_uses_facet_pipeline():
    items = [{"_id": 1}]
    collection, cursor = make_aggregate_collection(items=items, total=1)
    params = Params(page=1, size=10)

    await apaginate_aggregate(collection, params=params)

    call_args = collection.aggregate.call_args
    passed_pipeline = call_args[0][0]
    # pipeline should contain a $facet stage
    facet_stages = [s for s in passed_pipeline if "$facet" in s]
    assert len(facet_stages) == 1
    facet = facet_stages[0]["$facet"]
    assert "metadata" in facet
    assert "data" in facet


@pytest.mark.asyncio
async def test_apaginate_aggregate_pagination_offset():
    items = [{"_id": 10}]
    collection, cursor = make_aggregate_collection(items=items, total=20)
    params = Params(page=2, size=5)

    result = await apaginate_aggregate(collection, params=params)

    call_args = collection.aggregate.call_args
    passed_pipeline = call_args[0][0]
    facet = next(s["$facet"] for s in passed_pipeline if "$facet" in s)
    data_pipeline = facet["data"]
    # Should have $limit (5+5=10) and $skip (5)
    limits = [s["$limit"] for s in data_pipeline if "$limit" in s]
    skips = [s["$skip"] for s in data_pipeline if "$skip" in s]
    assert limits == [10]
    assert skips == [5]


# ---------------------------------------------------------------------------
# paginate (deprecated wrapper around apaginate)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paginate_returns_page():
    items = [{"_id": 1}]
    collection, _ = make_collection(items=items, total=3)
    params = Params(page=1, size=10)

    result = await paginate(collection, params=params)

    assert list(result.items) == items
    assert result.total == 3


@pytest.mark.asyncio
async def test_paginate_with_query_filter():
    items = [{"_id": 5}]
    collection, _ = make_collection(items=items, total=1)
    params = Params(page=1, size=10)
    query_filter = {"status": "active"}

    result = await paginate(collection, query_filter=query_filter, params=params)

    collection.count_documents.assert_called_once_with(query_filter)
    assert list(result.items) == items


# ---------------------------------------------------------------------------
# paginate_aggregate (deprecated wrapper around apaginate_aggregate)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paginate_aggregate_returns_page():
    items = [{"_id": 1}]
    collection, _ = make_aggregate_collection(items=items, total=4)
    params = Params(page=1, size=10)

    result = await paginate_aggregate(collection, params=params)

    assert list(result.items) == items
    assert result.total == 4


@pytest.mark.asyncio
async def test_paginate_aggregate_with_pipeline():
    items = [{"_id": 1}]
    collection, cursor = make_aggregate_collection(items=items, total=1)
    params = Params(page=1, size=10)
    pipeline = [{"$match": {"active": True}}]

    result = await paginate_aggregate(collection, aggregate_pipeline=pipeline, params=params)

    assert list(result.items) == items
    call_args = collection.aggregate.call_args
    passed_pipeline = call_args[0][0]
    assert {"$match": {"active": True}} in passed_pipeline
