import sys
from unittest.mock import MagicMock

import pytest

# Mock the `orm` package before importing fastapi_pagination.ext.orm
_orm_mock = MagicMock()
_orm_mock.models = MagicMock()
_orm_mock.models.QuerySet = MagicMock
sys.modules.setdefault("orm", _orm_mock)
sys.modules.setdefault("orm.models", _orm_mock.models)

from fastapi_pagination import Params  # noqa: E402
from fastapi_pagination.ext.orm import apaginate, paginate  # noqa: E402


def _make_queryset(items: list, total: int) -> MagicMock:
    qs = MagicMock()
    qs.count.return_value = total
    qs.limit.return_value = qs
    qs.offset.return_value = qs
    qs.all.return_value = items
    return qs


@pytest.mark.asyncio
async def test_apaginate_returns_page():
    items = [{"id": 1}, {"id": 2}]
    qs = _make_queryset(items, total=2)
    params = Params(page=1, size=10)

    result = await apaginate(qs, params=params)

    assert result.items == items
    assert result.total == 2
    assert result.page == 1


@pytest.mark.asyncio
async def test_apaginate_respects_pagination():
    items = [{"id": 3}]
    qs = _make_queryset(items, total=5)
    params = Params(page=2, size=1)

    result = await apaginate(qs, params=params)

    qs.limit.assert_called_once_with(1)
    qs.offset.assert_called_once_with(1)
    assert result.total == 5


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate():
    items = [{"id": 10}]
    qs = _make_queryset(items, total=1)
    params = Params(page=1, size=50)

    result = await paginate(qs, params=params)

    assert result.items == items
    assert result.total == 1


@pytest.mark.asyncio
async def test_paginate_empty_results():
    qs = _make_queryset([], total=0)
    params = Params(page=1, size=10)

    result = await paginate(qs, params=params)

    assert result.items == []
    assert result.total == 0
