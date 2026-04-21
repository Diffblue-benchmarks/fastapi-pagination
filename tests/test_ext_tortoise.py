from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from tortoise.queryset import QuerySet

from fastapi_pagination.ext.tortoise import _generate_query, apaginate, paginate


# --- Tests for _generate_query ---


def test_generate_query_no_prefetch():
    mock_qs = MagicMock()
    result = _generate_query(mock_qs, False)
    assert result is mock_qs
    mock_qs.prefetch_related.assert_not_called()


def test_generate_query_prefetch_true():
    mock_qs = MagicMock()
    mock_qs.model._meta.fetch_fields = ["field1", "field2"]
    mock_prefetched = MagicMock()
    mock_qs.prefetch_related.return_value = mock_prefetched

    result = _generate_query(mock_qs, True)

    mock_qs.prefetch_related.assert_called_once_with("field1", "field2")
    assert result is mock_prefetched


def test_generate_query_prefetch_list():
    mock_qs = MagicMock()
    mock_prefetched = MagicMock()
    mock_qs.prefetch_related.return_value = mock_prefetched

    result = _generate_query(mock_qs, ["rel1", "rel2"])

    mock_qs.prefetch_related.assert_called_once_with("rel1", "rel2")
    assert result is mock_prefetched


# --- Tests for apaginate ---


@pytest.mark.asyncio
async def test_apaginate_with_queryset_does_not_call_all(mocker):
    mock_qs = MagicMock(spec=QuerySet)
    mocker.patch(
        "fastapi_pagination.ext.tortoise.run_async_flow",
        new=AsyncMock(return_value="page_result"),
    )

    result = await apaginate(mock_qs)

    mock_qs.all.assert_not_called()
    assert result == "page_result"


@pytest.mark.asyncio
async def test_apaginate_with_model_class_calls_all(mocker):
    mock_all_qs = MagicMock(spec=QuerySet)
    mock_model = MagicMock()
    mock_model.all.return_value = mock_all_qs

    mocker.patch(
        "fastapi_pagination.ext.tortoise.run_async_flow",
        new=AsyncMock(return_value="page_result"),
    )

    result = await apaginate(mock_model)

    mock_model.all.assert_called_once()
    assert result == "page_result"


# --- Tests for paginate (deprecated wrapper) ---


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate(mocker):
    mock_qs = MagicMock(spec=QuerySet)
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.tortoise.apaginate",
        new=AsyncMock(return_value="page_result"),
    )

    result = await paginate(mock_qs)

    mock_apaginate.assert_called_once_with(
        mock_qs,
        params=None,
        prefetch_related=False,
        transformer=None,
        additional_data=None,
        total=None,
        config=None,
    )
    assert result == "page_result"
