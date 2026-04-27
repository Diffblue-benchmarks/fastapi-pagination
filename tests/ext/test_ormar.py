from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


# Create a real class to serve as QuerySet so isinstance() works properly
class _FakeQuerySet:
    def __class_getitem__(cls, item):
        return cls


class _FakeModel:
    def __class_getitem__(cls, item):
        return cls


# Mock ormar module before importing the module under test
_ormar_mock = MagicMock()
_ormar_mock.Model = _FakeModel
_ormar_mock.QuerySet = _FakeQuerySet
sys.modules["ormar"] = _ormar_mock
sys.modules.pop("fastapi_pagination.ext.ormar", None)

from fastapi_pagination.ext.ormar import apaginate, paginate  # noqa: E402


@pytest.mark.asyncio
async def test_apaginate_with_queryset(mocker):
    mock_run = mocker.patch(
        "fastapi_pagination.ext.ormar.run_async_flow",
        new_callable=AsyncMock,
        return_value="page_result",
    )
    # Provide a QuerySet instance so isinstance check passes and objects branch is skipped
    query = _FakeQuerySet()

    result = await apaginate(query)

    mock_run.assert_called_once()
    assert result == "page_result"


@pytest.mark.asyncio
async def test_apaginate_with_model_class_uses_objects(mocker):
    mock_run = mocker.patch(
        "fastapi_pagination.ext.ormar.run_async_flow",
        new_callable=AsyncMock,
        return_value="paged",
    )

    mock_objects = MagicMock()
    # Not a _FakeQuerySet instance, so isinstance(query, QuerySet) is False
    model_class = MagicMock()
    model_class.objects = mock_objects

    result = await apaginate(model_class)

    mock_run.assert_called_once()
    assert result == "paged"


@pytest.mark.asyncio
async def test_apaginate_passes_params(mocker):
    mock_run = mocker.patch(
        "fastapi_pagination.ext.ormar.run_async_flow",
        new_callable=AsyncMock,
        return_value="result_with_params",
    )

    query = _FakeQuerySet()
    params = MagicMock()

    result = await apaginate(query, params=params)

    mock_run.assert_called_once()
    assert result == "result_with_params"


@pytest.mark.asyncio
async def test_paginate_calls_apaginate(mocker):
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.ormar.apaginate",
        new_callable=AsyncMock,
        return_value="deprecated_result",
    )

    query = MagicMock()
    params = MagicMock()

    result = await paginate(query, params=params)

    mock_apaginate.assert_called_once_with(
        query,
        params=params,
        transformer=None,
        additional_data=None,
        config=None,
    )
    assert result == "deprecated_result"


@pytest.mark.asyncio
async def test_paginate_forwards_all_args(mocker):
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.ormar.apaginate",
        new_callable=AsyncMock,
        return_value="fwd_result",
    )

    query = MagicMock()
    transformer = MagicMock()
    additional_data = {"key": "value"}
    config = MagicMock()

    result = await paginate(query, transformer=transformer, additional_data=additional_data, config=config)

    mock_apaginate.assert_called_once_with(
        query,
        params=None,
        transformer=transformer,
        additional_data=additional_data,
        config=config,
    )
    assert result == "fwd_result"
