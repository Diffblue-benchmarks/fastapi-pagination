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
from fastapi_pagination.ext.sqlalchemy import create_paginate_query


class _FakeTextClause:
    def __init__(self, sql="SELECT 1"):
        self.text = sql


class _FakeFromStatement:
    def __init__(self, element):
        self.element = element

    def _generate(self):
        copy = _FakeFromStatement(self.element)
        return copy


class _FakeSelectQuery:
    def __init__(self):
        self._limited = MagicMock()
        self._limited.offset = MagicMock(return_value="offset_result")
        self.limit = MagicMock(return_value=self._limited)
        self.offset = MagicMock(return_value="offset_only_result")


def test_create_paginate_query_text_clause(mocker):
    """Test that TextClause input returns text() wrapping the paginated SQL"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)

    mock_paginate_from_text = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._create_paginate_query_from_text",
        return_value="SELECT 1 LIMIT 10 OFFSET 0",
    )
    mock_text = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.text",
        return_value="text_result",
    )

    query = _FakeTextClause("SELECT 1")
    params = RawParams(limit=10, offset=0)
    result = create_paginate_query(query, params)

    mock_paginate_from_text.assert_called_once_with("SELECT 1", params)
    mock_text.assert_called_once_with("SELECT 1 LIMIT 10 OFFSET 0")
    assert result == "text_result"


def test_create_paginate_query_text_clause_passes_params(mocker):
    """Test that TextClause branch passes params directly to _create_paginate_query_from_text"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)

    mock_paginate_from_text = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._create_paginate_query_from_text",
        return_value="SELECT * LIMIT 5 OFFSET 20",
    )
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.text",
        return_value="text_result",
    )

    query = _FakeTextClause("SELECT *")
    params = RawParams(limit=5, offset=20)
    create_paginate_query(query, params)

    mock_paginate_from_text.assert_called_once_with("SELECT *", params)


def test_create_paginate_query_from_statement(mocker):
    """Test that FromStatement input delegates to _paginate_from_statement"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)

    mock_paginate_from_stmt = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._paginate_from_statement",
        return_value="from_statement_result",
    )

    inner = _FakeTextClause("SELECT 1")
    query = _FakeFromStatement(element=inner)
    params = RawParams(limit=10, offset=0)
    result = create_paginate_query(query, params)

    mock_paginate_from_stmt.assert_called_once_with(query, params)
    assert result == "from_statement_result"


def test_create_paginate_query_generic_query_applies_params(mocker):
    """Test that a generic (non-TextClause, non-FromStatement) query calls generic_query_apply_params"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)

    raw_params = RawParams(limit=10, offset=5)
    mock_generic_apply = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.generic_query_apply_params",
        return_value="applied_result",
    )
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._unwrap_params",
        return_value=raw_params,
    )

    query = _FakeSelectQuery()
    params = RawParams(limit=10, offset=5)
    result = create_paginate_query(query, params)

    mock_generic_apply.assert_called_once_with(query, raw_params)
    assert result == "applied_result"


def test_create_paginate_query_generic_query_unwraps_params(mocker):
    """Test that generic branch calls _unwrap_params to convert AnyParams to RawParams"""
    mocker.patch("fastapi_pagination.ext.sqlalchemy.TextClause", _FakeTextClause)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.FromStatement", _FakeFromStatement)

    raw_params = RawParams(limit=20, offset=10)
    mock_unwrap = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._unwrap_params",
        return_value=raw_params,
    )
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.generic_query_apply_params",
        return_value="applied_result",
    )

    query = _FakeSelectQuery()
    params = MagicMock()
    create_paginate_query(query, params)

    mock_unwrap.assert_called_once_with(params)
