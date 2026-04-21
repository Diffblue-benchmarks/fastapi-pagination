"""Tests for _cursor_flow in fastapi_pagination.ext.sqlalchemy."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, select, table, text

from fastapi_pagination.bases import CursorRawParams
from fastapi_pagination.ext.sqlalchemy import _cursor_flow
from fastapi_pagination.flow import run_sync_flow


_table = table("test_table", Column("id", Integer))


def _make_mock_page(items, *, has_previous=False, has_next=False):
    page = MagicMock()
    page.__iter__ = MagicMock(return_value=iter(items))
    page.paging.bookmark_current = "cur"
    page.paging.bookmark_current_backwards = "cur_back"
    page.paging.has_previous = has_previous
    page.paging.bookmark_previous = "prev" if has_previous else None
    page.paging.has_next = has_next
    page.paging.bookmark_next = "next" if has_next else None
    return page


def _make_raw_params(size=10, cursor=None):
    return CursorRawParams(cursor=cursor, size=size)


def test_cursor_flow_raises_for_text_clause():
    raw_query = text("SELECT id FROM test_table")
    conn = MagicMock()
    raw_params = _make_raw_params()

    gen = _cursor_flow(raw_query, conn, unique=True, is_async=False, raw_params=raw_params)
    with pytest.raises(ValueError, match="raw SQL queries"):
        run_sync_flow(gen)


def test_cursor_flow_raises_for_from_statement(mocker):
    from sqlalchemy.orm import FromStatement

    from_stmt = MagicMock(spec=FromStatement)
    conn = MagicMock()
    raw_params = _make_raw_params()

    gen = _cursor_flow(from_stmt, conn, unique=True, is_async=False, raw_params=raw_params)
    with pytest.raises(ValueError, match="FromStatement"):
        run_sync_flow(gen)


def test_cursor_flow_raises_when_no_ordering():
    query = select(_table)  # no order_by
    conn = MagicMock()
    raw_params = _make_raw_params()

    gen = _cursor_flow(query, conn, unique=True, is_async=False, raw_params=raw_params)
    with pytest.raises(ValueError, match="ordering"):
        run_sync_flow(gen)


def test_cursor_flow_sync_happy_path():
    query = select(_table).order_by(_table.c.id)
    conn = MagicMock()
    raw_params = _make_raw_params(size=5, cursor=None)

    mock_page = _make_mock_page(["row1", "row2"], has_previous=False, has_next=True)
    mock_select_page = MagicMock(return_value=mock_page)

    with patch("fastapi_pagination.ext.sqlalchemy.paging") as mock_paging:
        mock_paging.select_page = mock_select_page
        gen = _cursor_flow(query, conn, unique=True, is_async=False, raw_params=raw_params)
        items, data = run_sync_flow(gen)

    assert items == ["row1", "row2"]
    assert data["current"] == "cur"
    assert data["current_backwards"] == "cur_back"
    assert data["previous"] is None
    assert data["next_"] == "next"

    mock_select_page.assert_called_once_with(
        conn,
        selectable=query,
        unique=True,
        per_page=5,
        page=None,
    )


def test_cursor_flow_sync_with_previous_and_next():
    query = select(_table).order_by(_table.c.id)
    conn = MagicMock()
    raw_params = _make_raw_params(size=10, cursor="some_cursor")

    mock_page = _make_mock_page(["row1"], has_previous=True, has_next=True)
    mock_select_page = MagicMock(return_value=mock_page)

    with patch("fastapi_pagination.ext.sqlalchemy.paging") as mock_paging:
        mock_paging.select_page = mock_select_page
        gen = _cursor_flow(query, conn, unique=False, is_async=False, raw_params=raw_params)
        items, data = run_sync_flow(gen)

    assert items == ["row1"]
    assert data["previous"] == "prev"
    assert data["next_"] == "next"


def test_cursor_flow_async_uses_apaging():
    query = select(_table).order_by(_table.c.id)
    conn = MagicMock()
    raw_params = _make_raw_params(size=3, cursor=None)

    mock_page = _make_mock_page(["a", "b"], has_previous=False, has_next=False)
    mock_coro = MagicMock(return_value=mock_page)

    with patch("fastapi_pagination.ext.sqlalchemy.apaging") as mock_apaging:
        mock_apaging.select_page = mock_coro
        gen = _cursor_flow(query, conn, unique=True, is_async=True, raw_params=raw_params)
        yielded = next(gen)
        try:
            gen.send(yielded)
        except StopIteration as exc:
            items, data = exc.value

    assert items == ["a", "b"]
    assert data["current"] == "cur"
    assert data["previous"] is None
    assert data["next_"] is None
