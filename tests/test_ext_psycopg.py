import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock

from psycopg.sql import SQL, Composed
from psycopg.rows import tuple_row

from fastapi_pagination import Params, Page
from fastapi_pagination.ext.psycopg import (
    _switch_factory,
    _compile_query,
    _resolve_query_args,
    paginate,
    apaginate,
)


# ---------------------------------------------------------------------------
# _switch_factory
# ---------------------------------------------------------------------------

def test_switch_factory_swaps_row_factory():
    mock_conn = MagicMock()
    original = MagicMock(name="original_factory")
    new = MagicMock(name="new_factory")
    mock_conn.row_factory = original

    with _switch_factory(mock_conn, new):
        assert mock_conn.row_factory == new

    assert mock_conn.row_factory == original


def test_switch_factory_restores_on_exception():
    mock_conn = MagicMock()
    original = MagicMock(name="original_factory")
    new = MagicMock(name="new_factory")
    mock_conn.row_factory = original

    with pytest.raises(RuntimeError):
        with _switch_factory(mock_conn, new):
            raise RuntimeError("boom")

    assert mock_conn.row_factory == original


# ---------------------------------------------------------------------------
# _compile_query
# ---------------------------------------------------------------------------

def test_compile_query_passthrough_for_plain_string():
    mock_conn = MagicMock()
    result = _compile_query("SELECT 1", mock_conn)
    assert result == "SELECT 1"


def test_compile_query_sql_object():
    mock_conn = MagicMock()
    sql_query = SQL("SELECT 1")
    result = _compile_query(sql_query, mock_conn)
    assert result == "SELECT 1"


def test_compile_query_composed_object():
    mock_conn = MagicMock()
    mock_conn.connection.pgconn._encoding = "utf-8"
    composed: Composed = SQL("SELECT {}").format("1")
    result = _compile_query(composed, mock_conn)
    assert isinstance(result, str)
    assert "SELECT" in result


# ---------------------------------------------------------------------------
# _resolve_query_args
# ---------------------------------------------------------------------------

def test_resolve_query_args_positional_only():
    result = _resolve_query_args((1, 2), None)
    assert result == (1, 2)


def test_resolve_query_args_query_params_only():
    params = {"id": 42}
    result = _resolve_query_args((), params)
    assert result == params


def test_resolve_query_args_neither():
    result = _resolve_query_args((), None)
    assert result is None


def test_resolve_query_args_both_raises():
    with pytest.raises(ValueError, match="Cannot use both"):
        _resolve_query_args((1,), {"id": 1})


# ---------------------------------------------------------------------------
# paginate (sync)
# ---------------------------------------------------------------------------

def _make_sync_conn(rows, count_row=(5,)):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_count_cursor = MagicMock()
    mock_conn.row_factory = None

    call_count = {"n": 0}

    def execute_side_effect(query, args=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return mock_count_cursor
        return mock_cursor

    mock_conn.execute.side_effect = execute_side_effect
    mock_cursor.fetchall.return_value = rows
    mock_count_cursor.fetchone.return_value = count_row
    return mock_conn


def test_paginate_returns_page():
    mock_conn = _make_sync_conn(rows=[(1,), (2,)])
    params = Params(page=1, size=2)
    result = paginate(mock_conn, "SELECT id FROM items", params=params)
    assert result.total == 5
    assert result.items == [(1,), (2,)]


def test_paginate_with_positional_args():
    mock_conn = _make_sync_conn(rows=[(10,)])
    params = Params(page=1, size=5)
    result = paginate(mock_conn, "SELECT id FROM items WHERE id = %s", 10, params=params)
    assert result.items == [(10,)]


def test_paginate_with_query_params():
    mock_conn = _make_sync_conn(rows=[(10,)])
    params = Params(page=1, size=5)
    result = paginate(
        mock_conn,
        "SELECT id FROM items WHERE id = %(id)s",
        query_params={"id": 10},
        params=params,
    )
    assert result.items == [(10,)]


def test_paginate_raises_with_both_args_and_query_params():
    mock_conn = MagicMock()
    mock_conn.row_factory = None
    params = Params(page=1, size=5)
    with pytest.raises(ValueError, match="Cannot use both"):
        paginate(
            mock_conn,
            "SELECT 1",
            1,
            query_params={"x": 1},
            params=params,
        )


# ---------------------------------------------------------------------------
# apaginate (async)
# ---------------------------------------------------------------------------

def _make_async_conn(rows, count_row=(5,)):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_count_cursor = MagicMock()
    mock_conn.row_factory = None

    call_count = {"n": 0}

    async def execute_side_effect(query, args=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return mock_count_cursor
        return mock_cursor

    mock_conn.execute = execute_side_effect
    mock_cursor.fetchall = AsyncMock(return_value=rows)
    mock_count_cursor.fetchone = AsyncMock(return_value=count_row)
    return mock_conn


@pytest.mark.asyncio
async def test_apaginate_returns_page():
    mock_conn = _make_async_conn(rows=[(1,), (2,)])
    params = Params(page=1, size=2)
    result = await apaginate(mock_conn, "SELECT id FROM items", params=params)
    assert result.total == 5
    assert result.items == [(1,), (2,)]


@pytest.mark.asyncio
async def test_apaginate_with_positional_args():
    mock_conn = _make_async_conn(rows=[(10,)])
    params = Params(page=1, size=5)
    result = await apaginate(mock_conn, "SELECT id FROM items WHERE id = %s", 10, params=params)
    assert result.items == [(10,)]


@pytest.mark.asyncio
async def test_apaginate_with_query_params():
    mock_conn = _make_async_conn(rows=[(10,)])
    params = Params(page=1, size=5)
    result = await apaginate(
        mock_conn,
        "SELECT id FROM items WHERE id = %(id)s",
        query_params={"id": 10},
        params=params,
    )
    assert result.items == [(10,)]


@pytest.mark.asyncio
async def test_apaginate_raises_with_both_args_and_query_params():
    mock_conn = MagicMock()
    mock_conn.row_factory = None
    params = Params(page=1, size=5)
    with pytest.raises(ValueError, match="Cannot use both"):
        await apaginate(
            mock_conn,
            "SELECT 1",
            1,
            query_params={"x": 1},
            params=params,
        )
