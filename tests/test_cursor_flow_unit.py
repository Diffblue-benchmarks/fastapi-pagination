from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, String, select, text
from sqlalchemy.orm import DeclarativeBase

from fastapi_pagination.bases import CursorRawParams
from fastapi_pagination.ext.sqlalchemy import _cursor_flow
from fastapi_pagination.flow import run_async_flow, run_sync_flow


class Base(DeclarativeBase):
    pass


class MyModel(Base):
    __tablename__ = "my_model_cursor"
    id = Column(Integer, primary_key=True)
    name = Column(String)


def _make_mock_page(items, has_previous=False, has_next=False, current="cur", current_back="cur_back"):
    mock_page = MagicMock()
    mock_page.__iter__ = MagicMock(return_value=iter(items))
    mock_page.paging.bookmark_current = current
    mock_page.paging.bookmark_current_backwards = current_back
    mock_page.paging.has_previous = has_previous
    mock_page.paging.bookmark_previous = "prev"
    mock_page.paging.has_next = has_next
    mock_page.paging.bookmark_next = "nxt"
    return mock_page


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_cursor_flow_raises_on_text_clause():
    raw_params = CursorRawParams(cursor=None, size=10)
    conn = MagicMock()

    with pytest.raises(ValueError, match="raw SQL queries"):
        run_sync_flow(_cursor_flow(text("SELECT 1"), conn, unique=False, is_async=False, raw_params=raw_params))


def test_cursor_flow_raises_on_from_statement():
    try:
        from sqlalchemy.orm import FromStatement
    except ImportError:
        pytest.skip("FromStatement not available")

    raw_params = CursorRawParams(cursor=None, size=10)
    conn = MagicMock()
    inner = select(MyModel)
    stmt = FromStatement(MyModel, inner)

    with pytest.raises(ValueError, match="FromStatement"):
        run_sync_flow(_cursor_flow(stmt, conn, unique=False, is_async=False, raw_params=raw_params))


def test_cursor_flow_raises_on_missing_ordering():
    raw_params = CursorRawParams(cursor=None, size=10)
    conn = MagicMock()
    q = select(MyModel)  # no ORDER BY -> _order_by_clauses is ()

    with pytest.raises(ValueError, match="ordering"):
        run_sync_flow(_cursor_flow(q, conn, unique=False, is_async=False, raw_params=raw_params))


# ---------------------------------------------------------------------------
# Happy path – sync (is_async=False)
# ---------------------------------------------------------------------------


def test_cursor_flow_sync_returns_items_and_data_no_prev_has_next():
    raw_params = CursorRawParams(cursor=None, size=10)
    conn = MagicMock()
    q = select(MyModel).order_by(MyModel.id)

    mock_item = MagicMock()
    mock_page = _make_mock_page([mock_item], has_previous=False, has_next=True)

    with patch("fastapi_pagination.ext.sqlalchemy.paging") as mock_paging:
        mock_paging.select_page.return_value = mock_page
        items, data = run_sync_flow(_cursor_flow(q, conn, unique=False, is_async=False, raw_params=raw_params))

    assert items == [mock_item]
    assert data["current"] == "cur"
    assert data["current_backwards"] == "cur_back"
    assert data["previous"] is None
    assert data["next_"] == "nxt"


def test_cursor_flow_sync_returns_items_and_data_has_prev_no_next():
    raw_params = CursorRawParams(cursor=None, size=10)
    conn = MagicMock()
    q = select(MyModel).order_by(MyModel.id)

    mock_item = MagicMock()
    mock_page = _make_mock_page([mock_item], has_previous=True, has_next=False)

    with patch("fastapi_pagination.ext.sqlalchemy.paging") as mock_paging:
        mock_paging.select_page.return_value = mock_page
        items, data = run_sync_flow(_cursor_flow(q, conn, unique=False, is_async=False, raw_params=raw_params))

    assert items == [mock_item]
    assert data["previous"] == "prev"
    assert data["next_"] is None


def test_cursor_flow_sync_passes_correct_args_to_select_page():
    raw_params = CursorRawParams(cursor="abc", size=5)
    conn = MagicMock()
    q = select(MyModel).order_by(MyModel.id)

    mock_page = _make_mock_page([])

    with patch("fastapi_pagination.ext.sqlalchemy.paging") as mock_paging:
        mock_paging.select_page.return_value = mock_page
        run_sync_flow(_cursor_flow(q, conn, unique=True, is_async=False, raw_params=raw_params))

    mock_paging.select_page.assert_called_once_with(
        conn,
        selectable=q,
        unique=True,
        per_page=5,
        page="abc",
    )


# ---------------------------------------------------------------------------
# Happy path – async (is_async=True)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cursor_flow_async_returns_items_and_data():
    raw_params = CursorRawParams(cursor=None, size=10)
    conn = MagicMock()
    q = select(MyModel).order_by(MyModel.id)

    mock_item = MagicMock()
    mock_page = _make_mock_page([mock_item], has_previous=True, has_next=True)

    with patch("fastapi_pagination.ext.sqlalchemy.apaging") as mock_apaging:
        mock_apaging.select_page.return_value = mock_page
        items, data = await run_async_flow(_cursor_flow(q, conn, unique=False, is_async=True, raw_params=raw_params))

    assert items == [mock_item]
    assert data["current"] == "cur"
    assert data["current_backwards"] == "cur_back"
    assert data["previous"] == "prev"
    assert data["next_"] == "nxt"
