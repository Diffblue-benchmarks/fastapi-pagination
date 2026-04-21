from __future__ import annotations

import warnings
from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from piccolo.columns import Integer, Varchar
from piccolo.engine.sqlite import SQLiteEngine
from piccolo.table import Table

from fastapi_pagination import Params
from fastapi_pagination.ext.piccolo import _copy_query, _total_flow, apaginate, paginate

# ---------------------------------------------------------------------------
# Test table definition using in-memory SQLite
# ---------------------------------------------------------------------------

DB = SQLiteEngine()


class Artist(Table, db=DB):
    name = Varchar()
    popularity = Integer()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await Artist.create_table(if_not_exists=True)
    await Artist.delete(force=True)
    yield
    await Artist.delete(force=True)


# ---------------------------------------------------------------------------
# Tests for _copy_query
# ---------------------------------------------------------------------------


def test_copy_query_returns_same_type():
    query = Artist.select()
    copied = _copy_query(query)
    assert type(copied) is type(query)


def test_copy_query_returns_different_object():
    query = Artist.select()
    copied = _copy_query(query)
    assert copied is not query


def test_copy_query_has_same_table():
    query = Artist.select()
    copied = _copy_query(query)
    assert copied.table is Artist


def test_copy_query_slots_are_deep_copied():
    query = Artist.select()
    copied = _copy_query(query)
    # delegates should be different objects (deep copied)
    assert copied.columns_delegate is not query.columns_delegate
    assert copied.order_by_delegate is not query.order_by_delegate
    assert copied.where_delegate is not query.where_delegate


# ---------------------------------------------------------------------------
# Tests for _total_flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_total_flow_with_rows():
    await Artist.insert(Artist(name="Radiohead", popularity=100))
    await Artist.insert(Artist(name="Portishead", popularity=80))
    query = Artist.select()
    from fastapi_pagination.flow import run_async_flow

    total = await run_async_flow(_total_flow(query))
    assert total == 2


@pytest.mark.asyncio
async def test_total_flow_empty_table():
    query = Artist.select()
    from fastapi_pagination.flow import run_async_flow

    total = await run_async_flow(_total_flow(query))
    assert total == 0


@pytest.mark.asyncio
async def test_total_flow_returns_none_when_row_is_falsy():
    """Test the None return path when the count query returns no row."""
    import asyncio

    query = Artist.select()
    from fastapi_pagination.flow import run_async_flow

    async def _none_coro():
        return None

    mock_columns_query = MagicMock()
    mock_columns_query.first = MagicMock(return_value=_none_coro())

    count_query_mock = MagicMock()
    count_query_mock.columns = MagicMock(return_value=mock_columns_query)
    count_query_mock.columns_delegate = MagicMock()
    count_query_mock.columns_delegate.selected_columns = []
    count_query_mock.order_by_delegate = MagicMock()
    count_query_mock.order_by_delegate._order_by = MagicMock()
    count_query_mock.order_by_delegate._order_by.order_by_items = []

    with patch("fastapi_pagination.ext.piccolo._copy_query", return_value=count_query_mock):
        total = await run_async_flow(_total_flow(query))
    assert total is None


# ---------------------------------------------------------------------------
# Tests for apaginate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_with_select_query():
    await Artist.insert(Artist(name="Radiohead", popularity=100))
    await Artist.insert(Artist(name="Portishead", popularity=80))
    result = await apaginate(Artist.select(), params=Params(page=1, size=10))
    assert result.total == 2
    assert len(result.items) == 2


@pytest.mark.asyncio
async def test_apaginate_with_table_class():
    """Test that passing a Table class (not Select) calls query.select() internally."""
    await Artist.insert(Artist(name="Blur", popularity=90))
    result = await apaginate(Artist, params=Params(page=1, size=10))
    assert result.total == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_apaginate_pagination():
    for i in range(5):
        await Artist.insert(Artist(name=f"Band{i}", popularity=i * 10))
    result = await apaginate(Artist.select(), params=Params(page=1, size=3))
    assert result.total == 5
    assert len(result.items) == 3
    result2 = await apaginate(Artist.select(), params=Params(page=2, size=3))
    assert len(result2.items) == 2


@pytest.mark.asyncio
async def test_apaginate_empty_table():
    result = await apaginate(Artist.select(), params=Params(page=1, size=10))
    assert result.total == 0
    assert result.items == []


# ---------------------------------------------------------------------------
# Tests for paginate (deprecated)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate():
    await Artist.insert(Artist(name="Muse", popularity=95))
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = await paginate(Artist.select(), params=Params(page=1, size=10))
    assert result.total == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_paginate_with_table_class():
    await Artist.insert(Artist(name="Oasis", popularity=85))
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = await paginate(Artist, params=Params(page=1, size=10))
    assert result.total == 1
    assert len(result.items) == 1
