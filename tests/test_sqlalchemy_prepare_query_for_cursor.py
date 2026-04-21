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

from fastapi_pagination.ext.sqlalchemy import _prepare_query_for_cursor


def test_prepare_query_for_cursor_non_compound_select_returns_query_unchanged(mocker):
    """When query is not a CompoundSelect, return it as-is (line 131)"""

    class FakeCompoundSelect:
        pass

    mocker.patch("fastapi_pagination.ext.sqlalchemy.CompoundSelect", FakeCompoundSelect)

    # Plain MagicMock is not an instance of FakeCompoundSelect
    mock_query = MagicMock()
    result = _prepare_query_for_cursor(mock_query)

    assert result is mock_query


def test_prepare_query_for_cursor_compound_select_with_ordering(mocker):
    """When query is a CompoundSelect with ordering, wraps in subquery and reapplies ordering (lines 124-129)"""

    class FakeCompoundSelect:
        pass

    mocker.patch("fastapi_pagination.ext.sqlalchemy.CompoundSelect", FakeCompoundSelect)

    ordering = [MagicMock(), MagicMock()]

    ordered_none = MagicMock()
    mock_subquery = MagicMock()
    ordered_none.subquery.return_value = mock_subquery

    mock_query = FakeCompoundSelect()
    mock_query._order_by_clauses = ordering
    mock_query.order_by = MagicMock(return_value=ordered_none)

    mock_final_select = MagicMock()
    mock_select_result = MagicMock()
    mock_final_select.order_by.return_value = mock_select_result

    mock_select = MagicMock(return_value=mock_final_select)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.select", mock_select)

    result = _prepare_query_for_cursor(mock_query)

    mock_query.order_by.assert_called_once_with(None)
    ordered_none.subquery.assert_called_once_with("__cursor_subquery__")
    mock_select.assert_called_once_with(mock_subquery)
    mock_final_select.order_by.assert_called_once_with(*ordering)
    assert result is mock_select_result


def test_prepare_query_for_cursor_compound_select_empty_ordering(mocker):
    """When query is a CompoundSelect with empty _order_by_clauses, uses empty tuple (line 125 falsy path)"""

    class FakeCompoundSelect:
        pass

    mocker.patch("fastapi_pagination.ext.sqlalchemy.CompoundSelect", FakeCompoundSelect)

    ordered_none = MagicMock()
    mock_subquery = MagicMock()
    ordered_none.subquery.return_value = mock_subquery

    mock_query = FakeCompoundSelect()
    mock_query._order_by_clauses = []  # falsy → falls back to ()
    mock_query.order_by = MagicMock(return_value=ordered_none)

    mock_final_select = MagicMock()
    mock_select_result = MagicMock()
    mock_final_select.order_by.return_value = mock_select_result

    mock_select = MagicMock(return_value=mock_final_select)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.select", mock_select)

    result = _prepare_query_for_cursor(mock_query)

    mock_query.order_by.assert_called_once_with(None)
    ordered_none.subquery.assert_called_once_with("__cursor_subquery__")
    mock_select.assert_called_once_with(mock_subquery)
    mock_final_select.order_by.assert_called_once_with()  # empty tuple unpacked
    assert result is mock_select_result
