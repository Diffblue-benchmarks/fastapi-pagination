import sys
import warnings
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# Mock the ormar module before importing the extension (ormar is an optional dependency)
_ormar_mock = ModuleType("ormar")


class _MockQuerySet:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, items=None, count_result=0):
        self._items = items or []
        self._count_result = count_result

    async def count(self):
        return self._count_result

    def limit(self, n):
        return self

    def offset(self, n):
        return self

    async def all(self):
        return self._items


class _MockModel:
    pass


_ormar_mock.Model = _MockModel
_ormar_mock.QuerySet = _MockQuerySet
sys.modules.setdefault("ormar", _ormar_mock)
sys.modules.pop("fastapi_pagination.ext.ormar", None)

from fastapi_pagination import Params  # noqa: E402
from fastapi_pagination.ext.ormar import apaginate, paginate  # noqa: E402


@pytest.mark.asyncio
async def test_apaginate_with_queryset_returns_page():
    qs = _MockQuerySet(items=[{"id": 1}, {"id": 2}], count_result=2)
    params = Params(page=1, size=10)

    result = await apaginate(qs, params=params)

    assert result.total == 2
    assert len(result.items) == 2


@pytest.mark.asyncio
async def test_apaginate_with_queryset_empty():
    qs = _MockQuerySet(items=[], count_result=0)
    params = Params(page=1, size=10)

    result = await apaginate(qs, params=params)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_with_model_class_uses_objects():
    qs = _MockQuerySet(items=[{"id": 10}], count_result=1)
    model = MagicMock()
    model.objects = qs
    params = Params(page=1, size=10)

    result = await apaginate(model, params=params)

    assert result.total == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_apaginate_second_page():
    qs = _MockQuerySet(items=[{"id": 11}], count_result=11)
    params = Params(page=2, size=10)

    result = await apaginate(qs, params=params)

    assert result.page == 2
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_paginate_calls_apaginate():
    qs = _MockQuerySet(items=[{"id": 1}], count_result=1)
    params = Params(page=1, size=10)

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = await paginate(qs, params=params)

    assert result.total == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_paginate_emits_deprecation_warning():
    qs = _MockQuerySet(items=[], count_result=0)
    params = Params(page=1, size=10)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        await paginate(qs, params=params)

    deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
    assert len(deprecation_warnings) >= 1
    assert "apaginate" in str(deprecation_warnings[0].message).lower()
