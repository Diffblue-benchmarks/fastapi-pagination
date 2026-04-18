from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Mock tortoise packages before importing the module under test
class _MockQuerySet:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, model=None):
        self.model = model or MagicMock()
        self.model._meta.fetch_fields = []

    def prefetch_related(self, *args):
        return self

    def count(self):
        return AsyncMock(return_value=0)()

    def all(self):
        return self

    def limit(self, n):
        return self

    def offset(self, n):
        return self


class _MockModel:
    pass


class _MockPrefetch:
    pass


_tortoise_mod = MagicMock()
_tortoise_models_mod = MagicMock()
_tortoise_models_mod.Model = _MockModel
_tortoise_query_utils_mod = MagicMock()
_tortoise_query_utils_mod.Prefetch = _MockPrefetch
_tortoise_queryset_mod = MagicMock()
_tortoise_queryset_mod.QuerySet = _MockQuerySet

for _key, _val in [
    ("tortoise", _tortoise_mod),
    ("tortoise.models", _tortoise_models_mod),
    ("tortoise.query_utils", _tortoise_query_utils_mod),
    ("tortoise.queryset", _tortoise_queryset_mod),
]:
    sys.modules.setdefault(_key, _val)

from fastapi_pagination.ext.tortoise import _generate_query, apaginate, paginate  # noqa: E402


# --- _generate_query ---

def test_generate_query_returns_query_when_prefetch_related_false():
    query = _MockQuerySet()
    result = _generate_query(query, prefetch_related=False)
    assert result is query


def test_generate_query_calls_prefetch_related_with_list():
    query = _MockQuerySet()
    prefetch_list = ["field1", "field2"]
    result = _generate_query(query, prefetch_related=prefetch_list)
    assert result is query  # our mock returns self


def test_generate_query_uses_fetch_fields_when_prefetch_related_true():
    query = _MockQuerySet()
    query.model._meta.fetch_fields = ["rel1", "rel2"]
    result = _generate_query(query, prefetch_related=True)
    assert result is query  # mock returns self after prefetch_related


def test_generate_query_returns_original_when_prefetch_related_empty_list():
    query = _MockQuerySet()
    result = _generate_query(query, prefetch_related=[])
    assert result is query


# --- apaginate ---

@pytest.mark.asyncio
async def test_apaginate_calls_all_when_query_is_not_queryset(mocker):
    mock_run = mocker.patch(
        "fastapi_pagination.ext.tortoise.run_async_flow",
        new_callable=AsyncMock,
        return_value={"items": [], "total": 0},
    )
    mocker.patch(
        "fastapi_pagination.ext.tortoise.generic_flow",
        return_value="flow_sentinel",
    )

    model_cls = MagicMock()
    qs = _MockQuerySet()
    model_cls.all.return_value = qs

    result = await apaginate(model_cls)

    model_cls.all.assert_called_once()
    mock_run.assert_awaited_once_with("flow_sentinel")
    assert result == {"items": [], "total": 0}


@pytest.mark.asyncio
async def test_apaginate_does_not_call_all_when_query_is_queryset(mocker):
    mock_run = mocker.patch(
        "fastapi_pagination.ext.tortoise.run_async_flow",
        new_callable=AsyncMock,
        return_value={"items": [], "total": 0},
    )
    mocker.patch(
        "fastapi_pagination.ext.tortoise.generic_flow",
        return_value="flow_sentinel",
    )

    query = _MockQuerySet()
    result = await apaginate(query)

    mock_run.assert_awaited_once_with("flow_sentinel")
    assert result == {"items": [], "total": 0}


@pytest.mark.asyncio
async def test_apaginate_passes_params_to_generic_flow(mocker):
    mocker.patch(
        "fastapi_pagination.ext.tortoise.run_async_flow",
        new_callable=AsyncMock,
        return_value=None,
    )
    mock_generic_flow = mocker.patch(
        "fastapi_pagination.ext.tortoise.generic_flow",
        return_value="flow_sentinel",
    )

    query = _MockQuerySet()
    params = MagicMock()
    additional_data = {"key": "value"}
    config = MagicMock()

    await apaginate(query, params=params, additional_data=additional_data, config=config)

    call_kwargs = mock_generic_flow.call_args.kwargs
    assert call_kwargs["params"] is params
    assert call_kwargs["additional_data"] is additional_data
    assert call_kwargs["config"] is config


# --- paginate ---

@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate(mocker):
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.tortoise.apaginate",
        new_callable=AsyncMock,
        return_value={"items": [], "total": 0},
    )

    query = _MockQuerySet()
    params = MagicMock()

    result = await paginate(query, params=params)

    mock_apaginate.assert_awaited_once()
    call_kwargs = mock_apaginate.call_args
    assert call_kwargs.args[0] is query
    assert call_kwargs.kwargs["params"] is params
    assert result == {"items": [], "total": 0}
