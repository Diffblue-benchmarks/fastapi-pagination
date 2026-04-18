import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi_pagination.api import set_params
from fastapi_pagination.default import Params, Page
from fastapi_pagination.ext.asyncpg import apaginate, paginate, _asyncpg_limit_offset_flow
from fastapi_pagination.bases import RawParams
from fastapi_pagination.flow import run_async_flow


class FakeRecord(dict):
    """Mimics asyncpg Record which supports **unpacking."""
    pass


def make_mock_conn(fetch_result=None, fetchval_result=0):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=fetch_result or [])
    conn.fetchval = AsyncMock(return_value=fetchval_result)
    return conn


@pytest.mark.asyncio
async def test_asyncpg_limit_offset_flow_returns_dicts():
    record = FakeRecord(id=1, name="Alice")
    conn = make_mock_conn(fetch_result=[record])
    raw_params = RawParams(limit=10, offset=0, include_total=True)

    gen = _asyncpg_limit_offset_flow(conn, "SELECT * FROM users", (), raw_params)
    result = await run_async_flow(gen)

    assert result == [{"id": 1, "name": "Alice"}]
    conn.fetch.assert_called_once()


@pytest.mark.asyncio
async def test_asyncpg_limit_offset_flow_empty_result():
    conn = make_mock_conn(fetch_result=[])
    raw_params = RawParams(limit=10, offset=0, include_total=True)

    gen = _asyncpg_limit_offset_flow(conn, "SELECT * FROM items", (), raw_params)
    result = await run_async_flow(gen)

    assert result == []


@pytest.mark.asyncio
async def test_apaginate_returns_page():
    record = FakeRecord(id=1, value="test")
    conn = make_mock_conn(fetch_result=[record], fetchval_result=1)
    params = Params(page=1, size=10)

    with set_params(params):
        result = await apaginate(conn, "SELECT * FROM items")

    assert isinstance(result, Page)
    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0] == {"id": 1, "value": "test"}


@pytest.mark.asyncio
async def test_apaginate_with_args():
    record = FakeRecord(id=2, name="Bob")
    conn = make_mock_conn(fetch_result=[record], fetchval_result=1)
    params = Params(page=1, size=10)

    with set_params(params):
        result = await apaginate(conn, "SELECT * FROM users WHERE id = $1", 2)

    assert isinstance(result, Page)
    assert result.total == 1
    assert result.items[0]["id"] == 2


@pytest.mark.asyncio
async def test_apaginate_empty_results():
    conn = make_mock_conn(fetch_result=[], fetchval_result=0)
    params = Params(page=1, size=10)

    with set_params(params):
        result = await apaginate(conn, "SELECT * FROM items")

    assert isinstance(result, Page)
    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_second_page():
    records = [FakeRecord(id=i) for i in range(11, 21)]
    conn = make_mock_conn(fetch_result=records, fetchval_result=25)
    params = Params(page=2, size=10)

    with set_params(params):
        result = await apaginate(conn, "SELECT * FROM items")

    assert isinstance(result, Page)
    assert result.total == 25
    assert result.page == 2
    assert len(result.items) == 10


@pytest.mark.asyncio
async def test_paginate_deprecated_calls_apaginate():
    record = FakeRecord(id=1)
    conn = make_mock_conn(fetch_result=[record], fetchval_result=1)
    params = Params(page=1, size=10)

    with set_params(params):
        with pytest.warns(DeprecationWarning):
            result = await paginate(conn, "SELECT * FROM items")

    assert isinstance(result, Page)
    assert result.total == 1
    assert result.items[0] == {"id": 1}


@pytest.mark.asyncio
async def test_paginate_deprecated_with_args():
    record = FakeRecord(id=5, status="active")
    conn = make_mock_conn(fetch_result=[record], fetchval_result=1)
    params = Params(page=1, size=10)

    with set_params(params):
        with pytest.warns(DeprecationWarning):
            result = await paginate(conn, "SELECT * FROM items WHERE status = $1", "active")

    assert isinstance(result, Page)
    assert result.items[0]["status"] == "active"
