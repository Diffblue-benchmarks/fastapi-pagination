import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


# Create proper Python classes for SQL/Composed so isinstance() works correctly
class _MockSQL:
    def __init__(self, query="SELECT 1"):
        self.query = query

    def as_string(self, conn):
        return self.query


class _MockComposed:
    def __init__(self, parts=None):
        self.parts = parts or []

    def as_string(self, conn):
        return "SELECT composed"


# Mock psycopg modules before importing the extension (only if not already installed)
_mock_psycopg = MagicMock()
_mock_psycopg_rows = MagicMock()
_mock_psycopg_rows.tuple_row = MagicMock()
_mock_psycopg_sql = MagicMock()
_mock_psycopg_sql.SQL = _MockSQL
_mock_psycopg_sql.Composed = _MockComposed

sys.modules.setdefault("psycopg", _mock_psycopg)
sys.modules.setdefault("psycopg.rows", _mock_psycopg_rows)
sys.modules.setdefault("psycopg.sql", _mock_psycopg_sql)

from fastapi_pagination.bases import RawParams  # noqa: E402
from fastapi_pagination.ext.psycopg import (  # noqa: E402
    _compile_query,
    _psycopg_limit_offset_flow,
    _psycopg_total_flow,
    _resolve_query_args,
    _switch_factory,
    apaginate,
    paginate,
)
from fastapi_pagination.flow import run_sync_flow  # noqa: E402

# After module import, get the actual SQL/Composed bound in the ext module
# (may be real psycopg classes if installed, or our mock classes if not)
from psycopg.sql import SQL, Composed  # noqa: E402


# ---- _switch_factory tests ----


def test_switch_factory_temporarily_changes_row_factory():
    conn = MagicMock()
    conn.row_factory = "original"
    new_factory = "new_factory"

    with _switch_factory(conn, new_factory):
        assert conn.row_factory == new_factory

    assert conn.row_factory == "original"


def test_switch_factory_restores_original_on_exception():
    conn = MagicMock()
    conn.row_factory = "original"

    with pytest.raises(RuntimeError):
        with _switch_factory(conn, "new_factory"):
            raise RuntimeError("test error")

    assert conn.row_factory == "original"


def test_switch_factory_yields_none():
    conn = MagicMock()
    conn.row_factory = "original"

    with _switch_factory(conn, "new") as result:
        assert result is None


# ---- _compile_query tests ----


def test_compile_query_with_plain_string():
    conn = MagicMock()
    result = _compile_query("SELECT 1", conn)
    assert result == "SELECT 1"


def test_compile_query_with_sql_object():
    conn = MagicMock()
    sql_obj = SQL("SELECT * FROM test")
    sql_obj.as_string = MagicMock(return_value="SELECT * FROM test")

    result = _compile_query(sql_obj, conn)

    assert result == "SELECT * FROM test"
    sql_obj.as_string.assert_called_once_with(conn)


def test_compile_query_with_composed_object():
    conn = MagicMock()
    composed_obj = Composed()
    composed_obj.as_string = MagicMock(return_value="SELECT composed query")

    result = _compile_query(composed_obj, conn)

    assert result == "SELECT composed query"
    composed_obj.as_string.assert_called_once_with(conn)


def test_compile_query_returns_string_unchanged():
    conn = MagicMock()
    query = "SELECT id FROM users WHERE id = %s"

    result = _compile_query(query, conn)

    assert result == query


# ---- _resolve_query_args tests ----


def test_resolve_query_args_with_positional_args_only():
    args = (1, 2, 3)
    result = _resolve_query_args(args, None)
    assert result == args


def test_resolve_query_args_with_query_params_only():
    params = {"key": "value", "other": 42}
    result = _resolve_query_args((), params)
    assert result == params


def test_resolve_query_args_raises_when_both_provided():
    with pytest.raises(ValueError, match="Cannot use both positional query arguments and 'query_params' keyword argument"):
        _resolve_query_args((1,), {"key": "value"})


def test_resolve_query_args_returns_none_when_neither_provided():
    result = _resolve_query_args((), None)
    assert result is None


def test_resolve_query_args_empty_args_with_params():
    params = [1, 2, 3]
    result = _resolve_query_args((), params)
    assert result == params


# ---- _psycopg_limit_offset_flow tests ----


def test_psycopg_limit_offset_flow_returns_items():
    conn = MagicMock()
    cursor = MagicMock()
    items = [{"id": 1}, {"id": 2}]
    conn.execute.return_value = cursor
    cursor.fetchall.return_value = items

    raw_params = RawParams(limit=10, offset=0)
    result = run_sync_flow(_psycopg_limit_offset_flow(conn, "SELECT * FROM test", None, raw_params))

    assert result == items
    conn.execute.assert_called_once()


def test_psycopg_limit_offset_flow_with_empty_result():
    conn = MagicMock()
    cursor = MagicMock()
    conn.execute.return_value = cursor
    cursor.fetchall.return_value = []

    raw_params = RawParams(limit=5, offset=10)
    result = run_sync_flow(_psycopg_limit_offset_flow(conn, "SELECT * FROM test", None, raw_params))

    assert result == []


def test_psycopg_limit_offset_flow_passes_args_to_execute():
    conn = MagicMock()
    cursor = MagicMock()
    conn.execute.return_value = cursor
    cursor.fetchall.return_value = []

    raw_params = RawParams(limit=5, offset=0)
    args = (42,)
    run_sync_flow(_psycopg_limit_offset_flow(conn, "SELECT * FROM test WHERE id = %s", args, raw_params))

    call_args = conn.execute.call_args
    assert call_args.args[1] == args


# ---- _psycopg_total_flow tests ----


def test_psycopg_total_flow_returns_count():
    conn = MagicMock()
    conn.row_factory = MagicMock()
    cursor = MagicMock()
    row = (42,)
    conn.execute.return_value = cursor
    cursor.fetchone.return_value = row

    result = run_sync_flow(_psycopg_total_flow(conn, "SELECT * FROM test", None))

    assert result == 42


def test_psycopg_total_flow_returns_zero_count():
    conn = MagicMock()
    conn.row_factory = MagicMock()
    cursor = MagicMock()
    conn.execute.return_value = cursor
    cursor.fetchone.return_value = (0,)

    result = run_sync_flow(_psycopg_total_flow(conn, "SELECT * FROM test", None))

    assert result == 0


def test_psycopg_total_flow_switches_row_factory():
    conn = MagicMock()
    original_factory = MagicMock()
    conn.row_factory = original_factory
    cursor = MagicMock()
    conn.execute.return_value = cursor
    cursor.fetchone.return_value = (5,)

    run_sync_flow(_psycopg_total_flow(conn, "SELECT 1", None))

    # row_factory should be restored to original after the flow
    assert conn.row_factory == original_factory


def test_psycopg_total_flow_passes_args_to_execute():
    conn = MagicMock()
    conn.row_factory = MagicMock()
    cursor = MagicMock()
    conn.execute.return_value = cursor
    cursor.fetchone.return_value = (3,)

    args = (10,)
    run_sync_flow(_psycopg_total_flow(conn, "SELECT * FROM test WHERE id > %s", args))

    call_args = conn.execute.call_args
    assert call_args.args[1] == args


# ---- paginate tests ----


def test_paginate_raises_when_args_and_query_params():
    conn = MagicMock()

    with pytest.raises(ValueError, match="Cannot use both positional query arguments and 'query_params' keyword argument"):
        paginate(conn, "SELECT 1", 1, query_params={"key": "val"})


def test_paginate_calls_run_sync_flow(mocker):
    mock_run_sync_flow = mocker.patch(
        "fastapi_pagination.ext.psycopg.run_sync_flow",
        return_value="paginated_result",
    )
    mocker.patch("fastapi_pagination.ext.psycopg.generic_flow", return_value=MagicMock())

    conn = MagicMock()
    result = paginate(conn, "SELECT 1")

    assert result == "paginated_result"
    mock_run_sync_flow.assert_called_once()


def test_paginate_with_query_params(mocker):
    mock_run_sync_flow = mocker.patch(
        "fastapi_pagination.ext.psycopg.run_sync_flow",
        return_value="result",
    )
    mocker.patch("fastapi_pagination.ext.psycopg.generic_flow", return_value=MagicMock())

    conn = MagicMock()
    result = paginate(conn, "SELECT 1 WHERE id = %(id)s", query_params={"id": 1})

    assert result == "result"
    mock_run_sync_flow.assert_called_once()


# ---- apaginate tests ----


@pytest.mark.asyncio
async def test_apaginate_raises_when_args_and_query_params():
    conn = MagicMock()

    with pytest.raises(ValueError, match="Cannot use both positional query arguments and 'query_params' keyword argument"):
        await apaginate(conn, "SELECT 1", 1, query_params={"key": "val"})


@pytest.mark.asyncio
async def test_apaginate_calls_run_async_flow(mocker):
    mock_run_async_flow = mocker.patch(
        "fastapi_pagination.ext.psycopg.run_async_flow",
        new_callable=AsyncMock,
        return_value="async_result",
    )
    mocker.patch("fastapi_pagination.ext.psycopg.generic_flow", return_value=MagicMock())

    conn = MagicMock()
    result = await apaginate(conn, "SELECT 1")

    assert result == "async_result"
    mock_run_async_flow.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_with_query_params(mocker):
    mock_run_async_flow = mocker.patch(
        "fastapi_pagination.ext.psycopg.run_async_flow",
        new_callable=AsyncMock,
        return_value="async_result",
    )
    mocker.patch("fastapi_pagination.ext.psycopg.generic_flow", return_value=MagicMock())

    conn = MagicMock()
    result = await apaginate(conn, "SELECT 1", query_params={"id": 5})

    assert result == "async_result"
    mock_run_async_flow.assert_called_once()
