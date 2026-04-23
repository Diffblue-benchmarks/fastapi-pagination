from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

# ============================================================
# Mock google.cloud.firestore_v1 before importing the extension.
# google-cloud-firestore may not be installed in the test environment.
# ============================================================


class _FakeCollectionReference:
    pass


class _FakeAsyncCollectionReference:
    pass


class _FakeQuery:
    def __init__(self, parent=None):
        self._parent = parent

    def start_after(self, snapshot):
        return _FakeQuery(self._parent)

    def limit(self, n):
        return _FakeQuery(self._parent)

    def offset(self, n):
        return _FakeQuery(self._parent)

    def get(self, transaction=None):
        return []


class _FakeAsyncQuery:
    def __init__(self, parent=None):
        self._parent = parent

    def start_after(self, snapshot):
        return _FakeAsyncQuery(self._parent)

    def limit(self, n):
        return _FakeAsyncQuery(self._parent)

    def offset(self, n):
        return _FakeAsyncQuery(self._parent)

    async def get(self, transaction=None):
        return []


class _FakeDocumentSnapshot:
    def __init__(self, doc_id: str, data: dict):
        self.id = doc_id
        self._data = data

    def to_dict(self):
        return self._data


_mock_fv1 = MagicMock()
_mock_fv1.CollectionReference = _FakeCollectionReference
_mock_fv1.AsyncCollectionReference = _FakeAsyncCollectionReference
_mock_fv1.Query = _FakeQuery
_mock_fv1.AsyncQuery = _FakeAsyncQuery
_mock_fv1.DocumentSnapshot = _FakeDocumentSnapshot
_mock_fv1.Transaction = MagicMock
_mock_fv1.AsyncTransaction = MagicMock

_mock_agg = MagicMock()
_mock_async_agg = MagicMock()

sys.modules.setdefault("google", MagicMock())
sys.modules.setdefault("google.cloud", MagicMock())
sys.modules["google.cloud.firestore_v1"] = _mock_fv1
sys.modules["google.cloud.firestore_v1.aggregation"] = _mock_agg
sys.modules["google.cloud.firestore_v1.async_aggregation"] = _mock_async_agg

import pytest

from fastapi_pagination.bases import CursorRawParams, RawParams
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


# ============================================================
# Tests for _apply_cursor
# ============================================================


def test_apply_cursor_with_snapshot():
    query = MagicMock()
    query.start_after.return_value = query
    query.limit.return_value = query
    params = CursorRawParams(cursor=None, size=10)
    snapshot = MagicMock()

    _apply_cursor(query, params, snapshot)

    query.start_after.assert_called_once_with(snapshot)
    query.limit.assert_called_once_with(10)


def test_apply_cursor_without_snapshot():
    query = MagicMock()
    query.limit.return_value = query
    params = CursorRawParams(cursor=None, size=5)

    _apply_cursor(query, params, None)

    query.start_after.assert_not_called()
    query.limit.assert_called_once_with(5)


def test_apply_cursor_without_size_returns_query_after_start_after():
    query = MagicMock()
    after_query = MagicMock()
    query.start_after.return_value = after_query
    snapshot = MagicMock()
    params = CursorRawParams(cursor=None, size=None)

    result = _apply_cursor(query, params, snapshot)

    query.start_after.assert_called_once_with(snapshot)
    query.limit.assert_not_called()
    assert result is after_query


def test_apply_cursor_no_snapshot_no_size_returns_original_query():
    query = MagicMock()
    params = CursorRawParams(cursor=None, size=None)

    result = _apply_cursor(query, params, None)

    query.start_after.assert_not_called()
    query.limit.assert_not_called()
    assert result is query


# ============================================================
# Tests for _convert_raw_items
# ============================================================


def test_convert_raw_items_with_data():
    docs = [
        _FakeDocumentSnapshot("doc1", {"name": "Alice"}),
        _FakeDocumentSnapshot("doc2", {"name": "Bob"}),
    ]

    result = _convert_raw_items(docs)

    assert result == [{"name": "Alice", "id": "doc1"}, {"name": "Bob", "id": "doc2"}]


def test_convert_raw_items_empty():
    result = _convert_raw_items([])

    assert result == []


def test_convert_raw_items_with_none_data():
    doc = MagicMock()
    doc.to_dict.return_value = None
    doc.id = "doc3"

    result = _convert_raw_items([doc])

    assert result == [{"id": "doc3"}]


# ============================================================
# Tests for _get_total
# ============================================================


def test_get_total_sync():
    query = MagicMock()
    mock_val = MagicMock()
    mock_val.value = 7

    with patch("fastapi_pagination.ext.firestore.AggregationQuery") as mock_agg_cls:
        mock_agg_cls.return_value.count.return_value.get.return_value = [[mock_val]]

        result = run_sync_flow(_get_total(False, query, None))

    assert result == 7
    mock_agg_cls.assert_called_once_with(query)
    mock_agg_cls.return_value.count.assert_called_once_with("total")


def test_get_total_async():
    query = MagicMock()
    mock_val = MagicMock()
    mock_val.value = 3

    with patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery") as mock_agg_cls:
        mock_agg_cls.return_value.count.return_value.get.return_value = [[mock_val]]

        result = run_sync_flow(_get_total(True, query, None))

    assert result == 3
    mock_agg_cls.assert_called_once_with(query)


def test_get_total_with_transaction():
    query = MagicMock()
    transaction = MagicMock()
    mock_val = MagicMock()
    mock_val.value = 15

    with patch("fastapi_pagination.ext.firestore.AggregationQuery") as mock_agg_cls:
        mock_agg_cls.return_value.count.return_value.get.return_value = [[mock_val]]

        result = run_sync_flow(_get_total(False, query, transaction))

    assert result == 15
    mock_agg_cls.return_value.count.return_value.get.assert_called_once_with(transaction=transaction)


# ============================================================
# Tests for _total_flow
# ============================================================


def test_total_flow_sync():
    query = MagicMock()
    mock_val = MagicMock()
    mock_val.value = 10

    with patch("fastapi_pagination.ext.firestore.AggregationQuery") as mock_agg_cls:
        mock_agg_cls.return_value.count.return_value.get.return_value = [[mock_val]]

        result = run_sync_flow(_total_flow(False, query, None))

    assert result == 10


def test_total_flow_async():
    query = MagicMock()
    mock_val = MagicMock()
    mock_val.value = 4

    with patch("fastapi_pagination.ext.firestore.AsyncAggregationQuery") as mock_agg_cls:
        mock_agg_cls.return_value.count.return_value.get.return_value = [[mock_val]]

        result = run_sync_flow(_total_flow(True, query, None))

    assert result == 4


# ============================================================
# Tests for _limit_offset_flow
# ============================================================


def test_limit_offset_flow():
    query = MagicMock()
    query.limit.return_value = query
    query.offset.return_value = query
    items = [MagicMock(), MagicMock()]
    query.get.return_value = items
    raw_params = RawParams(limit=10, offset=0)

    result = run_sync_flow(_limit_offset_flow(query, None, raw_params))

    assert result == items
    query.limit.assert_called_once_with(10)
    query.offset.assert_called_once_with(0)
    query.get.assert_called_once_with(transaction=None)


def test_limit_offset_flow_with_transaction():
    query = MagicMock()
    query.limit.return_value = query
    query.offset.return_value = query
    transaction = MagicMock()
    items = [MagicMock()]
    query.get.return_value = items
    raw_params = RawParams(limit=5, offset=10)

    result = run_sync_flow(_limit_offset_flow(query, transaction, raw_params))

    assert result == items
    query.get.assert_called_once_with(transaction=transaction)


# ============================================================
# Tests for _fetch_cursor
# ============================================================


def test_fetch_cursor_without_cursor():
    query = MagicMock()
    params = CursorRawParams(cursor=None, size=10)

    result = run_sync_flow(_fetch_cursor(query, params, None))

    assert result is None


def test_fetch_cursor_with_cursor():
    mock_doc = MagicMock()
    mock_parent = MagicMock()
    mock_parent.document.return_value.get.return_value = mock_doc
    query = MagicMock()
    query._parent = mock_parent
    params = CursorRawParams(cursor="some_cursor_id", size=10)

    result = run_sync_flow(_fetch_cursor(query, params, None))

    assert result is mock_doc
    mock_parent.document.assert_called_once_with("some_cursor_id")
    mock_parent.document.return_value.get.assert_called_once_with(transaction=None)


# ============================================================
# Tests for _cursor_flow
# ============================================================


def test_cursor_flow_with_items():
    mock_doc1 = MagicMock()
    mock_doc1.id = "doc_abc"
    mock_doc2 = MagicMock()
    mock_doc2.id = "doc_xyz"
    items = [mock_doc1, mock_doc2]

    query = MagicMock()
    query._parent = MagicMock()
    query.get.return_value = items
    params = CursorRawParams(cursor=None, size=5)

    with patch("fastapi_pagination.ext.firestore._apply_cursor", return_value=query):
        result_items, result_next = run_sync_flow(_cursor_flow(query, None, params))

    assert result_items == items
    assert result_next == {"next_": "doc_xyz"}


def test_cursor_flow_empty():
    query = MagicMock()
    query._parent = MagicMock()
    query.get.return_value = []
    params = CursorRawParams(cursor=None, size=5)

    with patch("fastapi_pagination.ext.firestore._apply_cursor", return_value=query):
        result_items, result_next = run_sync_flow(_cursor_flow(query, None, params))

    assert result_items == []
    assert result_next is None


# ============================================================
# Tests for _firebase_flow
# ============================================================


def _make_noop_generic_flow(mock_page):
    def _mock_generic_flow(**kwargs):
        return mock_page
        yield  # noqa: unreachable — makes this a generator function

    return _mock_generic_flow


def test_firebase_flow_with_async_collection_reference():
    mock_page = MagicMock()
    src = _FakeAsyncCollectionReference()

    with patch("fastapi_pagination.ext.firestore.generic_flow", _make_noop_generic_flow(mock_page)):
        result = run_sync_flow(
            _firebase_flow(
                src,
                params=None,
                raw=False,
                transaction=None,
                transformer=None,
                additional_data=None,
                config=None,
                async_=True,
            )
        )

    assert result == mock_page


def test_firebase_flow_with_collection_reference():
    mock_page = MagicMock()
    src = _FakeCollectionReference()

    with patch("fastapi_pagination.ext.firestore.generic_flow", _make_noop_generic_flow(mock_page)):
        result = run_sync_flow(
            _firebase_flow(
                src,
                params=None,
                raw=False,
                transaction=None,
                transformer=None,
                additional_data=None,
                config=None,
                async_=False,
            )
        )

    assert result == mock_page


def test_firebase_flow_with_query():
    mock_page = MagicMock()
    src = _FakeQuery()

    with patch("fastapi_pagination.ext.firestore.generic_flow", _make_noop_generic_flow(mock_page)):
        result = run_sync_flow(
            _firebase_flow(
                src,
                params=None,
                raw=False,
                transaction=None,
                transformer=None,
                additional_data=None,
                config=None,
                async_=False,
            )
        )

    assert result == mock_page


def test_firebase_flow_raw_true_sets_no_inner_transformer():
    captured_kwargs = {}

    def _mock_generic_flow(**kwargs):
        captured_kwargs.update(kwargs)
        return MagicMock()
        yield  # noqa: unreachable

    src = _FakeQuery()

    with patch("fastapi_pagination.ext.firestore.generic_flow", _mock_generic_flow):
        run_sync_flow(
            _firebase_flow(
                src,
                params=None,
                raw=True,
                transaction=None,
                transformer=None,
                additional_data=None,
                config=None,
                async_=False,
            )
        )

    assert captured_kwargs["inner_transformer"] is None


def test_firebase_flow_raw_false_sets_convert_raw_items_transformer():
    captured_kwargs = {}

    def _mock_generic_flow(**kwargs):
        captured_kwargs.update(kwargs)
        return MagicMock()
        yield  # noqa: unreachable

    src = _FakeQuery()

    with patch("fastapi_pagination.ext.firestore.generic_flow", _mock_generic_flow):
        run_sync_flow(
            _firebase_flow(
                src,
                params=None,
                raw=False,
                transaction=None,
                transformer=None,
                additional_data=None,
                config=None,
                async_=False,
            )
        )

    assert captured_kwargs["inner_transformer"] is _convert_raw_items


# ============================================================
# Tests for paginate
# ============================================================


def test_paginate():
    mock_page = MagicMock()

    def _mock_firebase_flow(src, /, **kwargs):
        return mock_page
        yield  # noqa: unreachable

    src = MagicMock()

    with patch("fastapi_pagination.ext.firestore._firebase_flow", _mock_firebase_flow):
        result = paginate(src)

    assert result == mock_page


def test_paginate_passes_kwargs():
    captured = {}

    def _mock_firebase_flow(src, /, **kwargs):
        captured.update(kwargs)
        return MagicMock()
        yield  # noqa: unreachable

    src = MagicMock()
    transaction = MagicMock()

    with patch("fastapi_pagination.ext.firestore._firebase_flow", _mock_firebase_flow):
        paginate(src, raw=True, transaction=transaction)

    assert captured["raw"] is True
    assert captured["transaction"] is transaction
    assert captured["async_"] is False


# ============================================================
# Tests for apaginate
# ============================================================


@pytest.mark.asyncio
async def test_apaginate():
    mock_page = MagicMock()

    def _mock_firebase_flow(src, /, **kwargs):
        return mock_page
        yield  # noqa: unreachable

    src = MagicMock()

    with patch("fastapi_pagination.ext.firestore._firebase_flow", _mock_firebase_flow):
        result = await apaginate(src)

    assert result == mock_page


@pytest.mark.asyncio
async def test_apaginate_passes_kwargs():
    captured = {}

    def _mock_firebase_flow(src, /, **kwargs):
        captured.update(kwargs)
        return MagicMock()
        yield  # noqa: unreachable

    src = MagicMock()

    with patch("fastapi_pagination.ext.firestore._firebase_flow", _mock_firebase_flow):
        await apaginate(src, raw=True)

    assert captured["raw"] is True
    assert captured["async_"] is True
