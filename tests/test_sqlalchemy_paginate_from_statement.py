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
from fastapi_pagination.ext.sqlalchemy import _paginate_from_statement


class _FakeTextClause:
    def __init__(self, sql="SELECT 1"):
        self.text = sql


class _FakeFromStatement:
    def __init__(self, element):
        self.element = element

    def _generate(self):
        copy = _FakeFromStatement(self.element)
        return copy


def test_paginate_from_statement_calls_generate(mocker):
    """Test that _paginate_from_statement calls _generate() on the query"""
    inner_element = _FakeTextClause("SELECT 1")
    query = _FakeFromStatement(element=inner_element)
    spy_generate = mocker.spy(query, "_generate")

    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.create_paginate_query",
        return_value="paginated_element",
    )

    params = RawParams(limit=10, offset=0)
    _paginate_from_statement(query, params)

    spy_generate.assert_called_once()


def test_paginate_from_statement_sets_element(mocker):
    """Test that _paginate_from_statement sets element to create_paginate_query result"""
    inner_element = _FakeTextClause("SELECT 1")
    query = _FakeFromStatement(element=inner_element)
    paginated = _FakeTextClause("SELECT 1 LIMIT 10 OFFSET 0")

    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.create_paginate_query",
        return_value=paginated,
    )

    params = RawParams(limit=10, offset=0)
    result = _paginate_from_statement(query, params)

    assert result.element is paginated


def test_paginate_from_statement_returns_generated_copy(mocker):
    """Test that _paginate_from_statement returns the generated copy, not the original"""
    inner_element = _FakeTextClause("SELECT 1")
    query = _FakeFromStatement(element=inner_element)

    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.create_paginate_query",
        return_value="paginated_element",
    )

    params = RawParams(limit=10, offset=0)
    result = _paginate_from_statement(query, params)

    assert result is not query
    assert result.element == "paginated_element"


def test_paginate_from_statement_passes_element_to_create_paginate_query(mocker):
    """Test that create_paginate_query is called with the generated query's element and params"""
    inner_element = _FakeTextClause("SELECT * FROM t")
    query = _FakeFromStatement(element=inner_element)

    mock_create_paginate = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.create_paginate_query",
        return_value="paginated_element",
    )

    params = RawParams(limit=5, offset=20)
    _paginate_from_statement(query, params)

    mock_create_paginate.assert_called_once_with(inner_element, params)


def test_paginate_from_statement_passes_params(mocker):
    """Test that _paginate_from_statement passes provided params to create_paginate_query"""
    inner_element = _FakeTextClause("SELECT id FROM users")
    query = _FakeFromStatement(element=inner_element)

    mock_create_paginate = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.create_paginate_query",
        return_value="paginated_element",
    )

    params = RawParams(limit=25, offset=50)
    _paginate_from_statement(query, params)

    _, call_params = mock_create_paginate.call_args[0]
    assert call_params is params
