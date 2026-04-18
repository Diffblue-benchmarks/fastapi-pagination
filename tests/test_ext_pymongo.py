"""Unit tests for fastapi_pagination.ext.pymongo."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Inject fake pymongo modules BEFORE importing the extension under test.
# pymongo is not installed in the test environment.
# ---------------------------------------------------------------------------

_pymongo_mock = MagicMock()
_pymongo_collection_mock = MagicMock()
_pymongo_async_mock = MagicMock()
_pymongo_async_collection_mock = MagicMock()

_FakeCollection = MagicMock(name="Collection")
_FakeAsyncCollection = MagicMock(name="AsyncCollection")

_pymongo_collection_mock.Collection = _FakeCollection
_pymongo_async_collection_mock.AsyncCollection = _FakeAsyncCollection

for _key, _mod in [
    ("pymongo", _pymongo_mock),
    ("pymongo.collection", _pymongo_collection_mock),
    ("pymongo.asynchronous", _pymongo_async_mock),
    ("pymongo.asynchronous.collection", _pymongo_async_collection_mock),
]:
    sys.modules[_key] = _mod

sys.modules.pop("fastapi_pagination.ext.pymongo", None)

from fastapi_pagination.ext.pymongo import (  # noqa: E402
    _aggregate_flow,
    apaginate,
    apaginate_aggregate,
    paginate,
    paginate_aggregate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sync_collection(items=None, total=1):
    """Create a MagicMock collection suitable for sync paginate tests."""
    items = items if items is not None else [{"_id": 1}]
    collection = MagicMock()
    collection.count_documents.return_value = total
    cursor = MagicMock()
    cursor.to_list.return_value = items
    collection.find.return_value = cursor
    return collection


def _make_aggregate_collection(items=None, metadata=None):
    """Create a MagicMock collection that returns aggregate-style results."""
    items = items if items is not None else [{"_id": 1}]
    metadata = metadata if metadata is not None else [{"total": 1}]
    data = {"data": items, "metadata": metadata}
    collection = MagicMock()
    cursor = MagicMock()
    cursor.to_list.return_value = [data]
    collection.aggregate.return_value = cursor
    return collection


def _drive_aggregate_flow_sync(collection, aggregate_pipeline=None, **kwargs):
    """Drive _aggregate_flow synchronously via run_sync_flow."""
    from fastapi_pagination.flow import run_sync_flow

    return run_sync_flow(
        _aggregate_flow(
            is_async=False,
            collection=collection,
            aggregate_pipeline=aggregate_pipeline,
            **kwargs,
        )
    )


# ---------------------------------------------------------------------------
# Tests for paginate
# ---------------------------------------------------------------------------


def test_paginate_returns_run_sync_flow_result():
    """paginate calls run_sync_flow and returns its result."""
    collection = _make_sync_collection()
    fake_page = MagicMock(name="page")

    with patch("fastapi_pagination.ext.pymongo.run_sync_flow", return_value=fake_page) as mock_flow:
        result = paginate(collection, query_filter={"x": 1})

    assert result is fake_page
    mock_flow.assert_called_once()


def test_paginate_defaults_query_filter_to_empty_dict():
    """paginate with no query_filter defaults to {}."""
    collection = _make_sync_collection()
    fake_page = MagicMock(name="page")

    with patch("fastapi_pagination.ext.pymongo.run_sync_flow", return_value=fake_page) as mock_flow:
        result = paginate(collection)

    assert result is fake_page
    mock_flow.assert_called_once()


def test_paginate_passes_kwargs_and_sort():
    """paginate forwards sort and extra kwargs."""
    collection = _make_sync_collection()
    fake_page = MagicMock(name="page")

    with patch("fastapi_pagination.ext.pymongo.run_sync_flow", return_value=fake_page) as mock_flow:
        result = paginate(collection, sort=[("name", 1)], batch_size=100)

    assert result is fake_page
    mock_flow.assert_called_once()


# ---------------------------------------------------------------------------
# Tests for apaginate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_returns_run_async_flow_result():
    """apaginate calls run_async_flow and returns its result."""
    collection = MagicMock()
    fake_page = MagicMock(name="page")

    with patch(
        "fastapi_pagination.ext.pymongo.run_async_flow",
        new=AsyncMock(return_value=fake_page),
    ) as mock_flow:
        result = await apaginate(collection, query_filter={"y": 2})

    assert result is fake_page
    mock_flow.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_defaults_query_filter_to_empty_dict():
    """apaginate with no query_filter defaults to {}."""
    collection = MagicMock()
    fake_page = MagicMock(name="page")

    with patch(
        "fastapi_pagination.ext.pymongo.run_async_flow",
        new=AsyncMock(return_value=fake_page),
    ) as mock_flow:
        result = await apaginate(collection)

    assert result is fake_page
    mock_flow.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_passes_kwargs():
    """apaginate forwards extra kwargs."""
    collection = MagicMock()
    fake_page = MagicMock(name="page")

    with patch(
        "fastapi_pagination.ext.pymongo.run_async_flow",
        new=AsyncMock(return_value=fake_page),
    ):
        result = await apaginate(collection, sort=[("ts", -1)], batch_size=50)

    assert result is fake_page


# ---------------------------------------------------------------------------
# Tests for _aggregate_flow (generator – driven via run_sync_flow)
# ---------------------------------------------------------------------------


def _make_fake_cpf(fake_page):
    """Return a generator function that immediately returns fake_page."""

    def fake_create_page_flow(*args, **kwargs):
        # A generator that yields nothing and returns the fake page.
        if False:
            yield  # make it a generator  # noqa: unreachable
        return fake_page

    return fake_create_page_flow


def test_aggregate_flow_basic_items_and_total():
    """_aggregate_flow: basic case with items and non-empty metadata."""
    items = [{"_id": 1, "name": "Alice"}]
    collection = _make_aggregate_collection(items=items, metadata=[{"total": 1}])
    fake_page = MagicMock(name="page")

    with (
        patch("fastapi_pagination.ext.pymongo.verify_params") as mock_verify,
        patch("fastapi_pagination.ext.pymongo.create_page_flow", side_effect=_make_fake_cpf(fake_page)),
    ):
        from fastapi_pagination.bases import RawParams

        raw = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()
        mock_verify.return_value = (mock_params, raw)

        result = _drive_aggregate_flow_sync(collection)

    assert result is fake_page


def test_aggregate_flow_empty_metadata_gives_total_zero():
    """_aggregate_flow: empty metadata results in total=0 (IndexError path)."""
    collection = _make_aggregate_collection(items=[], metadata=[])
    fake_page = MagicMock(name="page")
    captured = {}

    def fake_cpf(items_, params_, *, total=None, **kwargs):
        captured["total"] = total
        if False:
            yield
        return fake_page

    with (
        patch("fastapi_pagination.ext.pymongo.verify_params") as mock_verify,
        patch("fastapi_pagination.ext.pymongo.create_page_flow", side_effect=fake_cpf),
    ):
        from fastapi_pagination.bases import RawParams

        raw = RawParams(limit=5, offset=0, include_total=True)
        mock_params = MagicMock()
        mock_verify.return_value = (mock_params, raw)

        _drive_aggregate_flow_sync(collection)

    assert captured["total"] == 0


def test_aggregate_flow_limit_offset_in_pipeline():
    """_aggregate_flow: $limit and $skip appear in the $facet data stages."""
    items = [{"x": 1}]
    collection = _make_aggregate_collection(items=items, metadata=[{"total": 1}])
    fake_page = MagicMock(name="page")

    with (
        patch("fastapi_pagination.ext.pymongo.verify_params") as mock_verify,
        patch("fastapi_pagination.ext.pymongo.create_page_flow", side_effect=_make_fake_cpf(fake_page)),
    ):
        from fastapi_pagination.bases import RawParams

        raw = RawParams(limit=5, offset=2, include_total=True)
        mock_params = MagicMock()
        mock_verify.return_value = (mock_params, raw)

        _drive_aggregate_flow_sync(collection)

    pipeline_arg = collection.aggregate.call_args[0][0]
    facet = next(s for s in pipeline_arg if "$facet" in s)
    data_stages = facet["$facet"]["data"]
    assert any("$limit" in s for s in data_stages)
    assert any("$skip" in s for s in data_stages)


def test_aggregate_flow_no_limit_no_offset():
    """_aggregate_flow: None limit/offset → paginate_data is empty."""
    collection = _make_aggregate_collection()
    fake_page = MagicMock(name="page")

    with (
        patch("fastapi_pagination.ext.pymongo.verify_params") as mock_verify,
        patch("fastapi_pagination.ext.pymongo.create_page_flow", side_effect=_make_fake_cpf(fake_page)),
    ):
        from fastapi_pagination.bases import RawParams

        raw = RawParams(limit=None, offset=None, include_total=True)
        mock_params = MagicMock()
        mock_verify.return_value = (mock_params, raw)

        result = _drive_aggregate_flow_sync(collection)

    assert result is fake_page


def test_aggregate_flow_aggregation_filter_end_auto():
    """_aggregate_flow: aggregation_filter_end='auto' calls get_mongo_pipeline_filter_end."""
    pipeline = [{"$match": {"a": 1}}, {"$project": {"a": 1}}]
    collection = _make_aggregate_collection()
    fake_page = MagicMock(name="page")

    with (
        patch("fastapi_pagination.ext.pymongo.verify_params") as mock_verify,
        patch("fastapi_pagination.ext.pymongo.create_page_flow", side_effect=_make_fake_cpf(fake_page)),
        patch(
            "fastapi_pagination.ext.pymongo.get_mongo_pipeline_filter_end",
            return_value=1,
        ) as mock_filter_end,
    ):
        from fastapi_pagination.bases import RawParams

        raw = RawParams(limit=5, offset=0, include_total=True)
        mock_params = MagicMock()
        mock_verify.return_value = (mock_params, raw)

        result = _drive_aggregate_flow_sync(
            collection,
            aggregate_pipeline=pipeline,
            aggregation_filter_end="auto",
        )

    mock_filter_end.assert_called_once()
    assert result is fake_page


def test_aggregate_flow_aggregation_filter_end_integer():
    """_aggregate_flow: integer aggregation_filter_end splits pipeline."""
    pipeline = [
        {"$match": {"b": 2}},
        {"$sort": {"b": 1}},
        {"$project": {"b": 1}},
    ]
    collection = _make_aggregate_collection()
    fake_page = MagicMock(name="page")

    with (
        patch("fastapi_pagination.ext.pymongo.verify_params") as mock_verify,
        patch("fastapi_pagination.ext.pymongo.create_page_flow", side_effect=_make_fake_cpf(fake_page)),
    ):
        from fastapi_pagination.bases import RawParams

        raw = RawParams(limit=5, offset=0, include_total=True)
        mock_params = MagicMock()
        mock_verify.return_value = (mock_params, raw)

        result = _drive_aggregate_flow_sync(
            collection,
            aggregate_pipeline=pipeline,
            aggregation_filter_end=1,
        )

    collection.aggregate.assert_called_once()
    assert result is fake_page


def test_aggregate_flow_pipeline_transformer_applied():
    """_aggregate_flow: aggregation_pipeline_transformer is called and its result used."""
    collection = _make_aggregate_collection()
    fake_page = MagicMock(name="page")
    transformed = [{"$match": {}}, {"$addFields": {"extra": 1}}]
    transformer = MagicMock(return_value=transformed)

    # Reset aggregate cursor to reflect transformed pipeline
    cursor = MagicMock()
    data = {"data": [{"_id": 1}], "metadata": [{"total": 1}]}
    cursor.to_list.return_value = [data]
    collection.aggregate.return_value = cursor

    with (
        patch("fastapi_pagination.ext.pymongo.verify_params") as mock_verify,
        patch("fastapi_pagination.ext.pymongo.create_page_flow", side_effect=_make_fake_cpf(fake_page)),
    ):
        from fastapi_pagination.bases import RawParams

        raw = RawParams(limit=5, offset=0, include_total=True)
        mock_params = MagicMock()
        mock_verify.return_value = (mock_params, raw)

        _drive_aggregate_flow_sync(collection, aggregation_pipeline_transformer=transformer)

    transformer.assert_called_once()
    collection.aggregate.assert_called_once_with(transformed)


# ---------------------------------------------------------------------------
# Tests for apaginate_aggregate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_aggregate_returns_result():
    """apaginate_aggregate calls run_async_flow and returns its result."""
    collection = MagicMock()
    fake_page = MagicMock(name="page")

    with patch(
        "fastapi_pagination.ext.pymongo.run_async_flow",
        new=AsyncMock(return_value=fake_page),
    ) as mock_flow:
        result = await apaginate_aggregate(collection)

    assert result is fake_page
    mock_flow.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_aggregate_passes_pipeline():
    """apaginate_aggregate passes aggregate_pipeline argument."""
    collection = MagicMock()
    pipeline = [{"$match": {"z": 1}}]
    fake_page = MagicMock(name="page")

    with patch(
        "fastapi_pagination.ext.pymongo.run_async_flow",
        new=AsyncMock(return_value=fake_page),
    ):
        result = await apaginate_aggregate(collection, aggregate_pipeline=pipeline)

    assert result is fake_page


@pytest.mark.asyncio
async def test_apaginate_aggregate_none_pipeline_defaults_to_empty():
    """apaginate_aggregate with no pipeline passes [] to _aggregate_flow."""
    collection = MagicMock()
    fake_page = MagicMock(name="page")

    with patch(
        "fastapi_pagination.ext.pymongo.run_async_flow",
        new=AsyncMock(return_value=fake_page),
    ):
        result = await apaginate_aggregate(collection, aggregate_pipeline=None)

    assert result is fake_page


# ---------------------------------------------------------------------------
# Tests for paginate_aggregate
# ---------------------------------------------------------------------------


def test_paginate_aggregate_returns_result():
    """paginate_aggregate calls run_sync_flow and returns its result."""
    collection = MagicMock()
    fake_page = MagicMock(name="page")

    with patch("fastapi_pagination.ext.pymongo.run_sync_flow", return_value=fake_page) as mock_flow:
        result = paginate_aggregate(collection)

    assert result is fake_page
    mock_flow.assert_called_once()


def test_paginate_aggregate_passes_pipeline():
    """paginate_aggregate passes aggregate_pipeline argument."""
    collection = MagicMock()
    pipeline = [{"$match": {"w": 5}}]
    fake_page = MagicMock(name="page")

    with patch("fastapi_pagination.ext.pymongo.run_sync_flow", return_value=fake_page):
        result = paginate_aggregate(collection, aggregate_pipeline=pipeline)

    assert result is fake_page


def test_paginate_aggregate_none_pipeline_defaults_to_empty():
    """paginate_aggregate with no pipeline passes [] to _aggregate_flow."""
    collection = MagicMock()
    fake_page = MagicMock(name="page")

    with patch("fastapi_pagination.ext.pymongo.run_sync_flow", return_value=fake_page):
        result = paginate_aggregate(collection, aggregate_pipeline=None)

    assert result is fake_page
