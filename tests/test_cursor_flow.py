from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, select, text

from fastapi_pagination.bases import CursorRawParams
from fastapi_pagination.ext.sqlalchemy import _cursor_flow
from fastapi_pagination.flow import run_sync_flow


@pytest.fixture
def simple_table():
    meta = MetaData()
    return Table("items", meta, Column("id", Integer, primary_key=True))


@pytest.fixture
def ordered_query(simple_table):
    return select(simple_table).order_by(simple_table.c.id)


@pytest.fixture
def unordered_query(simple_table):
    return select(simple_table)


@pytest.fixture
def raw_params():
    return CursorRawParams(cursor=None, size=10, include_total=False)


def test_cursor_flow_raises_for_text_clause(raw_params):
    query = text("SELECT * FROM items")
    conn = MagicMock()

    with pytest.raises(ValueError, match="Cursor pagination cannot be used with raw SQL queries"):
        run_sync_flow(_cursor_flow(query, conn, unique=False, is_async=False, raw_params=raw_params))


def test_cursor_flow_raises_for_from_statement(simple_table, raw_params):
    try:
        from sqlalchemy.orm import FromStatement
    except ImportError:
        pytest.skip("FromStatement not available in this SQLAlchemy version")

    inner_query = select(simple_table)
    # Create a FromStatement using the ORM mapper mechanism
    mapper_mock = MagicMock()
    query = FromStatement(mapper_mock, inner_query)
    conn = MagicMock()

    with pytest.raises(ValueError, match="Cursor pagination cannot be used with FromStatement queries"):
        run_sync_flow(_cursor_flow(query, conn, unique=False, is_async=False, raw_params=raw_params))


def test_cursor_flow_raises_for_missing_order_by(unordered_query, raw_params):
    conn = MagicMock()

    with pytest.raises(ValueError, match="Cursor pagination requires ordering"):
        run_sync_flow(_cursor_flow(unordered_query, conn, unique=False, is_async=False, raw_params=raw_params))


def test_cursor_flow_success_sync(ordered_query, raw_params):
    conn = MagicMock()

    mock_page = MagicMock()
    mock_page.__iter__ = MagicMock(return_value=iter([{"id": 1}, {"id": 2}]))
    mock_page.paging.bookmark_current = "cur"
    mock_page.paging.bookmark_current_backwards = "cur_back"
    mock_page.paging.has_previous = True
    mock_page.paging.bookmark_previous = "prev"
    mock_page.paging.has_next = False
    mock_page.paging.bookmark_next = "next"

    with patch("fastapi_pagination.ext.sqlalchemy.paging") as mock_paging:
        mock_paging.select_page.return_value = mock_page
        items, data = run_sync_flow(
            _cursor_flow(ordered_query, conn, unique=False, is_async=False, raw_params=raw_params)
        )

    assert items == [{"id": 1}, {"id": 2}]
    assert data["current"] == "cur"
    assert data["current_backwards"] == "cur_back"
    assert data["previous"] == "prev"
    assert data["next_"] is None


def test_cursor_flow_success_async_flag(ordered_query, raw_params):
    conn = MagicMock()

    mock_page = MagicMock()
    mock_page.__iter__ = MagicMock(return_value=iter([{"id": 3}]))
    mock_page.paging.bookmark_current = "c"
    mock_page.paging.bookmark_current_backwards = "cb"
    mock_page.paging.has_previous = False
    mock_page.paging.bookmark_previous = "p"
    mock_page.paging.has_next = True
    mock_page.paging.bookmark_next = "n"

    with patch("fastapi_pagination.ext.sqlalchemy.apaging") as mock_apaging:
        mock_apaging.select_page.return_value = mock_page
        items, data = run_sync_flow(
            _cursor_flow(ordered_query, conn, unique=True, is_async=True, raw_params=raw_params)
        )

    assert items == [{"id": 3}]
    assert data["next_"] == "n"
    assert data["previous"] is None


def test_cursor_flow_next_present_when_has_next(ordered_query, raw_params):
    conn = MagicMock()

    mock_page = MagicMock()
    mock_page.__iter__ = MagicMock(return_value=iter([]))
    mock_page.paging.bookmark_current = "c"
    mock_page.paging.bookmark_current_backwards = "cb"
    mock_page.paging.has_previous = False
    mock_page.paging.bookmark_previous = "p"
    mock_page.paging.has_next = True
    mock_page.paging.bookmark_next = "next_token"

    with patch("fastapi_pagination.ext.sqlalchemy.paging") as mock_paging:
        mock_paging.select_page.return_value = mock_page
        items, data = run_sync_flow(
            _cursor_flow(ordered_query, conn, unique=False, is_async=False, raw_params=raw_params)
        )

    assert data["next_"] == "next_token"
    assert data["previous"] is None
