"""Tests for fastapi_pagination.ext.odmantic module."""
import sys
import warnings
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Fake odmantic classes (odmantic may not be installed in all environments)
# ---------------------------------------------------------------------------

class _FakeSyncEngine:
    def __init__(self, items=None, total=None):
        self._items = items if items is not None else [1, 2, 3]
        self._total = total if total is not None else len(self._items)

    def find(self, model, *queries, sort=None, session=None, limit=None, skip=0):
        return self._items

    def count(self, model, *queries, session=None):
        return self._total


class _FakeAIOEngine:
    def __init__(self, items=None, total=None):
        self._items = items if items is not None else [1, 2, 3]
        self._total = total if total is not None else len(self._items)

    async def find(self, model, *queries, sort=None, session=None, limit=None, skip=0):
        return self._items

    async def count(self, model, *queries, session=None):
        return self._total


class _FakeModel:
    pass


def _install_odmantic_mock():
    """Install fake odmantic module stubs into sys.modules."""
    odmantic_mod = MagicMock()
    odmantic_engine_mod = MagicMock()
    odmantic_query_mod = MagicMock()

    odmantic_mod.SyncEngine = _FakeSyncEngine
    odmantic_mod.AIOEngine = _FakeAIOEngine
    odmantic_mod.Model = _FakeModel
    odmantic_engine_mod.AIOSessionType = type("AIOSessionType", (), {})
    odmantic_engine_mod.SyncSessionType = type("SyncSessionType", (), {})
    odmantic_query_mod.QueryExpression = type("QueryExpression", (), {})

    sys.modules.setdefault("odmantic", odmantic_mod)
    sys.modules.setdefault("odmantic.engine", odmantic_engine_mod)
    sys.modules.setdefault("odmantic.query", odmantic_query_mod)


_install_odmantic_mock()

# Import after mocking
from fastapi_pagination.api import set_params  # noqa: E402
from fastapi_pagination.bases import RawParams  # noqa: E402
from fastapi_pagination.default import Page, Params  # noqa: E402
from fastapi_pagination.ext.odmantic import (  # noqa: E402
    _limit_offset_flow,
    _paginate_flow,
    apaginate,
    paginate,
)
from fastapi_pagination.flow import run_async_flow, run_sync_flow  # noqa: E402

MockModel = type("MockModel", (_FakeModel,), {})


# ---------------------------------------------------------------------------
# _limit_offset_flow
# ---------------------------------------------------------------------------


def test_limit_offset_flow_returns_list():
    engine = _FakeSyncEngine(items=["a", "b", "c"])
    raw_params = RawParams(limit=10, offset=0)
    result = run_sync_flow(_limit_offset_flow(MockModel, (), None, engine, None, raw_params))
    assert result == ["a", "b", "c"]


def test_limit_offset_flow_empty_result():
    engine = _FakeSyncEngine(items=[])
    raw_params = RawParams(limit=10, offset=0)
    result = run_sync_flow(_limit_offset_flow(MockModel, (), None, engine, None, raw_params))
    assert result == []


def test_limit_offset_flow_with_offset():
    engine = _FakeSyncEngine(items=[3, 4, 5])
    raw_params = RawParams(limit=3, offset=2)
    result = run_sync_flow(_limit_offset_flow(MockModel, (), None, engine, None, raw_params))
    assert result == [3, 4, 5]


# ---------------------------------------------------------------------------
# _paginate_flow (sync path)
# ---------------------------------------------------------------------------


def test_paginate_flow_sync_basic():
    engine = _FakeSyncEngine(items=[10, 20], total=2)
    with set_params(Params(page=1, size=10)):
        page = run_sync_flow(_paginate_flow(False, engine, MockModel))
    assert page.items == [10, 20]
    assert page.total == 2


def test_paginate_flow_sync_empty():
    engine = _FakeSyncEngine(items=[], total=0)
    with set_params(Params(page=1, size=10)):
        page = run_sync_flow(_paginate_flow(False, engine, MockModel))
    assert page.items == []
    assert page.total == 0


# ---------------------------------------------------------------------------
# _paginate_flow (async path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paginate_flow_async_basic():
    engine = _FakeAIOEngine(items=["x", "y"], total=2)
    with set_params(Params(page=1, size=10)):
        page = await run_async_flow(_paginate_flow(True, engine, MockModel))
    assert page.items == ["x", "y"]
    assert page.total == 2


@pytest.mark.asyncio
async def test_paginate_flow_async_empty():
    engine = _FakeAIOEngine(items=[], total=0)
    with set_params(Params(page=1, size=10)):
        page = await run_async_flow(_paginate_flow(True, engine, MockModel))
    assert page.items == []
    assert page.total == 0


# ---------------------------------------------------------------------------
# paginate() with SyncEngine
# ---------------------------------------------------------------------------


def test_paginate_sync_engine_basic():
    engine = _FakeSyncEngine(items=[1, 2, 3], total=3)
    with set_params(Params(page=1, size=10)):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = paginate(engine, MockModel)
    assert result.items == [1, 2, 3]
    assert result.total == 3


def test_paginate_sync_engine_second_page():
    engine = _FakeSyncEngine(items=[6, 7, 8], total=10)
    with set_params(Params(page=2, size=5)):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = paginate(engine, MockModel)
    assert result.page == 2


def test_paginate_sync_engine_emits_deprecation_warning():
    engine = _FakeSyncEngine()
    with set_params(Params()):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            paginate(engine, MockModel)
    # The @deprecated decorator on paginate should emit a DeprecationWarning
    deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecation_warnings) >= 1


# ---------------------------------------------------------------------------
# paginate() with AIOEngine (should delegate to apaginate)
# ---------------------------------------------------------------------------


def test_paginate_aio_engine_emits_deprecation_and_returns_coroutine():
    engine = _FakeAIOEngine(items=[1, 2], total=2)
    with set_params(Params(page=1, size=10)):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = paginate(engine, MockModel)
    # Caller gets back a coroutine from apaginate
    import inspect
    assert inspect.isawaitable(result)
    result.close()  # clean up coroutine

    deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecation_warnings) >= 1


# ---------------------------------------------------------------------------
# apaginate()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_basic():
    engine = _FakeAIOEngine(items=["a", "b", "c"], total=3)
    with set_params(Params(page=1, size=10)):
        result = await apaginate(engine, MockModel)
    assert result.items == ["a", "b", "c"]
    assert result.total == 3


@pytest.mark.asyncio
async def test_apaginate_empty():
    engine = _FakeAIOEngine(items=[], total=0)
    with set_params(Params(page=1, size=10)):
        result = await apaginate(engine, MockModel)
    assert result.items == []
    assert result.total == 0


@pytest.mark.asyncio
async def test_apaginate_with_params():
    engine = _FakeAIOEngine(items=list(range(5)), total=20)
    with set_params(Params(page=2, size=5)):
        result = await apaginate(engine, MockModel)
    assert result.page == 2
    assert result.size == 5
    assert result.total == 20
