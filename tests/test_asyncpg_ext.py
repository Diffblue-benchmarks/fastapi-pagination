import warnings
from unittest.mock import AsyncMock, MagicMock

import pytest

from fastapi_pagination import Params
from fastapi_pagination.bases import RawParams
from fastapi_pagination.ext.asyncpg import _asyncpg_limit_offset_flow, apaginate, paginate
from fastapi_pagination.flow import run_async_flow


def make_mock_conn(fetch_result=None, fetchval_result=0):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=fetch_result or [])
    conn.fetchval = AsyncMock(return_value=fetchval_result)
    return conn


@pytest.mark.asyncio
async def test_asyncpg_limit_offset_flow_returns_list_of_dicts():
    record = {"id": 1, "name": "Alice"}
    conn = make_mock_conn(fetch_result=[record])
    raw_params = RawParams(limit=10, offset=0, include_total=True)

    gen = _asyncpg_limit_offset_flow(conn, "SELECT * FROM users", (), raw_params)
    result = await run_async_flow(gen)

    assert result == [{"id": 1, "name": "Alice"}]
    conn.fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_asyncpg_limit_offset_flow_empty_result():
    conn = make_mock_conn(fetch_result=[])
    raw_params = RawParams(limit=5, offset=0, include_total=True)

    gen = _asyncpg_limit_offset_flow(conn, "SELECT * FROM items", (), raw_params)
    result = await run_async_flow(gen)

    assert result == []


@pytest.mark.asyncio
async def test_asyncpg_limit_offset_flow_passes_args():
    record = {"id": 2}
    conn = make_mock_conn(fetch_result=[record])
    raw_params = RawParams(limit=10, offset=0, include_total=True)

    gen = _asyncpg_limit_offset_flow(conn, "SELECT * FROM t WHERE id = $1", (42,), raw_params)
    await run_async_flow(gen)

    call_args = conn.fetch.call_args
    assert 42 in call_args.args


@pytest.mark.asyncio
async def test_apaginate_returns_page():
    records = [{"id": i} for i in range(3)]
    conn = make_mock_conn(fetch_result=records, fetchval_result=3)
    params = Params(page=1, size=10)

    result = await apaginate(conn, "SELECT * FROM items", params=params)

    assert result.total == 3
    assert len(result.items) == 3


@pytest.mark.asyncio
async def test_apaginate_with_query_args():
    records = [{"id": 1, "value": "x"}]
    conn = make_mock_conn(fetch_result=records, fetchval_result=1)
    params = Params(page=1, size=10)

    result = await apaginate(conn, "SELECT * FROM t WHERE id = $1", 1, params=params)

    assert result.total == 1
    assert result.items[0]["id"] == 1


@pytest.mark.asyncio
async def test_apaginate_second_page():
    records = [{"id": 11}]
    conn = make_mock_conn(fetch_result=records, fetchval_result=11)
    params = Params(page=2, size=10)

    result = await apaginate(conn, "SELECT * FROM items", params=params)

    assert result.page == 2
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_paginate_deprecated_calls_apaginate():
    records = [{"id": 1}]
    conn = make_mock_conn(fetch_result=records, fetchval_result=1)
    params = Params(page=1, size=10)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = await paginate(conn, "SELECT * FROM items", params=params)

    assert result.total == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_paginate_deprecated_emits_warning():
    conn = make_mock_conn(fetch_result=[], fetchval_result=0)
    params = Params(page=1, size=10)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        await paginate(conn, "SELECT * FROM items", params=params)

    deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
    assert len(deprecation_warnings) >= 1
    assert "apaginate" in str(deprecation_warnings[0].message).lower()
