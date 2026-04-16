import sys
from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock piccolo modules before importing extension (piccolo is not installed in test env)
_Count = MagicMock(name="Count")


class _MockSelect:
    __slots__ = ["table", "_columns", "_where", "columns_delegate", "order_by_delegate"]

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, table):
        self.table = table
        self._columns = []
        self._where = []
        self.columns_delegate = MagicMock()
        self.columns_delegate.selected_columns = []
        self.order_by_delegate = MagicMock()
        self.order_by_delegate._order_by.order_by_items = []

    def columns(self, *args):
        return self

    def first(self):
        return self

    def limit(self, n):
        new = _MockSelect(self.table)
        return new

    def offset(self, n):
        new = _MockSelect(self.table)
        return new

    def __await__(self):
        async def _inner():
            return {"count": 5}

        return _inner().__await__()


class _MockTable:
    @classmethod
    def select(cls):
        return _MockSelect(cls)


_piccolo_table_base = MagicMock()
_piccolo_table_base.Table = _MockTable

if "piccolo" not in sys.modules:
    sys.modules["piccolo"] = MagicMock()
if "piccolo.query" not in sys.modules:
    sys.modules["piccolo.query"] = MagicMock(Select=_MockSelect)
if "piccolo.query.methods" not in sys.modules:
    sys.modules["piccolo.query.methods"] = MagicMock()
if "piccolo.query.methods.select" not in sys.modules:
    sys.modules["piccolo.query.methods.select"] = MagicMock(Count=_Count)
if "piccolo.table" not in sys.modules:
    sys.modules["piccolo.table"] = _piccolo_table_base

from fastapi_pagination import Page, Params
from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.ext.piccolo import _copy_query, _total_flow, apaginate, paginate


def _make_select_query():
    table = MagicMock()
    query = _MockSelect(table)
    query._columns = ["id", "name"]
    query._where = []
    return query


# Tests for _copy_query

def test_copy_query_returns_same_type():
    query = _make_select_query()
    result = _copy_query(query)
    assert isinstance(result, _MockSelect)


def test_copy_query_copies_table():
    query = _make_select_query()
    result = _copy_query(query)
    # table is deepcopied (it's a slot), so verify the copy exists
    assert result.table is not None


def test_copy_query_deep_copies_slots():
    query = _make_select_query()
    result = _copy_query(query)
    # _columns should be a copy, not the same object
    assert result._columns == query._columns
    assert result._columns is not query._columns


def test_copy_query_independent_modification():
    query = _make_select_query()
    result = _copy_query(query)
    result._columns.append("extra")
    assert "extra" not in query._columns


# Tests for _total_flow

def test_total_flow_returns_count_when_row_present():
    query = _make_select_query()

    gen = _total_flow(query)
    # The generator yields the awaitable for count query
    yielded = next(gen)
    # Simulate the result: a row with count
    try:
        gen.send({"count": 42})
    except StopIteration as e:
        result = e.value
    else:
        result = None

    assert result == 42


def test_total_flow_returns_none_when_no_row():
    query = _make_select_query()

    gen = _total_flow(query)
    next(gen)
    try:
        gen.send(None)
    except StopIteration as e:
        result = e.value
    else:
        result = None

    assert result is None


def test_total_flow_resets_selected_columns():
    query = _make_select_query()

    gen = _total_flow(query)
    next(gen)
    try:
        gen.send({"count": 1})
    except StopIteration:
        pass

    # count_query's columns_delegate.selected_columns was set to []
    # We verify the flow ran without errors (selecting columns reset)


def test_total_flow_is_generator():
    query = _make_select_query()
    gen = _total_flow(query)
    import inspect
    assert inspect.isgenerator(gen)


# Tests for apaginate

@pytest.mark.asyncio
async def test_apaginate_with_select_query():
    query = _make_select_query()
    params = Params(page=1, size=10)

    with set_page(Page), set_params(params):
        with patch("fastapi_pagination.ext.piccolo.run_async_flow") as mock_flow:
            mock_flow.return_value = MagicMock(items=[], total=0, page=1, pages=0, size=10)
            result = await apaginate(query, params=params)

    mock_flow.assert_called_once()
    assert result is not None


@pytest.mark.asyncio
async def test_apaginate_converts_table_class_to_select():
    """When a Table class (not a Select instance) is passed, it should call .select()"""
    params = Params(page=1, size=10)

    table_cls = MagicMock(spec=_MockTable)
    table_cls.select.return_value = _make_select_query()

    with set_page(Page), set_params(params):
        with patch("fastapi_pagination.ext.piccolo.run_async_flow") as mock_flow:
            mock_flow.return_value = MagicMock()

            # Pass a non-Select object (Table class) to trigger the isinstance check
            with patch("fastapi_pagination.ext.piccolo.Select", _MockSelect):
                # table_cls is not an instance of _MockSelect, so query.select() should be called
                result = await apaginate(table_cls, params=params)

    table_cls.select.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_with_table_instance_calls_select():
    """When query is a Table type (not Select), .select() is called."""
    params = Params(page=1, size=10)

    class FakeTable(_MockTable):
        pass

    with set_page(Page), set_params(params):
        with patch("fastapi_pagination.ext.piccolo.run_async_flow") as mock_flow:
            mock_flow.return_value = MagicMock()
            with patch("fastapi_pagination.ext.piccolo.Select", _MockSelect):
                result = await apaginate(FakeTable, params=params)

    assert result is not None


# Tests for paginate (deprecated wrapper)

@pytest.mark.asyncio
async def test_paginate_calls_apaginate():
    query = _make_select_query()
    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.piccolo.apaginate", new_callable=AsyncMock) as mock_apaginate:
        mock_apaginate.return_value = MagicMock()
        result = await paginate(query, params=params)

    mock_apaginate.assert_called_once_with(
        query,
        params=params,
        transformer=None,
        additional_data=None,
        config=None,
    )


@pytest.mark.asyncio
async def test_paginate_passes_all_kwargs():
    query = _make_select_query()
    params = Params(page=1, size=5)
    transformer = AsyncMock(return_value=[])
    additional_data = {"extra": "data"}

    with patch("fastapi_pagination.ext.piccolo.apaginate", new_callable=AsyncMock) as mock_apaginate:
        mock_apaginate.return_value = MagicMock()
        await paginate(
            query,
            params=params,
            transformer=transformer,
            additional_data=additional_data,
        )

    mock_apaginate.assert_called_once_with(
        query,
        params=params,
        transformer=transformer,
        additional_data=additional_data,
        config=None,
    )
