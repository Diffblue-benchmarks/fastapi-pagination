import sys
import types
from unittest.mock import AsyncMock, MagicMock

# Mock asyncpg before importing the extension
_asyncpg_mock = types.ModuleType("asyncpg")
_asyncpg_mock.Connection = MagicMock
sys.modules.setdefault("asyncpg", _asyncpg_mock)

import pytest

from fastapi_pagination.api import set_params
from fastapi_pagination.bases import RawParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.asyncpg import apaginate, paginate, _asyncpg_limit_offset_flow
from fastapi_pagination.flow import run_async_flow


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    conn.fetch = AsyncMock()
    conn.fetchval = AsyncMock()
    return conn


@pytest.fixture
def default_params():
    return Params(page=1, size=10)


@pytest.mark.asyncio
async def test_asyncpg_limit_offset_flow_returns_list(mock_conn):
    raw_params = RawParams(limit=10, offset=0)
    mock_conn.fetch.return_value = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    gen = _asyncpg_limit_offset_flow(mock_conn, "SELECT * FROM users", (), raw_params)
    result = await run_async_flow(gen)

    assert mock_conn.fetch.called
    assert isinstance(result, list)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_asyncpg_limit_offset_flow_with_args(mock_conn):
    raw_params = RawParams(limit=5, offset=0)
    mock_conn.fetch.return_value = [{"id": 1}]

    gen = _asyncpg_limit_offset_flow(mock_conn, "SELECT * FROM users WHERE id=$1", (42,), raw_params)
    result = await run_async_flow(gen)

    assert mock_conn.fetch.called
    call_args = mock_conn.fetch.call_args[0]
    assert 42 in call_args
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_asyncpg_limit_offset_flow_empty_result(mock_conn):
    raw_params = RawParams(limit=10, offset=0)
    mock_conn.fetch.return_value = []

    gen = _asyncpg_limit_offset_flow(mock_conn, "SELECT * FROM empty_table", (), raw_params)
    result = await run_async_flow(gen)

    assert result == []


@pytest.mark.asyncio
async def test_apaginate_basic(mock_conn, default_params):
    mock_conn.fetchval.return_value = 2
    mock_conn.fetch.return_value = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    with set_params(default_params):
        result = await apaginate(mock_conn, "SELECT * FROM users")

    assert isinstance(result, Page)
    assert result.total == 2


@pytest.mark.asyncio
async def test_apaginate_with_explicit_params(mock_conn):
    params = Params(page=1, size=5)
    mock_conn.fetchval.return_value = 1
    mock_conn.fetch.return_value = [{"id": 1}]

    result = await apaginate(mock_conn, "SELECT * FROM users", params=params)

    assert isinstance(result, Page)
    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_with_args(mock_conn):
    params = Params(page=1, size=10)
    mock_conn.fetchval.return_value = 1
    mock_conn.fetch.return_value = [{"id": 42, "name": "Test"}]

    result = await apaginate(mock_conn, "SELECT * FROM users WHERE id=$1", 42, params=params)

    assert isinstance(result, Page)
    fetch_call_args = mock_conn.fetch.call_args[0]
    assert 42 in fetch_call_args


@pytest.mark.asyncio
async def test_apaginate_empty_results(mock_conn):
    params = Params(page=1, size=10)
    mock_conn.fetchval.return_value = 0
    mock_conn.fetch.return_value = []

    result = await apaginate(mock_conn, "SELECT * FROM users", params=params)

    assert isinstance(result, Page)
    assert result.total == 0
    assert list(result.items) == []


@pytest.mark.asyncio
async def test_paginate_calls_apaginate(mock_conn):
    params = Params(page=1, size=10)
    mock_conn.fetchval.return_value = 1
    mock_conn.fetch.return_value = [{"id": 1}]

    with pytest.warns(DeprecationWarning):
        result = await paginate(mock_conn, "SELECT * FROM items", params=params)

    assert isinstance(result, Page)
    assert result.total == 1


@pytest.mark.asyncio
async def test_paginate_with_args(mock_conn):
    params = Params(page=1, size=10)
    mock_conn.fetchval.return_value = 1
    mock_conn.fetch.return_value = [{"id": 99}]

    with pytest.warns(DeprecationWarning):
        result = await paginate(mock_conn, "SELECT * FROM items WHERE id=$1", 99, params=params)

    fetch_call_args = mock_conn.fetch.call_args[0]
    assert 99 in fetch_call_args
    assert isinstance(result, Page)


@pytest.mark.asyncio
async def test_apaginate_second_page(mock_conn):
    params = Params(page=2, size=2)
    mock_conn.fetchval.return_value = 4
    mock_conn.fetch.return_value = [{"id": 3}, {"id": 4}]

    result = await apaginate(mock_conn, "SELECT * FROM users", params=params)

    assert isinstance(result, Page)
    assert result.total == 4
    assert result.page == 2
    assert result.size == 2

    fetch_call_args = mock_conn.fetch.call_args[0]
    query_used = fetch_call_args[0]
    assert "OFFSET 2" in query_used
    assert "LIMIT 2" in query_used
