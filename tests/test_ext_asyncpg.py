"""Tests for fastapi_pagination/ext/asyncpg.py"""
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock the asyncpg module before it's imported by the extension
asyncpg_mock = MagicMock()
asyncpg_mock.Connection = MagicMock


@pytest.fixture(autouse=True)
def mock_asyncpg_module():
    with patch.dict(sys.modules, {"asyncpg": asyncpg_mock}):
        # Re-import to make sure the extension uses the mocked module
        if "fastapi_pagination.ext.asyncpg" in sys.modules:
            del sys.modules["fastapi_pagination.ext.asyncpg"]
        yield
    if "fastapi_pagination.ext.asyncpg" in sys.modules:
        del sys.modules["fastapi_pagination.ext.asyncpg"]


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    conn.fetch = AsyncMock()
    conn.fetchval = AsyncMock()
    return conn


@pytest.fixture
def sample_records():
    """Records that support dict unpacking like asyncpg.Record objects."""
    records = []
    for i in range(3):
        record = MagicMock()
        record.keys = MagicMock(return_value=["id", "name"])
        record.__iter__ = MagicMock(return_value=iter([("id", i), ("name", f"item_{i}")]))
        # Support {**r} via keys() method simulation
        record_dict = {"id": i, "name": f"item_{i}"}
        record.keys.return_value = record_dict.keys()
        # Make it behave like a mapping for {**r}
        mapping_mock = MagicMock()
        mapping_mock.__iter__ = MagicMock(return_value=iter(record_dict))
        mapping_mock.__getitem__ = MagicMock(side_effect=record_dict.__getitem__)
        mapping_mock.keys = MagicMock(return_value=record_dict.keys())
        records.append(record_dict)
    return records


@pytest.fixture
def params_and_page():
    """Create default Params and set page context."""
    from fastapi_pagination.default import Page, Params
    from fastapi_pagination.api import set_page, set_params

    params = Params(page=1, size=10)
    return params, Page


@pytest.mark.asyncio
async def test_apaginate_basic(mock_conn, params_and_page):
    """Test that apaginate executes a query and returns a page."""
    params, Page = params_and_page

    row = {"id": 1, "name": "test"}
    mock_conn.fetch.return_value = [row]
    mock_conn.fetchval.return_value = 1

    from fastapi_pagination.api import set_page, set_params
    from fastapi_pagination.ext.asyncpg import apaginate

    with set_page(Page), set_params(params):
        result = await apaginate(mock_conn, "SELECT * FROM items")

    assert result is not None
    assert mock_conn.fetch.called


@pytest.mark.asyncio
async def test_apaginate_with_args(mock_conn, params_and_page):
    """Test that apaginate passes extra args to the query."""
    params, Page = params_and_page

    row = {"id": 2, "name": "filtered"}
    mock_conn.fetch.return_value = [row]
    mock_conn.fetchval.return_value = 1

    from fastapi_pagination.api import set_page, set_params
    from fastapi_pagination.ext.asyncpg import apaginate

    with set_page(Page), set_params(params):
        result = await apaginate(mock_conn, "SELECT * FROM items WHERE id=$1", 2)

    assert result is not None
    call_args = mock_conn.fetch.call_args
    assert 2 in call_args[0]


@pytest.mark.asyncio
async def test_apaginate_empty_result(mock_conn, params_and_page):
    """Test that apaginate handles empty results."""
    params, Page = params_and_page

    mock_conn.fetch.return_value = []
    mock_conn.fetchval.return_value = 0

    from fastapi_pagination.api import set_page, set_params
    from fastapi_pagination.ext.asyncpg import apaginate

    with set_page(Page), set_params(params):
        result = await apaginate(mock_conn, "SELECT * FROM items")

    assert result is not None
    assert result.total == 0
    assert list(result.items) == []


@pytest.mark.asyncio
async def test_apaginate_multiple_rows(mock_conn, params_and_page):
    """Test that apaginate returns multiple rows as dict items."""
    params, Page = params_and_page

    rows = [{"id": i, "name": f"item_{i}"} for i in range(5)]
    mock_conn.fetch.return_value = rows
    mock_conn.fetchval.return_value = 5

    from fastapi_pagination.api import set_page, set_params
    from fastapi_pagination.ext.asyncpg import apaginate

    with set_page(Page), set_params(params):
        result = await apaginate(mock_conn, "SELECT * FROM items")

    assert result is not None
    assert result.total == 5
    assert len(list(result.items)) == 5


@pytest.mark.asyncio
async def test_paginate_deprecated(mock_conn, params_and_page):
    """Test that deprecated paginate function calls apaginate."""
    params, Page = params_and_page

    row = {"id": 1, "name": "test"}
    mock_conn.fetch.return_value = [row]
    mock_conn.fetchval.return_value = 1

    from fastapi_pagination.api import set_page, set_params
    from fastapi_pagination.ext.asyncpg import paginate

    import warnings

    with set_page(Page), set_params(params):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = await paginate(mock_conn, "SELECT * FROM items")

    assert result is not None
    assert mock_conn.fetch.called


@pytest.mark.asyncio
async def test_paginate_deprecated_passes_args(mock_conn, params_and_page):
    """Test that deprecated paginate passes args correctly to apaginate."""
    params, Page = params_and_page

    row = {"id": 3, "name": "arg_test"}
    mock_conn.fetch.return_value = [row]
    mock_conn.fetchval.return_value = 1

    from fastapi_pagination.api import set_page, set_params
    from fastapi_pagination.ext.asyncpg import paginate

    import warnings

    with set_page(Page), set_params(params):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = await paginate(mock_conn, "SELECT * FROM items WHERE id=$1", 3)

    assert result is not None
    call_args = mock_conn.fetch.call_args
    assert 3 in call_args[0]


@pytest.mark.asyncio
async def test_asyncpg_limit_offset_flow_returns_dicts(mock_conn):
    """Test that _asyncpg_limit_offset_flow converts records to dicts."""
    from fastapi_pagination.bases import RawParams
    from fastapi_pagination.ext.asyncpg import _asyncpg_limit_offset_flow
    from fastapi_pagination.flow import run_async_flow

    records = [{"id": 1, "value": "a"}, {"id": 2, "value": "b"}]
    mock_conn.fetch.return_value = records
    raw_params = RawParams(limit=10, offset=0)

    result = await run_async_flow(_asyncpg_limit_offset_flow(mock_conn, "SELECT * FROM t", (), raw_params))

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == {"id": 1, "value": "a"}
    assert result[1] == {"id": 2, "value": "b"}


@pytest.mark.asyncio
async def test_asyncpg_limit_offset_flow_calls_fetch(mock_conn):
    """Test that _asyncpg_limit_offset_flow calls conn.fetch with the right query."""
    from fastapi_pagination.bases import RawParams
    from fastapi_pagination.ext.asyncpg import _asyncpg_limit_offset_flow
    from fastapi_pagination.flow import run_async_flow

    mock_conn.fetch.return_value = []
    raw_params = RawParams(limit=5, offset=10)

    await run_async_flow(_asyncpg_limit_offset_flow(mock_conn, "SELECT * FROM t", (), raw_params))

    assert mock_conn.fetch.called
    called_query = mock_conn.fetch.call_args[0][0]
    assert "LIMIT 5" in called_query
    assert "OFFSET 10" in called_query


@pytest.mark.asyncio
async def test_apaginate_with_params_arg(mock_conn):
    """Test apaginate when params are passed explicitly."""
    from fastapi_pagination.default import Page, Params
    from fastapi_pagination.api import set_page
    from fastapi_pagination.ext.asyncpg import apaginate

    mock_conn.fetch.return_value = [{"id": 1}]
    mock_conn.fetchval.return_value = 1

    params = Params(page=1, size=5)
    with set_page(Page):
        result = await apaginate(mock_conn, "SELECT * FROM items", params=params)

    assert result is not None
    assert mock_conn.fetch.called


@pytest.mark.asyncio
async def test_paginate_with_params_arg(mock_conn):
    """Test deprecated paginate when params are passed explicitly."""
    from fastapi_pagination.default import Page, Params
    from fastapi_pagination.api import set_page
    from fastapi_pagination.ext.asyncpg import paginate

    mock_conn.fetch.return_value = [{"id": 1}]
    mock_conn.fetchval.return_value = 1

    params = Params(page=1, size=5)

    import warnings

    with set_page(Page):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = await paginate(mock_conn, "SELECT * FROM items", params=params)

    assert result is not None
    assert mock_conn.fetch.called
