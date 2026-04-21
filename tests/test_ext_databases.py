"""Tests for fastapi_pagination.ext.databases"""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# databases is not installed in test env; mock the module before import
if "databases" not in sys.modules:
    _db_mock = MagicMock()
    sys.modules["databases"] = _db_mock

from sqlalchemy import Column, Integer, MetaData, String, Table, select

from fastapi_pagination.api import set_page
from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.databases import _to_mappings, apaginate, paginate


def _make_row(data: dict):
    row = MagicMock()
    row._mapping = data
    return row


# ---------------------------------------------------------------------------
# _to_mappings
# ---------------------------------------------------------------------------


def test_to_mappings_empty():
    assert _to_mappings([]) == []


def test_to_mappings_single():
    row = _make_row({"id": 1, "name": "Alice"})
    result = _to_mappings([row])
    assert result == [{"id": 1, "name": "Alice"}]


def test_to_mappings_multiple():
    rows = [_make_row({"id": i}) for i in range(3)]
    result = _to_mappings(rows)
    assert result == [{"id": 0}, {"id": 1}, {"id": 2}]


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_query():
    metadata = MetaData()
    table = Table("items", metadata, Column("id", Integer), Column("name", String))
    return select(table)


def _make_db(total: int, rows: list):
    db = MagicMock()
    db.fetch_val = AsyncMock(return_value=total)
    db.fetch_all = AsyncMock(return_value=rows)
    return db


@pytest.mark.asyncio
async def test_apaginate_convert_to_mapping(sample_query):
    row = _make_row({"id": 1, "name": "Alice"})
    db = _make_db(total=1, rows=[row])
    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate(db, sample_query, params=params, convert_to_mapping=True)

    assert result.total == 1
    assert result.items == [{"id": 1, "name": "Alice"}]


@pytest.mark.asyncio
async def test_apaginate_no_convert_to_mapping(sample_query):
    row = _make_row({"id": 2, "name": "Bob"})
    db = _make_db(total=1, rows=[row])
    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate(db, sample_query, params=params, convert_to_mapping=False)

    assert result.total == 1
    assert result.items == [row]


@pytest.mark.asyncio
async def test_apaginate_empty_result(sample_query):
    db = _make_db(total=0, rows=[])
    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate(db, sample_query, params=params)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_second_page(sample_query):
    rows = [_make_row({"id": i}) for i in range(11, 21)]
    db = _make_db(total=100, rows=rows)
    params = Params(page=2, size=10)

    with set_page(Page):
        result = await apaginate(db, sample_query, params=params)

    assert result.total == 100
    assert len(result.items) == 10


# ---------------------------------------------------------------------------
# paginate (delegates to apaginate)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate(sample_query):
    row = _make_row({"id": 42, "name": "Test"})
    db = _make_db(total=1, rows=[row])
    params = Params(page=1, size=10)

    with set_page(Page):
        result = await paginate(db, sample_query, params=params)

    assert result.total == 1
    assert result.items == [{"id": 42, "name": "Test"}]


@pytest.mark.asyncio
async def test_paginate_no_convert_to_mapping(sample_query):
    row = _make_row({"id": 5})
    db = _make_db(total=1, rows=[row])
    params = Params(page=1, size=5)

    with set_page(Page):
        result = await paginate(db, sample_query, params=params, convert_to_mapping=False)

    assert result.total == 1
    assert result.items == [row]
