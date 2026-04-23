"""Tests for fastapi_pagination.ext.beanie (parse_cursor, apaginate, paginate)."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# Module-level setup: mock external dependencies before importing the module
# under test. beanie, bson, and pymongo are not installed in this environment.
# ============================================================================


class _MockInvalidId(Exception):
    """Mock for bson.errors.InvalidId."""


class _MockAggregationQuery:
    """Mock AggregationQuery that supports isinstance() checks in apaginate."""

    def __init__(self) -> None:
        self.projection_model = None
        self.aggregation_pipeline: list = []
        self.session = None
        self.pymongo_kwargs: dict = {}
        self.document_model = MagicMock()

    def clone(self) -> "_MockAggregationQuery":
        q = _MockAggregationQuery()
        q.projection_model = self.projection_model
        q.aggregation_pipeline = list(self.aggregation_pipeline)
        q.session = self.session
        q.pymongo_kwargs = dict(self.pymongo_kwargs)
        q.document_model = self.document_model
        return q

    def get_aggregation_pipeline(self) -> list:
        return list(self.aggregation_pipeline)


class _MockFindManyQuery:
    """Mock FindMany query that supports fluent chaining used by apaginate."""

    def __init__(self, items=None, total: int = 5) -> None:
        self._items = items if items is not None else []
        self._total = total

    def __copy__(self) -> "_MockFindManyQuery":
        return _MockFindManyQuery(items=list(self._items), total=self._total)

    def find(self, *args, **kwargs) -> "_MockFindManyQuery":
        return self

    def find_many(self, *args, **kwargs) -> "_MockFindManyQuery":
        return self

    def limit(self, *args, **kwargs) -> "_MockFindManyQuery":
        return self

    def sort(self, *args, **kwargs) -> "_MockFindManyQuery":
        return self

    async def to_list(self) -> list:
        return list(self._items)

    async def count(self) -> int:
        return self._total


# Build mock modules
_mock_pydantic_oid_cls = MagicMock()

_mock_beanie = MagicMock()
_mock_beanie.Document = MagicMock()
_mock_beanie.PydanticObjectId = _mock_pydantic_oid_cls

_mock_bson_errors = MagicMock()
_mock_bson_errors.InvalidId = _MockInvalidId

_mock_odm_queries_aggregation = MagicMock()
_mock_odm_queries_aggregation.AggregationQuery = _MockAggregationQuery

_mock_odm_queries_find = MagicMock()
_mock_odm_queries_find.FindMany = _MockFindManyQuery

_MOCK_MODULES = {
    "beanie": _mock_beanie,
    "beanie.odm": MagicMock(),
    "beanie.odm.enums": MagicMock(),
    "beanie.odm.interfaces": MagicMock(),
    "beanie.odm.interfaces.aggregate": MagicMock(),
    "beanie.odm.queries": MagicMock(),
    "beanie.odm.queries.aggregation": _mock_odm_queries_aggregation,
    "beanie.odm.queries.find": _mock_odm_queries_find,
    "beanie.odm.utils": MagicMock(),
    "beanie.odm.utils.projection": MagicMock(),
    "bson": MagicMock(),
    "bson.errors": _mock_bson_errors,
    "pymongo": MagicMock(),
    "pymongo.asynchronous": MagicMock(),
    "pymongo.asynchronous.client_session": MagicMock(),
}

for _mod_name, _mock_obj in _MOCK_MODULES.items():
    sys.modules.setdefault(_mod_name, _mock_obj)

# Now safe to import the module under test
from fastapi_pagination.ext.beanie import apaginate, paginate, parse_cursor  # noqa: E402
from fastapi_pagination.bases import CursorRawParams, RawParams  # noqa: E402


# ============================================================================
# Helpers
# ============================================================================


def _make_mock_item(oid: str = "507f1f77bcf86cd799439011") -> MagicMock:
    item = MagicMock()
    item.id = oid
    return item


def _make_aggr_query(items=None, total: int = 0, pipeline=None):
    """Build a _MockAggregationQuery wired up with a mock collection."""
    if items is None:
        items = []
    if pipeline is None:
        pipeline = [{"$match": {}}]

    metadata = [{"total": total}] if total else []
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[{"data": items, "metadata": metadata}])

    mock_collection = MagicMock()
    mock_collection.aggregate.return_value = mock_cursor

    mock_doc_model = MagicMock()
    mock_doc_model.get_pymongo_collection.return_value = mock_collection

    query = _MockAggregationQuery()
    query.document_model = mock_doc_model
    query.aggregation_pipeline = list(pipeline)
    return query


# ============================================================================
# Fixture: patch create_page and apply_items_transformer for apaginate tests
# ============================================================================


@pytest.fixture()
def patched_page_internals():
    mock_page = MagicMock()
    with (
        patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page) as mock_create,
        patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new=AsyncMock(side_effect=lambda items, t, **kw: items),
        ) as mock_apply,
    ):
        yield mock_create, mock_apply, mock_page


# ============================================================================
# Tests: parse_cursor (lines 29-33)
# ============================================================================


class TestParseCursor:
    def setup_method(self) -> None:
        _mock_pydantic_oid_cls.reset_mock()
        _mock_pydantic_oid_cls.side_effect = None

    def test_parse_cursor_with_next_prefix(self) -> None:
        mock_oid = MagicMock()
        _mock_pydantic_oid_cls.return_value = mock_oid

        result = parse_cursor("next_507f1f77bcf86cd799439011")

        _mock_pydantic_oid_cls.assert_called_once_with("507f1f77bcf86cd799439011")
        assert result == mock_oid

    def test_parse_cursor_with_prev_prefix(self) -> None:
        mock_oid = MagicMock()
        _mock_pydantic_oid_cls.return_value = mock_oid

        result = parse_cursor("prev_507f1f77bcf86cd799439011")

        _mock_pydantic_oid_cls.assert_called_once_with("507f1f77bcf86cd799439011")
        assert result == mock_oid

    def test_parse_cursor_without_prefix(self) -> None:
        mock_oid = MagicMock()
        _mock_pydantic_oid_cls.return_value = mock_oid

        result = parse_cursor("507f1f77bcf86cd799439011")

        _mock_pydantic_oid_cls.assert_called_once_with("507f1f77bcf86cd799439011")
        assert result == mock_oid

    def test_parse_cursor_invalid_raises_value_error(self) -> None:
        _mock_pydantic_oid_cls.side_effect = _MockInvalidId("invalid id")

        with pytest.raises(ValueError, match="Invalid cursor"):
            parse_cursor("invalid_cursor")


# ============================================================================
# Tests: paginate (lines 223, 238) — deprecated wrapper around apaginate
# ============================================================================


class TestPaginate:
    @pytest.mark.asyncio
    async def test_paginate_delegates_to_apaginate(self) -> None:
        mock_query = MagicMock()
        mock_result = MagicMock()

        with patch(
            "fastapi_pagination.ext.beanie.apaginate",
            new=AsyncMock(return_value=mock_result),
        ) as mock_apaginate:
            result = await paginate(mock_query)

        assert result == mock_result
        mock_apaginate.assert_awaited_once()
        assert mock_apaginate.call_args.args[0] is mock_query

    @pytest.mark.asyncio
    async def test_paginate_forwards_kwargs(self) -> None:
        mock_query = MagicMock()
        mock_result = MagicMock()
        extra_data = {"key": "value"}

        with patch(
            "fastapi_pagination.ext.beanie.apaginate",
            new=AsyncMock(return_value=mock_result),
        ) as mock_apaginate:
            result = await paginate(mock_query, additional_data=extra_data)

        assert result == mock_result
        call_kwargs = mock_apaginate.call_args.kwargs
        assert call_kwargs["additional_data"] == extra_data


# ============================================================================
# Tests: apaginate with FindMany query (limit-offset params)
# ============================================================================


class TestApaginateFindManyLimitOffset:
    @pytest.mark.asyncio
    async def test_with_total(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        items = [_make_mock_item(), _make_mock_item()]
        query = _MockFindManyQuery(items=items, total=20)
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        assert mock_create.call_args.kwargs["total"] == 20
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_without_total(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        items = [_make_mock_item()]
        query = _MockFindManyQuery(items=items, total=5)
        raw_params = RawParams(limit=10, offset=0, include_total=False)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        assert mock_create.call_args.kwargs["total"] is None
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_with_offset(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        items = [_make_mock_item()]
        query = _MockFindManyQuery(items=items, total=100)
        raw_params = RawParams(limit=10, offset=20, include_total=True)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        assert mock_create.call_args.kwargs["total"] == 100
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_with_none_limit(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        items = [_make_mock_item()]
        query = _MockFindManyQuery(items=items, total=100)
        raw_params = RawParams(limit=None, offset=None, include_total=True)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        assert result == mock_page


# ============================================================================
# Tests: apaginate with FindMany query (cursor params)
# ============================================================================


class TestApaginateFindManyCursor:
    def setup_method(self) -> None:
        _mock_pydantic_oid_cls.reset_mock()
        _mock_pydantic_oid_cls.side_effect = None
        _mock_pydantic_oid_cls.return_value = MagicMock()

    @pytest.mark.asyncio
    async def test_cursor_none_no_items(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        query = _MockFindManyQuery(items=[], total=0)
        raw_params = CursorRawParams(cursor=None, size=10, include_total=False)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        kwargs = mock_create.call_args.kwargs
        assert kwargs["next_"] is None
        assert kwargs["previous"] is None
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_cursor_none_with_items_fills_next(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        mock_item = _make_mock_item("507f1f77bcf86cd799439011")
        # size+1 items so next link is available
        query = _MockFindManyQuery(items=[mock_item] * 11, total=0)
        raw_params = CursorRawParams(cursor=None, size=10, include_total=False)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        kwargs = mock_create.call_args.kwargs
        assert kwargs["next_"] == "507f1f77bcf86cd799439011"
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_cursor_next_value(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        mock_item = _make_mock_item("507f1f77bcf86cd799439011")
        query = _MockFindManyQuery(items=[mock_item] * 11, total=0)
        raw_params = CursorRawParams(cursor="next_507f1f77bcf86cd799439011", size=10, include_total=False)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_cursor_prev_value_reverses_items(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        item_a = _make_mock_item("aaaaaaaaaaaaaaaaaaaaaaaa")
        item_b = _make_mock_item("bbbbbbbbbbbbbbbbbbbbbbbb")
        # Return size+1 items (11); after slicing to 10 and reversing:
        query = _MockFindManyQuery(items=[item_a] * 5 + [item_b] * 6, total=0)
        raw_params = CursorRawParams(cursor="prev_507f1f77bcf86cd799439011", size=10, include_total=False)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_cursor_with_additional_data(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        mock_item = _make_mock_item()
        query = _MockFindManyQuery(items=[], total=0)
        raw_params = CursorRawParams(cursor=None, size=10, include_total=False)
        mock_params = MagicMock()
        extra = {"custom": "value"}

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query, additional_data=extra)

        mock_create.assert_called_once()
        assert result == mock_page


# ============================================================================
# Tests: apaginate with AggregationQuery (lines 59-147)
# ============================================================================


class TestApaginateAggregationQuery:
    def setup_method(self) -> None:
        _mock_pydantic_oid_cls.reset_mock()
        _mock_pydantic_oid_cls.side_effect = None
        _mock_pydantic_oid_cls.return_value = MagicMock()

    @pytest.mark.asyncio
    async def test_limit_offset_with_data(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        items = [_make_mock_item(), _make_mock_item()]
        query = _make_aggr_query(items=items, total=100)
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        assert mock_create.call_args.kwargs["total"] == 100
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_limit_offset_empty_metadata_total_zero(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        query = _make_aggr_query(items=[], total=0)
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        assert mock_create.call_args.kwargs["total"] == 0
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_limit_offset_with_offset(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        query = _make_aggr_query(total=50)
        raw_params = RawParams(limit=10, offset=5, include_total=True)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_cursor_none_empty_items(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        query = _make_aggr_query(items=[], total=0)
        raw_params = CursorRawParams(cursor=None, size=10, include_total=False)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        kwargs = mock_create.call_args.kwargs
        assert kwargs.get("next_") is None
        assert kwargs.get("previous") is None
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_cursor_none_with_items(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        mock_item = _make_mock_item("507f1f77bcf86cd799439011")
        query = _make_aggr_query(items=[mock_item], total=1)
        raw_params = CursorRawParams(cursor=None, size=10, include_total=False)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        kwargs = mock_create.call_args.kwargs
        assert kwargs["next_"] == "507f1f77bcf86cd799439011"
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_cursor_prev_reverses_items(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        mock_item = _make_mock_item("507f1f77bcf86cd799439011")
        query = _make_aggr_query(items=[mock_item], total=1)
        raw_params = CursorRawParams(cursor="prev_507f1f77bcf86cd799439011", size=10, include_total=False)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_cursor_next_value(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        mock_item = _make_mock_item("507f1f77bcf86cd799439011")
        query = _make_aggr_query(items=[mock_item], total=1)
        raw_params = CursorRawParams(cursor="next_507f1f77bcf86cd799439011", size=10, include_total=False)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_with_projection_model(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        query = _make_aggr_query(total=0)
        query.projection_model = MagicMock()
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()

        with (
            patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)),
            patch("fastapi_pagination.ext.beanie.get_projection", return_value={"field": 1}),
        ):
            result = await apaginate(query)

        mock_create.assert_called_once()
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_with_projection_model_none_projection(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        query = _make_aggr_query(total=0)
        query.projection_model = MagicMock()
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()

        with (
            patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)),
            patch("fastapi_pagination.ext.beanie.get_projection", return_value=None),
        ):
            result = await apaginate(query)

        mock_create.assert_called_once()
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_with_aggregation_filter_end_explicit(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        query = _make_aggr_query(pipeline=[{"$match": {}}, {"$project": {"name": 1}}])
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query, aggregation_filter_end=1)

        mock_create.assert_called_once()
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_with_aggregation_filter_end_auto(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        query = _make_aggr_query(pipeline=[{"$match": {}}, {"$project": {"name": 1}}])
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query, aggregation_filter_end="auto")

        mock_create.assert_called_once()
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_with_pipeline_transformer(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        query = _make_aggr_query(total=0)
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()
        transformed_pipeline = [{"$match": {}}, {"$limit": 100}]
        transformer = MagicMock(return_value=transformed_pipeline)

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query, aggregation_pipeline_transformer=transformer)

        mock_create.assert_called_once()
        transformer.assert_called_once()
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_with_none_limit(self, patched_page_internals) -> None:
        mock_create, _, mock_page = patched_page_internals

        query = _make_aggr_query(total=0)
        raw_params = RawParams(limit=None, offset=None, include_total=True)
        mock_params = MagicMock()

        with patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params)):
            result = await apaginate(query)

        mock_create.assert_called_once()
        assert result == mock_page
