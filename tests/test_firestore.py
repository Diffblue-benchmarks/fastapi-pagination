"""Tests for fastapi_pagination.ext.firestore module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastapi_pagination.api import set_page
from fastapi_pagination.bases import CursorRawParams, RawParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.firestore import (
    _apply_cursor,
    _convert_raw_items,
    _cursor_flow,
    _fetch_cursor,
    _firebase_flow,
    _get_total,
    _limit_offset_flow,
    _total_flow,
    apaginate,
    paginate,
)
from fastapi_pagination.flow import run_async_flow, run_sync_flow


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_doc_snapshot(doc_id: str, data: dict):
    """Build a mock DocumentSnapshot."""
    snap = MagicMock()
    snap.id = doc_id
    snap.to_dict.return_value = data
    return snap


def _make_query(items=None, count_value=3):
    """Build a mock synchronous Query."""
    query = MagicMock()
    items = items or []
    query.get.return_value = items
    query.start_after.return_value = query
    query.limit.return_value = query
    query.offset.return_value = query

    # aggregation chain: query.count("total").get(transaction=...)
    agg_result_entry = MagicMock()
    agg_result_entry.value = count_value
    agg_query = MagicMock()
    agg_query.get.return_value = [[agg_result_entry]]
    query.count.return_value = agg_query  # for AggregationQuery(query).count(...)

    return query


def _make_async_query(items=None, count_value=3):
    """Build a mock asynchronous Query."""
    query = MagicMock()
    items = items or []
    query.get = AsyncMock(return_value=items)
    query.start_after.return_value = query
    query.limit.return_value = query
    query.offset.return_value = query

    agg_result_entry = MagicMock()
    agg_result_entry.value = count_value
    agg_query = MagicMock()
    agg_query.get = AsyncMock(return_value=[[agg_result_entry]])
    query.count.return_value = agg_query

    return query


# ---------------------------------------------------------------------------
# _apply_cursor
# ---------------------------------------------------------------------------


def test_apply_cursor_with_snapshot():
    query = MagicMock()
    after_query = MagicMock()
    limited_query = MagicMock()
    query.start_after.return_value = after_query
    after_query.limit.return_value = limited_query

    params = CursorRawParams(cursor=None, size=10)
    snapshot = MagicMock()

    result = _apply_cursor(query, params, snapshot)

    query.start_after.assert_called_once_with(snapshot)
    after_query.limit.assert_called_once_with(10)
    assert result is limited_query


def test_apply_cursor_without_snapshot():
    query = MagicMock()
    limited_query = MagicMock()
    query.limit.return_value = limited_query

    params = CursorRawParams(cursor=None, size=5)

    result = _apply_cursor(query, params, None)

    query.start_after.assert_not_called()
    query.limit.assert_called_once_with(5)
    assert result is limited_query


def test_apply_cursor_no_size():
    query = MagicMock()
    params = CursorRawParams(cursor=None, size=None, include_total=False)

    result = _apply_cursor(query, params, None)

    query.limit.assert_not_called()
    assert result is query


# ---------------------------------------------------------------------------
# _convert_raw_items
# ---------------------------------------------------------------------------


def test_convert_raw_items_basic():
    snap1 = _make_doc_snapshot("doc1", {"name": "Alice"})
    snap2 = _make_doc_snapshot("doc2", {"name": "Bob"})

    result = _convert_raw_items([snap1, snap2])

    assert result == [{"name": "Alice", "id": "doc1"}, {"name": "Bob", "id": "doc2"}]


def test_convert_raw_items_empty_dict():
    snap = _make_doc_snapshot("doc3", None)
    snap.to_dict.return_value = None

    result = _convert_raw_items([snap])

    assert result == [{"id": "doc3"}]


def test_convert_raw_items_empty_list():
    result = _convert_raw_items([])
    assert result == []


# ---------------------------------------------------------------------------
# _get_total
# ---------------------------------------------------------------------------


def test_get_total_sync():
    query = _make_query(count_value=7)

    with patch("fastapi_pagination.ext.firestore.AggregationQuery") as mock_agg_cls:
        agg_instance = MagicMock()
        agg_result = MagicMock()
        agg_result.value = 7
        count_mock = MagicMock()
        count_mock.get.return_value = [[agg_result]]
        agg_instance.count.return_value = count_mock
        mock_agg_cls.return_value = agg_instance

        result = run_sync_flow(_get_total(False, query, None))

    assert result == 7


@pytest.mark.asyncio
async def test_get_total_async():
    query = _make_async_query(count_value=5)

    with patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery") as mock_agg_cls:
        agg_instance = MagicMock()
        agg_result = MagicMock()
        agg_result.value = 5
        count_mock = MagicMock()
        count_mock.get = AsyncMock(return_value=[[agg_result]])
        agg_instance.count.return_value = count_mock
        mock_agg_cls.return_value = agg_instance

        result = await run_async_flow(_get_total(True, query, None))

    assert result == 5


# ---------------------------------------------------------------------------
# _total_flow
# ---------------------------------------------------------------------------


def test_total_flow_sync():
    query = _make_query(count_value=4)

    with patch("fastapi_pagination.ext.firestore.AggregationQuery") as mock_agg_cls:
        agg_instance = MagicMock()
        agg_result = MagicMock()
        agg_result.value = 4
        count_mock = MagicMock()
        count_mock.get.return_value = [[agg_result]]
        agg_instance.count.return_value = count_mock
        mock_agg_cls.return_value = agg_instance

        result = run_sync_flow(_total_flow(False, query, None))

    assert result == 4


@pytest.mark.asyncio
async def test_total_flow_async():
    query = _make_async_query(count_value=6)

    with patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery") as mock_agg_cls:
        agg_instance = MagicMock()
        agg_result = MagicMock()
        agg_result.value = 6
        count_mock = MagicMock()
        count_mock.get = AsyncMock(return_value=[[agg_result]])
        agg_instance.count.return_value = count_mock
        mock_agg_cls.return_value = agg_instance

        result = await run_async_flow(_total_flow(True, query, None))

    assert result == 6


# ---------------------------------------------------------------------------
# _limit_offset_flow
# ---------------------------------------------------------------------------


def test_limit_offset_flow_sync():
    docs = [_make_doc_snapshot("d1", {"x": 1}), _make_doc_snapshot("d2", {"x": 2})]
    query = _make_query(items=docs)
    raw_params = RawParams(limit=2, offset=0)

    result = run_sync_flow(_limit_offset_flow(query, None, raw_params))

    assert result == docs


@pytest.mark.asyncio
async def test_limit_offset_flow_async():
    docs = [_make_doc_snapshot("d3", {"y": 3})]
    query = _make_async_query(items=docs)
    raw_params = RawParams(limit=1, offset=0)

    result = await run_async_flow(_limit_offset_flow(query, None, raw_params))
    assert result == docs


# ---------------------------------------------------------------------------
# _fetch_cursor
# ---------------------------------------------------------------------------


def test_fetch_cursor_no_cursor():
    query = _make_query()
    params = CursorRawParams(cursor=None, size=10)

    gen = _fetch_cursor(query, params, None)
    try:
        next(gen)
        pytest.fail("Expected StopIteration")
    except StopIteration as exc:
        result = exc.value

    assert result is None


def test_fetch_cursor_with_cursor():
    snapshot = _make_doc_snapshot("cursor_doc", {"data": "val"})
    parent = MagicMock()
    doc_ref = MagicMock()
    doc_ref.get.return_value = snapshot
    parent.document.return_value = doc_ref

    query = _make_query()
    query._parent = parent

    params = CursorRawParams(cursor="cursor_doc", size=10)

    gen = _fetch_cursor(query, params, None)
    yielded = next(gen)
    try:
        gen.send(yielded)
    except StopIteration as exc:
        result = exc.value

    assert result is snapshot


@pytest.mark.asyncio
async def test_fetch_cursor_async_with_cursor():
    snapshot = _make_doc_snapshot("async_cursor_doc", {"data": "async_val"})
    parent = MagicMock()
    doc_ref = MagicMock()
    doc_ref.get = AsyncMock(return_value=snapshot)
    parent.document.return_value = doc_ref

    query = _make_async_query()
    query._parent = parent

    params = CursorRawParams(cursor="async_cursor_doc", size=5)

    result = await run_async_flow(_fetch_cursor(query, params, None))
    assert result is snapshot


# ---------------------------------------------------------------------------
# _cursor_flow
# ---------------------------------------------------------------------------


def test_cursor_flow_sync_with_items():
    docs = [_make_doc_snapshot("item1", {"a": 1}), _make_doc_snapshot("item2", {"a": 2})]
    docs[-1].id = "item2"

    query = _make_query(items=docs)
    query._parent = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=2)

    gen = _cursor_flow(query, None, raw_params)
    result = None
    value = None
    try:
        value = next(gen)
        while True:
            value = gen.send(value)
    except StopIteration as exc:
        result = exc.value

    items, next_info = result
    assert items == docs
    assert next_info == {"next_": "item2"}


def test_cursor_flow_sync_empty():
    query = _make_query(items=[])
    query._parent = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=10)

    gen = _cursor_flow(query, None, raw_params)
    result = None
    value = None
    try:
        value = next(gen)
        while True:
            value = gen.send(value)
    except StopIteration as exc:
        result = exc.value

    items, next_info = result
    assert items == []
    assert next_info is None


@pytest.mark.asyncio
async def test_cursor_flow_async_with_items():
    docs = [_make_doc_snapshot("ai1", {"b": 1}), _make_doc_snapshot("ai2", {"b": 2})]
    docs[-1].id = "ai2"

    query = _make_async_query(items=docs)
    query._parent = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=2)

    items, next_info = await run_async_flow(_cursor_flow(query, None, raw_params))
    assert items == docs
    assert next_info == {"next_": "ai2"}


# ---------------------------------------------------------------------------
# paginate  (sync)
# ---------------------------------------------------------------------------


def test_paginate_with_limit_offset():
    from google.cloud.firestore_v1 import CollectionReference, Query

    docs = [_make_doc_snapshot("p1", {"n": 1}), _make_doc_snapshot("p2", {"n": 2})]
    query = _make_query(items=docs, count_value=2)
    # Make query a proper mock of Query by patching isinstance check
    query.__class__ = Query

    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.firestore.AggregationQuery") as mock_agg_cls, set_page(Page):
        agg_instance = MagicMock()
        agg_result = MagicMock()
        agg_result.value = 2
        count_mock = MagicMock()
        count_mock.get.return_value = [[agg_result]]
        agg_instance.count.return_value = count_mock
        mock_agg_cls.return_value = agg_instance

        result = paginate(query, params=params, raw=True)

    assert result.total == 2
    assert len(result.items) == 2


def test_paginate_raw_false():
    from google.cloud.firestore_v1 import Query

    docs = [_make_doc_snapshot("r1", {"val": 10})]
    query = _make_query(items=docs, count_value=1)
    query.__class__ = Query

    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.firestore.AggregationQuery") as mock_agg_cls, set_page(Page):
        agg_instance = MagicMock()
        agg_result = MagicMock()
        agg_result.value = 1
        count_mock = MagicMock()
        count_mock.get.return_value = [[agg_result]]
        agg_instance.count.return_value = count_mock
        mock_agg_cls.return_value = agg_instance

        result = paginate(query, params=params, raw=False)

    assert result.total == 1
    assert result.items == [{"val": 10, "id": "r1"}]


# ---------------------------------------------------------------------------
# apaginate  (async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_with_limit_offset():
    from google.cloud.firestore_v1 import AsyncQuery

    docs = [_make_doc_snapshot("ap1", {"m": 1}), _make_doc_snapshot("ap2", {"m": 2})]
    query = _make_async_query(items=docs, count_value=2)
    query.__class__ = AsyncQuery

    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery") as mock_agg_cls, set_page(Page):
        agg_instance = MagicMock()
        agg_result = MagicMock()
        agg_result.value = 2
        count_mock = MagicMock()
        count_mock.get = AsyncMock(return_value=[[agg_result]])
        agg_instance.count.return_value = count_mock
        mock_agg_cls.return_value = agg_instance

        result = await apaginate(query, params=params, raw=True)

    assert result.total == 2
    assert len(result.items) == 2


@pytest.mark.asyncio
async def test_apaginate_raw_false():
    from google.cloud.firestore_v1 import AsyncQuery

    docs = [_make_doc_snapshot("ar1", {"k": 5})]
    query = _make_async_query(items=docs, count_value=1)
    query.__class__ = AsyncQuery

    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery") as mock_agg_cls, set_page(Page):
        agg_instance = MagicMock()
        agg_result = MagicMock()
        agg_result.value = 1
        count_mock = MagicMock()
        count_mock.get = AsyncMock(return_value=[[agg_result]])
        agg_instance.count.return_value = count_mock
        mock_agg_cls.return_value = agg_instance

        result = await apaginate(query, params=params, raw=False)

    assert result.total == 1
    assert result.items == [{"k": 5, "id": "ar1"}]


# ---------------------------------------------------------------------------
# _firebase_flow — CollectionReference / AsyncCollectionReference branches
# ---------------------------------------------------------------------------


def test_firebase_flow_collection_reference():
    from google.cloud.firestore_v1 import CollectionReference, Query

    docs = [_make_doc_snapshot("c1", {"z": 9})]
    collection = MagicMock(spec=CollectionReference)

    # The flow will wrap collection into Query(collection)
    mock_query = _make_query(items=docs, count_value=1)

    params = Params(page=1, size=10)

    with (
        patch("fastapi_pagination.ext.firestore.Query") as mock_query_cls,
        patch("fastapi_pagination.ext.firestore.AggregationQuery") as mock_agg_cls,
        set_page(Page),
    ):
        mock_query_cls.return_value = mock_query
        agg_instance = MagicMock()
        agg_result = MagicMock()
        agg_result.value = 1
        count_mock = MagicMock()
        count_mock.get.return_value = [[agg_result]]
        agg_instance.count.return_value = count_mock
        mock_agg_cls.return_value = agg_instance

        result = run_sync_flow(
            _firebase_flow(
                collection,
                params=params,
                raw=True,
                transaction=None,
                transformer=None,
                additional_data=None,
                config=None,
                async_=False,
            )
        )

    assert result.total == 1


@pytest.mark.asyncio
async def test_firebase_flow_async_collection_reference():
    from google.cloud.firestore_v1 import AsyncCollectionReference, AsyncQuery

    docs = [_make_doc_snapshot("ac1", {"w": 7})]
    collection = MagicMock(spec=AsyncCollectionReference)

    mock_query = _make_async_query(items=docs, count_value=1)

    params = Params(page=1, size=10)

    with (
        patch("fastapi_pagination.ext.firestore.AsyncQuery") as mock_async_query_cls,
        patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery") as mock_agg_cls,
        set_page(Page),
    ):
        mock_async_query_cls.return_value = mock_query
        agg_instance = MagicMock()
        agg_result = MagicMock()
        agg_result.value = 1
        count_mock = MagicMock()
        count_mock.get = AsyncMock(return_value=[[agg_result]])
        agg_instance.count.return_value = count_mock
        mock_agg_cls.return_value = agg_instance

        result = await run_async_flow(
            _firebase_flow(
                collection,
                params=params,
                raw=True,
                transaction=None,
                transformer=None,
                additional_data=None,
                config=None,
                async_=True,
            )
        )

    assert result.total == 1
