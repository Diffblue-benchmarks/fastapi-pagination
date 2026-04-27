"""Tests for fastapi_pagination.ext.psycopg.

psycopg is not installed in this environment, so it is mocked
at the sys.modules level before importing the module under test.
"""
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Minimal fake SQL/Composed classes so isinstance checks work correctly
# ---------------------------------------------------------------------------


class _FakeSQL:
    def __init__(self, s=""):
        self._s = s

    def as_string(self, conn):
        return self._s


class _FakeComposed:
    def __init__(self, s=""):
        self._s = s

    def as_string(self, conn):
        return self._s


# ---------------------------------------------------------------------------
# Mock all unavailable psycopg dependencies before importing the module
# ---------------------------------------------------------------------------

_mock_rows = MagicMock()
_mock_rows.tuple_row = MagicMock(name="tuple_row")
_mock_rows.AsyncRowFactory = MagicMock()
_mock_rows.RowFactory = MagicMock()

_mock_sql = MagicMock()
_mock_sql.SQL = _FakeSQL
_mock_sql.Composed = _FakeComposed

_mock_psycopg = MagicMock()
_mock_psycopg.AsyncConnection = MagicMock()
_mock_psycopg.AsyncCursor = MagicMock()
_mock_psycopg.Connection = MagicMock()
_mock_psycopg.Cursor = MagicMock()
_mock_psycopg.rows = _mock_rows
_mock_psycopg.sql = _mock_sql

for _mod, _obj in [
    ("psycopg", _mock_psycopg),
    ("psycopg.rows", _mock_rows),
    ("psycopg.sql", _mock_sql),
]:
    sys.modules.setdefault(_mod, _obj)

# Now the module can be imported
from fastapi_pagination.ext.psycopg import (  # noqa: E402
    _compile_query,
    _resolve_query_args,
    _switch_factory,
    apaginate,
    paginate,
)

from fastapi_pagination.api import set_page  # noqa: E402
from fastapi_pagination.default import Page, Params  # noqa: E402


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_sync_conn(items, count):
    cursor = MagicMock()
    cursor.fetchall.return_value = items
    cursor.fetchone.return_value = (count,)

    conn = MagicMock()
    conn.execute.return_value = cursor
    conn.row_factory = MagicMock(name="original_factory")
    return conn


def _make_async_conn(items, count):
    cursor = AsyncMock()
    cursor.fetchall.return_value = items
    cursor.fetchone.return_value = (count,)

    conn = AsyncMock()
    conn.execute.return_value = cursor
    conn.row_factory = MagicMock(name="original_factory")
    return conn


# ---------------------------------------------------------------------------
# Tests for _switch_factory (lines 31-36)
# ---------------------------------------------------------------------------


def test_switch_factory_swaps_row_factory():
    conn = MagicMock()
    original = MagicMock(name="original")
    new_factory = MagicMock(name="new")
    conn.row_factory = original

    with _switch_factory(conn, new_factory):
        assert conn.row_factory is new_factory

    assert conn.row_factory is original


def test_switch_factory_restores_on_exception():
    conn = MagicMock()
    original = MagicMock(name="original")
    new_factory = MagicMock(name="new")
    conn.row_factory = original

    with pytest.raises(ValueError):
        with _switch_factory(conn, new_factory):
            raise ValueError("boom")

    assert conn.row_factory is original


# ---------------------------------------------------------------------------
# Tests for _compile_query (lines 39-43)
# ---------------------------------------------------------------------------


def test_compile_query_with_plain_string():
    conn = MagicMock()
    result = _compile_query("SELECT * FROM t", conn)
    assert result == "SELECT * FROM t"


def test_compile_query_with_sql_object():
    conn = MagicMock()
    sql = _FakeSQL("SELECT 1")
    result = _compile_query(sql, conn)
    assert result == "SELECT 1"


def test_compile_query_with_composed_object():
    conn = MagicMock()
    composed = _FakeComposed("SELECT id FROM users")
    result = _compile_query(composed, conn)
    assert result == "SELECT id FROM users"


# ---------------------------------------------------------------------------
# Tests for _resolve_query_args (lines 79-83)
# ---------------------------------------------------------------------------


def test_resolve_query_args_raises_when_both_provided():
    with pytest.raises(ValueError, match="Cannot use both"):
        _resolve_query_args((1, 2), {"key": "val"})


def test_resolve_query_args_returns_positional_args():
    result = _resolve_query_args((1, 2), None)
    assert result == (1, 2)


def test_resolve_query_args_returns_query_params():
    result = _resolve_query_args((), {"id": 42})
    assert result == {"id": 42}


def test_resolve_query_args_returns_none_when_empty():
    result = _resolve_query_args((), None)
    assert result is None


# ---------------------------------------------------------------------------
# Tests for paginate (lines 111-123)
# ---------------------------------------------------------------------------


def test_paginate_returns_page():
    conn = _make_sync_conn([{"id": 1}, {"id": 2}], 2)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = paginate(conn, "SELECT * FROM t", params=params)

    assert result.total == 2
    assert len(result.items) == 2


def test_paginate_empty_result():
    conn = _make_sync_conn([], 0)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = paginate(conn, "SELECT * FROM t", params=params)

    assert result.total == 0
    assert result.items == []


def test_paginate_with_positional_args():
    conn = _make_sync_conn([{"id": 5}], 1)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = paginate(conn, "SELECT * FROM t WHERE id = %s", 5, params=params)

    assert result.total == 1
    assert conn.execute.called


def test_paginate_raises_with_both_args_and_query_params():
    conn = _make_sync_conn([], 0)
    params = Params(page=1, size=10)

    with set_page(Page):
        with pytest.raises(ValueError, match="Cannot use both"):
            paginate(conn, "SELECT * FROM t WHERE id = %s", 5, query_params={"id": 5}, params=params)


def test_paginate_executes_count_query():
    conn = _make_sync_conn([], 42)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = paginate(conn, "SELECT * FROM t", params=params)

    assert result.total == 42
    assert conn.execute.call_count == 2
    first_query = conn.execute.call_args_list[0][0][0]
    assert "count" in first_query.lower()


def test_paginate_applies_limit_offset():
    conn = _make_sync_conn([{"id": 3}], 10)
    params = Params(page=2, size=5)

    with set_page(Page):
        result = paginate(conn, "SELECT * FROM t", params=params)

    assert result.page == 2
    assert result.size == 5
    paginate_query = conn.execute.call_args_list[1][0][0]
    assert "LIMIT 5" in paginate_query
    assert "OFFSET 5" in paginate_query


# ---------------------------------------------------------------------------
# Tests for apaginate (lines 86-98)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_returns_page():
    conn = _make_async_conn([{"id": 1}, {"id": 2}], 2)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate(conn, "SELECT * FROM t", params=params)

    assert result.total == 2
    assert len(result.items) == 2


@pytest.mark.asyncio
async def test_apaginate_empty_result():
    conn = _make_async_conn([], 0)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate(conn, "SELECT * FROM t", params=params)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_with_positional_args():
    conn = _make_async_conn([{"id": 7}], 1)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate(conn, "SELECT * FROM t WHERE id = %s", 7, params=params)

    assert result.total == 1
    assert conn.execute.called


@pytest.mark.asyncio
async def test_apaginate_raises_with_both_args_and_query_params():
    conn = _make_async_conn([], 0)
    params = Params(page=1, size=10)

    with set_page(Page):
        with pytest.raises(ValueError, match="Cannot use both"):
            await apaginate(conn, "SELECT * FROM t WHERE id = %s", 7, query_params={"id": 7}, params=params)


@pytest.mark.asyncio
async def test_apaginate_executes_count_query():
    conn = _make_async_conn([], 99)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate(conn, "SELECT * FROM big_table", params=params)

    assert result.total == 99
    assert conn.execute.call_count == 2
    first_query = conn.execute.call_args_list[0][0][0]
    assert "count" in first_query.lower()


@pytest.mark.asyncio
async def test_apaginate_applies_limit_offset():
    conn = _make_async_conn([{"id": 3}], 20)
    params = Params(page=3, size=5)

    with set_page(Page):
        result = await apaginate(conn, "SELECT * FROM t", params=params)

    assert result.page == 3
    assert result.size == 5
    paginate_query = conn.execute.call_args_list[1][0][0]
    assert "LIMIT 5" in paginate_query
    assert "OFFSET 10" in paginate_query
