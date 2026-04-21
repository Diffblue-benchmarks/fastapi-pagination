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

from fastapi_pagination.ext.sqlalchemy import _inner_transformer


def test_inner_transformer_calls_maybe_unique_and_unwrap_items(mocker):
    """Test _inner_transformer calls _maybe_unique then _unwrap_items (lines 373-376)"""
    processed_items = [10, 20, 30]
    final_items = [10, 20, 30]

    mock_maybe_unique = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._maybe_unique",
        return_value=processed_items,
    )
    mock_unwrap = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._unwrap_items",
        return_value=final_items,
    )

    mock_query = MagicMock()
    original_items = MagicMock()

    result = _inner_transformer(original_items, query=mock_query, unwrap_mode=None, unique=True)

    mock_maybe_unique.assert_called_once_with(original_items, True)
    mock_unwrap.assert_called_once_with(processed_items, mock_query, None)
    assert result is final_items


def test_inner_transformer_unique_false(mocker):
    """Test _inner_transformer with unique=False passes it to _maybe_unique"""
    processed_items = [1, 2]

    mock_maybe_unique = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._maybe_unique",
        return_value=processed_items,
    )
    mock_unwrap = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._unwrap_items",
        return_value=processed_items,
    )

    mock_query = MagicMock()
    original_items = MagicMock()

    result = _inner_transformer(original_items, query=mock_query, unwrap_mode="no-unwrap", unique=False)

    mock_maybe_unique.assert_called_once_with(original_items, False)
    mock_unwrap.assert_called_once_with(processed_items, mock_query, "no-unwrap")
    assert result is processed_items


def test_inner_transformer_suppresses_attribute_error_from_maybe_unique(mocker):
    """Test _inner_transformer suppresses AttributeError from _maybe_unique (lines 373-374)"""
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._maybe_unique",
        side_effect=AttributeError("no unique method"),
    )
    original_items = [1, 2, 3]
    final_items = [1, 2, 3]
    mock_unwrap = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._unwrap_items",
        return_value=final_items,
    )

    mock_query = MagicMock()

    result = _inner_transformer(original_items, query=mock_query, unwrap_mode="auto", unique=True)

    # items stays as original since AttributeError was suppressed
    mock_unwrap.assert_called_once_with(original_items, mock_query, "auto")
    assert result is final_items


def test_inner_transformer_with_unwrap_mode(mocker):
    """Test _inner_transformer passes unwrap_mode through to _unwrap_items"""
    for mode in ["auto", "legacy", "no-unwrap", "unwrap", None]:
        processed = [42]
        mocker.patch(
            "fastapi_pagination.ext.sqlalchemy._maybe_unique",
            return_value=processed,
        )
        mock_unwrap = mocker.patch(
            "fastapi_pagination.ext.sqlalchemy._unwrap_items",
            return_value=processed,
        )

        mock_query = MagicMock()
        items = MagicMock()

        result = _inner_transformer(items, query=mock_query, unwrap_mode=mode, unique=True)

        mock_unwrap.assert_called_once_with(processed, mock_query, mode)
        assert result is processed
