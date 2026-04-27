from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


@pytest.fixture
def mock_queryset():
    qs = MagicMock()
    qs.__class__ = __import__("tortoise.queryset", fromlist=["QuerySet"]).QuerySet
    qs.model._meta.fetch_fields = ["related_a", "related_b"]
    qs.prefetch_related.return_value = qs
    qs.limit.return_value = qs
    qs.offset.return_value = qs
    qs.all.return_value = qs
    return qs


class TestGenerateQuery:
    def test_prefetch_related_false_returns_original_query(self, mock_queryset):
        from fastapi_pagination.ext.tortoise import _generate_query

        result = _generate_query(mock_queryset, False)

        assert result is mock_queryset
        mock_queryset.prefetch_related.assert_not_called()

    def test_prefetch_related_true_uses_model_fetch_fields(self, mock_queryset):
        from fastapi_pagination.ext.tortoise import _generate_query

        mock_queryset.model._meta.fetch_fields = ["rel_a", "rel_b"]
        result = _generate_query(mock_queryset, True)

        mock_queryset.prefetch_related.assert_called_once_with("rel_a", "rel_b")
        assert result is mock_queryset.prefetch_related.return_value

    def test_prefetch_related_list_uses_provided_list(self, mock_queryset):
        from fastapi_pagination.ext.tortoise import _generate_query

        prefetch_list = ["field_x", "field_y"]
        result = _generate_query(mock_queryset, prefetch_list)

        mock_queryset.prefetch_related.assert_called_once_with("field_x", "field_y")
        assert result is mock_queryset.prefetch_related.return_value

    def test_prefetch_related_empty_list_returns_original_query(self, mock_queryset):
        from fastapi_pagination.ext.tortoise import _generate_query

        result = _generate_query(mock_queryset, [])

        assert result is mock_queryset
        mock_queryset.prefetch_related.assert_not_called()


class TestApaginate:
    @pytest.mark.asyncio
    async def test_apaginate_with_queryset(self, mock_queryset):
        from fastapi_pagination.ext.tortoise import apaginate

        expected_result = MagicMock()
        with patch(
            "fastapi_pagination.ext.tortoise.run_async_flow",
            new=AsyncMock(return_value=expected_result),
        ) as mock_flow:
            result = await apaginate(mock_queryset)

        mock_flow.assert_called_once()
        assert result is expected_result

    @pytest.mark.asyncio
    async def test_apaginate_with_model_class_calls_all(self, mock_queryset):
        from fastapi_pagination.ext.tortoise import apaginate

        mock_model = MagicMock()
        mock_model.all.return_value = mock_queryset

        expected_result = MagicMock()
        with patch(
            "fastapi_pagination.ext.tortoise.run_async_flow",
            new=AsyncMock(return_value=expected_result),
        ):
            result = await apaginate(mock_model)

        mock_model.all.assert_called_once()
        assert result is expected_result

    @pytest.mark.asyncio
    async def test_apaginate_passes_kwargs(self, mock_queryset):
        from fastapi_pagination.ext.tortoise import apaginate

        expected_result = [1, 2, 3]
        with patch(
            "fastapi_pagination.ext.tortoise.run_async_flow",
            new=AsyncMock(return_value=expected_result),
        ):
            result = await apaginate(
                mock_queryset,
                prefetch_related=True,
                total=10,
            )

        assert result == expected_result


class TestPaginate:
    @pytest.mark.asyncio
    async def test_paginate_delegates_to_apaginate(self, mock_queryset):
        from fastapi_pagination.ext.tortoise import paginate

        expected_result = MagicMock()
        with patch(
            "fastapi_pagination.ext.tortoise.apaginate",
            new=AsyncMock(return_value=expected_result),
        ) as mock_apaginate:
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
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
    async def test_paginate_passes_all_kwargs(self, mock_queryset):
        from fastapi_pagination.ext.tortoise import paginate

        expected_result = MagicMock()
        extra_params = MagicMock()
        with patch(
            "fastapi_pagination.ext.tortoise.apaginate",
            new=AsyncMock(return_value=expected_result),
        ) as mock_apaginate:
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                result = await paginate(
                    mock_queryset,
                    params=extra_params,
                    prefetch_related=["field"],
                    total=5,
                )

        mock_apaginate.assert_called_once_with(
            mock_queryset,
            params=extra_params,
            prefetch_related=["field"],
            transformer=None,
            additional_data=None,
            total=5,
            config=None,
        )
        assert result is expected_result
