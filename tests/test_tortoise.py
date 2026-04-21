from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_tortoise_modules():
    """Create and inject mock tortoise modules so the extension can be imported."""
    tortoise_mod = ModuleType("tortoise")
    tortoise_models = ModuleType("tortoise.models")
    tortoise_query_utils = ModuleType("tortoise.query_utils")
    tortoise_queryset = ModuleType("tortoise.queryset")

    class MockModel:
        def __class_getitem__(cls, item):
            return cls

    class MockPrefetch:
        pass

    class MockQuerySet:
        def __class_getitem__(cls, item):
            return cls

    tortoise_models.Model = MockModel
    tortoise_query_utils.Prefetch = MockPrefetch
    tortoise_queryset.QuerySet = MockQuerySet

    sys.modules["tortoise"] = tortoise_mod
    sys.modules["tortoise.models"] = tortoise_models
    sys.modules["tortoise.query_utils"] = tortoise_query_utils
    sys.modules["tortoise.queryset"] = tortoise_queryset

    return MockModel, MockPrefetch, MockQuerySet


MockModel, MockPrefetch, MockQuerySet = _mock_tortoise_modules()

from fastapi_pagination.ext.tortoise import _generate_query, apaginate, paginate  # noqa: E402


class TestGenerateQuery:
    def test_returns_query_when_prefetch_related_false(self):
        query = MagicMock()
        result = _generate_query(query, False)
        assert result is query
        query.prefetch_related.assert_not_called()

    def test_returns_query_when_prefetch_related_empty_list(self):
        query = MagicMock()
        result = _generate_query(query, [])
        assert result is query
        query.prefetch_related.assert_not_called()

    def test_prefetch_related_true_uses_model_fetch_fields(self):
        query = MagicMock()
        query.model._meta.fetch_fields = ["rel1", "rel2"]
        mock_prefetched = MagicMock()
        query.prefetch_related.return_value = mock_prefetched

        result = _generate_query(query, True)

        query.prefetch_related.assert_called_once_with("rel1", "rel2")
        assert result is mock_prefetched

    def test_prefetch_related_list_of_strings(self):
        query = MagicMock()
        mock_prefetched = MagicMock()
        query.prefetch_related.return_value = mock_prefetched

        result = _generate_query(query, ["field1", "field2"])

        query.prefetch_related.assert_called_once_with("field1", "field2")
        assert result is mock_prefetched

    def test_prefetch_related_true_empty_fetch_fields(self):
        query = MagicMock()
        query.model._meta.fetch_fields = []
        mock_prefetched = MagicMock()
        query.prefetch_related.return_value = mock_prefetched

        result = _generate_query(query, True)

        query.prefetch_related.assert_called_once_with()
        assert result is mock_prefetched


class TestApaginate:
    @pytest.mark.asyncio
    async def test_converts_model_class_to_queryset(self):
        # plain MagicMock is not an instance of MockQuerySet, so .all() will be called
        mock_model = MagicMock()
        mock_queryset = MagicMock()

        expected_result = MagicMock()
        with patch("fastapi_pagination.ext.tortoise.run_async_flow", new_callable=AsyncMock) as mock_flow:
            mock_flow.return_value = expected_result
            result = await apaginate(mock_model)

        mock_model.all.assert_called_once()
        assert result is expected_result

    @pytest.mark.asyncio
    async def test_queryset_passed_directly_skips_all_call(self):
        # spec=MockQuerySet makes isinstance(mock, MockQuerySet) return True
        mock_queryset = MagicMock(spec=MockQuerySet)

        expected_result = MagicMock()
        with patch("fastapi_pagination.ext.tortoise.run_async_flow", new_callable=AsyncMock) as mock_flow:
            mock_flow.return_value = expected_result
            result = await apaginate(mock_queryset)

        # .all() should NOT have been called since the query is already a QuerySet
        assert result is expected_result

    @pytest.mark.asyncio
    async def test_returns_run_async_flow_result(self):
        mock_queryset = MagicMock(spec=MockQuerySet)
        expected = {"items": [], "total": 0}

        with patch("fastapi_pagination.ext.tortoise.run_async_flow", new_callable=AsyncMock) as mock_flow:
            mock_flow.return_value = expected
            result = await apaginate(mock_queryset)

        assert result == expected


class TestPaginate:
    @pytest.mark.asyncio
    async def test_delegates_to_apaginate(self):
        mock_queryset = MagicMock(spec=MockQuerySet)
        expected_result = MagicMock()

        with patch("fastapi_pagination.ext.tortoise.apaginate", new_callable=AsyncMock) as mock_apaginate:
            mock_apaginate.return_value = expected_result
            result = await paginate(mock_queryset)

        mock_apaginate.assert_called_once_with(
            mock_queryset,
            params=None,
            prefetch_related=False,
            transformer=None,
            additional_data=None,
            total=None,
            config=None,
        )
        assert result is expected_result

    @pytest.mark.asyncio
    async def test_passes_all_params_to_apaginate(self):
        mock_queryset = MagicMock(spec=MockQuerySet)
        mock_params = MagicMock()
        mock_transformer = AsyncMock()
        mock_additional_data = MagicMock()
        mock_config = MagicMock()

        with patch("fastapi_pagination.ext.tortoise.apaginate", new_callable=AsyncMock) as mock_apaginate:
            mock_apaginate.return_value = None
            await paginate(
                mock_queryset,
                params=mock_params,
                prefetch_related=["rel"],
                transformer=mock_transformer,
                additional_data=mock_additional_data,
                total=42,
                config=mock_config,
            )

        mock_apaginate.assert_called_once_with(
            mock_queryset,
            params=mock_params,
            prefetch_related=["rel"],
            transformer=mock_transformer,
            additional_data=mock_additional_data,
            total=42,
            config=mock_config,
        )
