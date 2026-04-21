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

from fastapi_pagination.bases import RawParams
from fastapi_pagination.ext.sqlalchemy import _unwrap_params


def test_unwrap_params_returns_raw_params_directly():
    """Test that _unwrap_params returns RawParams instances unchanged"""
    raw = RawParams(limit=10, offset=0)
    result = _unwrap_params(raw)
    assert result is raw


def test_unwrap_params_converts_abstract_params():
    """Test that _unwrap_params calls to_raw_params().as_limit_offset() for AbstractParams"""
    expected = RawParams(limit=5, offset=10)
    mock_raw = MagicMock()
    mock_raw.as_limit_offset.return_value = expected

    mock_params = MagicMock(spec=["to_raw_params"])  # not a RawParams instance
    mock_params.to_raw_params.return_value = mock_raw

    result = _unwrap_params(mock_params)

    mock_params.to_raw_params.assert_called_once()
    mock_raw.as_limit_offset.assert_called_once()
    assert result == expected


def test_unwrap_params_raw_params_with_none_limit():
    """Test that RawParams with None limit is returned directly"""
    raw = RawParams(limit=None, offset=0)
    result = _unwrap_params(raw)
    assert result is raw


def test_unwrap_params_raw_params_include_total_false():
    """Test that RawParams with include_total=False is returned directly"""
    raw = RawParams(limit=20, offset=5, include_total=False)
    result = _unwrap_params(raw)
    assert result is raw
