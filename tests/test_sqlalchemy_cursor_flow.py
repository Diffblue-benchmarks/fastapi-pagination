from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Mock sqlalchemy and related modules before importing fastapi_pagination.ext.sqlalchemy
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

from fastapi_pagination.bases import CursorRawParams
from fastapi_pagination.ext.sqlalchemy import _cursor_flow
from fastapi_pagination.flow import run_sync_flow


def _make_ordered_query():
    """Create a mock query that passes all isinstance and ordering checks."""
    mock_query = MagicMock()
    mock_query._order_by_clauses = [MagicMock()]  # truthy, so ordering check passes
    return mock_query


def _make_mock_page(items, has_previous=True, has_next=True):
    """Create a mock page object compatible with sqlakeyset paging protocol."""
    mock_page = MagicMock()
    mock_page.__iter__.return_value = iter(items)
    mock_page.paging.bookmark_current = "bookmark_current"
    mock_page.paging.bookmark_current_backwards = "bookmark_current_backwards"
    mock_page.paging.has_previous = has_previous
    mock_page.paging.bookmark_previous = "bookmark_previous"
    mock_page.paging.has_next = has_next
    mock_page.paging.bookmark_next = "bookmark_next"
    return mock_page


def test_cursor_flow_raises_for_text_clause(mocker):
    """Test _cursor_flow raises ValueError when query is a TextClause (lines 301-302)"""

    class FakeTextClause:
        pass

    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", FakeTextClause)
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._prepare_query_for_cursor",
        return_value=FakeTextClause(),
    )

    conn = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=10)

    gen = _cursor_flow(MagicMock(), conn, True, False, raw_params)
    with pytest.raises(ValueError, match="Cursor pagination cannot be used with raw SQL queries"):
        gen.send(None)


def test_cursor_flow_raises_for_from_statement(mocker):
    """Test _cursor_flow raises ValueError when query is a FromStatement (lines 303-304)"""

    class FakeTextClause:
        pass

    class FakeFromStatement:
        pass

    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", FakeFromStatement)
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._prepare_query_for_cursor",
        return_value=FakeFromStatement(),
    )

    conn = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=10)

    gen = _cursor_flow(MagicMock(), conn, True, False, raw_params)
    with pytest.raises(ValueError, match="Cursor pagination cannot be used with FromStatement queries"):
        gen.send(None)


def test_cursor_flow_raises_without_ordering(mocker):
    """Test _cursor_flow raises ValueError when query has no ordering (lines 307-308)"""

    class FakeTextClause:
        pass

    class FakeFromStatement:
        pass

    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", FakeFromStatement)

    mock_query = MagicMock()
    mock_query._order_by_clauses = []  # falsy → ordering check triggers

    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._prepare_query_for_cursor",
        return_value=mock_query,
    )

    conn = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=10)

    gen = _cursor_flow(MagicMock(), conn, True, False, raw_params)
    with pytest.raises(ValueError, match="Cursor pagination requires ordering"):
        gen.send(None)


def test_cursor_flow_sync_returns_items_and_data(mocker):
    """Test _cursor_flow sync path returns items and data dict (lines 299, 310, 312, 319, 321, 328)"""

    class FakeTextClause:
        pass

    class FakeFromStatement:
        pass

    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", FakeFromStatement)

    mock_query = _make_ordered_query()
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._prepare_query_for_cursor",
        return_value=mock_query,
    )

    item1, item2 = object(), object()
    mock_page = _make_mock_page([item1, item2], has_previous=True, has_next=False)

    mock_paging = MagicMock()
    mock_paging.select_page.return_value = mock_page
    mocker.patch("fastapi_pagination.ext.sqlalchemy.paging", mock_paging)

    conn = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=5)

    gen = _cursor_flow(mock_query, conn, True, False, raw_params)
    result = run_sync_flow(gen)

    items, data = result
    assert items == [item1, item2]
    assert data["current"] == "bookmark_current"
    assert data["current_backwards"] == "bookmark_current_backwards"
    assert data["previous"] == "bookmark_previous"  # has_previous=True
    assert data["next_"] is None  # has_next=False
    mock_paging.select_page.assert_called_once()


def test_cursor_flow_async_uses_apaging_select_page(mocker):
    """Test _cursor_flow async path uses apaging.select_page (line 310 async branch)"""

    class FakeTextClause:
        pass

    class FakeFromStatement:
        pass

    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", FakeFromStatement)

    mock_query = _make_ordered_query()
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._prepare_query_for_cursor",
        return_value=mock_query,
    )

    item1 = object()
    mock_page = _make_mock_page([item1], has_previous=False, has_next=True)

    mock_apaging = MagicMock()
    mock_apaging.select_page.return_value = mock_page
    mocker.patch("fastapi_pagination.ext.sqlalchemy.apaging", mock_apaging)

    conn = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=5)

    gen = _cursor_flow(mock_query, conn, True, True, raw_params)  # is_async=True
    result = run_sync_flow(gen)

    items, data = result
    assert items == [item1]
    assert data["previous"] is None  # has_previous=False
    assert data["next_"] == "bookmark_next"  # has_next=True
    mock_apaging.select_page.assert_called_once()


def test_cursor_flow_data_has_previous_false_has_next_true(mocker):
    """Test _cursor_flow data dict branches when previous absent and next present (lines 324-325)"""

    class FakeTextClause:
        pass

    class FakeFromStatement:
        pass

    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", FakeFromStatement)

    mock_query = _make_ordered_query()
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._prepare_query_for_cursor",
        return_value=mock_query,
    )

    mock_page = _make_mock_page([], has_previous=False, has_next=True)

    mock_paging = MagicMock()
    mock_paging.select_page.return_value = mock_page
    mocker.patch("fastapi_pagination.ext.sqlalchemy.paging", mock_paging)

    conn = MagicMock()
    raw_params = CursorRawParams(cursor="some_cursor", size=3)

    gen = _cursor_flow(mock_query, conn, False, False, raw_params)
    result = run_sync_flow(gen)

    items, data = result
    assert items == []
    assert data["previous"] is None
    assert data["next_"] == "bookmark_next"
