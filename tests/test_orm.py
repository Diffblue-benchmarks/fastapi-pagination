from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

# Inject mock orm modules before importing the module under test
# to handle environments where orm is not installed
if "orm" not in sys.modules:
    orm_mock = MagicMock()
    sys.modules["orm"] = orm_mock
    sys.modules["orm.models"] = MagicMock()

import pytest

from fastapi_pagination import Page, Params, set_page, set_params
from fastapi_pagination.ext.orm import apaginate, paginate


def make_mock_queryset(items=None, total=10):
    if items is None:
        items = [{"id": i, "name": f"item{i}"} for i in range(3)]

    queryset = MagicMock()
    queryset.count = AsyncMock(return_value=total)

    # limit/offset return a new queryset that supports .all()
    limited_qs = MagicMock()
    limited_qs.limit = MagicMock(return_value=limited_qs)
    limited_qs.offset = MagicMock(return_value=limited_qs)
    limited_qs.all = AsyncMock(return_value=items)

    queryset.limit = MagicMock(return_value=limited_qs)
    queryset.offset = MagicMock(return_value=limited_qs)
    queryset.all = AsyncMock(return_value=items)

    return queryset


@pytest.fixture
def pagination_ctx():
    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            yield


@pytest.mark.asyncio
async def test_apaginate_basic(pagination_ctx):
    items = [{"id": 1}, {"id": 2}]
    queryset = make_mock_queryset(items=items, total=2)

    result = await apaginate(queryset)

    assert result.total == 2
    assert list(result.items) == items


@pytest.mark.asyncio
async def test_apaginate_with_transformer(pagination_ctx):
    items = [{"id": 1}]
    queryset = make_mock_queryset(items=items, total=1)

    async def transformer(items):
        return [{"transformed": True}]

    result = await apaginate(queryset, transformer=transformer)

    assert list(result.items) == [{"transformed": True}]


@pytest.mark.asyncio
async def test_apaginate_with_additional_data(pagination_ctx):
    items = [{"id": 1}]
    queryset = make_mock_queryset(items=items, total=1)

    result = await apaginate(queryset, additional_data={})

    assert result is not None


@pytest.mark.asyncio
async def test_apaginate_with_params(pagination_ctx):
    items = [{"id": 1}]
    queryset = make_mock_queryset(items=items, total=1)
    params = Params(page=1, size=5)

    result = await apaginate(queryset, params=params)

    assert result is not None
    assert result.total == 1


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate(pagination_ctx):
    items = [{"id": 1}, {"id": 2}]
    queryset = make_mock_queryset(items=items, total=2)

    result = await paginate(queryset)

    assert result is not None
    assert result.total == 2
    assert list(result.items) == items


@pytest.mark.asyncio
async def test_paginate_with_transformer(pagination_ctx):
    items = [{"id": 1}]
    queryset = make_mock_queryset(items=items, total=1)

    async def transformer(items):
        return [{"transformed": True}]

    result = await paginate(queryset, transformer=transformer)

    assert list(result.items) == [{"transformed": True}]


@pytest.mark.asyncio
async def test_paginate_with_params(pagination_ctx):
    items = [{"id": 1}]
    queryset = make_mock_queryset(items=items, total=1)
    params = Params(page=2, size=5)

    result = await paginate(queryset, params=params)

    assert result is not None
