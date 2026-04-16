import warnings

import pytest
import sqlalchemy as sa
from unittest.mock import AsyncMock, MagicMock

from fastapi_pagination import Page, Params
from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.ext.databases import _to_mappings, apaginate, paginate
from fastapi_pagination.utils import disable_installed_extensions_check


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def disable_ext_check():
    disable_installed_extensions_check()


def _make_query():
    table = sa.table("test", sa.column("id"), sa.column("name"))
    return sa.select(table)


def _make_db_mock(total: int, rows: list):
    db = MagicMock()
    db.fetch_val = AsyncMock(return_value=total)
    db.fetch_all = AsyncMock(return_value=rows)
    return db


def _make_row(data: dict):
    row = MagicMock()
    row._mapping = data
    return row


async def test_to_mappings_converts_rows():
    rows = [_make_row({"id": 1, "name": "Alice"}), _make_row({"id": 2, "name": "Bob"})]
    result = _to_mappings(rows)
    assert result == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


async def test_to_mappings_empty():
    result = _to_mappings([])
    assert result == []


async def test_apaginate_basic():
    rows = [_make_row({"id": i}) for i in range(3)]
    db = _make_db_mock(total=3, rows=rows)
    query = _make_query()

    with set_page(Page), set_params(Params(page=1, size=10)):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate(db, query)

    assert result.total == 3
    assert result.items == [{"id": i} for i in range(3)]


async def test_apaginate_without_mapping():
    rows = [{"id": 1}, {"id": 2}]
    db = _make_db_mock(total=2, rows=rows)
    query = _make_query()

    with set_page(Page), set_params(Params(page=1, size=10)):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate(db, query, convert_to_mapping=False)

    assert result.total == 2
    assert result.items == [{"id": 1}, {"id": 2}]


async def test_apaginate_with_params_argument():
    rows = [_make_row({"id": i}) for i in range(5)]
    db = _make_db_mock(total=10, rows=rows)
    query = _make_query()
    params = Params(page=2, size=5)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate(db, query, params=params)

    assert result.total == 10
    assert len(result.items) == 5


async def test_paginate_delegates_to_apaginate():
    rows = [_make_row({"id": 1}), _make_row({"id": 2})]
    db = _make_db_mock(total=2, rows=rows)
    query = _make_query()

    with set_page(Page), set_params(Params(page=1, size=10)):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(db, query)

    assert result.total == 2
    assert result.items == [{"id": 1}, {"id": 2}]


async def test_paginate_without_mapping():
    rows = [{"val": 42}]
    db = _make_db_mock(total=1, rows=rows)
    query = _make_query()

    with set_page(Page), set_params(Params(page=1, size=10)):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(db, query, convert_to_mapping=False)

    assert result.total == 1
    assert result.items == [{"val": 42}]
