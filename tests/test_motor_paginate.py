"""Tests for fastapi_pagination.ext.motor."""
import sys
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Mock motor (not installed) before importing the extension module.
# ---------------------------------------------------------------------------

_motor_core_mock = MagicMock()


class _MockAgnosticCollection:
    pass


_motor_core_mock.AgnosticCollection = _MockAgnosticCollection

_motor_mocks = {
    "motor": MagicMock(),
    "motor.core": _motor_core_mock,
}
for _name, _mod in _motor_mocks.items():
    sys.modules[_name] = _mod

sys.modules.pop("fastapi_pagination.ext.motor", None)

from fastapi_pagination.ext.motor import apaginate, apaginate_aggregate, paginate, paginate_aggregate  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class _RawParams:
    limit: int | None = 10
    offset: int | None = 0
    include_total: bool = True
    type: str = "limit-offset"


def _make_params(limit=10, offset=0, include_total=True):
    params = MagicMock()
    raw = _RawParams(limit=limit, offset=offset, include_total=include_total)
    return params, raw


def _make_collection(items=None, total=5):
    """Create a mock AgnosticCollection."""
    if items is None:
        items = []

    cursor = MagicMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=items)

    collection = MagicMock()
    collection.count_documents = AsyncMock(return_value=total)
    collection.find = MagicMock(return_value=cursor)
    return collection, cursor


# ---------------------------------------------------------------------------
# Tests – apaginate
# ---------------------------------------------------------------------------


class TestApaginate:
    """Cover apaginate function."""

    @pytest.mark.asyncio
    async def test_basic_include_total(self):
        """apaginate with include_total=True calls count_documents."""
        params, raw = _make_params(limit=5, offset=0, include_total=True)
        items = [{"_id": 1}, {"_id": 2}]
        collection, cursor = _make_collection(items=items, total=2)

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
            patch("fastapi_pagination.ext.motor.create_page") as mock_create,
        ):
            await apaginate(collection)

            collection.count_documents.assert_called_once()
            mock_create.assert_called_once_with(items, total=2, params=params)

    @pytest.mark.asyncio
    async def test_include_total_false(self):
        """apaginate with include_total=False does not call count_documents."""
        params, raw = _make_params(limit=5, offset=0, include_total=False)
        items = [{"_id": 1}]
        collection, cursor = _make_collection(items=items)

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
            patch("fastapi_pagination.ext.motor.create_page") as mock_create,
        ):
            await apaginate(collection)

            collection.count_documents.assert_not_called()
            mock_create.assert_called_once_with(items, total=None, params=params)

    @pytest.mark.asyncio
    async def test_sort_tuple(self):
        """apaginate with sort as a tuple calls cursor.sort(*sort)."""
        params, raw = _make_params(limit=5, offset=0, include_total=True)
        items = [{"_id": 1}]
        collection, cursor = _make_collection(items=items, total=1)

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
            patch("fastapi_pagination.ext.motor.create_page"),
        ):
            await apaginate(collection, sort=("field", 1))

            cursor.sort.assert_called_once_with("field", 1)

    @pytest.mark.asyncio
    async def test_sort_non_tuple(self):
        """apaginate with sort as a non-tuple calls cursor.sort(sort)."""
        params, raw = _make_params(limit=5, offset=0, include_total=True)
        items = [{"_id": 1}]
        collection, cursor = _make_collection(items=items, total=1)

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
            patch("fastapi_pagination.ext.motor.create_page"),
        ):
            await apaginate(collection, sort=[("field", 1)])

            cursor.sort.assert_called_once_with([("field", 1)])

    @pytest.mark.asyncio
    async def test_sort_none(self):
        """apaginate with sort=None does not call cursor.sort."""
        params, raw = _make_params(limit=5, offset=0, include_total=True)
        items = []
        collection, cursor = _make_collection(items=items, total=0)

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
            patch("fastapi_pagination.ext.motor.create_page"),
        ):
            await apaginate(collection, sort=None)

            cursor.sort.assert_not_called()

    @pytest.mark.asyncio
    async def test_with_query_filter(self):
        """apaginate passes query_filter to collection.find and count_documents."""
        params, raw = _make_params(limit=5, offset=0, include_total=True)
        items = [{"_id": 42}]
        collection, cursor = _make_collection(items=items, total=1)
        query_filter = {"status": "active"}

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
            patch("fastapi_pagination.ext.motor.create_page") as mock_create,
        ):
            await apaginate(collection, query_filter=query_filter)

            collection.count_documents.assert_called_once_with(query_filter)
            collection.find.assert_called_once_with(
                query_filter,
                skip=raw.offset,
                limit=raw.limit,
            )
            mock_create.assert_called_once_with(items, total=1, params=params)

    @pytest.mark.asyncio
    async def test_with_additional_data(self):
        """apaginate passes additional_data to create_page."""
        params, raw = _make_params(limit=5, offset=0, include_total=True)
        items = [{"_id": 1}]
        collection, _ = _make_collection(items=items, total=1)
        additional_data = {"extra": "value"}

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
            patch("fastapi_pagination.ext.motor.create_page") as mock_create,
        ):
            await apaginate(collection, additional_data=additional_data)

            mock_create.assert_called_once_with(items, total=1, params=params, extra="value")


# ---------------------------------------------------------------------------
# Tests – apaginate_aggregate
# ---------------------------------------------------------------------------


class TestApaginateAggregate:
    """Cover apaginate_aggregate function."""

    def _make_aggregate_collection(self, data_items=None, total=None):
        if data_items is None:
            data_items = []
        metadata = [{"total": total}] if total is not None else []
        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=[{"data": data_items, "metadata": metadata}])
        collection = MagicMock()
        collection.aggregate = MagicMock(return_value=cursor)
        return collection, cursor

    @pytest.mark.asyncio
    async def test_basic_aggregation(self):
        """apaginate_aggregate with basic pipeline."""
        params, raw = _make_params(limit=5, offset=2)
        items = [{"_id": 1}]
        collection, _ = self._make_aggregate_collection(data_items=items, total=1)

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
            patch("fastapi_pagination.ext.motor.create_page") as mock_create,
        ):
            await apaginate_aggregate(collection)

            mock_create.assert_called_once_with(items, total=1, params=params)

    @pytest.mark.asyncio
    async def test_empty_metadata_total_zero(self):
        """When metadata is empty, total becomes 0."""
        params, raw = _make_params(limit=5, offset=0)
        collection, _ = self._make_aggregate_collection(data_items=[], total=None)

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=[])),
            patch("fastapi_pagination.ext.motor.create_page") as mock_create,
        ):
            await apaginate_aggregate(collection)

            mock_create.assert_called_once_with([], total=0, params=params)

    @pytest.mark.asyncio
    async def test_filter_end_integer(self):
        """aggregation_filter_end as explicit integer splits the pipeline."""
        params, raw = _make_params(limit=5, offset=1)
        pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]
        items = [{"name": "x"}]
        collection, _ = self._make_aggregate_collection(data_items=items, total=1)

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
            patch("fastapi_pagination.ext.motor.create_page") as mock_create,
        ):
            await apaginate_aggregate(collection, aggregate_pipeline=pipeline, aggregation_filter_end=1)

            mock_create.assert_called_once_with(items, total=1, params=params)

    @pytest.mark.asyncio
    async def test_filter_end_auto(self):
        """aggregation_filter_end='auto' delegates to get_mongo_pipeline_filter_end."""
        params, raw = _make_params(limit=5, offset=0)
        pipeline = [{"$match": {}}, {"$project": {"name": 1}}]
        items = [{"name": "y"}]
        collection, _ = self._make_aggregate_collection(data_items=items, total=1)

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch(
                "fastapi_pagination.ext.motor.get_mongo_pipeline_filter_end",
                return_value=1,
            ) as mock_filter,
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
            patch("fastapi_pagination.ext.motor.create_page") as mock_create,
        ):
            await apaginate_aggregate(collection, aggregate_pipeline=pipeline, aggregation_filter_end="auto")

            mock_filter.assert_called_once()
            mock_create.assert_called_once_with(items, total=1, params=params)

    @pytest.mark.asyncio
    async def test_pipeline_transformer(self):
        """aggregation_pipeline_transformer replaces the pipeline before execution."""
        params, raw = _make_params(limit=5, offset=0)
        transformed = [{"$customStage": True}]
        items = [{"_id": 99}]
        collection, _ = self._make_aggregate_collection(data_items=items, total=1)
        transformer = MagicMock(return_value=transformed)

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
            patch("fastapi_pagination.ext.motor.create_page") as mock_create,
        ):
            await apaginate_aggregate(collection, aggregation_pipeline_transformer=transformer)

            transformer.assert_called_once()
            mock_create.assert_called_once_with(items, total=1, params=params)

    @pytest.mark.asyncio
    async def test_no_limit(self):
        """When raw_params.limit is None, no $limit stage is added."""
        params, raw = _make_params(limit=None, offset=0)
        collection, _ = self._make_aggregate_collection(data_items=[], total=0)

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=[])),
            patch("fastapi_pagination.ext.motor.create_page") as mock_create,
        ):
            await apaginate_aggregate(collection)

            mock_create.assert_called_once_with([], total=0, params=params)

    @pytest.mark.asyncio
    async def test_no_offset(self):
        """When raw_params.offset is None, no $skip stage is added."""
        params, raw = _make_params(limit=5, offset=None)
        collection, _ = self._make_aggregate_collection(data_items=[], total=0)

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=[])),
            patch("fastapi_pagination.ext.motor.create_page") as mock_create,
        ):
            await apaginate_aggregate(collection)

            mock_create.assert_called_once_with([], total=0, params=params)

    @pytest.mark.asyncio
    async def test_with_additional_data(self):
        """apaginate_aggregate passes additional_data to create_page."""
        params, raw = _make_params(limit=5, offset=0)
        items = [{"_id": 1}]
        collection, _ = self._make_aggregate_collection(data_items=items, total=1)
        additional_data = {"extra": "value"}

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
            patch("fastapi_pagination.ext.motor.create_page") as mock_create,
        ):
            await apaginate_aggregate(collection, additional_data=additional_data)

            mock_create.assert_called_once_with(items, total=1, params=params, extra="value")


# ---------------------------------------------------------------------------
# Tests – paginate (deprecated alias for apaginate)
# ---------------------------------------------------------------------------


class TestPaginate:
    """Cover paginate function (deprecated alias)."""

    @pytest.mark.asyncio
    async def test_delegates_to_apaginate(self):
        """paginate delegates to apaginate."""
        params, raw = _make_params(limit=5, offset=0, include_total=True)
        items = [{"_id": 1}]
        collection, _ = _make_collection(items=items, total=1)

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
            patch("fastapi_pagination.ext.motor.create_page") as mock_create,
        ):
            await paginate(collection)

            mock_create.assert_called_once_with(items, total=1, params=params)


# ---------------------------------------------------------------------------
# Tests – paginate_aggregate (deprecated alias for apaginate_aggregate)
# ---------------------------------------------------------------------------


class TestPaginateAggregate:
    """Cover paginate_aggregate function (deprecated alias)."""

    @pytest.mark.asyncio
    async def test_delegates_to_apaginate_aggregate(self):
        """paginate_aggregate delegates to apaginate_aggregate."""
        params, raw = _make_params(limit=5, offset=0)
        items = [{"_id": 1}]

        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=[{"data": items, "metadata": [{"total": 1}]}])
        collection = MagicMock()
        collection.aggregate = MagicMock(return_value=cursor)

        with (
            patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
            patch("fastapi_pagination.ext.motor.create_page") as mock_create,
        ):
            await paginate_aggregate(collection)

            mock_create.assert_called_once_with(items, total=1, params=params)
