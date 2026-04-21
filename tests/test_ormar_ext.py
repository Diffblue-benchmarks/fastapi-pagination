import sys
import types
from unittest.mock import MagicMock


class _MockQuerySet:
    def __init__(self, items=None, total=0):
        self._items = items if items is not None else []
        self._total = total

    def __class_getitem__(cls, item):
        return cls

    async def count(self):
        return self._total

    def limit(self, n):
        return self

    def offset(self, n):
        return self

    async def all(self):
        return self._items


class _MockModel:
    pass


# Mock ormar before importing the extension
_ormar_mock = types.ModuleType("ormar")
_ormar_mock.Model = _MockModel
_ormar_mock.QuerySet = _MockQuerySet
sys.modules.setdefault("ormar", _ormar_mock)

import pytest

from fastapi_pagination.api import set_params
from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.ormar import apaginate, paginate


@pytest.mark.asyncio
async def test_apaginate_with_queryset():
    items = [{"id": 1}, {"id": 2}]
    query = _MockQuerySet(items=items, total=2)
    params = Params(page=1, size=10)

    result = await apaginate(query, params=params)

    assert isinstance(result, Page)
    assert result.total == 2


@pytest.mark.asyncio
async def test_apaginate_with_model_class():
    items = [{"id": 1}]
    qs = _MockQuerySet(items=items, total=1)

    class MockModel(_MockModel):
        objects = qs

    params = Params(page=1, size=10)
    result = await apaginate(MockModel, params=params)

    assert isinstance(result, Page)
    assert result.total == 1


@pytest.mark.asyncio
async def test_apaginate_empty_queryset():
    query = _MockQuerySet(items=[], total=0)
    params = Params(page=1, size=10)

    result = await apaginate(query, params=params)

    assert isinstance(result, Page)
    assert result.total == 0
    assert list(result.items) == []


@pytest.mark.asyncio
async def test_apaginate_with_set_params():
    query = _MockQuerySet(items=[], total=0)

    with set_params(Params(page=1, size=5)):
        result = await apaginate(query)

    assert isinstance(result, Page)


@pytest.mark.asyncio
async def test_paginate_calls_apaginate():
    items = [{"id": 1}]
    query = _MockQuerySet(items=items, total=1)
    params = Params(page=1, size=10)

    with pytest.warns(DeprecationWarning):
        result = await paginate(query, params=params)

    assert isinstance(result, Page)
    assert result.total == 1


@pytest.mark.asyncio
async def test_paginate_with_model_class():
    items = [{"id": 99}]
    qs = _MockQuerySet(items=items, total=1)

    class MockModel(_MockModel):
        objects = qs

    params = Params(page=1, size=10)

    with pytest.warns(DeprecationWarning):
        result = await paginate(MockModel, params=params)

    assert isinstance(result, Page)
    assert result.total == 1
