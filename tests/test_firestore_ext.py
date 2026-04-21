import sys
import types
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Mock google.cloud.firestore_v1 before importing the extension
# (google-cloud-firestore is an optional dependency)
# ---------------------------------------------------------------------------


class _MockDocumentSnapshot:
    def __init__(self, doc_id, data=None):
        self.id = doc_id
        self._data = data

    def to_dict(self):
        return self._data


class _MockCollectionReference:
    pass


class _MockAsyncCollectionReference:
    pass


class _MockQuery:
    def __init__(self, parent=None):
        self._parent = parent if parent is not None else MagicMock()
        self._items = []

    def limit(self, n):
        return self

    def offset(self, n):
        return self

    def start_after(self, snapshot):
        return self

    def get(self, transaction=None):
        return self._items


class _MockAsyncQuery:
    def __init__(self, parent=None):
        self._parent = parent if parent is not None else MagicMock()
        self._items = []

    def limit(self, n):
        return self

    def offset(self, n):
        return self

    def start_after(self, snapshot):
        return self

    async def get(self, transaction=None):
        return self._items


class _MockTransaction:
    pass


class _MockAsyncTransaction:
    pass


class _AggResult:
    def __init__(self, value):
        self.value = value


class _MockAggregationQuery:
    total = 3

    def __init__(self, query):
        self._query = query

    def count(self, alias):
        return self

    def get(self, transaction=None):
        return [[_AggResult(self.__class__.total)]]


class _MockAsyncAggregationQuery:
    total = 3

    def __init__(self, query):
        self._query = query

    def count(self, alias):
        return self

    async def get(self, transaction=None):
        return [[_AggResult(self.__class__.total)]]


# Build mock module hierarchy
_google_mod = types.ModuleType("google")
_google_cloud_mod = types.ModuleType("google.cloud")
_firestore_v1_mod = types.ModuleType("google.cloud.firestore_v1")
_aggregation_mod = types.ModuleType("google.cloud.firestore_v1.aggregation")
_async_aggregation_mod = types.ModuleType("google.cloud.firestore_v1.async_aggregation")

_google_mod.cloud = _google_cloud_mod
_google_cloud_mod.firestore_v1 = _firestore_v1_mod

_firestore_v1_mod.AsyncCollectionReference = _MockAsyncCollectionReference
_firestore_v1_mod.AsyncQuery = _MockAsyncQuery
_firestore_v1_mod.AsyncTransaction = _MockAsyncTransaction
_firestore_v1_mod.CollectionReference = _MockCollectionReference
_firestore_v1_mod.DocumentSnapshot = _MockDocumentSnapshot
_firestore_v1_mod.Query = _MockQuery
_firestore_v1_mod.Transaction = _MockTransaction

_aggregation_mod.AggregationQuery = _MockAggregationQuery
_async_aggregation_mod.AsyncAggregationQuery = _MockAsyncAggregationQuery

sys.modules.setdefault("google", _google_mod)
sys.modules.setdefault("google.cloud", _google_cloud_mod)
sys.modules.setdefault("google.cloud.firestore_v1", _firestore_v1_mod)
sys.modules.setdefault("google.cloud.firestore_v1.aggregation", _aggregation_mod)
sys.modules.setdefault("google.cloud.firestore_v1.async_aggregation", _async_aggregation_mod)

# ---------------------------------------------------------------------------
# Now import the module under test
# ---------------------------------------------------------------------------

import pytest

from fastapi_pagination.api import set_params
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
# _apply_cursor tests
# ---------------------------------------------------------------------------


def test_apply_cursor_no_snapshot_no_size():
    query = MagicMock()
    # size=None means limit should NOT be called
    params = CursorRawParams(cursor=None, size=None)  # type: ignore[arg-type]
    result = _apply_cursor(query, params, None)
    query.start_after.assert_not_called()
    query.limit.assert_not_called()
    assert result is query


def test_apply_cursor_with_snapshot():
    query = MagicMock()
    snapshot = MagicMock()
    params = CursorRawParams(cursor=None, size=10)
    result = _apply_cursor(query, params, snapshot)
    query.start_after.assert_called_once_with(snapshot)


def test_apply_cursor_with_size():
    query = MagicMock()
    params = CursorRawParams(cursor=None, size=5)
    _apply_cursor(query, params, None)
    query.limit.assert_called_once_with(5)


def test_apply_cursor_with_snapshot_and_size():
    query = MagicMock()
    snapshot = MagicMock()
    params = CursorRawParams(cursor=None, size=7)
    _apply_cursor(query, params, snapshot)
    query.start_after.assert_called_once_with(snapshot)
    # After start_after, query is reassigned to start_after's return value
    # so limit is called on start_after's return value
    query.start_after.return_value.limit.assert_called_once_with(7)


def test_apply_cursor_size_none_skips_limit():
    query = MagicMock()
    params = CursorRawParams(cursor=None, size=None)  # type: ignore[arg-type]
    _apply_cursor(query, params, None)
    query.limit.assert_not_called()


# ---------------------------------------------------------------------------
# _convert_raw_items tests
# ---------------------------------------------------------------------------


def test_convert_raw_items_basic():
    doc1 = _MockDocumentSnapshot("id1", {"name": "Alice", "age": 30})
    doc2 = _MockDocumentSnapshot("id2", {"name": "Bob", "age": 25})
    result = _convert_raw_items([doc1, doc2])
    assert result == [
        {"name": "Alice", "age": 30, "id": "id1"},
        {"name": "Bob", "age": 25, "id": "id2"},
    ]


def test_convert_raw_items_empty_list():
    result = _convert_raw_items([])
    assert result == []


def test_convert_raw_items_none_dict():
    # to_dict() returns None — should default to {}
    doc = _MockDocumentSnapshot("id1", None)
    result = _convert_raw_items([doc])
    assert result == [{"id": "id1"}]


def test_convert_raw_items_id_overrides_existing():
    # id field in document data should be overridden by doc.id
    doc = _MockDocumentSnapshot("real_id", {"id": "old_id", "val": 1})
    result = _convert_raw_items([doc])
    assert result[0]["id"] == "real_id"


# ---------------------------------------------------------------------------
# _get_total tests
# ---------------------------------------------------------------------------


def test_get_total_sync():
    query = _MockQuery()
    _MockAggregationQuery.total = 7
    gen = _get_total(False, query, None)
    result = run_sync_flow(gen)
    assert result == 7


@pytest.mark.asyncio
async def test_get_total_async():
    query = _MockAsyncQuery()
    _MockAsyncAggregationQuery.total = 4
    gen = _get_total(True, query, None)
    result = await run_async_flow(gen)
    assert result == 4


def test_get_total_sync_with_transaction():
    query = _MockQuery()
    _MockAggregationQuery.total = 2
    transaction = _MockTransaction()
    gen = _get_total(False, query, transaction)
    result = run_sync_flow(gen)
    assert result == 2


# ---------------------------------------------------------------------------
# _total_flow tests
# ---------------------------------------------------------------------------


def test_total_flow_sync():
    query = _MockQuery()
    _MockAggregationQuery.total = 10
    gen = _total_flow(False, query, None)
    result = run_sync_flow(gen)
    assert result == 10


@pytest.mark.asyncio
async def test_total_flow_async():
    query = _MockAsyncQuery()
    _MockAsyncAggregationQuery.total = 6
    gen = _total_flow(True, query, None)
    result = await run_async_flow(gen)
    assert result == 6


# ---------------------------------------------------------------------------
# _limit_offset_flow tests
# ---------------------------------------------------------------------------


def test_limit_offset_flow_returns_items():
    query = _MockQuery()
    doc = _MockDocumentSnapshot("id1", {"x": 1})
    query._items = [doc]
    raw_params = RawParams(limit=10, offset=0)
    gen = _limit_offset_flow(query, None, raw_params)
    result = run_sync_flow(gen)
    assert result == [doc]


def test_limit_offset_flow_empty():
    query = _MockQuery()
    query._items = []
    raw_params = RawParams(limit=5, offset=0)
    gen = _limit_offset_flow(query, None, raw_params)
    result = run_sync_flow(gen)
    assert result == []


@pytest.mark.asyncio
async def test_limit_offset_flow_async():
    query = _MockAsyncQuery()
    doc = _MockDocumentSnapshot("id2", {"y": 2})
    query._items = [doc]
    raw_params = RawParams(limit=10, offset=0)
    gen = _limit_offset_flow(query, None, raw_params)
    result = await run_async_flow(gen)
    assert result == [doc]


# ---------------------------------------------------------------------------
# _fetch_cursor tests
# ---------------------------------------------------------------------------


def test_fetch_cursor_no_cursor():
    query = _MockQuery()
    params = CursorRawParams(cursor=None, size=10)
    gen = _fetch_cursor(query, params, None)
    result = run_sync_flow(gen)
    assert result is None


def test_fetch_cursor_with_cursor():
    parent_mock = MagicMock()
    doc_mock = _MockDocumentSnapshot("doc123", {"a": 1})
    parent_mock.document.return_value.get.return_value = doc_mock

    query = _MockQuery()
    query._parent = parent_mock

    params = CursorRawParams(cursor="doc123", size=10)
    gen = _fetch_cursor(query, params, None)
    result = run_sync_flow(gen)
    assert result is doc_mock
    parent_mock.document.assert_called_once_with("doc123")


@pytest.mark.asyncio
async def test_fetch_cursor_with_cursor_async():
    parent_mock = MagicMock()
    doc_mock = _MockDocumentSnapshot("docABC", {"b": 2})
    parent_mock.document.return_value.get = AsyncMock(return_value=doc_mock)

    query = _MockAsyncQuery()
    query._parent = parent_mock

    params = CursorRawParams(cursor="docABC", size=5)
    gen = _fetch_cursor(query, params, None)
    result = await run_async_flow(gen)
    assert result is doc_mock


# ---------------------------------------------------------------------------
# _cursor_flow tests
# ---------------------------------------------------------------------------


def test_cursor_flow_no_items():
    query = _MockQuery()
    query._items = []
    raw_params = CursorRawParams(cursor=None, size=10)
    gen = _cursor_flow(query, None, raw_params)
    items, extra = run_sync_flow(gen)
    assert items == []
    assert extra is None


def test_cursor_flow_with_items():
    query = _MockQuery()
    doc1 = _MockDocumentSnapshot("id1", {"val": 1})
    doc2 = _MockDocumentSnapshot("id2", {"val": 2})
    query._items = [doc1, doc2]
    raw_params = CursorRawParams(cursor=None, size=10)
    gen = _cursor_flow(query, None, raw_params)
    items, extra = run_sync_flow(gen)
    assert items == [doc1, doc2]
    assert extra == {"next_": "id2"}


def test_cursor_flow_with_cursor_and_items():
    parent_mock = MagicMock()
    snapshot = _MockDocumentSnapshot("cursor_doc", {})
    parent_mock.document.return_value.get.return_value = snapshot

    query = _MockQuery()
    query._parent = parent_mock
    doc = _MockDocumentSnapshot("id_next", {"val": 99})
    query._items = [doc]

    raw_params = CursorRawParams(cursor="cursor_doc", size=5)
    gen = _cursor_flow(query, None, raw_params)
    items, extra = run_sync_flow(gen)
    assert items == [doc]
    assert extra == {"next_": "id_next"}


# ---------------------------------------------------------------------------
# _firebase_flow tests
# ---------------------------------------------------------------------------


def test_firebase_flow_with_query_instance():
    # When src is already a Query instance (not CollectionReference),
    # it should pass through directly
    query = _MockQuery()
    doc = _MockDocumentSnapshot("id1", {"k": "v"})
    query._items = [doc]
    _MockAggregationQuery.total = 1
    params = Params(page=1, size=10)

    gen = _firebase_flow(query, params=params, raw=True, transaction=None, transformer=None, additional_data=None, config=None, async_=False)
    result = run_sync_flow(gen)
    assert isinstance(result, Page)


def test_firebase_flow_with_collection_reference():
    # When src is a CollectionReference, it should be wrapped in Query
    src = _MockCollectionReference()
    _MockAggregationQuery.total = 0
    params = Params(page=1, size=10)

    gen = _firebase_flow(src, params=params, raw=False, transaction=None, transformer=None, additional_data=None, config=None, async_=False)
    result = run_sync_flow(gen)
    assert isinstance(result, Page)


def test_firebase_flow_with_async_collection_reference():
    # When src is an AsyncCollectionReference, it should be wrapped in AsyncQuery
    src = _MockAsyncCollectionReference()
    _MockAsyncAggregationQuery.total = 0
    params = Params(page=1, size=10)

    gen = _firebase_flow(src, params=params, raw=False, transaction=None, transformer=None, additional_data=None, config=None, async_=True)
    # run_async_flow needed since async_=True
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(run_async_flow(gen))
    assert isinstance(result, Page)


def test_firebase_flow_raw_false_uses_inner_transformer():
    # raw=False should attach _convert_raw_items as inner transformer
    query = _MockQuery()
    doc = _MockDocumentSnapshot("id1", {"field": "value"})
    query._items = [doc]
    _MockAggregationQuery.total = 1
    params = Params(page=1, size=10)

    gen = _firebase_flow(query, params=params, raw=False, transaction=None, transformer=None, additional_data=None, config=None, async_=False)
    result = run_sync_flow(gen)
    assert isinstance(result, Page)
    # Items should be converted to dicts
    assert result.items[0] == {"field": "value", "id": "id1"}


def test_firebase_flow_raw_true_no_conversion():
    # raw=True should NOT use _convert_raw_items inner transformer
    query = _MockQuery()
    doc = _MockDocumentSnapshot("id1", {"field": "value"})
    query._items = [doc]
    _MockAggregationQuery.total = 1
    params = Params(page=1, size=10)

    gen = _firebase_flow(query, params=params, raw=True, transaction=None, transformer=None, additional_data=None, config=None, async_=False)
    result = run_sync_flow(gen)
    assert isinstance(result, Page)
    # Items should be raw DocumentSnapshot objects (not converted)
    assert result.items[0] is doc


# ---------------------------------------------------------------------------
# paginate tests
# ---------------------------------------------------------------------------


def test_paginate_returns_page():
    query = _MockQuery()
    doc = _MockDocumentSnapshot("id1", {"name": "Test"})
    query._items = [doc]
    _MockAggregationQuery.total = 1
    params = Params(page=1, size=10)

    result = paginate(query, params=params, raw=True)
    assert isinstance(result, Page)
    assert result.total == 1
    assert result.items == [doc]


def test_paginate_empty():
    query = _MockQuery()
    query._items = []
    _MockAggregationQuery.total = 0
    params = Params(page=1, size=10)

    result = paginate(query, params=params, raw=True)
    assert isinstance(result, Page)
    assert result.total == 0
    assert result.items == []


def test_paginate_with_set_params():
    query = _MockQuery()
    query._items = []
    _MockAggregationQuery.total = 0

    with set_params(Params(page=1, size=5)):
        result = paginate(query, raw=True)
    assert isinstance(result, Page)


def test_paginate_converts_items():
    query = _MockQuery()
    doc = _MockDocumentSnapshot("id1", {"x": 42})
    query._items = [doc]
    _MockAggregationQuery.total = 1
    params = Params(page=1, size=10)

    result = paginate(query, params=params, raw=False)
    assert isinstance(result, Page)
    assert result.items[0] == {"x": 42, "id": "id1"}


# ---------------------------------------------------------------------------
# apaginate tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_returns_page():
    query = _MockAsyncQuery()
    doc = _MockDocumentSnapshot("id1", {"name": "Async"})
    query._items = [doc]
    _MockAsyncAggregationQuery.total = 1
    params = Params(page=1, size=10)

    result = await apaginate(query, params=params, raw=True)
    assert isinstance(result, Page)
    assert result.total == 1
    assert result.items == [doc]


@pytest.mark.asyncio
async def test_apaginate_empty():
    query = _MockAsyncQuery()
    query._items = []
    _MockAsyncAggregationQuery.total = 0
    params = Params(page=1, size=10)

    result = await apaginate(query, params=params, raw=True)
    assert isinstance(result, Page)
    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_with_set_params():
    query = _MockAsyncQuery()
    query._items = []
    _MockAsyncAggregationQuery.total = 0

    with set_params(Params(page=1, size=5)):
        result = await apaginate(query, raw=True)
    assert isinstance(result, Page)


@pytest.mark.asyncio
async def test_apaginate_converts_items():
    query = _MockAsyncQuery()
    doc = _MockDocumentSnapshot("id1", {"y": 99})
    query._items = [doc]
    _MockAsyncAggregationQuery.total = 1
    params = Params(page=1, size=10)

    result = await apaginate(query, params=params, raw=False)
    assert isinstance(result, Page)
    assert result.items[0] == {"y": 99, "id": "id1"}
