import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Mock piccolo modules before importing fastapi_pagination.ext.piccolo
# ---------------------------------------------------------------------------


class _MockTable:
    @classmethod
    def select(cls):
        return _MockSelect(cls)


class _MockSelect:
    __slots__ = ("table", "columns_delegate", "order_by_delegate")

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, table):
        self.table = table
        cd = MagicMock()
        cd.selected_columns = []
        self.columns_delegate = cd
        ob = MagicMock()
        ob._order_by = MagicMock()
        ob._order_by.order_by_items = []
        self.order_by_delegate = ob

    def columns(self, *args):
        m = MagicMock()
        m.first.return_value = {"count": 5}
        return m

    def limit(self, n):
        return self

    def offset(self, n):
        return self


_MockCount = MagicMock()

_piccolo_pkg = MagicMock()
_piccolo_query_mod = MagicMock()
_piccolo_query_mod.Select = _MockSelect
_piccolo_query_methods_mod = MagicMock()
_piccolo_query_methods_select_mod = MagicMock()
_piccolo_query_methods_select_mod.Count = _MockCount
_piccolo_table_mod = MagicMock()
_piccolo_table_mod.Table = _MockTable

sys.modules.setdefault("piccolo", _piccolo_pkg)
sys.modules.setdefault("piccolo.query", _piccolo_query_mod)
sys.modules.setdefault("piccolo.query.methods", _piccolo_query_methods_mod)
sys.modules.setdefault("piccolo.query.methods.select", _piccolo_query_methods_select_mod)
sys.modules.setdefault("piccolo.table", _piccolo_table_mod)

from fastapi_pagination import Page, Params  # noqa: E402
from fastapi_pagination.api import set_page  # noqa: E402
from fastapi_pagination.ext.piccolo import _copy_query, _total_flow, apaginate, paginate  # noqa: E402


# ---------------------------------------------------------------------------
# _copy_query
# ---------------------------------------------------------------------------


def test_copy_query_returns_new_instance():
    query = _MockSelect(_MockTable)
    result = _copy_query(query)
    assert result is not query
    assert type(result) is _MockSelect


def test_copy_query_copies_table():
    query = _MockSelect(_MockTable)
    result = _copy_query(query)
    assert result.table is query.table


def test_copy_query_suppresses_missing_slots():
    # Even with slots that may not be present on a subclass, no exception raised
    query = _MockSelect(_MockTable)

    class _Slim(_MockSelect):
        __slots__ = ("table",)

    slim = _Slim(_MockTable)
    result = _copy_query(slim)
    assert type(result) is _Slim


# ---------------------------------------------------------------------------
# _total_flow
# ---------------------------------------------------------------------------


def test_total_flow_returns_count_when_row_present():
    query = _MockSelect(_MockTable)

    gen = _total_flow(query)
    yielded = gen.send(None)  # advance to the yield
    # yielded is count_query.columns(Count()).first()
    assert yielded is not None

    row = {"count": 42}
    with pytest.raises(StopIteration) as exc_info:
        gen.send(row)

    assert exc_info.value.value == 42


def test_total_flow_returns_none_when_no_row():
    query = _MockSelect(_MockTable)

    gen = _total_flow(query)
    gen.send(None)

    with pytest.raises(StopIteration) as exc_info:
        gen.send(None)

    assert exc_info.value.value is None


def test_total_flow_resets_columns_and_order():
    query = _MockSelect(_MockTable)
    query.columns_delegate.selected_columns = ["id", "name"]
    query.order_by_delegate._order_by.order_by_items = ["id ASC"]

    gen = _total_flow(query)
    # The generator body runs up to the first yield
    gen.send(None)

    # Original query should be unaffected; copies should be reset
    assert query.columns_delegate.selected_columns == ["id", "name"]
    assert query.order_by_delegate._order_by.order_by_items == ["id ASC"]


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_calls_select_when_table_class_given():
    """When given a Table class (not a Select instance), .select() is called."""
    with patch("fastapi_pagination.ext.piccolo.run_async_flow", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = MagicMock()

        class MyTable(_MockTable):
            pass

        await apaginate(MyTable, params=Params())

    mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_does_not_call_select_when_given_select_instance():
    query = _MockSelect(_MockTable)
    with patch("fastapi_pagination.ext.piccolo.run_async_flow", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = MagicMock()
        await apaginate(query, params=Params())

    mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_passes_through_kwargs():
    query = _MockSelect(_MockTable)
    transformer = AsyncMock(return_value=[])
    with patch("fastapi_pagination.ext.piccolo.run_async_flow", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = MagicMock()
        await apaginate(query, params=Params(), transformer=transformer, additional_data={"key": "val"})

    mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# paginate (deprecated wrapper)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate():
    query = _MockSelect(_MockTable)
    with patch("fastapi_pagination.ext.piccolo.apaginate", new_callable=AsyncMock) as mock_apaginate:
        mock_apaginate.return_value = MagicMock()
        result = await paginate(query, params=Params())

    mock_apaginate.assert_called_once_with(
        query,
        params=Params(),
        transformer=None,
        additional_data=None,
        config=None,
    )
    assert result is mock_apaginate.return_value


@pytest.mark.asyncio
async def test_paginate_passes_optional_kwargs():
    query = _MockSelect(_MockTable)
    transformer = AsyncMock(return_value=[])
    with patch("fastapi_pagination.ext.piccolo.apaginate", new_callable=AsyncMock) as mock_apaginate:
        mock_apaginate.return_value = MagicMock()
        await paginate(query, params=Params(), transformer=transformer, additional_data={"x": 1})

    mock_apaginate.assert_called_once_with(
        query,
        params=Params(),
        transformer=transformer,
        additional_data={"x": 1},
        config=None,
    )
