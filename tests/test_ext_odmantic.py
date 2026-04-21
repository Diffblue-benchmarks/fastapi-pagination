"""Tests for fastapi_pagination.ext.odmantic"""

import sys
import warnings
from unittest.mock import MagicMock

import pytest

from fastapi_pagination.default import Params


# ---------------------------------------------------------------------------
# Mock odmantic classes
# ---------------------------------------------------------------------------


class MockModel:
    """Mock for odmantic Model."""
    pass


class MockSyncEngine:
    """Mock for odmantic SyncEngine (synchronous)."""

    def __init__(self, items, total=None):
        self._items = list(items)
        self._total = total if total is not None else len(self._items)

    def find(self, model, *queries, sort=None, session=None, limit=None, skip=0):
        start = skip or 0
        end = (start + limit) if limit else None
        return self._items[start:end]

    def count(self, model, *queries, session=None):
        return self._total


class MockAIOEngine:
    """Mock for odmantic AIOEngine (asynchronous)."""

    def __init__(self, items, total=None):
        self._items = list(items)
        self._total = total if total is not None else len(self._items)

    async def find(self, model, *queries, sort=None, session=None, limit=None, skip=0):
        start = skip or 0
        end = (start + limit) if limit else None
        return self._items[start:end]

    async def count(self, model, *queries, session=None):
        return self._total


class MockQueryExpression:
    """Mock for odmantic QueryExpression."""
    pass


# ---------------------------------------------------------------------------
# Inject mocks into sys.modules before importing the extension
# ---------------------------------------------------------------------------

_mock_odmantic_engine = MagicMock()
_mock_odmantic_engine.AIOSessionType = type(None)
_mock_odmantic_engine.SyncSessionType = type(None)

_mock_odmantic_query = MagicMock()
_mock_odmantic_query.QueryExpression = MockQueryExpression

_mock_odmantic = MagicMock()
_mock_odmantic.AIOEngine = MockAIOEngine
_mock_odmantic.Model = MockModel
_mock_odmantic.SyncEngine = MockSyncEngine

sys.modules.setdefault("odmantic", _mock_odmantic)
sys.modules.setdefault("odmantic.engine", _mock_odmantic_engine)
sys.modules.setdefault("odmantic.query", _mock_odmantic_query)

from fastapi_pagination.ext.odmantic import apaginate, paginate  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def params():
    return Params(page=1, size=5)


# ---------------------------------------------------------------------------
# Tests for paginate() with SyncEngine (line 149: return run_sync_flow(...))
# ---------------------------------------------------------------------------


def test_paginate_sync_engine_basic(params):
    items = list(range(10))
    engine = MockSyncEngine(items)
    result = paginate(engine, MockModel, params=params)
    assert result.total == 10
    assert len(result.items) == 5


def test_paginate_sync_engine_first_page():
    items = list(range(20))
    engine = MockSyncEngine(items)
    result = paginate(engine, MockModel, params=Params(page=1, size=5))
    assert result.total == 20
    assert result.items == list(range(5))


def test_paginate_sync_engine_second_page():
    items = list(range(20))
    engine = MockSyncEngine(items)
    result = paginate(engine, MockModel, params=Params(page=2, size=5))
    assert result.total == 20
    assert result.items == list(range(5, 10))


def test_paginate_sync_engine_empty():
    engine = MockSyncEngine([])
    result = paginate(engine, MockModel, params=Params(page=1, size=10))
    assert result.total == 0
    assert result.items == []


def test_paginate_sync_engine_with_query(params):
    items = ["a", "b", "c"]
    engine = MockSyncEngine(items)
    query = MockQueryExpression()
    result = paginate(engine, MockModel, query, params=params)
    assert result.total == 3
    assert result.items == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# Tests for paginate() with AIOEngine (lines 132-138: isinstance check + warn)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paginate_aio_engine_returns_coroutine():
    items = list(range(5))
    engine = MockAIOEngine(items)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        coro = paginate(engine, MockModel, params=Params(page=1, size=10))
    result = await coro
    assert result.total == 5
    assert len(result.items) == 5


@pytest.mark.asyncio
async def test_paginate_aio_engine_emits_deprecation_warning():
    items = list(range(3))
    engine = MockAIOEngine(items)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        coro = paginate(engine, MockModel, params=Params(page=1, size=10))
        await coro
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)


@pytest.mark.asyncio
async def test_paginate_aio_engine_result_correct():
    items = list(range(10))
    engine = MockAIOEngine(items)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        result = await paginate(engine, MockModel, params=Params(page=2, size=3))
    assert result.total == 10
    assert result.items == list(range(3, 6))


# ---------------------------------------------------------------------------
# Tests for apaginate() (lines 165, 178: async function + run_async_flow)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_basic():
    items = list(range(10))
    engine = MockAIOEngine(items)
    result = await apaginate(engine, MockModel, params=Params(page=1, size=5))
    assert result.total == 10
    assert len(result.items) == 5


@pytest.mark.asyncio
async def test_apaginate_first_page():
    items = list(range(15))
    engine = MockAIOEngine(items)
    result = await apaginate(engine, MockModel, params=Params(page=1, size=5))
    assert result.total == 15
    assert result.items == list(range(5))


@pytest.mark.asyncio
async def test_apaginate_second_page():
    items = list(range(20))
    engine = MockAIOEngine(items)
    result = await apaginate(engine, MockModel, params=Params(page=2, size=5))
    assert result.total == 20
    assert result.items == list(range(5, 10))


@pytest.mark.asyncio
async def test_apaginate_empty():
    engine = MockAIOEngine([])
    result = await apaginate(engine, MockModel, params=Params(page=1, size=10))
    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_with_query():
    items = ["x", "y", "z"]
    engine = MockAIOEngine(items)
    query = MockQueryExpression()
    result = await apaginate(engine, MockModel, query, params=Params(page=1, size=10))
    assert result.total == 3
    assert result.items == ["x", "y", "z"]


@pytest.mark.asyncio
async def test_apaginate_single_item():
    engine = MockAIOEngine([42])
    result = await apaginate(engine, MockModel, params=Params(page=1, size=10))
    assert result.total == 1
    assert result.items == [42]
