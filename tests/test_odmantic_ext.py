import sys
import warnings
from unittest.mock import AsyncMock, MagicMock

import pytest

# Create mock odmantic classes before importing the extension module
class _MockAIOEngine:
    pass


class _MockSyncEngine:
    pass


class _MockModel:
    pass


_odmantic_mock = MagicMock()
_odmantic_mock.AIOEngine = _MockAIOEngine
_odmantic_mock.SyncEngine = _MockSyncEngine
_odmantic_mock.Model = _MockModel

_odmantic_engine_mock = MagicMock()
_odmantic_engine_mock.AIOSessionType = type(None)
_odmantic_engine_mock.SyncSessionType = type(None)

_odmantic_query_mock = MagicMock()
_odmantic_query_mock.QueryExpression = MagicMock

# Remove any cached version of these modules so our mocks take effect
for _key in list(sys.modules.keys()):
    if _key == "odmantic" or _key.startswith("odmantic.") or _key == "fastapi_pagination.ext.odmantic":
        del sys.modules[_key]

sys.modules["odmantic"] = _odmantic_mock
sys.modules["odmantic.engine"] = _odmantic_engine_mock
sys.modules["odmantic.query"] = _odmantic_query_mock

from fastapi_pagination import Page, Params  # noqa: E402
from fastapi_pagination.api import set_page, set_params  # noqa: E402
from fastapi_pagination.ext.odmantic import apaginate, paginate  # noqa: E402
from fastapi_pagination.utils import disable_installed_extensions_check  # noqa: E402

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def disable_ext_check():
    disable_installed_extensions_check()


def _make_sync_engine(total: int, items: list):
    engine = _MockSyncEngine()
    engine.count = MagicMock(return_value=total)
    engine.find = MagicMock(return_value=items)
    return engine


def _make_async_engine(total: int, items: list):
    engine = _MockAIOEngine()
    engine.count = AsyncMock(return_value=total)
    engine.find = AsyncMock(return_value=items)
    return engine


def test_paginate_sync_basic():
    engine = _make_sync_engine(total=3, items=[1, 2, 3])

    with set_page(Page), set_params(Params(page=1, size=10)):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = paginate(engine, _MockModel)

    assert result.total == 3
    assert result.items == [1, 2, 3]


def test_paginate_sync_with_pagination():
    engine = _make_sync_engine(total=10, items=[5, 6, 7, 8, 9])

    with set_page(Page), set_params(Params(page=2, size=5)):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = paginate(engine, _MockModel)

    assert result.total == 10
    assert result.items == [5, 6, 7, 8, 9]


def test_paginate_sync_with_params_argument():
    engine = _make_sync_engine(total=7, items=[1, 2, 3])
    params = Params(page=1, size=3)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = paginate(engine, _MockModel, params=params)

    assert result.total == 7
    assert result.items == [1, 2, 3]


def test_paginate_aio_engine_returns_coroutine_with_deprecation_warning():
    engine = _make_async_engine(total=2, items=[1, 2])

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = paginate(engine, _MockModel)

    import inspect

    assert inspect.iscoroutine(result)
    result.close()
    assert any(issubclass(warning.category, DeprecationWarning) for warning in w)


async def test_paginate_aio_engine_delegates_to_apaginate():
    engine = _make_async_engine(total=2, items=[1, 2])

    with set_page(Page), set_params(Params(page=1, size=10)):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            coro = paginate(engine, _MockModel)
            result = await coro

    assert result.total == 2
    assert result.items == [1, 2]


async def test_apaginate_basic():
    engine = _make_async_engine(total=3, items=[1, 2, 3])

    with set_page(Page), set_params(Params(page=1, size=10)):
        result = await apaginate(engine, _MockModel)

    assert result.total == 3
    assert result.items == [1, 2, 3]


async def test_apaginate_with_pagination():
    engine = _make_async_engine(total=10, items=[5, 6, 7, 8, 9])

    with set_page(Page), set_params(Params(page=2, size=5)):
        result = await apaginate(engine, _MockModel)

    assert result.total == 10
    assert result.items == [5, 6, 7, 8, 9]


async def test_apaginate_with_params_argument():
    engine = _make_async_engine(total=5, items=[1, 2, 3])
    params = Params(page=1, size=3)

    with set_page(Page):
        result = await apaginate(engine, _MockModel, params=params)

    assert result.total == 5
    assert result.items == [1, 2, 3]


async def test_apaginate_empty_results():
    engine = _make_async_engine(total=0, items=[])

    with set_page(Page), set_params(Params(page=1, size=10)):
        result = await apaginate(engine, _MockModel)

    assert result.total == 0
    assert result.items == []
