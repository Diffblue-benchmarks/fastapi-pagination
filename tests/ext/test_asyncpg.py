import sys
import warnings
from unittest.mock import AsyncMock, MagicMock

import pytest

# Inject a mock asyncpg module so we can import the extension without asyncpg installed
if "asyncpg" not in sys.modules:
    _mock_asyncpg = MagicMock()
    _mock_asyncpg.Connection = MagicMock
    sys.modules["asyncpg"] = _mock_asyncpg

from fastapi_pagination.api import set_params
from fastapi_pagination.bases import RawParams
from fastapi_pagination.default import Params
from fastapi_pagination.ext.asyncpg import _asyncpg_limit_offset_flow, apaginate, paginate
from fastapi_pagination.flow import run_async_flow


class MockRecord(dict):
    """Mock asyncpg Record that supports ** spreading via mapping protocol."""
    pass


@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    return conn


@pytest.mark.asyncio
async def test_asyncpg_limit_offset_flow_returns_dicts(mock_conn):
    records = [MockRecord({"id": 1, "name": "Alice"}), MockRecord({"id": 2, "name": "Bob"})]
    mock_conn.fetch = AsyncMock(return_value=records)

    raw_params = RawParams(limit=10, offset=0)
    result = await run_async_flow(_asyncpg_limit_offset_flow(mock_conn, "SELECT * FROM users", (), raw_params))

    assert result == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


@pytest.mark.asyncio
async def test_asyncpg_limit_offset_flow_calls_fetch_with_paginated_query(mock_conn):
    mock_conn.fetch = AsyncMock(return_value=[])

    raw_params = RawParams(limit=5, offset=10)
    args = (42,)
    await run_async_flow(_asyncpg_limit_offset_flow(mock_conn, "SELECT * FROM items", args, raw_params))

    mock_conn.fetch.assert_called_once()
    call_query = mock_conn.fetch.call_args[0][0]
    assert "LIMIT 5" in call_query
    assert "OFFSET 10" in call_query
    assert mock_conn.fetch.call_args[0][1] == 42


@pytest.mark.asyncio
async def test_asyncpg_limit_offset_flow_empty_result(mock_conn):
    mock_conn.fetch = AsyncMock(return_value=[])

    raw_params = RawParams(limit=10, offset=0)
    result = await run_async_flow(_asyncpg_limit_offset_flow(mock_conn, "SELECT * FROM empty_table", (), raw_params))

    assert result == []


@pytest.mark.asyncio
async def test_apaginate_basic(mock_conn):
    records = [MockRecord({"id": 1, "name": "Alice"}), MockRecord({"id": 2, "name": "Bob"})]
    mock_conn.fetch = AsyncMock(return_value=records)
    mock_conn.fetchval = AsyncMock(return_value=2)

    params = Params(page=1, size=10)
    result = await apaginate(mock_conn, "SELECT * FROM users", params=params)

    assert result.total == 2
    assert len(result.items) == 2
    assert result.items[0] == {"id": 1, "name": "Alice"}


@pytest.mark.asyncio
async def test_apaginate_with_positional_args(mock_conn):
    records = [MockRecord({"id": 3, "name": "Charlie"})]
    mock_conn.fetch = AsyncMock(return_value=records)
    mock_conn.fetchval = AsyncMock(return_value=1)

    params = Params(page=1, size=10)
    result = await apaginate(mock_conn, "SELECT * FROM users WHERE id = $1", 3, params=params)

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0] == {"id": 3, "name": "Charlie"}


@pytest.mark.asyncio
async def test_apaginate_empty_result(mock_conn):
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.fetchval = AsyncMock(return_value=0)

    params = Params(page=1, size=10)
    result = await apaginate(mock_conn, "SELECT * FROM empty_table", params=params)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_uses_set_params_context(mock_conn):
    records = [MockRecord({"id": 1})]
    mock_conn.fetch = AsyncMock(return_value=records)
    mock_conn.fetchval = AsyncMock(return_value=1)

    params = Params(page=1, size=5)
    with set_params(params):
        result = await apaginate(mock_conn, "SELECT * FROM users")

    assert result.total == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_paginate_basic(mock_conn):
    records = [MockRecord({"id": 1, "value": "test"})]
    mock_conn.fetch = AsyncMock(return_value=records)
    mock_conn.fetchval = AsyncMock(return_value=1)

    params = Params(page=1, size=10)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        result = await paginate(mock_conn, "SELECT * FROM users", params=params)

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0] == {"id": 1, "value": "test"}


@pytest.mark.asyncio
async def test_paginate_passes_args_to_apaginate(mock_conn):
    records = [MockRecord({"id": 5, "value": "hello"})]
    mock_conn.fetch = AsyncMock(return_value=records)
    mock_conn.fetchval = AsyncMock(return_value=1)

    params = Params(page=1, size=10)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        result = await paginate(mock_conn, "SELECT * FROM users WHERE id = $1", 5, params=params)

    assert result.total == 1
    assert result.items[0] == {"id": 5, "value": "hello"}
