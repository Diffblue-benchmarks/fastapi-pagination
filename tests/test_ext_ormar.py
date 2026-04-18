"""Unit tests for fastapi_pagination.ext.ormar."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Inject fake ormar module BEFORE importing the extension under test.
# ormar may not be installed in the test environment.
# ---------------------------------------------------------------------------

_ormar_mock = MagicMock()


class _FakeQuerySet:
    """Minimal stand-in for ormar QuerySet."""

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, items=None, total=5):
        self._items = items if items is not None else [{"id": 1}]
        self._total = total

    def count(self):
        return self._total

    def limit(self, n):
        return self

    def offset(self, n):
        return self

    async def all(self):
        return self._items


class _FakeModel:
    """Minimal stand-in for ormar Model."""

    objects = _FakeQuerySet()

    def __class_getitem__(cls, item):
        return cls


_ormar_mock.QuerySet = _FakeQuerySet
_ormar_mock.Model = _FakeModel

for _key, _mod in [
    ("ormar", _ormar_mock),
]:
    sys.modules[_key] = _mod

sys.modules.pop("fastapi_pagination.ext.ormar", None)

from fastapi_pagination.ext.ormar import apaginate, paginate  # noqa: E402


# ---------------------------------------------------------------------------
# Tests for apaginate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_with_queryset():
    """apaginate with a QuerySet instance goes directly to run_async_flow."""
    query = _FakeQuerySet(items=[{"id": 1}, {"id": 2}], total=2)
    result_page = MagicMock(name="page")

    with patch("fastapi_pagination.ext.ormar.run_async_flow", new=AsyncMock(return_value=result_page)) as mock_flow:
        result = await apaginate(query)

    mock_flow.assert_called_once()
    assert result is result_page


@pytest.mark.asyncio
async def test_apaginate_with_model_class():
    """apaginate with a Model class (not QuerySet) uses query.objects (line 28)."""
    result_page = MagicMock(name="page")

    with patch("fastapi_pagination.ext.ormar.run_async_flow", new=AsyncMock(return_value=result_page)) as mock_flow:
        result = await apaginate(_FakeModel)

    mock_flow.assert_called_once()
    assert result is result_page


@pytest.mark.asyncio
async def test_apaginate_passes_params():
    """apaginate forwards params, transformer, additional_data, config to generic_flow."""
    query = _FakeQuerySet()
    params = MagicMock(name="params")
    transformer = MagicMock(name="transformer")
    additional_data = {"extra": "value"}
    config = MagicMock(name="config")
    result_page = MagicMock(name="page")

    with (
        patch("fastapi_pagination.ext.ormar.run_async_flow", new=AsyncMock(return_value=result_page)),
        patch("fastapi_pagination.ext.ormar.generic_flow", return_value=MagicMock()) as mock_generic_flow,
    ):
        result = await apaginate(
            query,
            params=params,
            transformer=transformer,
            additional_data=additional_data,
            config=config,
        )

    mock_generic_flow.assert_called_once_with(
        async_=True,
        total_flow=mock_generic_flow.call_args[1]["total_flow"],
        limit_offset_flow=mock_generic_flow.call_args[1]["limit_offset_flow"],
        params=params,
        transformer=transformer,
        additional_data=additional_data,
        config=config,
    )
    assert result is result_page


# ---------------------------------------------------------------------------
# Tests for paginate (deprecated wrapper)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate():
    """paginate (deprecated) delegates to apaginate."""
    query = _FakeQuerySet()
    result_page = MagicMock(name="page")

    with patch("fastapi_pagination.ext.ormar.apaginate", new=AsyncMock(return_value=result_page)) as mock_apaginate:
        result = await paginate(query)

    mock_apaginate.assert_called_once()
    assert result is result_page


@pytest.mark.asyncio
async def test_paginate_forwards_all_kwargs():
    """paginate forwards params, transformer, additional_data, config to apaginate."""
    query = _FakeQuerySet()
    params = MagicMock(name="params")
    transformer = MagicMock(name="transformer")
    additional_data = {"key": "val"}
    config = MagicMock(name="config")
    result_page = MagicMock(name="page")

    with patch("fastapi_pagination.ext.ormar.apaginate", new=AsyncMock(return_value=result_page)) as mock_apaginate:
        result = await paginate(
            query,
            params=params,
            transformer=transformer,
            additional_data=additional_data,
            config=config,
        )

    mock_apaginate.assert_called_once_with(
        query,
        params=params,
        transformer=transformer,
        additional_data=additional_data,
        config=config,
    )
    assert result is result_page
