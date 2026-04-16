"""Unit tests for fastapi_pagination.ext.psycopg module."""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# psycopg is not installed; mock the module before import
_psycopg_mock = MagicMock()
_psycopg_rows_mock = MagicMock()
_psycopg_sql_mock = MagicMock()

sys.modules.setdefault("psycopg", _psycopg_mock)
sys.modules.setdefault("psycopg.rows", _psycopg_rows_mock)
sys.modules.setdefault("psycopg.sql", _psycopg_sql_mock)

# Set up SQL and Composed as distinguishable mock classes
_SQL_class = type("SQL", (), {})
_Composed_class = type("Composed", (), {})
_psycopg_sql_mock.SQL = _SQL_class
_psycopg_sql_mock.Composed = _Composed_class

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


# ---------------------------------------------------------------------------
# _switch_factory
# ---------------------------------------------------------------------------


def test_switch_factory_swaps_and_restores():
    conn = MagicMock()
    conn.row_factory = "original_factory"
    new_factory = "new_factory"

    with _switch_factory(conn, new_factory):
        assert conn.row_factory == new_factory

    assert conn.row_factory == "original_factory"


def test_switch_factory_restores_on_exception():
    conn = MagicMock()
    conn.row_factory = "original_factory"
    new_factory = "new_factory"

    with pytest.raises(RuntimeError):
        with _switch_factory(conn, new_factory):
            assert conn.row_factory == new_factory
            raise RuntimeError("boom")

    assert conn.row_factory == "original_factory"


# ---------------------------------------------------------------------------
# _compile_query
# ---------------------------------------------------------------------------


def test_compile_query_with_string_returns_string():
    conn = MagicMock()
    result = _compile_query("SELECT 1", conn)

    assert result == "SELECT 1"


def test_compile_query_with_sql_calls_as_string():
    conn = MagicMock()
    sql_obj = _SQL_class()
    sql_obj.as_string = MagicMock(return_value="SELECT compiled")

    with patch("fastapi_pagination.ext.psycopg.SQL", _SQL_class), patch(
        "fastapi_pagination.ext.psycopg.Composed", _Composed_class
    ):
        result = _compile_query(sql_obj, conn)

    sql_obj.as_string.assert_called_once_with(conn)
    assert result == "SELECT compiled"


def test_compile_query_with_composed_calls_as_string():
    conn = MagicMock()
    composed_obj = _Composed_class()
    composed_obj.as_string = MagicMock(return_value="SELECT composed")

    with patch("fastapi_pagination.ext.psycopg.SQL", _SQL_class), patch(
        "fastapi_pagination.ext.psycopg.Composed", _Composed_class
    ):
        result = _compile_query(composed_obj, conn)

    composed_obj.as_string.assert_called_once_with(conn)
    assert result == "SELECT composed"


# ---------------------------------------------------------------------------
# _resolve_query_args
# ---------------------------------------------------------------------------


def test_resolve_query_args_raises_when_both_provided():
    with pytest.raises(ValueError, match="Cannot use both positional query arguments"):
        _resolve_query_args((1, 2), {"key": "value"})


def test_resolve_query_args_returns_positional_args():
    result = _resolve_query_args((1, 2), None)
    assert result == (1, 2)


def test_resolve_query_args_returns_query_params():
    params = {"key": "value"}
    result = _resolve_query_args((), params)
    assert result is params


def test_resolve_query_args_returns_none_when_both_empty():
    result = _resolve_query_args((), None)
    assert result is None


# ---------------------------------------------------------------------------
# _psycopg_limit_offset_flow
# ---------------------------------------------------------------------------


def test_psycopg_limit_offset_flow_returns_items():
    from fastapi_pagination.bases import RawParams

    conn = MagicMock()
    cursor_mock = MagicMock()
    cursor_mock.fetchall.return_value = [("row1",), ("row2",)]
    conn.execute.return_value = cursor_mock
    raw_params = RawParams(limit=10, offset=0)

    result = run_sync_flow(_psycopg_limit_offset_flow(conn, "SELECT 1", None, raw_params))

    assert result == [("row1",), ("row2",)]


def test_psycopg_limit_offset_flow_passes_args():
    from fastapi_pagination.bases import RawParams

    conn = MagicMock()
    cursor_mock = MagicMock()
    cursor_mock.fetchall.return_value = []
    conn.execute.return_value = cursor_mock
    raw_params = RawParams(limit=5, offset=5)
    args = [42]

    run_sync_flow(_psycopg_limit_offset_flow(conn, "SELECT 1 WHERE id = %s", args, raw_params))

    conn.execute.assert_called_once()
    call_args = conn.execute.call_args
    assert call_args[0][1] is args


# ---------------------------------------------------------------------------
# _psycopg_total_flow
# ---------------------------------------------------------------------------


def test_psycopg_total_flow_returns_count():
    conn = MagicMock()
    cursor_mock = MagicMock()
    cursor_mock.fetchone.return_value = (42,)
    conn.execute.return_value = cursor_mock
    conn.row_factory = "original"

    result = run_sync_flow(_psycopg_total_flow(conn, "SELECT 1", None))

    assert result == 42


def test_psycopg_total_flow_restores_row_factory():
    conn = MagicMock()
    original_factory = "original_factory"
    conn.row_factory = original_factory
    cursor_mock = MagicMock()
    cursor_mock.fetchone.return_value = (10,)
    conn.execute.return_value = cursor_mock

    run_sync_flow(_psycopg_total_flow(conn, "SELECT 1", None))

    assert conn.row_factory == original_factory


def test_psycopg_total_flow_passes_args():
    conn = MagicMock()
    conn.row_factory = "original"
    cursor_mock = MagicMock()
    cursor_mock.fetchone.return_value = (5,)
    conn.execute.return_value = cursor_mock
    args = [1, 2]

    run_sync_flow(_psycopg_total_flow(conn, "SELECT 1", args))

    conn.execute.assert_called_once()
    call_args = conn.execute.call_args
    assert call_args[0][1] is args


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_returns_result():
    conn = MagicMock()
    expected_result = MagicMock()

    with (
        patch("fastapi_pagination.ext.psycopg.run_async_flow", new=AsyncMock(return_value=expected_result)) as mock_run,
        patch("fastapi_pagination.ext.psycopg.generic_flow", return_value=MagicMock()) as mock_flow,
    ):
        result = await apaginate(conn, "SELECT 1")

    assert result is expected_result
    mock_run.assert_called_once()
    mock_flow.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_passes_kwargs():
    conn = MagicMock()
    expected_result = MagicMock()
    params = MagicMock()
    transformer = AsyncMock()
    additional_data = {"key": "value"}
    config = MagicMock()

    with (
        patch("fastapi_pagination.ext.psycopg.run_async_flow", new=AsyncMock(return_value=expected_result)),
        patch("fastapi_pagination.ext.psycopg.generic_flow", return_value=MagicMock()) as mock_flow,
    ):
        result = await apaginate(
            conn,
            "SELECT 1",
            params=params,
            transformer=transformer,
            additional_data=additional_data,
            config=config,
        )

    assert result is expected_result
    _, kwargs = mock_flow.call_args
    assert kwargs["params"] is params
    assert kwargs["transformer"] is transformer
    assert kwargs["additional_data"] is additional_data
    assert kwargs["config"] is config


@pytest.mark.asyncio
async def test_apaginate_raises_on_conflicting_args():
    conn = MagicMock()

    with pytest.raises(ValueError, match="Cannot use both positional query arguments"):
        await apaginate(conn, "SELECT 1", 1, 2, query_params={"a": 1})


@pytest.mark.asyncio
async def test_apaginate_resolves_positional_args():
    conn = MagicMock()
    expected_result = MagicMock()

    with (
        patch("fastapi_pagination.ext.psycopg.run_async_flow", new=AsyncMock(return_value=expected_result)),
        patch("fastapi_pagination.ext.psycopg.generic_flow", return_value=MagicMock()) as mock_flow,
    ):
        await apaginate(conn, "SELECT 1", "arg1", "arg2")

    _, kwargs = mock_flow.call_args
    assert kwargs["limit_offset_flow"].args[2] == ("arg1", "arg2")


def test_paginate_returns_result():
    conn = MagicMock()
    expected_result = MagicMock()

    with (
        patch("fastapi_pagination.ext.psycopg.run_sync_flow", return_value=expected_result) as mock_run,
        patch("fastapi_pagination.ext.psycopg.generic_flow", return_value=MagicMock()) as mock_flow,
    ):
        result = paginate(conn, "SELECT 1")

    assert result is expected_result
    mock_run.assert_called_once()
    mock_flow.assert_called_once()


def test_paginate_passes_kwargs():
    conn = MagicMock()
    expected_result = MagicMock()
    params = MagicMock()
    transformer = MagicMock()
    additional_data = {"key": "value"}
    config = MagicMock()

    with (
        patch("fastapi_pagination.ext.psycopg.run_sync_flow", return_value=expected_result),
        patch("fastapi_pagination.ext.psycopg.generic_flow", return_value=MagicMock()) as mock_flow,
    ):
        result = paginate(
            conn,
            "SELECT 1",
            params=params,
            transformer=transformer,
            additional_data=additional_data,
            config=config,
        )

    assert result is expected_result
    _, kwargs = mock_flow.call_args
    assert kwargs["params"] is params
    assert kwargs["transformer"] is transformer
    assert kwargs["additional_data"] is additional_data
    assert kwargs["config"] is config


def test_paginate_raises_on_conflicting_args():
    conn = MagicMock()

    with pytest.raises(ValueError, match="Cannot use both positional query arguments"):
        paginate(conn, "SELECT 1", 1, 2, query_params={"a": 1})


def test_paginate_resolves_positional_args():
    conn = MagicMock()
    expected_result = MagicMock()

    with (
        patch("fastapi_pagination.ext.psycopg.run_sync_flow", return_value=expected_result),
        patch("fastapi_pagination.ext.psycopg.generic_flow", return_value=MagicMock()) as mock_flow,
    ):
        paginate(conn, "SELECT 1", "arg1", "arg2")

    _, kwargs = mock_flow.call_args
    assert kwargs["limit_offset_flow"].args[2] == ("arg1", "arg2")
