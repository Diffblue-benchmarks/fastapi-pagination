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

from fastapi_pagination.ext.sqlalchemy import _unwrap_items


class _FakeTextClause:
    pass


class _FakeFromStatement:
    pass


class _FakeSelectQuery:
    pass


def test_unwrap_items_text_clause_defaults_to_legacy_mode(mocker):
    """Test that TextClause query with no unwrap_mode defaults to 'legacy' and calls unwrap_scalars"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)
    mock_unwrap_scalars = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.unwrap_scalars",
        return_value=[1, 2],
    )

    query = _FakeTextClause()
    items = [(1,), (2,)]

    result = _unwrap_items(items, query, None)

    mock_unwrap_scalars.assert_called_once_with(items)
    assert result == [1, 2]


def test_unwrap_items_from_statement_defaults_to_legacy_mode(mocker):
    """Test that FromStatement query with no unwrap_mode defaults to 'legacy' and calls unwrap_scalars"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)
    mock_unwrap_scalars = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.unwrap_scalars",
        return_value=[42],
    )

    query = _FakeFromStatement()
    items = [(42,)]

    result = _unwrap_items(items, query, None)

    mock_unwrap_scalars.assert_called_once_with(items)
    assert result == [42]


def test_unwrap_items_non_raw_query_defaults_to_auto_mode(mocker):
    """Test that a plain select query with no unwrap_mode defaults to 'auto'"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)
    mock_should_unwrap = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._should_unwrap_scalars",
        return_value=False,
    )
    mock_unwrap_scalars = mocker.patch("fastapi_pagination.ext.sqlalchemy.unwrap_scalars")

    query = _FakeSelectQuery()
    items = [1, 2]

    result = _unwrap_items(items, query, None)

    mock_should_unwrap.assert_called_once_with(query)
    mock_unwrap_scalars.assert_not_called()
    assert result is items


def test_unwrap_items_legacy_mode_calls_unwrap_scalars_without_force(mocker):
    """Test that explicit 'legacy' unwrap_mode calls unwrap_scalars without force_unwrap"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)
    mock_unwrap_scalars = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.unwrap_scalars",
        return_value=[10],
    )

    query = _FakeSelectQuery()
    items = [(10,)]

    result = _unwrap_items(items, query, "legacy")

    mock_unwrap_scalars.assert_called_once_with(items)
    assert result == [10]


def test_unwrap_items_no_unwrap_mode_returns_items_unchanged(mocker):
    """Test that 'no-unwrap' mode passes through items without calling unwrap_scalars"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)
    mock_unwrap_scalars = mocker.patch("fastapi_pagination.ext.sqlalchemy.unwrap_scalars")

    query = _FakeSelectQuery()
    items = [(1, 2), (3, 4)]

    result = _unwrap_items(items, query, "no-unwrap")

    mock_unwrap_scalars.assert_not_called()
    assert result is items


def test_unwrap_items_unwrap_mode_calls_unwrap_scalars_with_force(mocker):
    """Test that 'unwrap' mode calls unwrap_scalars with force_unwrap=True"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)
    mock_unwrap_scalars = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.unwrap_scalars",
        return_value=[5, 6],
    )

    query = _FakeSelectQuery()
    items = [(5,), (6,)]

    result = _unwrap_items(items, query, "unwrap")

    mock_unwrap_scalars.assert_called_once_with(items, force_unwrap=True)
    assert result == [5, 6]


def test_unwrap_items_auto_mode_with_should_unwrap_true(mocker):
    """Test that 'auto' mode calls unwrap_scalars with force_unwrap=True when _should_unwrap_scalars is True"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._should_unwrap_scalars",
        return_value=True,
    )
    mock_unwrap_scalars = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.unwrap_scalars",
        return_value=[7, 8],
    )

    query = _FakeSelectQuery()
    items = [(7,), (8,)]

    result = _unwrap_items(items, query, "auto")

    mock_unwrap_scalars.assert_called_once_with(items, force_unwrap=True)
    assert result == [7, 8]


def test_unwrap_items_auto_mode_with_should_unwrap_false(mocker):
    """Test that 'auto' mode skips unwrap_scalars when _should_unwrap_scalars returns False"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._should_unwrap_scalars",
        return_value=False,
    )
    mock_unwrap_scalars = mocker.patch("fastapi_pagination.ext.sqlalchemy.unwrap_scalars")

    query = _FakeSelectQuery()
    items = [1, 2, 3]

    result = _unwrap_items(items, query, "auto")

    mock_unwrap_scalars.assert_not_called()
    assert result is items


def test_unwrap_items_text_clause_explicit_mode_overrides_default(mocker):
    """Test that explicit unwrap_mode is preserved for TextClause (not forced to 'legacy')"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)
    mock_unwrap_scalars = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.unwrap_scalars",
        return_value=[9],
    )

    query = _FakeTextClause()
    items = [(9,)]

    result = _unwrap_items(items, query, "unwrap")

    mock_unwrap_scalars.assert_called_once_with(items, force_unwrap=True)
    assert result == [9]
