"""Unit tests for fastapi_pagination/ext/firestore.py."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

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
    _firebase_flow,
    paginate,
    apaginate,
)
from fastapi_pagination.default import Page, Params


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doc_snapshot(doc_id: str, data: dict) -> MagicMock:
    snap = MagicMock()
    snap.id = doc_id
    snap.to_dict.return_value = data
    return snap


def _make_aggregation_result(value: int) -> list:
    inner = MagicMock()
    inner.value = value
    return [[inner]]


def _make_sync_query(items=None, total: int = 0):
    """Build a minimal mock Query that behaves synchronously."""
    if items is None:
        items = []

    query = MagicMock()
    query.limit.return_value = query
    query.offset.return_value = query
    query.start_after.return_value = query
    query.get.return_value = items

    # _parent.document(cursor).get() for cursor flow
    doc_ref = MagicMock()
    doc_ref.get.return_value = MagicMock()
    query._parent.document.return_value = doc_ref

    return query


# ---------------------------------------------------------------------------
# _apply_cursor
# ---------------------------------------------------------------------------


def test_apply_cursor_with_snapshot_and_size():
    query = MagicMock()
    query.start_after.return_value = query
    query.limit.return_value = query

    snapshot = MagicMock()
    params = CursorRawParams(cursor="abc", size=5)

    result = _apply_cursor(query, params, snapshot)

    query.start_after.assert_called_once_with(snapshot)
    query.limit.assert_called_once_with(5)
    assert result is query


def test_apply_cursor_without_snapshot():
    query = MagicMock()
    query.limit.return_value = query

    params = CursorRawParams(cursor=None, size=10)

    result = _apply_cursor(query, params, None)

    query.start_after.assert_not_called()
    query.limit.assert_called_once_with(10)
    assert result is query


def test_apply_cursor_without_size():
    query = MagicMock()
    snapshot = MagicMock()
    query.start_after.return_value = query

    params = CursorRawParams(cursor="x", size=None)

    result = _apply_cursor(query, params, snapshot)

    query.start_after.assert_called_once_with(snapshot)
    query.limit.assert_not_called()
    assert result is query


def test_apply_cursor_no_snapshot_no_size():
    query = MagicMock()
    params = CursorRawParams(cursor=None, size=None)

    result = _apply_cursor(query, params, None)

    query.start_after.assert_not_called()
    query.limit.assert_not_called()
    assert result is query


# ---------------------------------------------------------------------------
# _convert_raw_items
# ---------------------------------------------------------------------------


def test_convert_raw_items_basic():
    snaps = [
        _make_doc_snapshot("doc1", {"name": "Alice"}),
        _make_doc_snapshot("doc2", {"name": "Bob"}),
    ]

    result = _convert_raw_items(snaps)

    assert result == [
        {"name": "Alice", "id": "doc1"},
        {"name": "Bob", "id": "doc2"},
    ]


def test_convert_raw_items_empty_dict():
    snap = _make_doc_snapshot("doc3", {})
    snap.to_dict.return_value = None  # to_dict returns None → fallback to {}

    result = _convert_raw_items([snap])

    assert result == [{"id": "doc3"}]


def test_convert_raw_items_empty_list():
    result = _convert_raw_items([])
    assert result == []


# ---------------------------------------------------------------------------
# _get_total
# ---------------------------------------------------------------------------


def test_get_total_sync():
    query = MagicMock()
    aggr_query_instance = MagicMock()
    aggr_query_instance.count.return_value = aggr_query_instance
    aggr_query_instance.get.return_value = _make_aggregation_result(42)

    with patch("fastapi_pagination.ext.firestore.AggregationQuery", return_value=aggr_query_instance):
        result = run_sync_flow(_get_total(async_=False, query=query, transaction=None))

    assert result == 42


def test_get_total_async_uses_async_aggregation():
    query = MagicMock()
    aggr_query_instance = MagicMock()
    aggr_query_instance.count.return_value = aggr_query_instance
    aggr_query_instance.get.return_value = _make_aggregation_result(7)

    with patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery", return_value=aggr_query_instance):
        result = run_sync_flow(_get_total(async_=True, query=query, transaction=None))

    assert result == 7


# ---------------------------------------------------------------------------
# _total_flow
# ---------------------------------------------------------------------------


def test_total_flow_sync():
    query = MagicMock()
    aggr_query_instance = MagicMock()
    aggr_query_instance.count.return_value = aggr_query_instance
    aggr_query_instance.get.return_value = _make_aggregation_result(15)

    with patch("fastapi_pagination.ext.firestore.AggregationQuery", return_value=aggr_query_instance):
        result = run_sync_flow(_total_flow(async_=False, query=query, transaction=None))

    assert result == 15


def test_total_flow_with_transaction():
    query = MagicMock()
    transaction = MagicMock()
    aggr_query_instance = MagicMock()
    aggr_query_instance.count.return_value = aggr_query_instance
    aggr_query_instance.get.return_value = _make_aggregation_result(3)

    with patch("fastapi_pagination.ext.firestore.AggregationQuery", return_value=aggr_query_instance):
        result = run_sync_flow(_total_flow(async_=False, query=query, transaction=transaction))

    aggr_query_instance.get.assert_called_once_with(transaction=transaction)
    assert result == 3


# ---------------------------------------------------------------------------
# _limit_offset_flow
# ---------------------------------------------------------------------------


def test_limit_offset_flow_returns_items():
    items = [_make_doc_snapshot("a", {"x": 1})]
    query = _make_sync_query(items=items)
    raw_params = RawParams(limit=10, offset=0)

    result = run_sync_flow(_limit_offset_flow(query=query, transaction=None, raw_params=raw_params))

    assert result is items


def test_limit_offset_flow_applies_limit_and_offset():
    query = _make_sync_query(items=[])
    raw_params = RawParams(limit=5, offset=20)

    run_sync_flow(_limit_offset_flow(query=query, transaction=None, raw_params=raw_params))

    query.limit.assert_called_once_with(5)
    query.offset.assert_called_once_with(20)


# ---------------------------------------------------------------------------
# _fetch_cursor
# ---------------------------------------------------------------------------


def test_fetch_cursor_with_cursor():
    query = _make_sync_query()
    cursor_doc = MagicMock()
    query._parent.document.return_value.get.return_value = cursor_doc

    params = CursorRawParams(cursor="my-cursor-id", size=5)
    result = run_sync_flow(_fetch_cursor(query=query, params=params, transaction=None))

    query._parent.document.assert_called_once_with("my-cursor-id")
    assert result is cursor_doc


def test_fetch_cursor_without_cursor():
    query = _make_sync_query()
    params = CursorRawParams(cursor=None, size=5)

    result = run_sync_flow(_fetch_cursor(query=query, params=params, transaction=None))

    query._parent.document.assert_not_called()
    assert result is None


# ---------------------------------------------------------------------------
# _cursor_flow
# ---------------------------------------------------------------------------


def test_cursor_flow_with_items():
    items = [_make_doc_snapshot("doc1", {"v": 1}), _make_doc_snapshot("doc2", {"v": 2})]
    query = _make_sync_query(items=items)
    query.get.return_value = items

    params = CursorRawParams(cursor=None, size=10)
    result_items, meta = run_sync_flow(_cursor_flow(query=query, transaction=None, raw_params=params))

    assert result_items is items
    assert meta == {"next_": "doc2"}


def test_cursor_flow_empty_items():
    query = _make_sync_query(items=[])
    query.get.return_value = []

    params = CursorRawParams(cursor=None, size=10)
    result_items, meta = run_sync_flow(_cursor_flow(query=query, transaction=None, raw_params=params))

    assert result_items == []
    assert meta is None


# ---------------------------------------------------------------------------
# _firebase_flow  (sync, with CollectionReference / Query / AsyncCollectionReference)
# ---------------------------------------------------------------------------


def _build_sync_paginate_mocks(total: int = 2):
    """Build all mocks needed for a sync paginate call."""
    items = [_make_doc_snapshot(f"doc{i}", {"n": i}) for i in range(total)]

    query = MagicMock()
    query.limit.return_value = query
    query.offset.return_value = query
    query.get.return_value = items

    aggr = MagicMock()
    aggr.count.return_value = aggr
    aggr.get.return_value = _make_aggregation_result(total)

    return query, aggr, items


def test_firebase_flow_with_query_src():
    from google.cloud.firestore_v1 import Query as FSQuery

    query, aggr, items = _build_sync_paginate_mocks(total=2)
    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.firestore.AggregationQuery", return_value=aggr):
        result = run_sync_flow(
            _firebase_flow(
                query,
                params=params,
                raw=True,
                transaction=None,
                transformer=None,
                additional_data=None,
                config=None,
                async_=False,
            )
        )

    assert result is not None
    assert len(result.items) == 2


def test_firebase_flow_raw_false_converts_items():
    query, aggr, items = _build_sync_paginate_mocks(total=1)
    params = Params(page=1, size=10)

    items[0].to_dict.return_value = {"name": "test"}

    with patch("fastapi_pagination.ext.firestore.AggregationQuery", return_value=aggr):
        result = run_sync_flow(
            _firebase_flow(
                query,
                params=params,
                raw=False,
                transaction=None,
                transformer=None,
                additional_data=None,
                config=None,
                async_=False,
            )
        )

    assert result.items[0] == {"name": "test", "id": items[0].id}


def test_firebase_flow_with_collection_ref():
    from google.cloud.firestore_v1 import CollectionReference

    query, aggr, items = _build_sync_paginate_mocks(total=1)
    params = Params(page=1, size=10)

    # CollectionReference source — _firebase_flow wraps it in Query(src)
    col_ref = MagicMock(spec=CollectionReference)

    built_query = MagicMock()
    built_query.limit.return_value = built_query
    built_query.offset.return_value = built_query
    built_query.get.return_value = items

    aggr2 = MagicMock()
    aggr2.count.return_value = aggr2
    aggr2.get.return_value = _make_aggregation_result(1)

    with patch("fastapi_pagination.ext.firestore.Query", return_value=built_query), \
         patch("fastapi_pagination.ext.firestore.AggregationQuery", return_value=aggr2):
        result = run_sync_flow(
            _firebase_flow(
                col_ref,
                params=params,
                raw=True,
                transaction=None,
                transformer=None,
                additional_data=None,
                config=None,
                async_=False,
            )
        )

    assert result is not None


def test_firebase_flow_with_async_collection_ref():
    from google.cloud.firestore_v1 import AsyncCollectionReference

    params = Params(page=1, size=10)
    items = [_make_doc_snapshot("d1", {"k": "v"})]

    built_query = MagicMock()
    built_query.limit.return_value = built_query
    built_query.offset.return_value = built_query
    built_query.get.return_value = items

    aggr = MagicMock()
    aggr.count.return_value = aggr
    aggr.get.return_value = _make_aggregation_result(1)

    async_col_ref = MagicMock(spec=AsyncCollectionReference)

    with patch("fastapi_pagination.ext.firestore.AsyncQuery", return_value=built_query), \
         patch("fastapi_pagination.ext.firestore.AggregationQuery", return_value=aggr):
        result = run_sync_flow(
            _firebase_flow(
                async_col_ref,
                params=params,
                raw=True,
                transaction=None,
                transformer=None,
                additional_data=None,
                config=None,
                async_=False,
            )
        )

    assert result is not None


# ---------------------------------------------------------------------------
# paginate
# ---------------------------------------------------------------------------


def test_paginate_returns_page():
    query, aggr, items = _build_sync_paginate_mocks(total=2)
    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.firestore.AggregationQuery", return_value=aggr):
        result = paginate(query, params=params, raw=True)

    assert result is not None
    assert len(result.items) == 2


def test_paginate_raw_false():
    query, aggr, items = _build_sync_paginate_mocks(total=1)
    items[0].to_dict.return_value = {"field": "value"}
    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.firestore.AggregationQuery", return_value=aggr):
        result = paginate(query, params=params, raw=False)

    assert result.items[0]["field"] == "value"
    assert "id" in result.items[0]


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_returns_page():
    items = [_make_doc_snapshot("a1", {"x": 10})]

    query = MagicMock()
    query.limit.return_value = query
    query.offset.return_value = query
    query.get = AsyncMock(return_value=items)

    aggr = MagicMock()
    aggr.count.return_value = aggr
    aggr.get = AsyncMock(return_value=_make_aggregation_result(1))

    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery", return_value=aggr):
        result = await apaginate(query, params=params, raw=True)

    assert result is not None
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_apaginate_raw_false_converts():
    items = [_make_doc_snapshot("b1", {"y": 20})]
    items[0].to_dict.return_value = {"y": 20}

    query = MagicMock()
    query.limit.return_value = query
    query.offset.return_value = query
    query.get = AsyncMock(return_value=items)

    aggr = MagicMock()
    aggr.count.return_value = aggr
    aggr.get = AsyncMock(return_value=_make_aggregation_result(1))

    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery", return_value=aggr):
        result = await apaginate(query, params=params, raw=False)

    assert result.items[0] == {"y": 20, "id": items[0].id}
