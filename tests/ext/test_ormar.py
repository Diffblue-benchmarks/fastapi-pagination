"""Tests for fastapi_pagination.ext.ormar (apaginate, paginate)."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# Module-level setup: mock external dependencies before importing the module
# under test. The `ormar` package is not installed in this environment.
# ============================================================================


class _MockQuerySet:
    """Mock for ormar.QuerySet."""

    def __init__(self, items=None, total: int = 0) -> None:
        self._items = items if items is not None else []
        self._total = total

    def __class_getitem__(cls, item):
        return cls

    def count(self):
        return self._total

    def all(self):
        return self._items


class _MockModel:
    """Mock for ormar.Model."""

    objects = _MockQuerySet()


_mock_ormar = MagicMock()
_mock_ormar.Model = _MockModel
_mock_ormar.QuerySet = _MockQuerySet

_MOCK_MODULES = {
    "ormar": _mock_ormar,
}

for _mod_name, _mock_obj in _MOCK_MODULES.items():
    sys.modules.setdefault(_mod_name, _mock_obj)

# Now safe to import the module under test
from fastapi_pagination.ext.ormar import apaginate, paginate  # noqa: E402


# ============================================================================
# Tests: apaginate — calls run_async_flow(generic_flow(...))
# ============================================================================


class TestApaginate:
    @pytest.mark.asyncio
    async def test_apaginate_with_queryset_returns_run_async_flow_result(self) -> None:
        mock_query = MagicMock(spec=_MockQuerySet)
        mock_result = MagicMock()

        with patch(
            "fastapi_pagination.ext.ormar.run_async_flow",
            new=AsyncMock(return_value=mock_result),
        ) as mock_run:
            result = await apaginate(mock_query)

        assert result == mock_result
        mock_run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_apaginate_with_model_class_uses_objects(self) -> None:
        """When query is a Model class (not QuerySet), it should use query.objects."""
        mock_objects = MagicMock(spec=_MockQuerySet)
        mock_model_class = MagicMock()
        mock_model_class.objects = mock_objects
        # Ensure isinstance check returns False for QuerySet
        mock_result = MagicMock()

        with (
            patch(
                "fastapi_pagination.ext.ormar.run_async_flow",
                new=AsyncMock(return_value=mock_result),
            ),
            patch(
                "fastapi_pagination.ext.ormar.generic_flow",
                return_value=MagicMock(),
            ) as mock_generic_flow,
        ):
            # mock_model_class is not a _MockQuerySet instance, so line 28 executes
            result = await apaginate(mock_model_class)

        assert result == mock_result
        # Verify generic_flow was called (meaning execution reached line 30)
        mock_generic_flow.assert_called_once()

    @pytest.mark.asyncio
    async def test_apaginate_calls_generic_flow(self) -> None:
        mock_query = MagicMock(spec=_MockQuerySet)
        mock_page = MagicMock()

        with (
            patch(
                "fastapi_pagination.ext.ormar.generic_flow",
                return_value=MagicMock(),
            ) as mock_generic_flow,
            patch(
                "fastapi_pagination.ext.ormar.run_async_flow",
                new=AsyncMock(return_value=mock_page),
            ),
        ):
            result = await apaginate(mock_query)

        mock_generic_flow.assert_called_once()
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_apaginate_passes_params_to_generic_flow(self) -> None:
        mock_query = MagicMock(spec=_MockQuerySet)
        mock_params = MagicMock()
        mock_page = MagicMock()

        with (
            patch(
                "fastapi_pagination.ext.ormar.generic_flow",
                return_value=MagicMock(),
            ) as mock_generic_flow,
            patch(
                "fastapi_pagination.ext.ormar.run_async_flow",
                new=AsyncMock(return_value=mock_page),
            ),
        ):
            result = await apaginate(mock_query, params=mock_params)

        call_kwargs = mock_generic_flow.call_args.kwargs
        assert call_kwargs["params"] is mock_params
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_apaginate_passes_transformer_to_generic_flow(self) -> None:
        mock_query = MagicMock(spec=_MockQuerySet)
        mock_transformer = AsyncMock()
        mock_page = MagicMock()

        with (
            patch(
                "fastapi_pagination.ext.ormar.generic_flow",
                return_value=MagicMock(),
            ) as mock_generic_flow,
            patch(
                "fastapi_pagination.ext.ormar.run_async_flow",
                new=AsyncMock(return_value=mock_page),
            ),
        ):
            result = await apaginate(mock_query, transformer=mock_transformer)

        call_kwargs = mock_generic_flow.call_args.kwargs
        assert call_kwargs["transformer"] is mock_transformer
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_apaginate_passes_additional_data_to_generic_flow(self) -> None:
        mock_query = MagicMock(spec=_MockQuerySet)
        extra_data = {"meta": "value"}
        mock_page = MagicMock()

        with (
            patch(
                "fastapi_pagination.ext.ormar.generic_flow",
                return_value=MagicMock(),
            ) as mock_generic_flow,
            patch(
                "fastapi_pagination.ext.ormar.run_async_flow",
                new=AsyncMock(return_value=mock_page),
            ),
        ):
            result = await apaginate(mock_query, additional_data=extra_data)

        call_kwargs = mock_generic_flow.call_args.kwargs
        assert call_kwargs["additional_data"] == extra_data
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_apaginate_passes_config_to_generic_flow(self) -> None:
        mock_query = MagicMock(spec=_MockQuerySet)
        mock_config = MagicMock()
        mock_page = MagicMock()

        with (
            patch(
                "fastapi_pagination.ext.ormar.generic_flow",
                return_value=MagicMock(),
            ) as mock_generic_flow,
            patch(
                "fastapi_pagination.ext.ormar.run_async_flow",
                new=AsyncMock(return_value=mock_page),
            ),
        ):
            result = await apaginate(mock_query, config=mock_config)

        call_kwargs = mock_generic_flow.call_args.kwargs
        assert call_kwargs["config"] is mock_config
        assert result == mock_page

    @pytest.mark.asyncio
    async def test_apaginate_generic_flow_uses_async_true(self) -> None:
        mock_query = MagicMock(spec=_MockQuerySet)
        mock_page = MagicMock()

        with (
            patch(
                "fastapi_pagination.ext.ormar.generic_flow",
                return_value=MagicMock(),
            ) as mock_generic_flow,
            patch(
                "fastapi_pagination.ext.ormar.run_async_flow",
                new=AsyncMock(return_value=mock_page),
            ),
        ):
            await apaginate(mock_query)

        call_kwargs = mock_generic_flow.call_args.kwargs
        assert call_kwargs["async_"] is True


# ============================================================================
# Tests: paginate — deprecated wrapper around apaginate
# ============================================================================


class TestPaginate:
    @pytest.mark.asyncio
    async def test_paginate_delegates_to_apaginate(self) -> None:
        mock_query = MagicMock(spec=_MockQuerySet)
        mock_result = MagicMock()

        with patch(
            "fastapi_pagination.ext.ormar.apaginate",
            new=AsyncMock(return_value=mock_result),
        ) as mock_apaginate:
            result = await paginate(mock_query)

        assert result == mock_result
        mock_apaginate.assert_awaited_once()
        assert mock_apaginate.call_args.args[0] is mock_query

    @pytest.mark.asyncio
    async def test_paginate_forwards_kwargs(self) -> None:
        mock_query = MagicMock(spec=_MockQuerySet)
        mock_result = MagicMock()
        extra_data = {"key": "value"}

        with patch(
            "fastapi_pagination.ext.ormar.apaginate",
            new=AsyncMock(return_value=mock_result),
        ) as mock_apaginate:
            result = await paginate(mock_query, additional_data=extra_data)

        assert result == mock_result
        call_kwargs = mock_apaginate.call_args.kwargs
        assert call_kwargs["additional_data"] == extra_data

    @pytest.mark.asyncio
    async def test_paginate_forwards_transformer(self) -> None:
        mock_query = MagicMock(spec=_MockQuerySet)
        mock_result = MagicMock()
        mock_transformer = AsyncMock()

        with patch(
            "fastapi_pagination.ext.ormar.apaginate",
            new=AsyncMock(return_value=mock_result),
        ) as mock_apaginate:
            result = await paginate(mock_query, transformer=mock_transformer)

        assert result == mock_result
        call_kwargs = mock_apaginate.call_args.kwargs
        assert call_kwargs["transformer"] is mock_transformer
