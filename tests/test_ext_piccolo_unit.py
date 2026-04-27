"""Unit tests for fastapi_pagination/ext/piccolo.py."""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Mock piccolo modules before importing the extension module
# ---------------------------------------------------------------------------


class _ColDelegate:
    def __init__(self):
        self.selected_columns = []


class _OrderBy:
    def __init__(self):
        self.order_by_items = []


class _OrderByDelegate:
    def __init__(self):
        self._order_by = _OrderBy()


class MockSelect:
    __slots__ = ("table", "_limit", "_offset", "columns_delegate", "order_by_delegate")

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, table=None):
        self.table = table
        self._limit = None
        self._offset = None
        self.columns_delegate = _ColDelegate()
        self.order_by_delegate = _OrderByDelegate()

    def columns(self, *args, **kwargs):
        result = MagicMock()
        result.first = MagicMock(return_value=MagicMock())
        return result

    def limit(self, n):
        return type(self)(self.table)

    def offset(self, n):
        return type(self)(self.table)

    def select(self):
        return MockSelect(self)


class MockTable:
    pass


def _install_piccolo_mocks():
    piccolo_mock = MagicMock()
    piccolo_query_mock = MagicMock()
    piccolo_query_mock.Select = MockSelect
    piccolo_query_methods_mock = MagicMock()
    piccolo_query_methods_select_mock = MagicMock()
    piccolo_query_methods_select_mock.Count = MagicMock(return_value=MagicMock())
    piccolo_table_mock = MagicMock()
    piccolo_table_mock.Table = MockTable

    for key, value in [
        ("piccolo", piccolo_mock),
        ("piccolo.query", piccolo_query_mock),
        ("piccolo.query.methods", piccolo_query_methods_mock),
        ("piccolo.query.methods.select", piccolo_query_methods_select_mock),
        ("piccolo.table", piccolo_table_mock),
    ]:
        sys.modules.setdefault(key, value)


_install_piccolo_mocks()

# Now import the module under test
from fastapi_pagination.ext.piccolo import _copy_query, _total_flow, apaginate, paginate  # noqa: E402
from fastapi_pagination.api import set_page  # noqa: E402
from fastapi_pagination.default import Page, Params  # noqa: E402


# ---------------------------------------------------------------------------
# _copy_query
# ---------------------------------------------------------------------------


def test_copy_query_returns_new_instance():
    query = MockSelect(table="test_table")
    result = _copy_query(query)

    assert result is not query
    assert isinstance(result, MockSelect)
    assert result.table == "test_table"


def test_copy_query_copies_slot_values():
    query = MockSelect(table="my_table")
    query._limit = 10
    query._offset = 5

    result = _copy_query(query)

    assert result._limit == 10
    assert result._offset == 5


def test_copy_query_deep_copies_mutable_slots():
    query = MockSelect(table="tbl")
    query.columns_delegate.selected_columns = ["col1", "col2"]

    result = _copy_query(query)

    # Mutating the original should not affect the copy
    query.columns_delegate.selected_columns.append("col3")
    assert "col3" not in result.columns_delegate.selected_columns


def test_copy_query_suppresses_missing_slots():
    """Slots without values should raise AttributeError, which is suppressed."""
    query = object.__new__(MockSelect)
    object.__setattr__(query, "table", "tbl")
    # Other slots intentionally unset

    result = _copy_query(query)

    assert result is not query
    assert result.table == "tbl"


# ---------------------------------------------------------------------------
# _total_flow
# ---------------------------------------------------------------------------


def test_total_flow_returns_count_when_row_exists():
    query = MockSelect(table="tbl")
    gen = _total_flow(query)

    # Advance generator to the yield point
    gen.send(None)

    # Send back a row with a count value
    with pytest.raises(StopIteration) as exc_info:
        gen.send({"count": 42})

    assert exc_info.value.value == 42


def test_total_flow_returns_none_when_no_row():
    query = MockSelect(table="tbl")
    gen = _total_flow(query)

    gen.send(None)

    with pytest.raises(StopIteration) as exc_info:
        gen.send(None)

    assert exc_info.value.value is None


def test_total_flow_does_not_modify_original_query():
    query = MockSelect(table="tbl")
    query.columns_delegate.selected_columns = ["col1"]
    query.order_by_delegate._order_by.order_by_items = ["id ASC"]

    gen = _total_flow(query)
    gen.send(None)

    # The original query's columns and order_by should be unchanged
    assert query.columns_delegate.selected_columns == ["col1"]
    assert query.order_by_delegate._order_by.order_by_items == ["id ASC"]


def test_total_flow_zero_count_is_truthy_and_returned():
    query = MockSelect(table="tbl")
    gen = _total_flow(query)
    gen.send(None)

    # {"count": 0} is truthy as a dict; cast(int, row["count"]) returns 0
    with pytest.raises(StopIteration) as exc_info:
        gen.send({"count": 0})

    assert exc_info.value.value == 0


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_with_select_instance():
    query = MockSelect(table="tbl")
    params = Params()
    mock_page = MagicMock()

    with patch(
        "fastapi_pagination.ext.piccolo.run_async_flow",
        new_callable=AsyncMock,
        return_value=mock_page,
    ):
        with set_page(Page):
            result = await apaginate(query, params=params)

    assert result is mock_page


@pytest.mark.asyncio
async def test_apaginate_with_table_class_calls_select():
    """When query is a Table class (not a Select instance), .select() should be called."""

    class MyTable(MockTable):
        @classmethod
        def select(cls):
            return MockSelect(table="my_table")

    params = Params()
    mock_page = MagicMock()

    with patch(
        "fastapi_pagination.ext.piccolo.run_async_flow",
        new_callable=AsyncMock,
        return_value=mock_page,
    ):
        with set_page(Page):
            result = await apaginate(MyTable, params=params)

    assert result is mock_page


@pytest.mark.asyncio
async def test_apaginate_calls_run_async_flow():
    query = MockSelect()
    params = Params()
    mock_page = MagicMock()

    with patch(
        "fastapi_pagination.ext.piccolo.run_async_flow",
        new_callable=AsyncMock,
        return_value=mock_page,
    ) as mock_run:
        with set_page(Page):
            await apaginate(query, params=params)

    mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# paginate (deprecated wrapper)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paginate_calls_apaginate():
    query = MockSelect()
    params = Params()
    mock_page = MagicMock()

    with patch(
        "fastapi_pagination.ext.piccolo.apaginate",
        new_callable=AsyncMock,
        return_value=mock_page,
    ) as mock_apaginate:
        result = await paginate(query, params=params)

    assert result is mock_page
    mock_apaginate.assert_called_once_with(
        query,
        params=params,
        transformer=None,
        additional_data=None,
        config=None,
    )


@pytest.mark.asyncio
async def test_paginate_forwards_all_kwargs():
    query = MockSelect()
    params = Params()
    transformer = MagicMock()
    additional_data = {"key": "value"}
    mock_page = MagicMock()

    with patch(
        "fastapi_pagination.ext.piccolo.apaginate",
        new_callable=AsyncMock,
        return_value=mock_page,
    ) as mock_apaginate:
        result = await paginate(
            query,
            params=params,
            transformer=transformer,
            additional_data=additional_data,
        )

    assert result is mock_page
    mock_apaginate.assert_called_once_with(
        query,
        params=params,
        transformer=transformer,
        additional_data=additional_data,
        config=None,
    )
