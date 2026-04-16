"""Unit tests for fastapi_pagination.ext.firestore."""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Inject mock google modules before fastapi_pagination.ext.firestore is imported
_firestore_v1_mock = MagicMock()
_aggregation_mock = MagicMock()
_async_aggregation_mock = MagicMock()

for _name, _mod in [
    ("google", MagicMock()),
    ("google.cloud", MagicMock()),
    ("google.cloud.firestore_v1", _firestore_v1_mock),
    ("google.cloud.firestore_v1.aggregation", _aggregation_mock),
    ("google.cloud.firestore_v1.async_aggregation", _async_aggregation_mock),
]:
    sys.modules.setdefault(_name, _mod)

from fastapi_pagination.bases import CursorRawParams, RawParams  # noqa: E402
from fastapi_pagination.ext.firestore import (  # noqa: E402
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
from fastapi_pagination.flow import run_async_flow, run_sync_flow  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doc_snapshot(id_: str, data: dict) -> MagicMock:
    doc = MagicMock()
    doc.id = id_
    doc.to_dict.return_value = data
    return doc


def _make_query(items=None, get_return=None):
    """Return a sync-style mock Query."""
    query = MagicMock()
    # start_after / limit return the query itself (for chaining)
    query.start_after.return_value = query
    query.limit.return_value = query
    query.offset.return_value = query
    if get_return is not None:
        query.get.return_value = get_return
    elif items is not None:
        query.get.return_value = items
    return query


# ---------------------------------------------------------------------------
# _apply_cursor
# ---------------------------------------------------------------------------


def test_apply_cursor_no_snapshot_no_size():
    query = _make_query()
    params = CursorRawParams(cursor=None, size=None, include_total=True)

    result = _apply_cursor(query, params, snapshot=None)

    query.start_after.assert_not_called()
    query.limit.assert_not_called()
    assert result is query


def test_apply_cursor_with_snapshot_no_size():
    query = _make_query()
    snapshot = MagicMock()
    params = CursorRawParams(cursor=None, size=None, include_total=True)

    result = _apply_cursor(query, params, snapshot=snapshot)

    query.start_after.assert_called_once_with(snapshot)
    query.limit.assert_not_called()
    assert result is query.start_after.return_value


def test_apply_cursor_with_snapshot_and_size():
    base_query = MagicMock()
    after_query = MagicMock()
    limited_query = MagicMock()
    base_query.start_after.return_value = after_query
    after_query.limit.return_value = limited_query

    snapshot = MagicMock()
    params = CursorRawParams(cursor=None, size=10, include_total=True)

    result = _apply_cursor(base_query, params, snapshot=snapshot)

    base_query.start_after.assert_called_once_with(snapshot)
    after_query.limit.assert_called_once_with(10)
    assert result is limited_query


def test_apply_cursor_no_snapshot_with_size():
    query = MagicMock()
    limited_query = MagicMock()
    query.limit.return_value = limited_query

    params = CursorRawParams(cursor=None, size=5, include_total=True)

    result = _apply_cursor(query, params, snapshot=None)

    query.start_after.assert_not_called()
    query.limit.assert_called_once_with(5)
    assert result is limited_query


# ---------------------------------------------------------------------------
# _convert_raw_items
# ---------------------------------------------------------------------------


def test_convert_raw_items_basic():
    doc1 = _make_doc_snapshot("abc", {"name": "Alice"})
    doc2 = _make_doc_snapshot("xyz", {"name": "Bob"})

    result = _convert_raw_items([doc1, doc2])

    assert result == [
        {"name": "Alice", "id": "abc"},
        {"name": "Bob", "id": "xyz"},
    ]


def test_convert_raw_items_empty():
    result = _convert_raw_items([])

    assert result == []


def test_convert_raw_items_to_dict_none():
    doc = _make_doc_snapshot("id1", None)
    doc.to_dict.return_value = None

    result = _convert_raw_items([doc])

    assert result == [{"id": "id1"}]


# ---------------------------------------------------------------------------
# _get_total
# ---------------------------------------------------------------------------


def test_get_total_sync():
    import fastapi_pagination.ext.firestore as fs_module

    aggr_instance = MagicMock()
    count_result = MagicMock()
    count_result[0][0].value = 42
    aggr_instance.count.return_value.get.return_value = count_result

    mock_aggr_cls = MagicMock(return_value=aggr_instance)

    original = fs_module.AggregationQuery
    fs_module.AggregationQuery = mock_aggr_cls
    try:
        query = MagicMock()
        total = run_sync_flow(_get_total(False, query, None))
        assert total == 42
    finally:
        fs_module.AggregationQuery = original


def test_get_total_async():
    import fastapi_pagination.ext.firestore as fs_module

    aggr_instance = MagicMock()
    count_result = MagicMock()
    count_result[0][0].value = 7
    aggr_instance.count.return_value.get.return_value = count_result

    mock_aggr_cls = MagicMock(return_value=aggr_instance)

    original = fs_module.AsyncAggregationQuery
    fs_module.AsyncAggregationQuery = mock_aggr_cls
    try:
        query = MagicMock()
        total = run_sync_flow(_get_total(True, query, None))
        assert total == 7
    finally:
        fs_module.AsyncAggregationQuery = original


# ---------------------------------------------------------------------------
# _total_flow
# ---------------------------------------------------------------------------


def test_total_flow_sync():
    import fastapi_pagination.ext.firestore as fs_module

    aggr_instance = MagicMock()
    count_result = MagicMock()
    count_result[0][0].value = 99
    aggr_instance.count.return_value.get.return_value = count_result

    mock_aggr_cls = MagicMock(return_value=aggr_instance)

    original = fs_module.AggregationQuery
    fs_module.AggregationQuery = mock_aggr_cls
    try:
        query = MagicMock()
        total = run_sync_flow(_total_flow(False, query, None))
        assert total == 99
    finally:
        fs_module.AggregationQuery = original


# ---------------------------------------------------------------------------
# _limit_offset_flow
# ---------------------------------------------------------------------------


def test_limit_offset_flow_returns_items():
    docs = [_make_doc_snapshot("a", {"x": 1})]
    query = _make_query(items=docs)
    raw_params = RawParams(limit=10, offset=0)

    items = run_sync_flow(_limit_offset_flow(query, None, raw_params))

    assert items is docs


def test_limit_offset_flow_applies_limit_and_offset():
    inner_query = MagicMock()
    query = MagicMock()
    query.limit.return_value = inner_query
    inner_query.offset.return_value = inner_query
    inner_query.get.return_value = []

    raw_params = RawParams(limit=5, offset=10)
    run_sync_flow(_limit_offset_flow(query, None, raw_params))

    query.limit.assert_called_once_with(5)
    inner_query.offset.assert_called_once_with(10)


# ---------------------------------------------------------------------------
# _fetch_cursor
# ---------------------------------------------------------------------------


def test_fetch_cursor_no_cursor():
    query = MagicMock()
    params = CursorRawParams(cursor=None, size=10, include_total=True)

    result = run_sync_flow(_fetch_cursor(query, params, None))

    assert result is None
    query._parent.document.assert_not_called()


def test_fetch_cursor_with_cursor():
    snapshot = MagicMock()
    doc_ref = MagicMock()
    doc_ref.get.return_value = snapshot

    query = MagicMock()
    query._parent.document.return_value = doc_ref

    params = CursorRawParams(cursor="doc123", size=10, include_total=True)

    result = run_sync_flow(_fetch_cursor(query, params, None))

    query._parent.document.assert_called_once_with("doc123")
    assert result is snapshot


# ---------------------------------------------------------------------------
# _cursor_flow
# ---------------------------------------------------------------------------


def test_cursor_flow_with_no_items():
    query = MagicMock()
    query.start_after.return_value = query
    query.limit.return_value = query
    query.get.return_value = []
    query._parent.document.return_value.get.return_value = None

    params = CursorRawParams(cursor=None, size=5, include_total=True)

    items, extra = run_sync_flow(_cursor_flow(query, None, params))

    assert items == []
    assert extra is None


def test_cursor_flow_with_items():
    doc = _make_doc_snapshot("last_doc_id", {"val": 1})
    doc.id = "last_doc_id"

    query = MagicMock()
    query.start_after.return_value = query
    query.limit.return_value = query
    query.get.return_value = [doc]
    query._parent.document.return_value.get.return_value = None

    params = CursorRawParams(cursor=None, size=5, include_total=True)

    items, extra = run_sync_flow(_cursor_flow(query, None, params))

    assert items == [doc]
    assert extra == {"next_": "last_doc_id"}


# ---------------------------------------------------------------------------
# _firebase_flow
# ---------------------------------------------------------------------------


class _NeverInstance:
    """A sentinel class that nothing is an instance of (for isinstance patching)."""


def test_firebase_flow_query_src_raw_false(mocker):
    page_result = MagicMock()

    mocker.patch(
        "fastapi_pagination.ext.firestore.generic_flow",
        return_value=_yield_once(page_result),
    )
    # Patch collection-reference classes so the else-branch is taken (src is already a query)
    mocker.patch("fastapi_pagination.ext.firestore.AsyncCollectionReference", new=_NeverInstance)
    mocker.patch("fastapi_pagination.ext.firestore.CollectionReference", new=_NeverInstance)

    query = MagicMock()
    result = run_sync_flow(
        _firebase_flow(
            query,
            params=None,
            raw=False,
            transaction=None,
            transformer=None,
            additional_data=None,
            config=None,
            async_=False,
        )
    )

    assert result is page_result


def test_firebase_flow_raw_true(mocker):
    page_result = MagicMock()

    mock_generic_flow = mocker.patch(
        "fastapi_pagination.ext.firestore.generic_flow",
        return_value=_yield_once(page_result),
    )
    mocker.patch("fastapi_pagination.ext.firestore.AsyncCollectionReference", new=_NeverInstance)
    mocker.patch("fastapi_pagination.ext.firestore.CollectionReference", new=_NeverInstance)

    query = MagicMock()
    run_sync_flow(
        _firebase_flow(
            query,
            params=None,
            raw=True,
            transaction=None,
            transformer=None,
            additional_data=None,
            config=None,
            async_=False,
        )
    )

    _, kwargs = mock_generic_flow.call_args
    assert kwargs.get("inner_transformer") is None


# ---------------------------------------------------------------------------
# paginate
# ---------------------------------------------------------------------------


def test_paginate_calls_run_sync_flow(mocker):
    page_result = MagicMock()
    mocker.patch(
        "fastapi_pagination.ext.firestore.run_sync_flow",
        return_value=page_result,
    )
    mock_flow = mocker.patch(
        "fastapi_pagination.ext.firestore._firebase_flow",
        return_value=MagicMock(),
    )

    query = MagicMock()
    result = paginate(query, params=None, raw=True)

    assert result is page_result
    mock_flow.assert_called_once()
    _, kwargs = mock_flow.call_args
    assert kwargs["async_"] is False
    assert kwargs["raw"] is True


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_calls_run_async_flow(mocker):
    page_result = MagicMock()
    mocker.patch(
        "fastapi_pagination.ext.firestore.run_async_flow",
        new=AsyncMock(return_value=page_result),
    )
    mock_flow = mocker.patch(
        "fastapi_pagination.ext.firestore._firebase_flow",
        return_value=MagicMock(),
    )

    query = MagicMock()
    result = await apaginate(query, params=None, raw=True)

    assert result is page_result
    mock_flow.assert_called_once()
    _, kwargs = mock_flow.call_args
    assert kwargs["async_"] is True
    assert kwargs["raw"] is True


# ---------------------------------------------------------------------------
# Helpers for test setup
# ---------------------------------------------------------------------------


def _yield_once(value):
    """Return a generator that yields value once then returns it."""
    result = yield value
    return value



