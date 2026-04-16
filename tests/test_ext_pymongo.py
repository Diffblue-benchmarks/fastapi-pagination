from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _setup_pymongo_mocks():
    """Set up mock pymongo modules so fastapi_pagination.ext.pymongo can be imported."""
    pymongo_mock = ModuleType("pymongo")
    pymongo_collection = ModuleType("pymongo.collection")
    pymongo_async = ModuleType("pymongo.asynchronous")
    pymongo_async_collection = ModuleType("pymongo.asynchronous.collection")

    mock_collection_cls = MagicMock()
    mock_async_collection_cls = MagicMock()

    pymongo_collection.Collection = mock_collection_cls
    pymongo_async_collection.AsyncCollection = mock_async_collection_cls

    sys.modules.setdefault("pymongo", pymongo_mock)
    sys.modules.setdefault("pymongo.collection", pymongo_collection)
    sys.modules.setdefault("pymongo.asynchronous", pymongo_async)
    sys.modules.setdefault("pymongo.asynchronous.collection", pymongo_async_collection)

    return mock_collection_cls, mock_async_collection_cls


_collection_cls, _async_collection_cls = _setup_pymongo_mocks()

from fastapi_pagination.ext.pymongo import (  # noqa: E402
    _aggregate_flow,
    apaginate,
    apaginate_aggregate,
    paginate,
    paginate_aggregate,
)
from fastapi_pagination.flow import run_sync_flow  # noqa: E402


# ---------------------------------------------------------------------------
# paginate
# ---------------------------------------------------------------------------


def test_paginate_calls_run_sync_flow_and_generic_flow():
    mock_collection = MagicMock()

    with patch("fastapi_pagination.ext.pymongo.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.pymongo.generic_flow") as mock_flow:
        mock_run.return_value = "page_result"
        mock_flow.return_value = "flow_obj"

        result = paginate(mock_collection)

        assert result == "page_result"
        mock_flow.assert_called_once()
        mock_run.assert_called_once_with("flow_obj")


def test_paginate_default_query_filter_is_empty_dict():
    mock_collection = MagicMock()

    with patch("fastapi_pagination.ext.pymongo.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.pymongo.generic_flow") as mock_flow:
        mock_run.return_value = "page"
        mock_flow.return_value = "flow"

        paginate(mock_collection)

        # The flow was created; verify the collection is used with empty filter
        mock_collection.count_documents.side_effect = None
        mock_flow.assert_called_once()


def test_paginate_passes_params_transformer_additional_data_config():
    mock_collection = MagicMock()
    mock_params = MagicMock()
    mock_transformer = MagicMock()
    mock_additional_data = {"key": "val"}
    mock_config = MagicMock()

    with patch("fastapi_pagination.ext.pymongo.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.pymongo.generic_flow") as mock_flow:
        mock_run.return_value = "page"
        mock_flow.return_value = "flow"

        paginate(
            mock_collection,
            params=mock_params,
            transformer=mock_transformer,
            additional_data=mock_additional_data,
            config=mock_config,
        )

        call_kwargs = mock_flow.call_args.kwargs
        assert call_kwargs["params"] is mock_params
        assert call_kwargs["transformer"] is mock_transformer
        assert call_kwargs["additional_data"] is mock_additional_data
        assert call_kwargs["config"] is mock_config


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_calls_run_async_flow_and_generic_flow():
    mock_collection = MagicMock()

    with patch("fastapi_pagination.ext.pymongo.run_async_flow", new_callable=AsyncMock) as mock_run, \
         patch("fastapi_pagination.ext.pymongo.generic_flow") as mock_flow:
        mock_run.return_value = "page_result"
        mock_flow.return_value = "flow_obj"

        result = await apaginate(mock_collection)

        assert result == "page_result"
        mock_flow.assert_called_once()
        mock_run.assert_called_once_with("flow_obj")


@pytest.mark.asyncio
async def test_apaginate_passes_params_transformer_additional_data_config():
    mock_collection = MagicMock()
    mock_params = MagicMock()
    mock_transformer = MagicMock()
    mock_additional_data = {"key": "val"}
    mock_config = MagicMock()

    with patch("fastapi_pagination.ext.pymongo.run_async_flow", new_callable=AsyncMock) as mock_run, \
         patch("fastapi_pagination.ext.pymongo.generic_flow") as mock_flow:
        mock_run.return_value = "page"
        mock_flow.return_value = "flow"

        await apaginate(
            mock_collection,
            params=mock_params,
            transformer=mock_transformer,
            additional_data=mock_additional_data,
            config=mock_config,
        )

        call_kwargs = mock_flow.call_args.kwargs
        assert call_kwargs["params"] is mock_params
        assert call_kwargs["transformer"] is mock_transformer
        assert call_kwargs["additional_data"] is mock_additional_data
        assert call_kwargs["config"] is mock_config


@pytest.mark.asyncio
async def test_apaginate_default_query_filter_applied():
    mock_collection = MagicMock()

    with patch("fastapi_pagination.ext.pymongo.run_async_flow", new_callable=AsyncMock) as mock_run, \
         patch("fastapi_pagination.ext.pymongo.generic_flow") as mock_flow:
        mock_run.return_value = "page"
        mock_flow.return_value = "flow"

        await apaginate(mock_collection, query_filter=None)

        mock_flow.assert_called_once()


# ---------------------------------------------------------------------------
# _aggregate_flow
# ---------------------------------------------------------------------------


def test_aggregate_flow_builds_pipeline_and_returns_page():
    mock_cursor = MagicMock()
    mock_data = {"data": [{"id": 1}], "metadata": [{"total": 1}]}
    mock_cursor.to_list.return_value = [mock_data]

    mock_collection = MagicMock()
    mock_collection.aggregate.return_value = mock_cursor

    with patch("fastapi_pagination.ext.pymongo.verify_params") as mock_verify, \
         patch("fastapi_pagination.ext.pymongo.create_page_flow") as mock_page_flow:
        mock_raw_params = MagicMock()
        mock_raw_params.limit = 10
        mock_raw_params.offset = 0
        mock_params = MagicMock()
        mock_verify.return_value = (mock_params, mock_raw_params)

        mock_page_flow.return_value = iter([])

        def fake_create_page_flow(*args, **kwargs):
            yield "page_result"
            return "page_result"

        mock_page_flow.side_effect = fake_create_page_flow

        result = run_sync_flow(
            _aggregate_flow(
                is_async=False,
                collection=mock_collection,
                aggregate_pipeline=[],
            )
        )

        mock_collection.aggregate.assert_called_once()
        mock_cursor.to_list.assert_called_once_with(length=None)
        assert result == "page_result"


def test_aggregate_flow_empty_metadata_gives_total_zero():
    mock_cursor = MagicMock()
    mock_data = {"data": [], "metadata": []}
    mock_cursor.to_list.return_value = [mock_data]

    mock_collection = MagicMock()
    mock_collection.aggregate.return_value = mock_cursor

    with patch("fastapi_pagination.ext.pymongo.verify_params") as mock_verify, \
         patch("fastapi_pagination.ext.pymongo.create_page_flow") as mock_page_flow:
        mock_raw_params = MagicMock()
        mock_raw_params.limit = 10
        mock_raw_params.offset = 0
        mock_params = MagicMock()
        mock_verify.return_value = (mock_params, mock_raw_params)

        captured_total = {}

        def fake_create_page_flow(items, params, *, total=None, **kwargs):
            captured_total["total"] = total
            yield "page_result"
            return "page_result"

        mock_page_flow.side_effect = fake_create_page_flow

        run_sync_flow(
            _aggregate_flow(
                is_async=False,
                collection=mock_collection,
                aggregate_pipeline=[],
            )
        )

        assert captured_total["total"] == 0


def test_aggregate_flow_with_aggregation_filter_end_auto():
    mock_cursor = MagicMock()
    mock_data = {"data": [{"id": 1}], "metadata": [{"total": 1}]}
    mock_cursor.to_list.return_value = [mock_data]

    mock_collection = MagicMock()
    mock_collection.aggregate.return_value = mock_cursor

    pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]

    with patch("fastapi_pagination.ext.pymongo.verify_params") as mock_verify, \
         patch("fastapi_pagination.ext.pymongo.create_page_flow") as mock_page_flow, \
         patch("fastapi_pagination.ext.pymongo.get_mongo_pipeline_filter_end", return_value=1) as mock_filter_end:
        mock_raw_params = MagicMock()
        mock_raw_params.limit = 10
        mock_raw_params.offset = 0
        mock_params = MagicMock()
        mock_verify.return_value = (mock_params, mock_raw_params)

        def fake_create_page_flow(*args, **kwargs):
            yield "page_result"
            return "page_result"

        mock_page_flow.side_effect = fake_create_page_flow

        run_sync_flow(
            _aggregate_flow(
                is_async=False,
                collection=mock_collection,
                aggregate_pipeline=pipeline,
                aggregation_filter_end="auto",
            )
        )

        mock_filter_end.assert_called_once_with(pipeline)


def test_aggregate_flow_with_pipeline_transformer():
    mock_cursor = MagicMock()
    mock_data = {"data": [{"id": 1}], "metadata": [{"total": 1}]}
    mock_cursor.to_list.return_value = [mock_data]

    mock_collection = MagicMock()
    mock_collection.aggregate.return_value = mock_cursor

    transformed_pipeline = [{"$match": {}}, {"$facet": {"metadata": [], "data": []}}]
    mock_transformer = MagicMock(return_value=transformed_pipeline)

    with patch("fastapi_pagination.ext.pymongo.verify_params") as mock_verify, \
         patch("fastapi_pagination.ext.pymongo.create_page_flow") as mock_page_flow:
        mock_raw_params = MagicMock()
        mock_raw_params.limit = 5
        mock_raw_params.offset = 0
        mock_params = MagicMock()
        mock_verify.return_value = (mock_params, mock_raw_params)

        def fake_create_page_flow(*args, **kwargs):
            yield "page_result"
            return "page_result"

        mock_page_flow.side_effect = fake_create_page_flow

        run_sync_flow(
            _aggregate_flow(
                is_async=False,
                collection=mock_collection,
                aggregate_pipeline=[],
                aggregation_pipeline_transformer=mock_transformer,
            )
        )

        mock_transformer.assert_called_once()
        mock_collection.aggregate.assert_called_once_with(transformed_pipeline)


def test_aggregate_flow_no_limit_no_offset():
    mock_cursor = MagicMock()
    mock_data = {"data": [], "metadata": [{"total": 0}]}
    mock_cursor.to_list.return_value = [mock_data]

    mock_collection = MagicMock()
    mock_collection.aggregate.return_value = mock_cursor

    with patch("fastapi_pagination.ext.pymongo.verify_params") as mock_verify, \
         patch("fastapi_pagination.ext.pymongo.create_page_flow") as mock_page_flow:
        mock_raw_params = MagicMock()
        mock_raw_params.limit = None
        mock_raw_params.offset = None
        mock_params = MagicMock()
        mock_verify.return_value = (mock_params, mock_raw_params)

        def fake_create_page_flow(*args, **kwargs):
            yield "page_result"
            return "page_result"

        mock_page_flow.side_effect = fake_create_page_flow

        result = run_sync_flow(
            _aggregate_flow(
                is_async=False,
                collection=mock_collection,
                aggregate_pipeline=[],
            )
        )

        assert result == "page_result"


# ---------------------------------------------------------------------------
# apaginate_aggregate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_aggregate_calls_run_async_flow():
    mock_collection = MagicMock()

    with patch("fastapi_pagination.ext.pymongo.run_async_flow", new_callable=AsyncMock) as mock_run, \
         patch("fastapi_pagination.ext.pymongo._aggregate_flow") as mock_agg_flow:
        mock_run.return_value = "page_result"
        mock_agg_flow.return_value = "agg_flow_obj"

        result = await apaginate_aggregate(mock_collection)

        assert result == "page_result"
        mock_agg_flow.assert_called_once()
        call_kwargs = mock_agg_flow.call_args.kwargs
        assert call_kwargs["is_async"] is True
        assert call_kwargs["collection"] is mock_collection
        mock_run.assert_called_once_with("agg_flow_obj")


@pytest.mark.asyncio
async def test_apaginate_aggregate_passes_all_params():
    mock_collection = MagicMock()
    mock_params = MagicMock()
    mock_transformer = MagicMock()
    mock_additional_data = {"x": 1}
    mock_config = MagicMock()
    mock_pipeline_transformer = MagicMock()
    pipeline = [{"$match": {}}]

    with patch("fastapi_pagination.ext.pymongo.run_async_flow", new_callable=AsyncMock) as mock_run, \
         patch("fastapi_pagination.ext.pymongo._aggregate_flow") as mock_agg_flow:
        mock_run.return_value = "page"
        mock_agg_flow.return_value = "flow"

        await apaginate_aggregate(
            mock_collection,
            aggregate_pipeline=pipeline,
            params=mock_params,
            transformer=mock_transformer,
            additional_data=mock_additional_data,
            aggregation_filter_end=5,
            aggregation_pipeline_transformer=mock_pipeline_transformer,
            config=mock_config,
        )

        call_kwargs = mock_agg_flow.call_args.kwargs
        assert call_kwargs["aggregate_pipeline"] is pipeline
        assert call_kwargs["params"] is mock_params
        assert call_kwargs["transformer"] is mock_transformer
        assert call_kwargs["additional_data"] is mock_additional_data
        assert call_kwargs["aggregation_filter_end"] == 5
        assert call_kwargs["aggregation_pipeline_transformer"] is mock_pipeline_transformer
        assert call_kwargs["config"] is mock_config


# ---------------------------------------------------------------------------
# paginate_aggregate
# ---------------------------------------------------------------------------


def test_paginate_aggregate_calls_run_sync_flow():
    mock_collection = MagicMock()

    with patch("fastapi_pagination.ext.pymongo.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.pymongo._aggregate_flow") as mock_agg_flow:
        mock_run.return_value = "page_result"
        mock_agg_flow.return_value = "agg_flow_obj"

        result = paginate_aggregate(mock_collection)

        assert result == "page_result"
        mock_agg_flow.assert_called_once()
        call_kwargs = mock_agg_flow.call_args.kwargs
        assert call_kwargs["is_async"] is False
        assert call_kwargs["collection"] is mock_collection
        mock_run.assert_called_once_with("agg_flow_obj")


def test_paginate_aggregate_passes_all_params():
    mock_collection = MagicMock()
    mock_params = MagicMock()
    mock_transformer = MagicMock()
    mock_additional_data = {"x": 1}
    mock_config = MagicMock()
    mock_pipeline_transformer = MagicMock()
    pipeline = [{"$match": {}}]

    with patch("fastapi_pagination.ext.pymongo.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.pymongo._aggregate_flow") as mock_agg_flow:
        mock_run.return_value = "page"
        mock_agg_flow.return_value = "flow"

        paginate_aggregate(
            mock_collection,
            aggregate_pipeline=pipeline,
            params=mock_params,
            transformer=mock_transformer,
            additional_data=mock_additional_data,
            aggregation_filter_end=3,
            aggregation_pipeline_transformer=mock_pipeline_transformer,
            config=mock_config,
        )

        call_kwargs = mock_agg_flow.call_args.kwargs
        assert call_kwargs["aggregate_pipeline"] is pipeline
        assert call_kwargs["params"] is mock_params
        assert call_kwargs["transformer"] is mock_transformer
        assert call_kwargs["additional_data"] is mock_additional_data
        assert call_kwargs["aggregation_filter_end"] == 3
        assert call_kwargs["aggregation_pipeline_transformer"] is mock_pipeline_transformer
        assert call_kwargs["config"] is mock_config
