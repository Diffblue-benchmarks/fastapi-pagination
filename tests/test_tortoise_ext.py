import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_tortoise_mocks():
    tortoise_mock = ModuleType("tortoise")
    tortoise_models_mock = ModuleType("tortoise.models")
    tortoise_query_utils_mock = ModuleType("tortoise.query_utils")
    tortoise_queryset_mock = ModuleType("tortoise.queryset")

    class FakeModel:
        pass

    class FakeQuerySet:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, model=None):
            self.model = model or MagicMock()

    class FakePrefetch:
        pass

    tortoise_models_mock.Model = FakeModel
    tortoise_query_utils_mock.Prefetch = FakePrefetch
    tortoise_queryset_mock.QuerySet = FakeQuerySet

    tortoise_mock.models = tortoise_models_mock
    tortoise_mock.query_utils = tortoise_query_utils_mock
    tortoise_mock.queryset = tortoise_queryset_mock

    return {
        "tortoise": tortoise_mock,
        "tortoise.models": tortoise_models_mock,
        "tortoise.query_utils": tortoise_query_utils_mock,
        "tortoise.queryset": tortoise_queryset_mock,
    }


@pytest.fixture(autouse=True)
def mock_tortoise_modules():
    mocks = _make_tortoise_mocks()
    with patch.dict(sys.modules, mocks):
        for mod_name in list(sys.modules):
            if "fastapi_pagination.ext.tortoise" in mod_name:
                del sys.modules[mod_name]
        yield


def _get_module():
    if "fastapi_pagination.ext.tortoise" in sys.modules:
        del sys.modules["fastapi_pagination.ext.tortoise"]
    from fastapi_pagination.ext import tortoise as tortoise_ext  # noqa: PLC0415

    return tortoise_ext


def test_generate_query_no_prefetch():
    mod = _get_module()
    query = MagicMock()
    result = mod._generate_query(query, False)
    assert result is query
    query.prefetch_related.assert_not_called()


def test_generate_query_prefetch_true():
    mod = _get_module()
    query = MagicMock()
    query.model._meta.fetch_fields = ["field1", "field2"]
    prefetched_query = MagicMock()
    query.prefetch_related.return_value = prefetched_query

    result = mod._generate_query(query, True)

    query.prefetch_related.assert_called_once_with("field1", "field2")
    assert result is prefetched_query


def test_generate_query_prefetch_list():
    mod = _get_module()
    query = MagicMock()
    prefetched_query = MagicMock()
    query.prefetch_related.return_value = prefetched_query

    result = mod._generate_query(query, ["related_field"])

    query.prefetch_related.assert_called_once_with("related_field")
    assert result is prefetched_query


@pytest.mark.asyncio
async def test_apaginate_with_queryset():
    mod = _get_module()
    from tortoise.queryset import QuerySet  # noqa: PLC0415

    mock_result = MagicMock()
    query = QuerySet()

    with patch("fastapi_pagination.ext.tortoise.run_async_flow", new=AsyncMock(return_value=mock_result)) as mock_raf:
        result = await mod.apaginate(query)

    assert result is mock_result
    mock_raf.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_with_model_class():
    mod = _get_module()

    mock_result = MagicMock()
    model_cls = MagicMock()
    mock_qs = MagicMock()
    model_cls.all.return_value = mock_qs

    with patch("fastapi_pagination.ext.tortoise.run_async_flow", new=AsyncMock(return_value=mock_result)):
        result = await mod.apaginate(model_cls)

    model_cls.all.assert_called_once()
    assert result is mock_result


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate():
    mod = _get_module()

    mock_result = MagicMock()
    query = MagicMock()

    with patch.object(mod, "apaginate", new=AsyncMock(return_value=mock_result)) as mock_ap:
        result = await mod.paginate(query)

    mock_ap.assert_called_once_with(
        query,
        params=None,
        prefetch_related=False,
        transformer=None,
        additional_data=None,
        total=None,
        config=None,
    )
    assert result is mock_result


@pytest.mark.asyncio
async def test_paginate_passes_kwargs_to_apaginate():
    mod = _get_module()

    mock_result = MagicMock()
    query = MagicMock()
    params = MagicMock()
    transformer = MagicMock()

    with patch.object(mod, "apaginate", new=AsyncMock(return_value=mock_result)) as mock_ap:
        result = await mod.paginate(query, params=params, total=42, transformer=transformer)

    mock_ap.assert_called_once_with(
        query,
        params=params,
        prefetch_related=False,
        transformer=transformer,
        additional_data=None,
        total=42,
        config=None,
    )
    assert result is mock_result
