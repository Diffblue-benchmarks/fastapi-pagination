from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Mock psycopg before importing the module under test
# ---------------------------------------------------------------------------

class _MockGenericClass:
    """A class that supports subscripting (e.g. Connection[Any])."""

    def __class_getitem__(cls, item: object) -> object:
        return cls


class _MockConnection(_MockGenericClass):
    pass


class _MockCursor(_MockGenericClass):
    pass


class _MockAsyncConnection(_MockGenericClass):
    pass


class _MockAsyncCursor(_MockGenericClass):
    pass


class _MockRowFactory(_MockGenericClass):
    pass


class _MockAsyncRowFactory(_MockGenericClass):
    pass


class _MockSQL:
    """Minimal stand-in for psycopg.sql.SQL."""

    def __init__(self, template: str) -> None:
        self._template = template

    def as_string(self, conn: object) -> str:  # noqa: ARG002
        return self._template

    def format(self, *args: object) -> "_MockComposed":
        return _MockComposed(f"COMPOSED({self._template})")


class _MockComposed:
    """Minimal stand-in for psycopg.sql.Composed."""

    def __init__(self, value: str = "COMPOSED") -> None:
        self._value = value

    def as_string(self, conn: object) -> str:  # noqa: ARG002
        return self._value


_mock_tuple_row = object()  # sentinel used as tuple_row

_mock_psycopg_rows = MagicMock()
_mock_psycopg_rows.tuple_row = _mock_tuple_row
_mock_psycopg_rows.RowFactory = _MockRowFactory
_mock_psycopg_rows.AsyncRowFactory = _MockAsyncRowFactory

_mock_psycopg_sql = MagicMock()
_mock_psycopg_sql.SQL = _MockSQL
_mock_psycopg_sql.Composed = _MockComposed

_mock_psycopg = MagicMock()
_mock_psycopg.AsyncConnection = _MockAsyncConnection
_mock_psycopg.AsyncCursor = _MockAsyncCursor
_mock_psycopg.Connection = _MockConnection
_mock_psycopg.Cursor = _MockCursor

sys.modules.setdefault("psycopg", _mock_psycopg)
sys.modules.setdefault("psycopg.rows", _mock_psycopg_rows)
sys.modules.setdefault("psycopg.sql", _mock_psycopg_sql)

# Now we can safely import the module under test.
from fastapi_pagination.ext.psycopg import (  # noqa: E402
    _compile_query,
    _psycopg_limit_offset_flow,
    _psycopg_total_flow,
    _resolve_query_args,
    _switch_factory,
    apaginate,
    paginate,
)
from fastapi_pagination.default import Page, Params  # noqa: E402
from fastapi_pagination.flow import run_async_flow, run_sync_flow  # noqa: E402


# ---------------------------------------------------------------------------
# _switch_factory
# ---------------------------------------------------------------------------


def test_switch_factory_switches_and_restores():
    original = object()
    new_factory = object()

    conn = MagicMock()
    conn.row_factory = original

    with _switch_factory(conn, new_factory):
        assert conn.row_factory is new_factory

    assert conn.row_factory is original


def test_switch_factory_restores_on_exception():
    original = object()

    conn = MagicMock()
    conn.row_factory = original

    with pytest.raises(RuntimeError):
        with _switch_factory(conn, object()):
            raise RuntimeError("boom")

    assert conn.row_factory is original


# ---------------------------------------------------------------------------
# _compile_query
# ---------------------------------------------------------------------------


def test_compile_query_with_plain_string():
    conn = MagicMock()
    result = _compile_query("SELECT 1", conn)
    assert result == "SELECT 1"


def test_compile_query_with_sql_object():
    conn = MagicMock()
    sql_obj = _MockSQL("SELECT * FROM t")
    result = _compile_query(sql_obj, conn)  # type: ignore[arg-type]
    assert result == "SELECT * FROM t"


def test_compile_query_with_composed_object():
    conn = MagicMock()
    composed = _MockComposed("SELECT a FROM b")
    result = _compile_query(composed, conn)  # type: ignore[arg-type]
    assert result == "SELECT a FROM b"


# ---------------------------------------------------------------------------
# _resolve_query_args
# ---------------------------------------------------------------------------


def test_resolve_query_args_returns_positional_args():
    result = _resolve_query_args((1, 2, 3), None)
    assert result == (1, 2, 3)


def test_resolve_query_args_returns_query_params():
    qp = {"key": "value"}
    result = _resolve_query_args((), qp)
    assert result is qp


def test_resolve_query_args_returns_none_when_neither():
    result = _resolve_query_args((), None)
    assert result is None


def test_resolve_query_args_raises_when_both_provided():
    with pytest.raises(ValueError, match="Cannot use both"):
        _resolve_query_args((1,), {"key": "value"})


# ---------------------------------------------------------------------------
# _psycopg_limit_offset_flow (sync)
# ---------------------------------------------------------------------------


def _build_sync_conn(items: list, *, row_factory: object = None) -> MagicMock:
    """Return a MagicMock connection suitable for sync flow tests."""
    cursor = MagicMock()
    cursor.fetchall.return_value = items

    conn = MagicMock()
    conn.row_factory = row_factory
    conn.execute.return_value = cursor
    return conn


def test_psycopg_limit_offset_flow_returns_items():
    from fastapi_pagination.bases import RawParams

    raw_params = RawParams(limit=5, offset=0, include_total=False)
    items = [{"id": i} for i in range(3)]
    conn = _build_sync_conn(items)

    result = run_sync_flow(_psycopg_limit_offset_flow(conn, "SELECT * FROM t", None, raw_params))

    assert result == items


# ---------------------------------------------------------------------------
# _psycopg_total_flow (sync)
# ---------------------------------------------------------------------------


def test_psycopg_total_flow_returns_count():
    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = (42,)

    conn = MagicMock()
    conn.row_factory = _mock_tuple_row
    conn.execute.return_value = count_cursor

    result = run_sync_flow(_psycopg_total_flow(conn, "SELECT * FROM t", None))

    assert result == 42


# ---------------------------------------------------------------------------
# paginate (sync)
# ---------------------------------------------------------------------------


def test_paginate_returns_page():
    params = Params(page=1, size=10)
    items = [{"id": i} for i in range(3)]

    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = (3,)

    data_cursor = MagicMock()
    data_cursor.fetchall.return_value = items

    conn = MagicMock()
    conn.row_factory = _mock_tuple_row
    conn.execute.side_effect = [count_cursor, data_cursor]

    result = paginate(conn, "SELECT * FROM t", params=params)

    assert result.total == 3
    assert list(result.items) == items


def test_paginate_with_query_params():
    params = Params(page=1, size=5)
    items = [{"id": 1}]

    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = (1,)

    data_cursor = MagicMock()
    data_cursor.fetchall.return_value = items

    conn = MagicMock()
    conn.row_factory = _mock_tuple_row
    conn.execute.side_effect = [count_cursor, data_cursor]

    result = paginate(conn, "SELECT * FROM t WHERE id = %(id)s", query_params={"id": 1}, params=params)

    assert result.total == 1


def test_paginate_raises_on_args_and_query_params():
    conn = MagicMock()
    params = Params(page=1, size=10)

    with pytest.raises(ValueError, match="Cannot use both"):
        paginate(conn, "SELECT * FROM t WHERE id = %s", 1, query_params={"id": 1}, params=params)


# ---------------------------------------------------------------------------
# apaginate (async)
# ---------------------------------------------------------------------------


def _build_async_conn(count: int, items: list) -> AsyncMock:
    """Return an AsyncMock connection suitable for async flow tests."""
    count_cursor = AsyncMock()
    count_cursor.fetchone = AsyncMock(return_value=(count,))

    data_cursor = AsyncMock()
    data_cursor.fetchall = AsyncMock(return_value=items)

    conn = AsyncMock()
    conn.row_factory = _mock_tuple_row
    conn.execute = AsyncMock(side_effect=[count_cursor, data_cursor])
    return conn


@pytest.mark.asyncio
async def test_apaginate_returns_page():
    params = Params(page=1, size=10)
    items = [{"id": i} for i in range(4)]
    conn = _build_async_conn(4, items)

    result = await apaginate(conn, "SELECT * FROM t", params=params)

    assert result.total == 4
    assert list(result.items) == items


@pytest.mark.asyncio
async def test_apaginate_with_query_params():
    params = Params(page=1, size=5)
    items = [{"id": 7}]
    conn = _build_async_conn(1, items)

    result = await apaginate(conn, "SELECT * FROM t WHERE id = %(id)s", query_params={"id": 7}, params=params)

    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_raises_on_args_and_query_params():
    conn = AsyncMock()
    params = Params(page=1, size=10)

    with pytest.raises(ValueError, match="Cannot use both"):
        await apaginate(conn, "SELECT * FROM t WHERE id = %s", 1, query_params={"id": 1}, params=params)
