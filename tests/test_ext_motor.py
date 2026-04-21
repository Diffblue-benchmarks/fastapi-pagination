"""Tests for fastapi_pagination.ext.motor"""
from __future__ import annotations

import sys
import warnings
from unittest.mock import AsyncMock, MagicMock

import pytest

# motor is not installed in test env; mock the module before import
if "motor" not in sys.modules:
    _motor_mock = MagicMock()
    sys.modules["motor"] = _motor_mock
    sys.modules["motor.core"] = _motor_mock.core

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from fastapi_pagination.ext.motor import (
        apaginate,
        apaginate_aggregate,
        paginate,
        paginate_aggregate,
    )

from fastapi_pagination.api import set_page
from fastapi_pagination.default import Page, Params


def _make_cursor(items: list) -> MagicMock:
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=items)
    cursor.sort = MagicMock(return_value=cursor)
    return cursor


def _make_collection(
    total: int = 0,
    find_items: list | None = None,
    aggregate_result: list | None = None,
) -> MagicMock:
    collection = MagicMock()
    collection.count_documents = AsyncMock(return_value=total)
    collection.find = MagicMock(return_value=_make_cursor(find_items or []))
    collection.aggregate = MagicMock(return_value=_make_cursor(aggregate_result or []))
    return collection


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_basic():
    items = [{"_id": i, "name": f"item{i}"} for i in range(1, 6)]
    collection = _make_collection(total=5, find_items=items)
    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate(collection, params=params)

    assert result.total == 5
    assert result.items == items


@pytest.mark.asyncio
async def test_apaginate_with_query_filter():
    items = [{"_id": 1}]
    collection = _make_collection(total=1, find_items=items)
    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate(collection, query_filter={"active": True}, params=params)

    assert result.total == 1
    assert result.items == items
    collection.count_documents.assert_called_once_with({"active": True})


@pytest.mark.asyncio
async def test_apaginate_empty_result():
    collection = _make_collection(total=0, find_items=[])
    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate(collection, params=params)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_with_sort_tuple():
    items = [{"_id": 2}, {"_id": 1}]
    collection = _make_collection(total=2, find_items=items)
    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate(collection, params=params, sort=("name", -1))

    assert result.items == items
    cursor = collection.find.return_value
    cursor.sort.assert_called_once_with("name", -1)


@pytest.mark.asyncio
async def test_apaginate_with_sort_list():
    items = [{"_id": 1}, {"_id": 2}]
    collection = _make_collection(total=2, find_items=items)
    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate(collection, params=params, sort=[("name", 1)])

    assert result.items == items
    cursor = collection.find.return_value
    cursor.sort.assert_called_once_with([("name", 1)])


@pytest.mark.asyncio
async def test_apaginate_with_transformer():
    items = [{"_id": 1, "val": 10}]
    collection = _make_collection(total=1, find_items=items)
    params = Params(page=1, size=10)

    async def transformer(it):
        return [{"val": doc["val"] * 2} for doc in it]

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate(collection, params=params, transformer=transformer)

    assert result.items == [{"val": 20}]


@pytest.mark.asyncio
async def test_apaginate_second_page():
    items = [{"_id": i} for i in range(11, 21)]
    collection = _make_collection(total=100, find_items=items)
    params = Params(page=2, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate(collection, params=params)

    assert result.total == 100
    assert len(result.items) == 10


# ---------------------------------------------------------------------------
# apaginate_aggregate
# ---------------------------------------------------------------------------


def _make_aggregate_result(data: list, total: int | None = None) -> list:
    if total is None:
        metadata = []
    else:
        metadata = [{"total": total}]
    return [{"data": data, "metadata": metadata}]


@pytest.mark.asyncio
async def test_apaginate_aggregate_basic():
    data = [{"_id": 1}, {"_id": 2}]
    aggregate_result = _make_aggregate_result(data, total=2)
    collection = _make_collection(aggregate_result=aggregate_result)
    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate_aggregate(collection, params=params)

    assert result.total == 2
    assert result.items == data


@pytest.mark.asyncio
async def test_apaginate_aggregate_empty_metadata():
    data = []
    aggregate_result = _make_aggregate_result(data, total=None)
    collection = _make_collection(aggregate_result=aggregate_result)
    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate_aggregate(collection, params=params)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_pipeline():
    data = [{"_id": 1}]
    aggregate_result = _make_aggregate_result(data, total=1)
    collection = _make_collection(aggregate_result=aggregate_result)
    params = Params(page=1, size=10)
    pipeline = [{"$match": {"active": True}}]

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate_aggregate(collection, aggregate_pipeline=pipeline, params=params)

    assert result.total == 1
    assert result.items == data


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_aggregation_filter_end_int():
    data = [{"_id": 1}]
    aggregate_result = _make_aggregate_result(data, total=1)
    collection = _make_collection(aggregate_result=aggregate_result)
    params = Params(page=1, size=5)
    pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate_aggregate(
                collection,
                aggregate_pipeline=pipeline,
                params=params,
                aggregation_filter_end=1,
            )

    assert result.items == data


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_aggregation_filter_end_auto():
    data = [{"_id": 1}]
    aggregate_result = _make_aggregate_result(data, total=1)
    collection = _make_collection(aggregate_result=aggregate_result)
    params = Params(page=1, size=5)
    pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate_aggregate(
                collection,
                aggregate_pipeline=pipeline,
                params=params,
                aggregation_filter_end="auto",
            )

    assert result.items == data


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_pipeline_transformer():
    data = [{"_id": 1}]
    aggregate_result = _make_aggregate_result(data, total=1)
    collection = _make_collection(aggregate_result=aggregate_result)
    params = Params(page=1, size=10)

    captured_pipeline = []

    def pipeline_transformer(pipeline):
        captured_pipeline.extend(pipeline)
        return pipeline

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate_aggregate(
                collection,
                params=params,
                aggregation_pipeline_transformer=pipeline_transformer,
            )

    assert result.items == data
    assert len(captured_pipeline) > 0


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_transformer():
    data = [{"_id": 1, "val": 5}]
    aggregate_result = _make_aggregate_result(data, total=1)
    collection = _make_collection(aggregate_result=aggregate_result)
    params = Params(page=1, size=10)

    async def transformer(it):
        return [{"val": doc["val"] * 3} for doc in it]

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate_aggregate(collection, params=params, transformer=transformer)

    assert result.items == [{"val": 15}]


@pytest.mark.asyncio
async def test_apaginate_aggregate_additional_data():
    data = [{"_id": 1}]
    aggregate_result = _make_aggregate_result(data, total=1)
    collection = _make_collection(aggregate_result=aggregate_result)
    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate_aggregate(
                collection,
                params=params,
                additional_data={},
            )

    assert result.total == 1


# ---------------------------------------------------------------------------
# paginate (delegates to apaginate)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate():
    items = [{"_id": 1, "name": "test"}]
    collection = _make_collection(total=1, find_items=items)
    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(collection, params=params)

    assert result.total == 1
    assert result.items == items


@pytest.mark.asyncio
async def test_paginate_with_query_filter():
    items = [{"_id": 2}]
    collection = _make_collection(total=1, find_items=items)
    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(collection, query_filter={"x": 1}, params=params)

    assert result.total == 1
    assert result.items == items


# ---------------------------------------------------------------------------
# paginate_aggregate (delegates to apaginate_aggregate)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paginate_aggregate_delegates():
    data = [{"_id": 1}]
    aggregate_result = _make_aggregate_result(data, total=1)
    collection = _make_collection(aggregate_result=aggregate_result)
    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate_aggregate(collection, params=params)

    assert result.total == 1
    assert result.items == data


@pytest.mark.asyncio
async def test_paginate_aggregate_with_pipeline():
    data = [{"_id": 3}]
    aggregate_result = _make_aggregate_result(data, total=1)
    collection = _make_collection(aggregate_result=aggregate_result)
    params = Params(page=1, size=10)
    pipeline = [{"$match": {"status": "active"}}]

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate_aggregate(collection, aggregate_pipeline=pipeline, params=params)

    assert result.total == 1
    assert result.items == data
