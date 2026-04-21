"""Tests for fastapi_pagination.ext.psycopg"""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Mock psycopg if not installed (mirrors test_ext_mongoengine.py pattern)
# ---------------------------------------------------------------------------

class _MockSQL:
    def __init__(self, template=""):
        self.template = template

    def as_string(self, conn):
        return self.template


class _MockComposed:
    def __init__(self, items=None):
        self.items = items or []

    def as_string(self, conn):
        return "composed_query"


if "psycopg" not in sys.modules:
    _psycopg_rows_mock = MagicMock()
    _psycopg_rows_mock.tuple_row = lambda cursor: tuple

    _psycopg_sql_mock = MagicMock()
    _psycopg_sql_mock.SQL = _MockSQL
    _psycopg_sql_mock.Composed = _MockComposed

    def _subscriptable_type(name):
        return type(name, (), {"__class_getitem__": classmethod(lambda cls, item: cls)})

    _psycopg_mock = MagicMock()
    _psycopg_mock.AsyncConnection = _subscriptable_type("AsyncConnection")
    _psycopg_mock.AsyncCursor = _subscriptable_type("AsyncCursor")
    _psycopg_mock.Connection = _subscriptable_type("Connection")
    _psycopg_mock.Cursor = _subscriptable_type("Cursor")

    sys.modules["psycopg"] = _psycopg_mock
    sys.modules["psycopg.rows"] = _psycopg_rows_mock
    sys.modules["psycopg.sql"] = _psycopg_sql_mock


from fastapi_pagination.bases import RawParams  # noqa: E402
from fastapi_pagination.flow import run_sync_flow  # noqa: E402
from fastapi_pagination.ext.psycopg import (  # noqa: E402
    _switch_factory,
    _compile_query,
    _psycopg_limit_offset_flow,
    _psycopg_total_flow,
    _resolve_query_args,
    apaginate,
    paginate,
)
from psycopg.sql import SQL as _SQL, Composed as _Composed  # noqa: E402


# ---------------------------------------------------------------------------
# _switch_factory
# ---------------------------------------------------------------------------

def test_switch_factory_swaps_and_restores():
    conn = MagicMock()
    original_factory = MagicMock()
    new_factory = MagicMock()
    conn.row_factory = original_factory

    with _switch_factory(conn, new_factory):
        assert conn.row_factory is new_factory

    assert conn.row_factory is original_factory


def test_switch_factory_restores_on_exception():
    conn = MagicMock()
    original_factory = MagicMock()
    new_factory = MagicMock()
    conn.row_factory = original_factory

    with pytest.raises(RuntimeError):
        with _switch_factory(conn, new_factory):
            raise RuntimeError("error inside context")

    assert conn.row_factory is original_factory


# ---------------------------------------------------------------------------
# _compile_query
# ---------------------------------------------------------------------------

def test_compile_query_with_plain_string():
    conn = MagicMock()
    result = _compile_query("SELECT * FROM foo", conn)
    assert result == "SELECT * FROM foo"


def test_compile_query_with_sql_object():
    conn = MagicMock()
    sql_obj = _SQL("SELECT bar")
    result = _compile_query(sql_obj, conn)
    assert isinstance(result, str)
    assert result == "SELECT bar"


def test_compile_query_with_composed_object():
    conn = MagicMock()
    composed_obj = _Composed()
    result = _compile_query(composed_obj, conn)
    assert isinstance(result, str)
    assert result == "composed_query"


# ---------------------------------------------------------------------------
# _resolve_query_args
# ---------------------------------------------------------------------------

def test_resolve_query_args_raises_when_both_provided():
    with pytest.raises(ValueError, match="Cannot use both"):
        _resolve_query_args(("arg1",), {"key": "value"})


def test_resolve_query_args_returns_args_when_only_args():
    result = _resolve_query_args(("arg1", "arg2"), None)
    assert result == ("arg1", "arg2")


def test_resolve_query_args_returns_query_params_when_no_args():
    result = _resolve_query_args((), {"key": "value"})
    assert result == {"key": "value"}


def test_resolve_query_args_returns_none_when_neither():
    result = _resolve_query_args((), None)
    assert result is None


# ---------------------------------------------------------------------------
# _psycopg_limit_offset_flow
# ---------------------------------------------------------------------------

def test_psycopg_limit_offset_flow():
    conn = MagicMock()
    mock_cursor = MagicMock()
    mock_items = [10, 20, 30]
    conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = mock_items

    raw_params = RawParams(limit=10, offset=0)
    gen = _psycopg_limit_offset_flow(conn, "SELECT 1", None, raw_params)
    result = run_sync_flow(gen)

    assert result == [10, 20, 30]
    conn.execute.assert_called_once()


def test_psycopg_limit_offset_flow_with_args():
    conn = MagicMock()
    mock_cursor = MagicMock()
    conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [1, 2]

    raw_params = RawParams(limit=5, offset=10)
    gen = _psycopg_limit_offset_flow(conn, "SELECT %s", ("val",), raw_params)
    result = run_sync_flow(gen)

    assert result == [1, 2]


# ---------------------------------------------------------------------------
# _psycopg_total_flow
# ---------------------------------------------------------------------------

def test_psycopg_total_flow_with_row():
    conn = MagicMock()
    conn.row_factory = MagicMock()
    mock_cursor = MagicMock()
    conn.execute.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (42,)

    gen = _psycopg_total_flow(conn, "SELECT 1", None)
    result = run_sync_flow(gen)

    assert result == 42
    conn.execute.assert_called_once()


def test_psycopg_total_flow_with_no_row():
    conn = MagicMock()
    conn.row_factory = MagicMock()
    mock_cursor = MagicMock()
    conn.execute.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None

    gen = _psycopg_total_flow(conn, "SELECT 1", None)
    result = run_sync_flow(gen)

    assert result is None


def test_psycopg_total_flow_switches_factory():
    conn = MagicMock()
    original_factory = MagicMock()
    conn.row_factory = original_factory
    mock_cursor = MagicMock()
    conn.execute.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (7,)

    gen = _psycopg_total_flow(conn, "SELECT count(*)", None)
    run_sync_flow(gen)

    assert conn.row_factory is original_factory


# ---------------------------------------------------------------------------
# paginate
# ---------------------------------------------------------------------------

def test_paginate_calls_run_sync_flow(mocker):
    mock_result = MagicMock()
    mock_run_sync = mocker.patch(
        "fastapi_pagination.ext.psycopg.run_sync_flow",
        return_value=mock_result,
    )
    conn = MagicMock()

    result = paginate(conn, "SELECT 1", query_params=None)

    assert mock_run_sync.called
    assert result is mock_result


def test_paginate_resolves_query_args(mocker):
    mocker.patch(
        "fastapi_pagination.ext.psycopg.run_sync_flow",
        return_value=MagicMock(),
    )
    conn = MagicMock()

    with pytest.raises(ValueError, match="Cannot use both"):
        paginate(conn, "SELECT 1", "arg1", query_params={"key": "val"})


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apaginate_calls_run_async_flow(mocker):
    mock_result = MagicMock()
    mock_run_async = mocker.patch(
        "fastapi_pagination.ext.psycopg.run_async_flow",
        new_callable=AsyncMock,
        return_value=mock_result,
    )
    conn = AsyncMock()

    result = await apaginate(conn, "SELECT 1", query_params=None)

    assert mock_run_async.called
    assert result is mock_result


@pytest.mark.asyncio
async def test_apaginate_resolves_query_args(mocker):
    mocker.patch(
        "fastapi_pagination.ext.psycopg.run_async_flow",
        new_callable=AsyncMock,
        return_value=MagicMock(),
    )
    conn = AsyncMock()

    with pytest.raises(ValueError, match="Cannot use both"):
        await apaginate(conn, "SELECT 1", "arg1", query_params={"key": "val"})
