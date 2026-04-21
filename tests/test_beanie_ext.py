from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId
from beanie.odm.queries.aggregation import AggregationQuery

from fastapi_pagination import Page, Params
from fastapi_pagination.api import set_page
from fastapi_pagination.cursor import CursorPage, CursorParams
from fastapi_pagination.ext.beanie import apaginate, paginate, parse_cursor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_OID = "507f1f77bcf86cd799439011"
VALID_OID_2 = "507f1f77bcf86cd799439012"


def _make_item(oid: str = VALID_OID) -> MagicMock:
    item = MagicMock()
    item.id = PydanticObjectId(oid)
    return item


def _make_find_many_query(items: list, count: int = 1) -> MagicMock:
    """Build a minimal mock that satisfies the FindMany path in apaginate."""
    count_mock = AsyncMock(return_value=count)
    find_chain = MagicMock()
    find_chain.count = count_mock

    to_list_mock = AsyncMock(return_value=items)
    find_many_chain = MagicMock()
    find_many_chain.to_list = to_list_mock

    query = MagicMock()
    query.find = MagicMock(return_value=find_chain)
    query.find_many = MagicMock(return_value=find_many_chain)
    return query


def _make_cursor_query(items: list, count: int = 10) -> MagicMock:
    """Build a mock for the cursor pagination path."""
    count_mock = AsyncMock(return_value=count)
    find_chain = MagicMock()
    find_chain.count = count_mock

    to_list_mock = AsyncMock(return_value=items)
    limit_chain = MagicMock()
    limit_chain.to_list = to_list_mock

    find_many_chain = MagicMock()
    find_many_chain.limit = MagicMock(return_value=limit_chain)
    find_many_chain.find = MagicMock(return_value=find_many_chain)
    find_many_chain.sort = MagicMock(return_value=find_many_chain)

    query = MagicMock()
    query.find = MagicMock(return_value=find_chain)
    query.find_many = MagicMock(return_value=find_many_chain)
    return query


def _make_aggregation_query(items: list, total: int = 1) -> MagicMock:
    """Build a mock AggregationQuery."""
    data = [{"data": items, "metadata": [{"total": total}]}]

    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=data)

    collection_mock = MagicMock()
    collection_mock.aggregate = MagicMock(return_value=cursor_mock)

    doc_model = MagicMock()
    doc_model.get_pymongo_collection = MagicMock(return_value=collection_mock)

    agg_query = MagicMock(spec=AggregationQuery)
    agg_query.aggregation_pipeline = [{"$match": {}}]
    agg_query.projection_model = None
    agg_query.session = None
    agg_query.pymongo_kwargs = {}
    agg_query.document_model = doc_model
    agg_query.clone = MagicMock(return_value=agg_query)
    agg_query.get_aggregation_pipeline = MagicMock(return_value=[{"$match": {}}, {"$facet": {}}])
    return agg_query


# ---------------------------------------------------------------------------
# parse_cursor tests
# ---------------------------------------------------------------------------


def test_parse_cursor_with_prefix():
    result = parse_cursor(f"prev_{VALID_OID}")
    assert result == PydanticObjectId(VALID_OID)


def test_parse_cursor_without_prefix():
    result = parse_cursor(VALID_OID)
    assert result == PydanticObjectId(VALID_OID)


def test_parse_cursor_invalid_raises_value_error():
    with pytest.raises(ValueError, match="Invalid cursor"):
        parse_cursor("notanobjectid!")


def test_parse_cursor_invalid_plain_string():
    with pytest.raises(ValueError, match="Invalid cursor"):
        parse_cursor("prefix_notvalid")


# ---------------------------------------------------------------------------
# apaginate – limit-offset (FindMany) path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_limit_offset_with_total():
    item = _make_item()
    query = _make_find_many_query([item], count=1)

    params = Params()
    with set_page(Page):
        result = await apaginate(query, params=params)

    assert result.total == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_apaginate_limit_offset_empty_results():
    query = _make_find_many_query([], count=0)

    params = Params()
    with set_page(Page):
        result = await apaginate(query, params=params)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_with_additional_data():
    item = _make_item()
    query = _make_find_many_query([item], count=1)

    params = Params()
    with set_page(Page):
        result = await apaginate(query, params=params, additional_data={})

    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_with_transformer():
    item = _make_item()
    query = _make_find_many_query([item], count=1)

    async def transformer(items):
        return [str(i.id) for i in items]

    params = Params()
    with set_page(Page):
        result = await apaginate(query, params=params, transformer=transformer)

    assert result.items == [VALID_OID]


# ---------------------------------------------------------------------------
# apaginate – cursor (FindMany) path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_cursor_no_cursor():
    item = _make_item()
    query = _make_cursor_query([item, _make_item(VALID_OID_2)], count=10)

    params = CursorParams()
    with set_page(CursorPage):
        result = await apaginate(query, params=params)

    assert len(result.items) <= 2


@pytest.mark.asyncio
async def test_apaginate_cursor_next_cursor():
    item = _make_item()
    query = _make_cursor_query([item], count=5)

    import base64

    encoded = base64.b64encode(VALID_OID.encode()).decode()
    params = CursorParams(cursor=encoded)

    with set_page(CursorPage):
        result = await apaginate(query, params=params)

    assert result is not None


@pytest.mark.asyncio
async def test_apaginate_cursor_prev_cursor():
    item = _make_item()
    query = _make_cursor_query([item], count=5)

    import base64

    prev_cursor = f"prev_{VALID_OID}"
    encoded = base64.b64encode(prev_cursor.encode()).decode()
    params = CursorParams(cursor=encoded)

    with set_page(CursorPage):
        result = await apaginate(query, params=params)

    assert result is not None


@pytest.mark.asyncio
async def test_apaginate_cursor_empty_results():
    query = _make_cursor_query([], count=0)

    params = CursorParams()
    with set_page(CursorPage):
        result = await apaginate(query, params=params)

    assert result.items == []


# ---------------------------------------------------------------------------
# apaginate – AggregationQuery path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_aggregation_limit_offset():
    item = {"_id": PydanticObjectId(VALID_OID)}
    agg_query = _make_aggregation_query([item], total=1)

    params = Params()
    with set_page(Page):
        result = await apaginate(agg_query, params=params)

    assert result.total == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_apaginate_aggregation_empty():
    agg_query = _make_aggregation_query([], total=0)
    agg_query.to_list = AsyncMock(return_value=[{"data": [], "metadata": []}])

    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=[{"data": [], "metadata": []}])
    agg_query.document_model.get_pymongo_collection.return_value.aggregate.return_value = cursor_mock

    params = Params()
    with set_page(Page):
        result = await apaginate(agg_query, params=params)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_aggregation_with_projection_model():
    item = {"_id": PydanticObjectId(VALID_OID)}
    agg_query = _make_aggregation_query([item], total=1)

    projection_model = MagicMock()
    agg_query.projection_model = projection_model

    with patch("fastapi_pagination.ext.beanie.get_projection", return_value={"_id": 1}):
        params = Params()
        with set_page(Page):
            result = await apaginate(agg_query, params=params)

    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_aggregation_with_pipeline_transformer():
    item = {"_id": PydanticObjectId(VALID_OID)}
    agg_query = _make_aggregation_query([item], total=1)

    def transformer(pipeline):
        return pipeline

    params = Params()
    with set_page(Page):
        result = await apaginate(agg_query, params=params, aggregation_pipeline_transformer=transformer)

    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_aggregation_filter_end_integer():
    item = {"_id": PydanticObjectId(VALID_OID)}
    agg_query = _make_aggregation_query([item], total=1)
    agg_query.aggregation_pipeline = [{"$match": {}}, {"$project": {}}, {"$sort": {}}]

    params = Params()
    with set_page(Page):
        result = await apaginate(agg_query, params=params, aggregation_filter_end=1)

    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_aggregation_filter_end_auto():
    item = {"_id": PydanticObjectId(VALID_OID)}
    agg_query = _make_aggregation_query([item], total=1)
    agg_query.aggregation_pipeline = [{"$match": {}}, {"$project": {}}]

    with patch("fastapi_pagination.ext.beanie.get_mongo_pipeline_filter_end", return_value=1):
        params = Params()
        with set_page(Page):
            result = await apaginate(agg_query, params=params, aggregation_filter_end="auto")

    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_aggregation_cursor_next():
    item = MagicMock()
    item.id = PydanticObjectId(VALID_OID)
    agg_query = _make_aggregation_query([item], total=5)

    import base64

    encoded = base64.b64encode(VALID_OID.encode()).decode()
    params = CursorParams(cursor=encoded)

    with set_page(CursorPage):
        result = await apaginate(agg_query, params=params)

    assert result is not None


@pytest.mark.asyncio
async def test_apaginate_aggregation_cursor_prev():
    item = MagicMock()
    item.id = PydanticObjectId(VALID_OID)
    agg_query = _make_aggregation_query([item], total=5)

    import base64

    prev_cursor = f"prev_{VALID_OID}"
    encoded = base64.b64encode(prev_cursor.encode()).decode()
    params = CursorParams(cursor=encoded)

    with set_page(CursorPage):
        result = await apaginate(agg_query, params=params)

    assert result is not None


@pytest.mark.asyncio
async def test_apaginate_aggregation_coroutine_cursor():
    """Test the inspect.iscoroutine(mongo_cursor) branch."""
    item = {"_id": PydanticObjectId(VALID_OID)}
    data = [{"data": [item], "metadata": [{"total": 1}]}]

    inner_cursor = MagicMock()
    inner_cursor.to_list = AsyncMock(return_value=data)

    collection_mock = MagicMock()
    collection_mock.aggregate = AsyncMock(return_value=inner_cursor)

    doc_model = MagicMock()
    doc_model.get_pymongo_collection = MagicMock(return_value=collection_mock)

    agg_query = MagicMock(spec=AggregationQuery)
    agg_query.aggregation_pipeline = [{"$match": {}}]
    agg_query.projection_model = None
    agg_query.session = None
    agg_query.pymongo_kwargs = {}
    agg_query.document_model = doc_model
    agg_query.clone = MagicMock(return_value=agg_query)
    agg_query.get_aggregation_pipeline = MagicMock(return_value=[{"$match": {}}, {"$facet": {}}])

    params = Params()
    with set_page(Page):
        result = await apaginate(agg_query, params=params)

    assert result.total == 1


# ---------------------------------------------------------------------------
# paginate (deprecated wrapper)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate():
    item = _make_item()
    query = _make_find_many_query([item], count=1)

    params = Params()
    with set_page(Page):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(query, params=params)

    assert result.total == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_paginate_passes_kwargs():
    item = _make_item()
    query = _make_find_many_query([item], count=1)

    params = Params()
    with set_page(Page):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(query, params=params, ignore_cache=True, fetch_links=False)

    assert result is not None
