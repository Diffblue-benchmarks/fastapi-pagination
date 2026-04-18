"""Tests for fastapi_pagination.ext.orm apaginate and paginate"""
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

# Provide mock orm modules before importing the extension
_orm_pkg = types.ModuleType("orm")
_orm_models = types.ModuleType("orm.models")


class _QuerySet:
    pass


_orm_models.QuerySet = _QuerySet
_orm_pkg.models = _orm_models

sys.modules.setdefault("orm", _orm_pkg)
sys.modules.setdefault("orm.models", _orm_models)

from fastapi_pagination import Page, Params  # noqa: E402
from fastapi_pagination.api import set_page  # noqa: E402
from fastapi_pagination.ext.orm import apaginate, paginate  # noqa: E402


def _make_mock_queryset(items=None, count=0):
    """Create a mock orm QuerySet."""
    mock_qs = MagicMock()
    mock_qs.count = AsyncMock(return_value=count)
    result_qs = MagicMock()
    result_qs.all = AsyncMock(return_value=items if items is not None else [])
    mock_qs.limit.return_value = result_qs
    result_qs.limit.return_value = result_qs
    result_qs.offset.return_value = result_qs
    mock_qs.offset.return_value = mock_qs
    return mock_qs


@pytest.mark.asyncio
async def test_apaginate_returns_page():
    """Test that apaginate returns a page with items."""
    items = [{"id": 1}, {"id": 2}]
    query = _make_mock_queryset(items=items, count=2)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate(query, params=params)

    assert result is not None
    assert result.items == items


@pytest.mark.asyncio
async def test_apaginate_empty_queryset():
    """Test that apaginate handles empty queryset."""
    query = _make_mock_queryset(items=[], count=0)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate(query, params=params)

    assert result is not None
    assert result.items == []
    assert result.total == 0


@pytest.mark.asyncio
async def test_apaginate_with_transformer():
    """Test that apaginate applies an async transformer to items."""
    items = [{"id": 1}]
    query = _make_mock_queryset(items=items, count=1)
    params = Params(page=1, size=10)

    transformed = [{"id": 1, "extra": "added"}]

    async def transformer(i):
        return transformed

    with set_page(Page):
        result = await apaginate(query, params=params, transformer=transformer)

    assert result.items == transformed


@pytest.mark.asyncio
async def test_apaginate_with_additional_data():
    """Test that apaginate accepts additional_data without raising."""
    query = _make_mock_queryset(items=[], count=0)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = await apaginate(query, params=params, additional_data={})

    assert result is not None


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate():
    """Test that paginate returns same result as calling apaginate directly."""
    items = [{"id": 10}]
    query = _make_mock_queryset(items=items, count=1)
    params = Params(page=1, size=10)

    with set_page(Page):
        result = await paginate(query, params=params)

    assert result is not None
    assert result.items == items


@pytest.mark.asyncio
async def test_paginate_count_is_called():
    """Test that count() is called on the queryset during paginate."""
    query = _make_mock_queryset(items=[], count=0)
    params = Params(page=1, size=10)

    with set_page(Page):
        await paginate(query, params=params)

    query.count.assert_called_once()


@pytest.mark.asyncio
async def test_paginate_with_transformer():
    """Test that paginate applies a transformer."""
    items = [{"id": 5}]
    query = _make_mock_queryset(items=items, count=1)
    params = Params(page=1, size=10)

    transformed = [{"id": 5, "transformed": True}]

    async def transformer(i):
        return transformed

    with set_page(Page):
        result = await paginate(query, params=params, transformer=transformer)

    assert result.items == transformed
