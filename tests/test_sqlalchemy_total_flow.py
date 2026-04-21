from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Mock sqlalchemy and related modules before importing fastapi_pagination.ext.sqlalchemy
for _mod in [
    "sqlalchemy",
    "sqlalchemy.engine",
    "sqlalchemy.exc",
    "sqlalchemy.orm",
    "sqlalchemy.sql",
    "sqlalchemy.sql.elements",
    "sqlalchemy.ext",
    "sqlalchemy.ext.asyncio",
    "sqlalchemy.util",
    "sqlakeyset",
    "sqlakeyset.asyncio",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from fastapi_pagination.ext.sqlalchemy import _total_flow
from fastapi_pagination.flow import run_sync_flow


def test_total_flow_returns_scalar_result(mocker):
    """Test _total_flow yields conn.scalar and returns the result (lines 279-280)"""
    mock_query = MagicMock()
    mock_count_query = MagicMock()
    mock_total = 42

    conn = MagicMock()
    conn.scalar.return_value = mock_total

    gen = _total_flow(mock_query, conn, mock_count_query, False)
    result = run_sync_flow(gen)

    assert result == mock_total
    conn.scalar.assert_called_once_with(mock_count_query)


def test_total_flow_creates_count_query_when_none(mocker):
    """Test _total_flow calls create_count_query when count_query is None (lines 276-277)"""
    mock_query = MagicMock()
    mock_generated_count_query = MagicMock()
    mock_total = 7

    mock_create_count_query = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.create_count_query",
        return_value=mock_generated_count_query,
    )

    conn = MagicMock()
    conn.scalar.return_value = mock_total

    gen = _total_flow(mock_query, conn, None, False)
    result = run_sync_flow(gen)

    mock_create_count_query.assert_called_once_with(mock_query, use_subquery=False)
    conn.scalar.assert_called_once_with(mock_generated_count_query)
    assert result == mock_total


def test_total_flow_creates_count_query_with_subquery(mocker):
    """Test _total_flow passes subquery_count=True to create_count_query (line 277)"""
    mock_query = MagicMock()
    mock_generated_count_query = MagicMock()

    mock_create_count_query = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.create_count_query",
        return_value=mock_generated_count_query,
    )

    conn = MagicMock()
    conn.scalar.return_value = 100

    gen = _total_flow(mock_query, conn, None, True)
    run_sync_flow(gen)

    mock_create_count_query.assert_called_once_with(mock_query, use_subquery=True)


def test_total_flow_skips_create_count_query_when_provided(mocker):
    """Test _total_flow does not call create_count_query when count_query is provided (line 276)"""
    mock_query = MagicMock()
    mock_count_query = MagicMock()

    mock_create_count_query = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.create_count_query",
    )

    conn = MagicMock()
    conn.scalar.return_value = 5

    gen = _total_flow(mock_query, conn, mock_count_query, False)
    run_sync_flow(gen)

    mock_create_count_query.assert_not_called()
    conn.scalar.assert_called_once_with(mock_count_query)


def test_total_flow_returns_none_when_scalar_is_none(mocker):
    """Test _total_flow returns None when conn.scalar returns None (lines 279-280)"""
    mock_query = MagicMock()
    mock_count_query = MagicMock()

    conn = MagicMock()
    conn.scalar.return_value = None

    gen = _total_flow(mock_query, conn, mock_count_query, False)
    result = run_sync_flow(gen)

    assert result is None
