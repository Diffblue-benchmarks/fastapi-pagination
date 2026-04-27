from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from bson import ObjectId
from beanie.odm.queries.aggregation import AggregationQuery

from fastapi_pagination.bases import CursorRawParams, RawParams
from fastapi_pagination.ext.beanie import apaginate, paginate, parse_cursor


class TestParseCursor:
    def test_with_prev_prefix(self):
        valid_id = str(ObjectId())
        result = parse_cursor(f"prev_{valid_id}")
        assert str(result) == valid_id

    def test_with_next_prefix(self):
        valid_id = str(ObjectId())
        result = parse_cursor(f"next_{valid_id}")
        assert str(result) == valid_id

    def test_without_prefix(self):
        valid_id = str(ObjectId())
        result = parse_cursor(valid_id)
        assert str(result) == valid_id

    def test_invalid_cursor_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid cursor"):
            parse_cursor("prev_not_an_objectid")

    def test_invalid_cursor_without_prefix_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid cursor"):
            parse_cursor("_totally_invalid")


def _make_aggr_mock():
    mock = MagicMock()
    mock.__class__ = AggregationQuery
    mock.projection_model = None
    mock.aggregation_pipeline = []
    mock.session = None
    mock.pymongo_kwargs = {}
    mock.clone.return_value = mock
    mock.get_aggregation_pipeline.return_value = []
    return mock


@pytest.mark.asyncio
class TestApaginateLimitOffset:
    async def test_with_include_total(self, mocker):
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        mock_items = [MagicMock(), MagicMock()]
        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=mock_items,
        )

        find_chain = MagicMock()
        find_chain.count = AsyncMock(return_value=5)

        find_many_chain = MagicMock()
        find_many_chain.to_list = AsyncMock(return_value=mock_items)

        mock_query = MagicMock()
        mock_query.find.return_value = find_chain
        mock_query.find_many.return_value = find_many_chain

        mocker.patch("fastapi_pagination.ext.beanie.copy", return_value=mock_query)

        result = await apaginate(mock_query)
        assert result == mock_page

    async def test_without_include_total(self, mocker):
        raw_params = RawParams(limit=5, offset=0, include_total=False)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        mock_items = []
        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=mock_items,
        )

        find_many_chain = MagicMock()
        find_many_chain.to_list = AsyncMock(return_value=mock_items)

        mock_query = MagicMock()
        mock_query.find_many.return_value = find_many_chain

        mocker.patch("fastapi_pagination.ext.beanie.copy", return_value=mock_query)

        result = await apaginate(mock_query)
        assert result == mock_page

    async def test_with_additional_data(self, mocker):
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        mock_items = []
        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=mock_items,
        )

        find_chain = MagicMock()
        find_chain.count = AsyncMock(return_value=0)

        find_many_chain = MagicMock()
        find_many_chain.to_list = AsyncMock(return_value=mock_items)

        mock_query = MagicMock()
        mock_query.find.return_value = find_chain
        mock_query.find_many.return_value = find_many_chain

        mocker.patch("fastapi_pagination.ext.beanie.copy", return_value=mock_query)

        result = await apaginate(mock_query, additional_data={"custom": "value"})
        assert result == mock_page

    async def test_with_offset(self, mocker):
        raw_params = RawParams(limit=10, offset=5, include_total=True)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        mock_items = []
        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=mock_items,
        )

        find_chain = MagicMock()
        find_chain.count = AsyncMock(return_value=0)

        find_many_chain = MagicMock()
        find_many_chain.to_list = AsyncMock(return_value=mock_items)

        mock_query = MagicMock()
        mock_query.find.return_value = find_chain
        mock_query.find_many.return_value = find_many_chain

        mocker.patch("fastapi_pagination.ext.beanie.copy", return_value=mock_query)

        result = await apaginate(mock_query)
        assert result == mock_page


@pytest.mark.asyncio
class TestApaginateCursor:
    async def test_cursor_next_with_items(self, mocker):
        valid_id = str(ObjectId())
        cursor_str = f"next_{valid_id}"
        raw_params = CursorRawParams(cursor=cursor_str, size=2, include_total=False)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        item1 = MagicMock()
        item1.id = ObjectId()
        item2 = MagicMock()
        item2.id = ObjectId()
        items_from_db = [item1, item2, MagicMock()]

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=[item1, item2],
        )

        limit_chain = MagicMock()
        limit_chain.to_list = AsyncMock(return_value=items_from_db)

        find_chain = MagicMock()
        find_chain.limit = MagicMock(return_value=limit_chain)

        find_many_chain = MagicMock()
        find_many_chain.find = MagicMock(return_value=find_chain)
        find_many_chain.limit = MagicMock(return_value=limit_chain)

        mock_query = MagicMock()
        mock_query.find_many.return_value = find_many_chain

        mocker.patch("fastapi_pagination.ext.beanie.copy", return_value=mock_query)

        result = await apaginate(mock_query)
        assert result == mock_page

    async def test_cursor_prev_with_items(self, mocker):
        valid_id = str(ObjectId())
        cursor_str = f"prev_{valid_id}"
        raw_params = CursorRawParams(cursor=cursor_str, size=2, include_total=False)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        item1 = MagicMock()
        item1.id = ObjectId()
        item2 = MagicMock()
        item2.id = ObjectId()
        items_from_db = [item1, item2]

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=list(reversed(items_from_db)),
        )

        limit_chain = MagicMock()
        limit_chain.to_list = AsyncMock(return_value=items_from_db)

        sort_chain = MagicMock()
        sort_chain.limit = MagicMock(return_value=limit_chain)

        find_chain = MagicMock()
        find_chain.sort = MagicMock(return_value=sort_chain)

        find_many_chain = MagicMock()
        find_many_chain.find = MagicMock(return_value=find_chain)

        mock_query = MagicMock()
        mock_query.find_many.return_value = find_many_chain

        mocker.patch("fastapi_pagination.ext.beanie.copy", return_value=mock_query)

        result = await apaginate(mock_query)
        assert result == mock_page

    async def test_cursor_next_no_more_items(self, mocker):
        valid_id = str(ObjectId())
        cursor_str = f"next_{valid_id}"
        raw_params = CursorRawParams(cursor=cursor_str, size=5, include_total=False)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=[],
        )

        limit_chain = MagicMock()
        limit_chain.to_list = AsyncMock(return_value=[])

        find_chain = MagicMock()
        find_chain.limit = MagicMock(return_value=limit_chain)

        find_many_chain = MagicMock()
        find_many_chain.find = MagicMock(return_value=find_chain)

        mock_query = MagicMock()
        mock_query.find_many.return_value = find_many_chain

        mocker.patch("fastapi_pagination.ext.beanie.copy", return_value=mock_query)

        result = await apaginate(mock_query)
        assert result == mock_page

    async def test_cursor_none(self, mocker):
        raw_params = CursorRawParams(cursor=None, size=10, include_total=False)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        item = MagicMock()
        item.id = ObjectId()
        items_from_db = [item]

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=items_from_db,
        )

        limit_chain = MagicMock()
        limit_chain.to_list = AsyncMock(return_value=items_from_db)

        find_many_chain = MagicMock()
        find_many_chain.limit = MagicMock(return_value=limit_chain)

        mock_query = MagicMock()
        mock_query.find_many.return_value = find_many_chain

        mocker.patch("fastapi_pagination.ext.beanie.copy", return_value=mock_query)

        result = await apaginate(mock_query)
        assert result == mock_page


@pytest.mark.asyncio
class TestApaginateAggregation:
    async def test_basic_limit_offset(self, mocker):
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=[],
        )

        result_data = {"data": [], "metadata": [{"total": 3}]}
        mongo_cursor = MagicMock()
        mongo_cursor.to_list = AsyncMock(return_value=[result_data])

        mock_collection = MagicMock()
        mock_collection.aggregate = MagicMock(return_value=mongo_cursor)

        mock_aggr = _make_aggr_mock()
        mock_aggr.document_model.get_pymongo_collection.return_value = mock_collection

        result = await apaginate(mock_aggr)
        assert result == mock_page

    async def test_empty_metadata_gives_zero_total(self, mocker):
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=[],
        )

        result_data = {"data": [], "metadata": []}
        mongo_cursor = MagicMock()
        mongo_cursor.to_list = AsyncMock(return_value=[result_data])

        mock_collection = MagicMock()
        mock_collection.aggregate = MagicMock(return_value=mongo_cursor)

        mock_aggr = _make_aggr_mock()
        mock_aggr.document_model.get_pymongo_collection.return_value = mock_collection

        result = await apaginate(mock_aggr)
        assert result == mock_page

    async def test_with_aggregation_filter_end_auto(self, mocker):
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=[],
        )
        mocker.patch("fastapi_pagination.ext.beanie.get_mongo_pipeline_filter_end", return_value=1)

        result_data = {"data": [], "metadata": [{"total": 0}]}
        mongo_cursor = MagicMock()
        mongo_cursor.to_list = AsyncMock(return_value=[result_data])

        mock_collection = MagicMock()
        mock_collection.aggregate = MagicMock(return_value=mongo_cursor)

        mock_aggr = _make_aggr_mock()
        mock_aggr.aggregation_pipeline = [{"$match": {}}, {"$project": {"name": 1}}]
        mock_aggr.document_model.get_pymongo_collection.return_value = mock_collection

        result = await apaginate(mock_aggr, aggregation_filter_end="auto")
        assert result == mock_page

    async def test_with_aggregation_filter_end_int(self, mocker):
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=[],
        )

        result_data = {"data": [], "metadata": [{"total": 0}]}
        mongo_cursor = MagicMock()
        mongo_cursor.to_list = AsyncMock(return_value=[result_data])

        mock_collection = MagicMock()
        mock_collection.aggregate = MagicMock(return_value=mongo_cursor)

        mock_aggr = _make_aggr_mock()
        mock_aggr.aggregation_pipeline = [{"$match": {}}, {"$project": {"name": 1}}]
        mock_aggr.document_model.get_pymongo_collection.return_value = mock_collection

        result = await apaginate(mock_aggr, aggregation_filter_end=1)
        assert result == mock_page

    async def test_with_pipeline_transformer(self, mocker):
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=[],
        )

        result_data = {"data": [], "metadata": [{"total": 0}]}
        mongo_cursor = MagicMock()
        mongo_cursor.to_list = AsyncMock(return_value=[result_data])

        mock_collection = MagicMock()
        mock_collection.aggregate = MagicMock(return_value=mongo_cursor)

        mock_aggr = _make_aggr_mock()
        mock_aggr.get_aggregation_pipeline.return_value = [{"$match": {}}]
        mock_aggr.document_model.get_pymongo_collection.return_value = mock_collection

        transformed_pipeline = [{"$match": {}}, {"$limit": 10}]
        pipeline_transformer = MagicMock(return_value=transformed_pipeline)

        result = await apaginate(mock_aggr, aggregation_pipeline_transformer=pipeline_transformer)
        pipeline_transformer.assert_called_once_with([{"$match": {}}])
        assert result == mock_page

    async def test_aggregation_coroutine_cursor(self, mocker):
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=[],
        )

        result_data = {"data": [], "metadata": [{"total": 0}]}
        actual_cursor = MagicMock()
        actual_cursor.to_list = AsyncMock(return_value=[result_data])

        async def coro_cursor():
            return actual_cursor

        mock_collection = MagicMock()
        mock_collection.aggregate = MagicMock(return_value=coro_cursor())

        mock_aggr = _make_aggr_mock()
        mock_aggr.document_model.get_pymongo_collection.return_value = mock_collection

        result = await apaginate(mock_aggr)
        assert result == mock_page

    async def test_aggregation_limit_offset_with_offset(self, mocker):
        raw_params = RawParams(limit=5, offset=10, include_total=True)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=[],
        )

        result_data = {"data": [], "metadata": [{"total": 20}]}
        mongo_cursor = MagicMock()
        mongo_cursor.to_list = AsyncMock(return_value=[result_data])

        mock_collection = MagicMock()
        mock_collection.aggregate = MagicMock(return_value=mongo_cursor)

        mock_aggr = _make_aggr_mock()
        mock_aggr.document_model.get_pymongo_collection.return_value = mock_collection

        result = await apaginate(mock_aggr)
        assert result == mock_page

    async def test_aggregation_cursor_prev(self, mocker):
        valid_id = str(ObjectId())
        cursor_str = f"prev_{valid_id}"
        raw_params = CursorRawParams(cursor=cursor_str, size=2, include_total=False)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        item1 = MagicMock()
        item1.id = ObjectId()
        item2 = MagicMock()
        item2.id = ObjectId()
        items = [item1, item2]

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=list(reversed(items)),
        )

        result_data = {"data": items, "metadata": []}
        mongo_cursor = MagicMock()
        mongo_cursor.to_list = AsyncMock(return_value=[result_data])

        mock_collection = MagicMock()
        mock_collection.aggregate = MagicMock(return_value=mongo_cursor)

        mock_aggr = _make_aggr_mock()
        mock_aggr.document_model.get_pymongo_collection.return_value = mock_collection

        result = await apaginate(mock_aggr)
        assert result == mock_page

    async def test_aggregation_cursor_next(self, mocker):
        valid_id = str(ObjectId())
        cursor_str = f"next_{valid_id}"
        raw_params = CursorRawParams(cursor=cursor_str, size=2, include_total=False)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        item1 = MagicMock()
        item1.id = ObjectId()
        items = [item1]

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=items,
        )

        result_data = {"data": items, "metadata": []}
        mongo_cursor = MagicMock()
        mongo_cursor.to_list = AsyncMock(return_value=[result_data])

        mock_collection = MagicMock()
        mock_collection.aggregate = MagicMock(return_value=mongo_cursor)

        mock_aggr = _make_aggr_mock()
        mock_aggr.document_model.get_pymongo_collection.return_value = mock_collection

        result = await apaginate(mock_aggr)
        assert result == mock_page

    async def test_aggregation_with_projection_model(self, mocker):
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=[],
        )
        mocker.patch(
            "fastapi_pagination.ext.beanie.get_projection",
            return_value={"name": 1, "_id": 0},
        )

        result_data = {"data": [], "metadata": [{"total": 0}]}
        mongo_cursor = MagicMock()
        mongo_cursor.to_list = AsyncMock(return_value=[result_data])

        mock_collection = MagicMock()
        mock_collection.aggregate = MagicMock(return_value=mongo_cursor)

        mock_aggr = _make_aggr_mock()
        mock_aggr.projection_model = MagicMock()
        mock_aggr.document_model.get_pymongo_collection.return_value = mock_collection

        result = await apaginate(mock_aggr)
        assert result == mock_page

    async def test_aggregation_with_projection_model_none_projection(self, mocker):
        raw_params = RawParams(limit=10, offset=0, include_total=True)
        mock_params = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.verify_params", return_value=(mock_params, raw_params))

        mock_page = MagicMock()
        mocker.patch("fastapi_pagination.ext.beanie.create_page", return_value=mock_page)
        mocker.patch(
            "fastapi_pagination.ext.beanie.apply_items_transformer",
            new_callable=AsyncMock,
            return_value=[],
        )
        mocker.patch(
            "fastapi_pagination.ext.beanie.get_projection",
            return_value=None,
        )

        result_data = {"data": [], "metadata": [{"total": 0}]}
        mongo_cursor = MagicMock()
        mongo_cursor.to_list = AsyncMock(return_value=[result_data])

        mock_collection = MagicMock()
        mock_collection.aggregate = MagicMock(return_value=mongo_cursor)

        mock_aggr = _make_aggr_mock()
        mock_aggr.projection_model = MagicMock()
        mock_aggr.document_model.get_pymongo_collection.return_value = mock_collection

        result = await apaginate(mock_aggr)
        assert result == mock_page


@pytest.mark.asyncio
class TestPaginate:
    async def test_paginate_calls_apaginate(self, mocker):
        mock_result = MagicMock()
        mock_apaginate = mocker.patch(
            "fastapi_pagination.ext.beanie.apaginate",
            new_callable=AsyncMock,
            return_value=mock_result,
        )

        mock_query = MagicMock()
        result = await paginate(mock_query)

        assert result == mock_result
        mock_apaginate.assert_called_once()

    async def test_paginate_passes_params(self, mocker):
        mock_result = MagicMock()
        mock_apaginate = mocker.patch(
            "fastapi_pagination.ext.beanie.apaginate",
            new_callable=AsyncMock,
            return_value=mock_result,
        )

        mock_query = MagicMock()
        mock_params = MagicMock()
        result = await paginate(mock_query, params=mock_params, ignore_cache=True)

        assert result == mock_result
        call_kwargs = mock_apaginate.call_args
        assert call_kwargs is not None
