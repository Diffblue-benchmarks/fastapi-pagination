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

from fastapi_pagination.ext.sqlalchemy import _should_unwrap_scalars


class _FakeSelect:
    pass


class _FakeTextClause:
    pass


class _FakeFromStatement:
    pass


class _FakeCompoundSelect:
    pass


class _FakeOtherQuery:
    pass


def test_should_unwrap_scalars_non_selectable_returns_false(mocker):
    """Test that a non-selectable query returns False"""
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._selectable_classes",
        (_FakeSelect, _FakeTextClause, _FakeFromStatement, _FakeCompoundSelect),
    )
    mocker.patch("fastapi_pagination.ext.sqlalchemy.CompoundSelect", _FakeCompoundSelect)

    query = _FakeOtherQuery()
    result = _should_unwrap_scalars(query)

    assert result is False


def test_should_unwrap_scalars_compound_select_returns_false(mocker):
    """Test that a CompoundSelect query returns False"""
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._selectable_classes",
        (_FakeSelect, _FakeTextClause, _FakeFromStatement, _FakeCompoundSelect),
    )
    mocker.patch("fastapi_pagination.ext.sqlalchemy.CompoundSelect", _FakeCompoundSelect)

    query = _FakeCompoundSelect()
    result = _should_unwrap_scalars(query)

    assert result is False


def test_should_unwrap_scalars_select_delegates_to_helper(mocker):
    """Test that a Select query delegates to _should_unwrap_scalars_for_query"""
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._selectable_classes",
        (_FakeSelect, _FakeTextClause, _FakeFromStatement, _FakeCompoundSelect),
    )
    mocker.patch("fastapi_pagination.ext.sqlalchemy.CompoundSelect", _FakeCompoundSelect)
    mock_helper = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._should_unwrap_scalars_for_query",
        return_value=True,
    )

    query = _FakeSelect()
    result = _should_unwrap_scalars(query)

    mock_helper.assert_called_once_with(query)
    assert result is True


def test_should_unwrap_scalars_select_helper_returns_false(mocker):
    """Test that a Select query returns False when helper returns False"""
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._selectable_classes",
        (_FakeSelect, _FakeTextClause, _FakeFromStatement, _FakeCompoundSelect),
    )
    mocker.patch("fastapi_pagination.ext.sqlalchemy.CompoundSelect", _FakeCompoundSelect)
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._should_unwrap_scalars_for_query",
        return_value=False,
    )

    query = _FakeSelect()
    result = _should_unwrap_scalars(query)

    assert result is False


def test_should_unwrap_scalars_attribute_error_returns_true(mocker):
    """Test that AttributeError from helper causes return True"""
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._selectable_classes",
        (_FakeSelect, _FakeTextClause, _FakeFromStatement, _FakeCompoundSelect),
    )
    mocker.patch("fastapi_pagination.ext.sqlalchemy.CompoundSelect", _FakeCompoundSelect)
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._should_unwrap_scalars_for_query",
        side_effect=AttributeError("no attribute"),
    )

    query = _FakeSelect()
    result = _should_unwrap_scalars(query)

    assert result is True


def test_should_unwrap_scalars_not_implemented_error_returns_true(mocker):
    """Test that NotImplementedError from helper causes return True"""
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._selectable_classes",
        (_FakeSelect, _FakeTextClause, _FakeFromStatement, _FakeCompoundSelect),
    )
    mocker.patch("fastapi_pagination.ext.sqlalchemy.CompoundSelect", _FakeCompoundSelect)
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._should_unwrap_scalars_for_query",
        side_effect=NotImplementedError("not implemented"),
    )

    query = _FakeSelect()
    result = _should_unwrap_scalars(query)

    assert result is True


def test_should_unwrap_scalars_text_clause_delegates_to_helper(mocker):
    """Test that a TextClause query delegates to _should_unwrap_scalars_for_query"""
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._selectable_classes",
        (_FakeSelect, _FakeTextClause, _FakeFromStatement, _FakeCompoundSelect),
    )
    mocker.patch("fastapi_pagination.ext.sqlalchemy.CompoundSelect", _FakeCompoundSelect)
    mock_helper = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._should_unwrap_scalars_for_query",
        return_value=True,
    )

    query = _FakeTextClause()
    result = _should_unwrap_scalars(query)

    mock_helper.assert_called_once_with(query)
    assert result is True
