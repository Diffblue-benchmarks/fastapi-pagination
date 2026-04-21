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

from fastapi_pagination.bases import RawParams
from fastapi_pagination.ext.sqlalchemy import _limit_offset_flow
from fastapi_pagination.flow import run_sync_flow


def test_limit_offset_flow_returns_items(mocker):
    """Test _limit_offset_flow calls create_paginate_query and conn.execute, returns items (lines 284-288)"""
    mock_query = MagicMock()
    mock_paginated_query = MagicMock()
    mock_items = MagicMock()

    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.create_paginate_query",
        return_value=mock_paginated_query,
    )

    conn = MagicMock()
    conn.execute.return_value = mock_items

    raw_params = RawParams(limit=10, offset=0)

    gen = _limit_offset_flow(mock_query, conn, raw_params)
    result = run_sync_flow(gen)

    assert result is mock_items


def test_limit_offset_flow_calls_create_paginate_query_with_correct_args(mocker):
    """Test _limit_offset_flow passes query and raw_params to create_paginate_query (line 285)"""
    mock_query = MagicMock()
    mock_paginated_query = MagicMock()
    mock_items = MagicMock()

    mock_create_paginate_query = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.create_paginate_query",
        return_value=mock_paginated_query,
    )

    conn = MagicMock()
    conn.execute.return_value = mock_items

    raw_params = RawParams(limit=5, offset=20)

    gen = _limit_offset_flow(mock_query, conn, raw_params)
    run_sync_flow(gen)

    mock_create_paginate_query.assert_called_once_with(mock_query, raw_params)


def test_limit_offset_flow_calls_conn_execute_with_paginated_query(mocker):
    """Test _limit_offset_flow calls conn.execute with the paginated query (line 286)"""
    mock_query = MagicMock()
    mock_paginated_query = MagicMock()
    mock_items = [object(), object(), object()]

    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.create_paginate_query",
        return_value=mock_paginated_query,
    )

    conn = MagicMock()
    conn.execute.return_value = mock_items

    raw_params = RawParams(limit=3, offset=0)

    gen = _limit_offset_flow(mock_query, conn, raw_params)
    result = run_sync_flow(gen)

    conn.execute.assert_called_once_with(mock_paginated_query)
    assert result is mock_items


def test_limit_offset_flow_with_none_limit_and_offset(mocker):
    """Test _limit_offset_flow works when limit and offset are None (lines 284-288)"""
    mock_query = MagicMock()
    mock_paginated_query = MagicMock()
    mock_items = MagicMock()

    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.create_paginate_query",
        return_value=mock_paginated_query,
    )

    conn = MagicMock()
    conn.execute.return_value = mock_items

    raw_params = RawParams(limit=None, offset=None)

    gen = _limit_offset_flow(mock_query, conn, raw_params)
    result = run_sync_flow(gen)

    assert result is mock_items
