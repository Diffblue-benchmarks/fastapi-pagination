from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

# Mock sqlalchemy and related modules before importing fastapi_pagination.ext.sqlalchemy
# to handle environments where sqlalchemy is not installed
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

import pytest

from fastapi_pagination import Page, Params, set_page, set_params
from fastapi_pagination.ext.sqlalchemy import apaginate


@pytest.fixture
def pagination_ctx():
    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            yield


def make_mock_query():
    query = MagicMock()
    # Ensure _statement_20 returns a mock (simulates _prepare_query behavior)
    query._statement_20.return_value = MagicMock()
    return query


@pytest.mark.asyncio
async def test_apaginate_basic(mocker, pagination_ctx):
    mock_page = MagicMock()
    mock_run = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.run_async_flow",
        new=AsyncMock(return_value=mock_page),
    )

    conn = MagicMock()
    query = make_mock_query()

    result = await apaginate(conn, query)

    assert result is mock_page
    mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_with_count_query(mocker, pagination_ctx):
    mock_page = MagicMock()
    mock_run = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.run_async_flow",
        new=AsyncMock(return_value=mock_page),
    )

    conn = MagicMock()
    query = make_mock_query()
    count_query = make_mock_query()

    result = await apaginate(conn, query, count_query=count_query)

    assert result is mock_page
    mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_with_none_count_query(mocker, pagination_ctx):
    mock_page = MagicMock()
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.run_async_flow",
        new=AsyncMock(return_value=mock_page),
    )

    conn = MagicMock()
    query = make_mock_query()

    result = await apaginate(conn, query, count_query=None)

    assert result is mock_page


@pytest.mark.asyncio
async def test_apaginate_with_params(mocker, pagination_ctx):
    mock_page = MagicMock()
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.run_async_flow",
        new=AsyncMock(return_value=mock_page),
    )

    conn = MagicMock()
    query = make_mock_query()
    params = Params(page=2, size=5)

    result = await apaginate(conn, query, params=params)

    assert result is mock_page


@pytest.mark.asyncio
async def test_apaginate_with_transformer(mocker, pagination_ctx):
    mock_page = MagicMock()
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.run_async_flow",
        new=AsyncMock(return_value=mock_page),
    )

    conn = MagicMock()
    query = make_mock_query()

    async def transformer(items):
        return [{"transformed": True}]

    result = await apaginate(conn, query, transformer=transformer)

    assert result is mock_page


@pytest.mark.asyncio
async def test_apaginate_returns_run_async_flow_result(mocker, pagination_ctx):
    expected = MagicMock()
    expected.total = 10
    expected.items = [1, 2, 3]
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.run_async_flow",
        new=AsyncMock(return_value=expected),
    )

    conn = MagicMock()
    query = make_mock_query()

    result = await apaginate(conn, query)

    assert result is expected
    assert result.total == 10
