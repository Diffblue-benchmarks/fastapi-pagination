import sys
import warnings
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Stub odmantic classes so isinstance() checks in the extension work properly
# ---------------------------------------------------------------------------

class _MockSyncEngine:
    def count(self, *args, **kwargs):
        return 0

    def find(self, *args, **kwargs):
        return []


class _MockAIOEngine:
    def count(self, *args, **kwargs):
        return 0

    def find(self, *args, **kwargs):
        return []


class _MockModel:
    pass


class _MockQueryExpression:
    pass


# Register mocks before the extension module is imported so its top-level
# "from odmantic import ..." statements resolve to our stubs.
_odmantic_mod = MagicMock()
_odmantic_mod.AIOEngine = _MockAIOEngine
_odmantic_mod.SyncEngine = _MockSyncEngine
_odmantic_mod.Model = _MockModel

_odmantic_engine_mod = MagicMock()
_odmantic_engine_mod.AIOSessionType = type(None)
_odmantic_engine_mod.SyncSessionType = type(None)

_odmantic_query_mod = MagicMock()
_odmantic_query_mod.QueryExpression = _MockQueryExpression

sys.modules.setdefault("odmantic", _odmantic_mod)
sys.modules.setdefault("odmantic.engine", _odmantic_engine_mod)
sys.modules.setdefault("odmantic.query", _odmantic_query_mod)

from fastapi_pagination.api import set_page  # noqa: E402
from fastapi_pagination.default import Page, Params  # noqa: E402
from fastapi_pagination.ext.odmantic import apaginate, paginate  # noqa: E402
from fastapi_pagination.utils import disable_installed_extensions_check  # noqa: E402


@pytest.fixture(autouse=True)
def _disable_ext_check():
    disable_installed_extensions_check()


# ---------------------------------------------------------------------------
# paginate() with SyncEngine  →  covers lines 119, 149
# ---------------------------------------------------------------------------

def test_paginate_sync_engine_returns_page():
    engine = _MockSyncEngine()
    engine.count = MagicMock(return_value=3)
    engine.find = MagicMock(return_value=["item1", "item2", "item3"])

    params = Params(page=1, size=10)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        with set_page(Page):
            result = paginate(engine, _MockModel, params=params)

    assert result.total == 3
    assert result.items == ["item1", "item2", "item3"]


def test_paginate_sync_engine_empty_results():
    engine = _MockSyncEngine()
    engine.count = MagicMock(return_value=0)
    engine.find = MagicMock(return_value=[])

    params = Params(page=1, size=5)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        with set_page(Page):
            result = paginate(engine, _MockModel, params=params)

    assert result.total == 0
    assert result.items == []


def test_paginate_sync_engine_with_queries():
    engine = _MockSyncEngine()
    engine.count = MagicMock(return_value=1)
    engine.find = MagicMock(return_value=["single"])

    params = Params(page=1, size=10)
    query = {"field": "value"}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        with set_page(Page):
            result = paginate(engine, _MockModel, query, params=params)

    assert result.total == 1
    assert result.items == ["single"]


# ---------------------------------------------------------------------------
# paginate() with AIOEngine  →  covers lines 132, 133, 138
# ---------------------------------------------------------------------------

def test_paginate_aio_engine_emits_deprecation_warning():
    engine = _MockAIOEngine()
    engine.count = MagicMock(return_value=0)
    engine.find = MagicMock(return_value=[])

    params = Params(page=1, size=5)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with set_page(Page):
            result = paginate(engine, _MockModel, params=params)

    dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(dep_warnings) >= 1

    # Result should be a coroutine (apaginate is async)
    import inspect
    assert inspect.iscoroutine(result)
    result.close()


def test_paginate_aio_engine_returns_coroutine():
    engine = _MockAIOEngine()
    params = Params(page=1, size=5)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        with set_page(Page):
            result = paginate(engine, _MockModel, params=params)

    import inspect
    assert inspect.iscoroutine(result)
    result.close()


# ---------------------------------------------------------------------------
# apaginate()  →  covers lines 165, 178
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apaginate_returns_page():
    engine = _MockAIOEngine()
    engine.count = MagicMock(return_value=2)
    engine.find = MagicMock(return_value=["a", "b"])

    params = Params(page=1, size=10)
    with set_page(Page):
        result = await apaginate(engine, _MockModel, params=params)

    assert result.total == 2
    assert result.items == ["a", "b"]


@pytest.mark.asyncio
async def test_apaginate_empty():
    engine = _MockAIOEngine()
    engine.count = MagicMock(return_value=0)
    engine.find = MagicMock(return_value=[])

    params = Params(page=1, size=5)
    with set_page(Page):
        result = await apaginate(engine, _MockModel, params=params)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_with_queries():
    engine = _MockAIOEngine()
    engine.count = MagicMock(return_value=1)
    engine.find = MagicMock(return_value=["item"])

    params = Params(page=1, size=10)
    query = {"field": "value"}
    with set_page(Page):
        result = await apaginate(engine, _MockModel, query, params=params)

    assert result.total == 1
    assert result.items == ["item"]


@pytest.mark.asyncio
async def test_apaginate_pagination_second_page():
    engine = _MockAIOEngine()
    engine.count = MagicMock(return_value=10)
    engine.find = MagicMock(return_value=["f", "g", "h", "i", "j"])

    params = Params(page=2, size=5)
    with set_page(Page):
        result = await apaginate(engine, _MockModel, params=params)

    assert result.total == 10
    assert result.items == ["f", "g", "h", "i", "j"]
