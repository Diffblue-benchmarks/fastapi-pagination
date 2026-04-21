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

from fastapi_pagination.ext.sqlalchemy import create_count_query


class _FakeTextClause:
    def __init__(self, text="SELECT 1"):
        self.text = text


class _FakeFromStatement:
    def __init__(self, element):
        self.element = element


class _FakeSelectQuery:
    def __init__(self):
        self._ordered = MagicMock()
        self._ordered.options = MagicMock(return_value=self._ordered)
        self.order_by = MagicMock(return_value=self._ordered)
        self._ordered.subquery = MagicMock(return_value="subquery_result")
        self._ordered.with_only_columns = MagicMock(return_value="with_only_columns_result")


def test_create_count_query_text_clause(mocker):
    """Test that TextClause input returns text() with count query from text"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)
    mock_count_from_text = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._create_count_query_from_text",
        return_value="SELECT COUNT(*) FROM t",
    )
    mock_text = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.text",
        return_value="text_result",
    )

    query = _FakeTextClause("SELECT * FROM t")
    result = create_count_query(query)

    mock_count_from_text.assert_called_once_with("SELECT * FROM t")
    mock_text.assert_called_once_with("SELECT COUNT(*) FROM t")
    assert result == "text_result"


def test_create_count_query_from_statement_delegates_to_element(mocker):
    """Test that FromStatement input recursively calls create_count_query on its element"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)
    mock_count_from_text = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._create_count_query_from_text",
        return_value="SELECT COUNT(*) FROM t",
    )
    mock_text = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.text",
        return_value="text_result",
    )

    inner_query = _FakeTextClause("SELECT * FROM t")
    from_stmt = _FakeFromStatement(element=inner_query)

    result = create_count_query(from_stmt)

    mock_count_from_text.assert_called_once_with("SELECT * FROM t")
    mock_text.assert_called_once_with("SELECT COUNT(*) FROM t")
    assert result == "text_result"


def test_create_count_query_use_subquery_true(mocker):
    """Test that a regular query with use_subquery=True returns select(func.count()).select_from(subquery)"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)

    mock_func = MagicMock()
    mock_func.count.return_value = "count_func"
    mocker.patch("fastapi_pagination.ext.sqlalchemy.func", mock_func)

    mock_noload = mocker.patch("fastapi_pagination.ext.sqlalchemy.noload", return_value="noload_star")

    mock_select = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.select",
        return_value=MagicMock(select_from=MagicMock(return_value="select_result")),
    )

    query = _FakeSelectQuery()
    result = create_count_query(query, use_subquery=True)

    query.order_by.assert_called_once_with(None)
    mock_noload.assert_called_once_with("*")
    mock_func.count.assert_called_once()
    mock_select.assert_called_once_with("count_func")
    assert result == "select_result"


def test_create_count_query_use_subquery_default_is_true(mocker):
    """Test that the default value of use_subquery is True"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)

    mock_func = MagicMock()
    mock_func.count.return_value = "count_func"
    mocker.patch("fastapi_pagination.ext.sqlalchemy.func", mock_func)

    mocker.patch("fastapi_pagination.ext.sqlalchemy.noload", return_value="noload_star")

    select_mock = MagicMock()
    select_mock.select_from.return_value = "select_from_result"
    mock_select = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.select",
        return_value=select_mock,
    )

    query = _FakeSelectQuery()
    result = create_count_query(query)

    mock_select.assert_called_once_with("count_func")
    assert result == "select_from_result"


def test_create_count_query_use_subquery_false(mocker):
    """Test that a regular query with use_subquery=False returns with_only_columns"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)

    mock_func = MagicMock()
    mock_func.count.return_value = "count_func"
    mocker.patch("fastapi_pagination.ext.sqlalchemy.func", mock_func)

    mocker.patch("fastapi_pagination.ext.sqlalchemy.noload", return_value="noload_star")
    mocker.patch("fastapi_pagination.ext.sqlalchemy.select")

    query = _FakeSelectQuery()
    result = create_count_query(query, use_subquery=False)

    query.order_by.assert_called_once_with(None)
    mock_func.count.assert_called_once()
    query._ordered.with_only_columns.assert_called_once_with(
        "count_func",
        maintain_column_froms=True,
    )
    assert result == "with_only_columns_result"
