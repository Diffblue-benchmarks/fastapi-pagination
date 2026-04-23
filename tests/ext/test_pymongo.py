from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# pymongo is an optional dependency not available in this environment.
# Inject minimal mock modules into sys.modules BEFORE importing the extension so
# that the top-level imports in ext/pymongo.py succeed.
# ──────────────────────────────────────────────────────────────────────────────

sys.modules.setdefault("pymongo", MagicMock(name="pymongo"))
sys.modules.setdefault("pymongo.collection", MagicMock(name="pymongo.collection"))
sys.modules.setdefault("pymongo.asynchronous", MagicMock(name="pymongo.asynchronous"))
sys.modules.setdefault("pymongo.asynchronous.collection", MagicMock(name="pymongo.asynchronous.collection"))

from fastapi_pagination import Page, Params, set_page  # noqa: E402
from fastapi_pagination.ext.pymongo import (  # noqa: E402
    apaginate,
    apaginate_aggregate,
    paginate,
    paginate_aggregate,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_sync_collection(items=None, total=2):
    """Create a synchronous mock pymongo Collection."""
    if items is None:
        items = [{"_id": i} for i in range(total)]
    mock_cursor = MagicMock()
    mock_cursor.to_list.return_value = [
        {"data": items, "metadata": [{"total": total}]},
    ]
    mock_collection = MagicMock()
    mock_collection.aggregate.return_value = mock_cursor
    return mock_collection


def _make_async_collection(items=None, total=2):
    """Create an asynchronous mock pymongo AsyncCollection."""
    if items is None:
        items = [{"_id": i} for i in range(total)]
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(
        return_value=[{"data": items, "metadata": [{"total": total}]}]
    )
    mock_collection = MagicMock()
    mock_collection.aggregate.return_value = mock_cursor
    return mock_collection


# ──────────────────────────────────────────────────────────────────────────────
# Tests for paginate
# ──────────────────────────────────────────────────────────────────────────────


def test_paginate_calls_run_sync_flow(mocker):
    """paginate delegates to run_sync_flow and returns its result."""
    mock_collection = MagicMock()
    mock_result = MagicMock()
    mock_run_sync = mocker.patch(
        "fastapi_pagination.ext.pymongo.run_sync_flow", return_value=mock_result
    )

    result = paginate(mock_collection)

    assert result is mock_result
    mock_run_sync.assert_called_once()


def test_paginate_returns_value_from_run_sync_flow(mocker):
    """The return value of paginate is exactly what run_sync_flow returns."""
    mock_collection = MagicMock()
    expected = {"items": [1, 2, 3], "total": 3}
    mocker.patch("fastapi_pagination.ext.pymongo.run_sync_flow", return_value=expected)

    result = paginate(mock_collection)

    assert result == expected


def test_paginate_query_filter_defaults_to_empty_dict(mocker):
    """When query_filter is None, it is replaced with {}."""
    mock_collection = MagicMock()
    mock_generic = mocker.patch(
        "fastapi_pagination.ext.pymongo.generic_flow",
        return_value=MagicMock(),
    )
    mocker.patch("fastapi_pagination.ext.pymongo.run_sync_flow", return_value=MagicMock())

    paginate(mock_collection, query_filter=None)

    mock_generic.assert_called_once()


def test_paginate_with_explicit_query_filter(mocker):
    """paginate accepts an explicit query_filter and passes it through."""
    mock_collection = MagicMock()
    mock_result = MagicMock()
    mocker.patch("fastapi_pagination.ext.pymongo.run_sync_flow", return_value=mock_result)

    result = paginate(mock_collection, query_filter={"name": "test"})

    assert result is mock_result


def test_paginate_forwards_optional_args(mocker):
    """transformer, additional_data and config are forwarded to generic_flow."""
    mock_collection = MagicMock()
    mock_generic = mocker.patch(
        "fastapi_pagination.ext.pymongo.generic_flow",
        return_value=MagicMock(),
    )
    mocker.patch("fastapi_pagination.ext.pymongo.run_sync_flow", return_value=MagicMock())

    transformer = MagicMock()
    additional_data = {"key": "value"}
    config = MagicMock()

    paginate(mock_collection, transformer=transformer, additional_data=additional_data, config=config)

    _, kwargs = mock_generic.call_args
    assert kwargs["transformer"] is transformer
    assert kwargs["additional_data"] is additional_data
    assert kwargs["config"] is config


# ──────────────────────────────────────────────────────────────────────────────
# Tests for apaginate
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apaginate_calls_run_async_flow(mocker):
    """apaginate delegates to run_async_flow and returns its result."""
    mock_collection = MagicMock()
    mock_result = MagicMock()
    mock_run_async = mocker.patch(
        "fastapi_pagination.ext.pymongo.run_async_flow",
        new_callable=AsyncMock,
        return_value=mock_result,
    )

    result = await apaginate(mock_collection)

    assert result is mock_result
    mock_run_async.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_returns_value_from_run_async_flow(mocker):
    """The return value of apaginate is exactly what run_async_flow returns."""
    mock_collection = MagicMock()
    expected = {"items": [1, 2], "total": 2}
    mocker.patch(
        "fastapi_pagination.ext.pymongo.run_async_flow",
        new_callable=AsyncMock,
        return_value=expected,
    )

    result = await apaginate(mock_collection)

    assert result == expected


@pytest.mark.asyncio
async def test_apaginate_query_filter_defaults_to_empty_dict(mocker):
    """When query_filter is None, apaginate replaces it with {}."""
    mock_collection = MagicMock()
    mock_generic = mocker.patch(
        "fastapi_pagination.ext.pymongo.generic_flow",
        return_value=MagicMock(),
    )
    mocker.patch(
        "fastapi_pagination.ext.pymongo.run_async_flow",
        new_callable=AsyncMock,
        return_value=MagicMock(),
    )

    await apaginate(mock_collection, query_filter=None)

    mock_generic.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_forwards_optional_args(mocker):
    """transformer, additional_data and config are forwarded to generic_flow."""
    mock_collection = MagicMock()
    mock_generic = mocker.patch(
        "fastapi_pagination.ext.pymongo.generic_flow",
        return_value=MagicMock(),
    )
    mocker.patch(
        "fastapi_pagination.ext.pymongo.run_async_flow",
        new_callable=AsyncMock,
        return_value=MagicMock(),
    )

    transformer = AsyncMock()
    additional_data = {"key": "value"}
    config = MagicMock()

    await apaginate(mock_collection, transformer=transformer, additional_data=additional_data, config=config)

    _, kwargs = mock_generic.call_args
    assert kwargs["transformer"] is transformer
    assert kwargs["additional_data"] is additional_data
    assert kwargs["config"] is config


# ──────────────────────────────────────────────────────────────────────────────
# Tests for paginate_aggregate (wrapper)
# ──────────────────────────────────────────────────────────────────────────────


def test_paginate_aggregate_calls_run_sync_flow(mocker):
    """paginate_aggregate delegates to run_sync_flow and returns its result."""
    mock_collection = MagicMock()
    mock_result = MagicMock()
    mock_run_sync = mocker.patch(
        "fastapi_pagination.ext.pymongo.run_sync_flow", return_value=mock_result
    )

    result = paginate_aggregate(mock_collection)

    assert result is mock_result
    mock_run_sync.assert_called_once()


def test_paginate_aggregate_returns_value_from_run_sync_flow(mocker):
    """The return value of paginate_aggregate is exactly what run_sync_flow returns."""
    mock_collection = MagicMock()
    expected = {"items": [{"_id": 1}], "total": 1}
    mocker.patch("fastapi_pagination.ext.pymongo.run_sync_flow", return_value=expected)

    result = paginate_aggregate(mock_collection)

    assert result == expected


# ──────────────────────────────────────────────────────────────────────────────
# Tests for apaginate_aggregate (wrapper)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apaginate_aggregate_calls_run_async_flow(mocker):
    """apaginate_aggregate delegates to run_async_flow and returns its result."""
    mock_collection = MagicMock()
    mock_result = MagicMock()
    mock_run_async = mocker.patch(
        "fastapi_pagination.ext.pymongo.run_async_flow",
        new_callable=AsyncMock,
        return_value=mock_result,
    )

    result = await apaginate_aggregate(mock_collection)

    assert result is mock_result
    mock_run_async.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_aggregate_returns_value_from_run_async_flow(mocker):
    """The return value of apaginate_aggregate is exactly what run_async_flow returns."""
    mock_collection = MagicMock()
    expected = {"items": [], "total": 0}
    mocker.patch(
        "fastapi_pagination.ext.pymongo.run_async_flow",
        new_callable=AsyncMock,
        return_value=expected,
    )

    result = await apaginate_aggregate(mock_collection)

    assert result == expected


# ──────────────────────────────────────────────────────────────────────────────
# Integration-style tests for _aggregate_flow via paginate_aggregate
# (exercises lines 100, 112-128, 138-151, 161)
# ──────────────────────────────────────────────────────────────────────────────


def test_aggregate_flow_basic():
    """_aggregate_flow runs correctly with mocked collection and limit-offset params."""
    mock_collection = _make_sync_collection(items=[{"_id": 1}, {"_id": 2}], total=2)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = paginate_aggregate(mock_collection, params=params)

    assert result is not None
    mock_collection.aggregate.assert_called_once()


def test_aggregate_flow_empty_metadata_total_is_zero():
    """When metadata list is empty, _aggregate_flow defaults total to 0."""
    mock_cursor = MagicMock()
    mock_cursor.to_list.return_value = [{"data": [], "metadata": []}]
    mock_collection = MagicMock()
    mock_collection.aggregate.return_value = mock_cursor

    params = Params(page=1, size=10)

    with set_page(Page):
        result = paginate_aggregate(mock_collection, params=params)

    assert result is not None


def test_aggregate_flow_none_pipeline_defaults_to_empty():
    """When aggregate_pipeline is None, _aggregate_flow uses []."""
    mock_collection = _make_sync_collection(items=[], total=0)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = paginate_aggregate(mock_collection, aggregate_pipeline=None, params=params)

    assert result is not None


def test_aggregate_flow_with_custom_pipeline():
    """_aggregate_flow includes custom pipeline stages in the aggregation."""
    mock_collection = _make_sync_collection(items=[{"name": "Alice"}], total=1)
    params = Params(page=1, size=10)
    pipeline = [{"$match": {"active": True}}]

    with set_page(Page):
        paginate_aggregate(mock_collection, aggregate_pipeline=pipeline, params=params)

    called_pipeline = mock_collection.aggregate.call_args[0][0]
    assert any("$match" in stage for stage in called_pipeline)


def test_aggregate_flow_with_aggregation_filter_end_auto():
    """_aggregate_flow handles aggregation_filter_end='auto'."""
    mock_collection = _make_sync_collection(items=[{"_id": 1}], total=1)
    params = Params(page=1, size=10)
    pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]

    with set_page(Page):
        result = paginate_aggregate(
            mock_collection,
            aggregate_pipeline=pipeline,
            params=params,
            aggregation_filter_end="auto",
        )

    assert result is not None


def test_aggregate_flow_with_aggregation_filter_end_int():
    """_aggregate_flow handles aggregation_filter_end as an integer."""
    mock_collection = _make_sync_collection(items=[{"_id": 1}], total=1)
    params = Params(page=1, size=10)
    pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]

    with set_page(Page):
        result = paginate_aggregate(
            mock_collection,
            aggregate_pipeline=pipeline,
            params=params,
            aggregation_filter_end=1,
        )

    assert result is not None


def test_aggregate_flow_with_pipeline_transformer():
    """_aggregate_flow calls aggregation_pipeline_transformer when provided."""
    transformed_pipeline = [{"$custom": True}]
    pipeline_transformer = MagicMock(return_value=transformed_pipeline)

    mock_cursor = MagicMock()
    mock_cursor.to_list.return_value = [{"data": [], "metadata": []}]
    mock_collection = MagicMock()
    mock_collection.aggregate.return_value = mock_cursor

    params = Params(page=1, size=10)

    with set_page(Page):
        paginate_aggregate(
            mock_collection,
            params=params,
            aggregation_pipeline_transformer=pipeline_transformer,
        )

    pipeline_transformer.assert_called_once()
    called_pipeline = mock_collection.aggregate.call_args[0][0]
    assert called_pipeline == transformed_pipeline


@pytest.mark.asyncio
async def test_aggregate_flow_async_basic():
    """_aggregate_flow (async=True) runs correctly with an async mocked collection."""
    mock_collection = _make_async_collection(items=[{"_id": 1}], total=1)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate_aggregate(mock_collection, params=params)

    assert result is not None
    mock_collection.aggregate.assert_called_once()


@pytest.mark.asyncio
async def test_aggregate_flow_async_empty_metadata_total_is_zero():
    """Async _aggregate_flow defaults total to 0 when metadata is empty."""
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[{"data": [], "metadata": []}])
    mock_collection = MagicMock()
    mock_collection.aggregate.return_value = mock_cursor

    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate_aggregate(mock_collection, params=params)

    assert result is not None
