import warnings

import pytest
import pytest_asyncio

from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.bases import RawParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.asyncpg import apaginate, paginate


class FakeRecord(dict):
    """Minimal asyncpg.Record-like object that supports **r unpacking."""
    pass


@pytest.fixture()
def fake_conn(mocker):
    conn = mocker.AsyncMock()
    return conn


@pytest.mark.asyncio
async def test_apaginate_returns_page(fake_conn):
    fake_conn.fetch.return_value = [FakeRecord(id=1, name="Alice"), FakeRecord(id=2, name="Bob")]
    fake_conn.fetchval.return_value = 2

    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate(fake_conn, "SELECT * FROM users", params=params)

    assert result.total == 2
    assert len(result.items) == 2
    assert result.items[0] == {"id": 1, "name": "Alice"}
    assert result.items[1] == {"id": 2, "name": "Bob"}


@pytest.mark.asyncio
async def test_apaginate_empty_result(fake_conn):
    fake_conn.fetch.return_value = []
    fake_conn.fetchval.return_value = 0

    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate(fake_conn, "SELECT * FROM users", params=params)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_passes_args_to_fetch(fake_conn):
    fake_conn.fetch.return_value = [FakeRecord(id=1, name="Alice")]
    fake_conn.fetchval.return_value = 1

    params = Params(page=1, size=10)

    with set_page(Page):
        await apaginate(fake_conn, "SELECT * FROM users WHERE id = $1", 42, params=params)

    assert fake_conn.fetch.called
    call_args = fake_conn.fetch.call_args
    assert 42 in call_args.args


@pytest.mark.asyncio
async def test_apaginate_pagination_query(fake_conn):
    fake_conn.fetch.return_value = [FakeRecord(id=3, val="x")]
    fake_conn.fetchval.return_value = 10

    params = Params(page=2, size=5)

    with set_page(Page):
        result = await apaginate(fake_conn, "SELECT * FROM t", params=params)

    assert result.page == 2
    assert result.size == 5
    fetch_query = fake_conn.fetch.call_args.args[0]
    assert "LIMIT 5" in fetch_query
    assert "OFFSET 5" in fetch_query


@pytest.mark.asyncio
async def test_paginate_deprecated_calls_apaginate(fake_conn):
    fake_conn.fetch.return_value = [FakeRecord(id=10, data="test")]
    fake_conn.fetchval.return_value = 1

    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(fake_conn, "SELECT * FROM items", params=params)

    assert result.total == 1
    assert result.items == [{"id": 10, "data": "test"}]


@pytest.mark.asyncio
async def test_paginate_deprecated_emits_warning(fake_conn):
    fake_conn.fetch.return_value = []
    fake_conn.fetchval.return_value = 0

    params = Params(page=1, size=10)

    with set_page(Page):
        with pytest.warns(DeprecationWarning):
            await paginate(fake_conn, "SELECT * FROM items", params=params)


@pytest.mark.asyncio
async def test_apaginate_count_query(fake_conn):
    fake_conn.fetch.return_value = []
    fake_conn.fetchval.return_value = 99

    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate(fake_conn, "SELECT * FROM big_table", params=params)

    assert result.total == 99
    count_query = fake_conn.fetchval.call_args.args[0]
    assert "count(*)" in count_query.lower()
