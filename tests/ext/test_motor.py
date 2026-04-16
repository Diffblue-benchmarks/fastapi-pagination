"""Unit tests for fastapi_pagination.ext.motor"""
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _setup_motor_mocks():
    """Install mock motor modules into sys.modules before the motor module is loaded."""
    if "motor" in sys.modules:
        return

    motor_mod = types.ModuleType("motor")
    motor_core = types.ModuleType("motor.core")

    class _AgnosticCollection:
        pass

    motor_core.AgnosticCollection = _AgnosticCollection
    motor_mod.core = motor_core

    sys.modules["motor"] = motor_mod
    sys.modules["motor.core"] = motor_core


_setup_motor_mocks()

# Now safe to import
from fastapi_pagination.bases import RawParams  # noqa: E402
from fastapi_pagination.ext.motor import apaginate, apaginate_aggregate, paginate, paginate_aggregate  # noqa: E402


def _make_raw_params(limit=10, offset=0, include_total=True):
    return RawParams(limit=limit, offset=offset, include_total=include_total)


def _make_mock_params(raw_params):
    mock_params = MagicMock()
    mock_params.to_raw_params.return_value = raw_params
    return mock_params


def _make_mock_collection(items=None, count=5):
    """Build a mock motor collection with async-capable methods."""
    if items is None:
        items = [{"_id": 1}, {"_id": 2}]

    cursor = MagicMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=items)

    collection = MagicMock()
    collection.count_documents = AsyncMock(return_value=count)
    collection.find = MagicMock(return_value=cursor)

    aggregate_cursor = MagicMock()
    aggregate_cursor.to_list = AsyncMock(
        return_value=[{"data": items, "metadata": [{"total": count}]}]
    )
    collection.aggregate = MagicMock(return_value=aggregate_cursor)

    return collection, cursor, aggregate_cursor


# ---------------------------------------------------------------------------
# apaginate tests
# ---------------------------------------------------------------------------


class TestApaginate:
    @pytest.mark.asyncio
    async def test_basic_with_total(self):
        raw_params = _make_raw_params(limit=5, offset=2, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, cursor, _ = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = [{"_id": 1}]
            cp.return_value = MagicMock(name="page")

            result = await apaginate(collection, query_filter={"active": True})

        vp.assert_called_once_with(None, "limit-offset")
        collection.count_documents.assert_awaited_once_with({"active": True})
        collection.find.assert_called_once_with({"active": True}, skip=2, limit=5)
        cursor.to_list.assert_awaited_once_with(length=5)
        ait.assert_awaited_once()
        cp.assert_called_once()
        assert result == cp.return_value

    @pytest.mark.asyncio
    async def test_without_total(self):
        raw_params = _make_raw_params(limit=10, offset=0, include_total=False)
        mock_params = _make_mock_params(raw_params)
        collection, cursor, _ = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            await apaginate(collection)

        collection.count_documents.assert_not_awaited()
        call_kwargs = cp.call_args[1]
        assert call_kwargs["total"] is None

    @pytest.mark.asyncio
    async def test_default_empty_query_filter(self):
        raw_params = _make_raw_params(limit=10, offset=0, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, cursor, _ = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            await apaginate(collection)

        # None query_filter should default to {}
        collection.count_documents.assert_awaited_once_with({})
        collection.find.assert_called_once_with({}, skip=0, limit=10)

    @pytest.mark.asyncio
    async def test_sort_as_tuple(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=False)
        mock_params = _make_mock_params(raw_params)
        collection, cursor, _ = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            await apaginate(collection, sort=("name", 1))

        cursor.sort.assert_called_once_with("name", 1)

    @pytest.mark.asyncio
    async def test_sort_as_non_tuple(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=False)
        mock_params = _make_mock_params(raw_params)
        collection, cursor, _ = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            await apaginate(collection, sort=[("name", 1)])

        cursor.sort.assert_called_once_with([("name", 1)])

    @pytest.mark.asyncio
    async def test_sort_none_not_called(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=False)
        mock_params = _make_mock_params(raw_params)
        collection, cursor, _ = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            await apaginate(collection, sort=None)

        cursor.sort.assert_not_called()

    @pytest.mark.asyncio
    async def test_additional_data_passed_to_create_page(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, cursor, _ = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            await apaginate(collection, additional_data={"extra": "value"})

        call_kwargs = cp.call_args[1]
        assert call_kwargs.get("extra") == "value"

    @pytest.mark.asyncio
    async def test_kwargs_passed_to_find(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=False)
        mock_params = _make_mock_params(raw_params)
        collection, cursor, _ = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            await apaginate(collection, projection={"name": 1})

        collection.find.assert_called_once_with({}, skip=0, limit=5, projection={"name": 1})


# ---------------------------------------------------------------------------
# apaginate_aggregate tests
# ---------------------------------------------------------------------------


class TestApaginateAggregate:
    @pytest.mark.asyncio
    async def test_basic_with_limit_and_offset(self):
        raw_params = _make_raw_params(limit=5, offset=2, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, _, agg_cursor = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = [{"_id": 1}]
            cp.return_value = MagicMock(name="page")

            result = await apaginate_aggregate(collection)

        vp.assert_called_once_with(None, "limit-offset")
        collection.aggregate.assert_called_once()
        agg_cursor.to_list.assert_awaited_once_with(length=None)
        pipeline_used = collection.aggregate.call_args[0][0]
        facet_stage = pipeline_used[-1]
        assert "$facet" in facet_stage
        data_stages = facet_stage["$facet"]["data"]
        stage_keys = [list(s.keys())[0] for s in data_stages]
        assert "$limit" in stage_keys
        assert "$skip" in stage_keys
        assert result == cp.return_value

    @pytest.mark.asyncio
    async def test_limit_none(self):
        raw_params = _make_raw_params(limit=None, offset=3, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, _, agg_cursor = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            await apaginate_aggregate(collection)

        pipeline_used = collection.aggregate.call_args[0][0]
        facet_stage = pipeline_used[-1]
        data_stages = facet_stage["$facet"]["data"]
        stage_keys = [list(s.keys())[0] for s in data_stages]
        assert "$limit" not in stage_keys
        assert "$skip" in stage_keys

    @pytest.mark.asyncio
    async def test_offset_none(self):
        raw_params = _make_raw_params(limit=5, offset=None, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, _, agg_cursor = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            await apaginate_aggregate(collection)

        pipeline_used = collection.aggregate.call_args[0][0]
        facet_stage = pipeline_used[-1]
        data_stages = facet_stage["$facet"]["data"]
        stage_keys = [list(s.keys())[0] for s in data_stages]
        assert "$skip" not in stage_keys

    @pytest.mark.asyncio
    async def test_empty_metadata_total_zero(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, _, agg_cursor = _make_mock_collection()
        agg_cursor.to_list.return_value = [{"data": [], "metadata": []}]

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            await apaginate_aggregate(collection)

        call_kwargs = cp.call_args[1]
        assert call_kwargs["total"] == 0

    @pytest.mark.asyncio
    async def test_aggregation_filter_end_int(self):
        raw_params = _make_raw_params(limit=5, offset=2, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, _, agg_cursor = _make_mock_collection()
        pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}, {"$sort": {"name": 1}}]

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = [{"_id": 1}]
            cp.return_value = MagicMock()

            await apaginate_aggregate(collection, aggregate_pipeline=list(pipeline), aggregation_filter_end=2)

        pipeline_used = collection.aggregate.call_args[0][0]
        facet_stage = pipeline_used[-1]
        assert "$facet" in facet_stage

    @pytest.mark.asyncio
    async def test_aggregation_filter_end_auto(self):
        raw_params = _make_raw_params(limit=5, offset=2, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, _, agg_cursor = _make_mock_collection()
        pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp, \
             patch("fastapi_pagination.ext.motor.get_mongo_pipeline_filter_end", return_value=1) as gmpfe:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = [{"_id": 1}]
            cp.return_value = MagicMock()

            await apaginate_aggregate(collection, aggregate_pipeline=list(pipeline), aggregation_filter_end="auto")

        gmpfe.assert_called_once_with(pipeline)

    @pytest.mark.asyncio
    async def test_aggregation_pipeline_transformer(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, _, agg_cursor = _make_mock_collection()
        transformed_pipeline = [{"$match": {}}, {"$limit": 10}]
        transformer = MagicMock(return_value=transformed_pipeline)

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = [{"_id": 1}]
            cp.return_value = MagicMock()

            await apaginate_aggregate(collection, aggregation_pipeline_transformer=transformer)

        transformer.assert_called_once()
        collection.aggregate.assert_called_once_with(transformed_pipeline)

    @pytest.mark.asyncio
    async def test_aggregate_pipeline_default_empty(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, _, agg_cursor = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            await apaginate_aggregate(collection, aggregate_pipeline=None)

        pipeline_used = collection.aggregate.call_args[0][0]
        # Should have a $facet stage built from empty pipeline
        assert any("$facet" in stage for stage in pipeline_used)

    @pytest.mark.asyncio
    async def test_additional_data_passed_to_create_page(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, _, agg_cursor = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            await apaginate_aggregate(collection, additional_data={"extra": "data"})

        call_kwargs = cp.call_args[1]
        assert call_kwargs.get("extra") == "data"


# ---------------------------------------------------------------------------
# paginate (deprecated wrapper) tests
# ---------------------------------------------------------------------------


class TestPaginate:
    @pytest.mark.asyncio
    async def test_paginate_delegates_to_apaginate(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, cursor, _ = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock(name="page")

            result = await paginate(collection, query_filter={"x": 1})

        collection.find.assert_called_once_with({"x": 1}, skip=0, limit=5)
        assert result == cp.return_value

    @pytest.mark.asyncio
    async def test_paginate_with_sort(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=False)
        mock_params = _make_mock_params(raw_params)
        collection, cursor, _ = _make_mock_collection()

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            await paginate(collection, sort=("name", 1))

        cursor.sort.assert_called_once_with("name", 1)


# ---------------------------------------------------------------------------
# paginate_aggregate (deprecated wrapper) tests
# ---------------------------------------------------------------------------


class TestPaginateAggregate:
    @pytest.mark.asyncio
    async def test_paginate_aggregate_delegates_to_apaginate_aggregate(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, _, agg_cursor = _make_mock_collection()
        pipeline = [{"$match": {"active": True}}]

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock(name="page")

            result = await paginate_aggregate(collection, aggregate_pipeline=pipeline)

        collection.aggregate.assert_called_once()
        assert result == cp.return_value

    @pytest.mark.asyncio
    async def test_paginate_aggregate_with_transformer(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=True)
        mock_params = _make_mock_params(raw_params)
        collection, _, agg_cursor = _make_mock_collection()
        item_transformer = MagicMock(return_value=["t"])

        with patch("fastapi_pagination.ext.motor.verify_params") as vp, \
             patch("fastapi_pagination.ext.motor.apply_items_transformer", new_callable=AsyncMock) as ait, \
             patch("fastapi_pagination.ext.motor.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = ["t"]
            cp.return_value = MagicMock()

            await paginate_aggregate(collection, transformer=item_transformer)

        ait.assert_awaited_once()
        call_args = ait.call_args
        assert call_args[1].get("async_") is True or call_args[0][1] == item_transformer
