"""Unit tests for fastapi_pagination.ext.firestore module."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from fastapi_pagination import Params
from fastapi_pagination.bases import CursorRawParams, RawParams
from fastapi_pagination.flow import run_sync_flow, run_async_flow
from fastapi_pagination.ext.firestore import (
    _apply_cursor,
    _convert_raw_items,
    _get_total,
    _total_flow,
    _limit_offset_flow,
    _fetch_cursor,
    _cursor_flow,
    paginate,
    apaginate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(doc_id: str, data: dict | None = None):
    doc = MagicMock()
    doc.id = doc_id
    doc.to_dict.return_value = data if data is not None else {}
    return doc


def _make_aggr_query_class(total: int = 5):
    mock_count = MagicMock()
    mock_count.get.return_value = [[MagicMock(value=total)]]
    mock_aggr = MagicMock()
    mock_aggr.count.return_value = mock_count
    return MagicMock(return_value=mock_aggr)


def _make_async_aggr_query_class(total: int = 5):
    mock_count = MagicMock()
    mock_count.get = AsyncMock(return_value=[[MagicMock(value=total)]])
    mock_aggr = MagicMock()
    mock_aggr.count.return_value = mock_count
    return MagicMock(return_value=mock_aggr)


# ---------------------------------------------------------------------------
# _apply_cursor
# ---------------------------------------------------------------------------

def test_apply_cursor_with_snapshot_and_size():
    mock_query = MagicMock()
    mock_query.start_after.return_value = mock_query
    mock_query.limit.return_value = mock_query
    snapshot = MagicMock()
    params = CursorRawParams(cursor="abc", size=10)

    result = _apply_cursor(mock_query, params, snapshot)

    mock_query.start_after.assert_called_once_with(snapshot)
    mock_query.limit.assert_called_once_with(10)
    assert result is mock_query


def test_apply_cursor_without_snapshot():
    mock_query = MagicMock()
    mock_query.limit.return_value = mock_query
    params = CursorRawParams(cursor=None, size=10)

    result = _apply_cursor(mock_query, params, None)

    mock_query.start_after.assert_not_called()
    mock_query.limit.assert_called_once_with(10)
    assert result is mock_query


def test_apply_cursor_with_none_size():
    mock_query = MagicMock()
    mock_query.start_after.return_value = mock_query
    snapshot = MagicMock()
    params = CursorRawParams(cursor="abc", size=None)

    result = _apply_cursor(mock_query, params, snapshot)

    mock_query.start_after.assert_called_once_with(snapshot)
    mock_query.limit.assert_not_called()
    assert result is mock_query


def test_apply_cursor_no_snapshot_no_size():
    mock_query = MagicMock()
    params = CursorRawParams(cursor=None, size=None)

    result = _apply_cursor(mock_query, params, None)

    mock_query.start_after.assert_not_called()
    mock_query.limit.assert_not_called()
    assert result is mock_query


# ---------------------------------------------------------------------------
# _convert_raw_items
# ---------------------------------------------------------------------------

def test_convert_raw_items_with_data():
    doc1 = _make_doc("id1", {"name": "Alice"})
    doc2 = _make_doc("id2", {"name": "Bob"})

    result = _convert_raw_items([doc1, doc2])

    assert result == [
        {"name": "Alice", "id": "id1"},
        {"name": "Bob", "id": "id2"},
    ]


def test_convert_raw_items_empty_dict():
    doc = _make_doc("id1", None)
    doc.to_dict.return_value = None

    result = _convert_raw_items([doc])

    assert result == [{"id": "id1"}]


def test_convert_raw_items_empty_list():
    result = _convert_raw_items([])
    assert result == []


# ---------------------------------------------------------------------------
# _get_total
# ---------------------------------------------------------------------------

def test_get_total_sync():
    mock_query = MagicMock()
    aggr_class = _make_aggr_query_class(total=7)

    with patch("fastapi_pagination.ext.firestore.AggregationQuery", aggr_class):
        result = run_sync_flow(_get_total(async_=False, query=mock_query, transaction=None))

    assert result == 7


def test_get_total_async():
    mock_query = MagicMock()
    aggr_class = _make_async_aggr_query_class(total=3)

    async def _run():
        with patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery", aggr_class):
            return await run_async_flow(_get_total(async_=True, query=mock_query, transaction=None))

    import asyncio
    result = asyncio.get_event_loop().run_until_complete(_run())
    assert result == 3


# ---------------------------------------------------------------------------
# _total_flow
# ---------------------------------------------------------------------------

def test_total_flow_sync():
    mock_query = MagicMock()
    aggr_class = _make_aggr_query_class(total=4)

    with patch("fastapi_pagination.ext.firestore.AggregationQuery", aggr_class):
        result = run_sync_flow(_total_flow(async_=False, query=mock_query, transaction=None))

    assert result == 4


def test_total_flow_async():
    mock_query = MagicMock()
    aggr_class = _make_async_aggr_query_class(total=6)

    async def _run():
        with patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery", aggr_class):
            return await run_async_flow(_total_flow(async_=True, query=mock_query, transaction=None))

    import asyncio
    result = asyncio.get_event_loop().run_until_complete(_run())
    assert result == 6


# ---------------------------------------------------------------------------
# _limit_offset_flow
# ---------------------------------------------------------------------------

def test_limit_offset_flow_with_limit_and_offset():
    doc1 = _make_doc("id1", {"x": 1})
    mock_query = MagicMock()
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.get.return_value = [doc1]
    raw_params = RawParams(limit=10, offset=5)

    result = run_sync_flow(_limit_offset_flow(query=mock_query, transaction=None, raw_params=raw_params))

    mock_query.limit.assert_called_once_with(10)
    mock_query.offset.assert_called_once_with(5)
    assert result == [doc1]


def test_limit_offset_flow_no_limit_offset():
    doc1 = _make_doc("id1", {"x": 1})
    mock_query = MagicMock()
    mock_query.get.return_value = [doc1]
    raw_params = RawParams(limit=None, offset=None)

    result = run_sync_flow(_limit_offset_flow(query=mock_query, transaction=None, raw_params=raw_params))

    mock_query.limit.assert_not_called()
    mock_query.offset.assert_not_called()
    assert result == [doc1]


# ---------------------------------------------------------------------------
# _fetch_cursor
# ---------------------------------------------------------------------------

def test_fetch_cursor_with_cursor():
    mock_doc_ref = MagicMock()
    mock_snapshot = MagicMock()
    mock_doc_ref.get.return_value = mock_snapshot
    mock_query = MagicMock()
    mock_query._parent.document.return_value = mock_doc_ref
    params = CursorRawParams(cursor="cursor123", size=10)

    result = run_sync_flow(_fetch_cursor(query=mock_query, params=params, transaction=None))

    mock_query._parent.document.assert_called_once_with("cursor123")
    assert result is mock_snapshot


def test_fetch_cursor_without_cursor():
    mock_query = MagicMock()
    params = CursorRawParams(cursor=None, size=10)

    result = run_sync_flow(_fetch_cursor(query=mock_query, params=params, transaction=None))

    mock_query._parent.document.assert_not_called()
    assert result is None


# ---------------------------------------------------------------------------
# _cursor_flow
# ---------------------------------------------------------------------------

def test_cursor_flow_with_items():
    doc1 = _make_doc("last_doc", {"val": 1})
    mock_query = MagicMock()
    mock_query.start_after.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.get.return_value = [doc1]
    params = CursorRawParams(cursor=None, size=5)

    result = run_sync_flow(_cursor_flow(query=mock_query, transaction=None, raw_params=params))

    items, extra = result
    assert items == [doc1]
    assert extra == {"next_": "last_doc"}


def test_cursor_flow_empty_items():
    mock_query = MagicMock()
    mock_query.start_after.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.get.return_value = []
    params = CursorRawParams(cursor=None, size=5)

    result = run_sync_flow(_cursor_flow(query=mock_query, transaction=None, raw_params=params))

    items, extra = result
    assert items == []
    assert extra is None


def test_cursor_flow_with_cursor_param():
    mock_snapshot = MagicMock()
    mock_snapshot.id = "snap_id"
    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_snapshot

    doc1 = _make_doc("page_doc", {"val": 2})
    mock_query = MagicMock()
    mock_query._parent.document.return_value = mock_doc_ref
    mock_query.start_after.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.get.return_value = [doc1]
    params = CursorRawParams(cursor="cursor_id", size=5)

    result = run_sync_flow(_cursor_flow(query=mock_query, transaction=None, raw_params=params))

    items, extra = result
    assert items == [doc1]
    mock_query.start_after.assert_called_once_with(mock_snapshot)


# ---------------------------------------------------------------------------
# paginate (sync) — with CollectionReference mock
# ---------------------------------------------------------------------------

def test_paginate_limit_offset():
    from google.cloud.firestore_v1 import Query
    doc1 = _make_doc("id1", {"name": "Alice"})
    doc2 = _make_doc("id2", {"name": "Bob"})

    mock_query = MagicMock(spec=Query)
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.get.return_value = [doc1, doc2]
    aggr_class = _make_aggr_query_class(total=2)

    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.firestore.AggregationQuery", aggr_class):
        result = paginate(mock_query, params=params)

    assert result.total == 2
    assert len(result.items) == 2
    assert result.items[0]["id"] == "id1"
    assert result.items[1]["id"] == "id2"


def test_paginate_raw_true():
    from google.cloud.firestore_v1 import Query
    doc1 = _make_doc("id1", {"name": "Alice"})

    mock_query = MagicMock(spec=Query)
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.get.return_value = [doc1]
    aggr_class = _make_aggr_query_class(total=1)

    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.firestore.AggregationQuery", aggr_class):
        result = paginate(mock_query, params=params, raw=True)

    assert result.total == 1
    assert result.items[0] is doc1


def test_paginate_with_collection_reference():
    from google.cloud.firestore_v1 import CollectionReference, Query
    doc1 = _make_doc("id1", {"x": 1})

    mock_query = MagicMock(spec=Query)
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.get.return_value = [doc1]

    mock_col = MagicMock(spec=CollectionReference)
    aggr_class = _make_aggr_query_class(total=1)

    params = Params(page=1, size=10)

    with (
        patch("fastapi_pagination.ext.firestore.AggregationQuery", aggr_class),
        patch("fastapi_pagination.ext.firestore.Query", return_value=mock_query),
    ):
        result = paginate(mock_col, params=params)

    assert result.total == 1


# ---------------------------------------------------------------------------
# apaginate (async)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apaginate_limit_offset():
    from google.cloud.firestore_v1 import AsyncQuery
    doc1 = _make_doc("id1", {"name": "Alice"})
    doc2 = _make_doc("id2", {"name": "Bob"})

    mock_query = MagicMock(spec=AsyncQuery)
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.get = AsyncMock(return_value=[doc1, doc2])
    aggr_class = _make_async_aggr_query_class(total=2)

    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery", aggr_class):
        result = await apaginate(mock_query, params=params)

    assert result.total == 2
    assert len(result.items) == 2
    assert result.items[0]["id"] == "id1"


@pytest.mark.asyncio
async def test_apaginate_raw_true():
    from google.cloud.firestore_v1 import AsyncQuery
    doc1 = _make_doc("id1", {"name": "Alice"})

    mock_query = MagicMock(spec=AsyncQuery)
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.get = AsyncMock(return_value=[doc1])
    aggr_class = _make_async_aggr_query_class(total=1)

    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery", aggr_class):
        result = await apaginate(mock_query, params=params, raw=True)

    assert result.total == 1
    assert result.items[0] is doc1


@pytest.mark.asyncio
async def test_apaginate_with_async_collection_reference():
    from google.cloud.firestore_v1 import AsyncCollectionReference, AsyncQuery
    doc1 = _make_doc("id1", {"x": 1})

    mock_query = MagicMock(spec=AsyncQuery)
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.get = AsyncMock(return_value=[doc1])

    mock_col = MagicMock(spec=AsyncCollectionReference)
    aggr_class = _make_async_aggr_query_class(total=1)

    params = Params(page=1, size=10)

    with (
        patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery", aggr_class),
        patch("fastapi_pagination.ext.firestore.AsyncQuery", return_value=mock_query),
    ):
        result = await apaginate(mock_col, params=params)

    assert result.total == 1
