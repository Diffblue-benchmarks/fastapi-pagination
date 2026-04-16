"""Unit tests for fastapi_pagination.ext.orm module."""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# orm is not installed; mock the module before import
_orm_mock = MagicMock()
_orm_models_mock = MagicMock()
sys.modules.setdefault("orm", _orm_mock)
sys.modules.setdefault("orm.models", _orm_models_mock)

from fastapi_pagination.ext.orm import apaginate, paginate  # noqa: E402


@pytest.mark.asyncio
async def test_apaginate_returns_result():
    mock_query = MagicMock()
    expected_result = MagicMock()

    with (
        patch("fastapi_pagination.ext.orm.run_async_flow", new=AsyncMock(return_value=expected_result)) as mock_run,
        patch("fastapi_pagination.ext.orm.generic_flow", return_value=MagicMock()) as mock_flow,
    ):
        result = await apaginate(mock_query)

    assert result is expected_result
    mock_run.assert_called_once()
    mock_flow.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_passes_kwargs():
    mock_query = MagicMock()
    expected_result = MagicMock()
    params = MagicMock()
    transformer = AsyncMock()
    additional_data = {"key": "value"}
    config = MagicMock()

    with (
        patch("fastapi_pagination.ext.orm.run_async_flow", new=AsyncMock(return_value=expected_result)),
        patch("fastapi_pagination.ext.orm.generic_flow", return_value=MagicMock()) as mock_flow,
    ):
        result = await apaginate(
            mock_query,
            params=params,
            transformer=transformer,
            additional_data=additional_data,
            config=config,
        )

    assert result is expected_result
    _, kwargs = mock_flow.call_args
    assert kwargs["params"] is params
    assert kwargs["transformer"] is transformer
    assert kwargs["additional_data"] is additional_data
    assert kwargs["config"] is config


@pytest.mark.asyncio
async def test_paginate_calls_apaginate():
    mock_query = MagicMock()
    expected_result = MagicMock()
    params = MagicMock()

    with patch("fastapi_pagination.ext.orm.apaginate", new=AsyncMock(return_value=expected_result)) as mock_apag:
        result = await paginate(mock_query, params=params)

    assert result is expected_result
    mock_apag.assert_called_once_with(
        mock_query,
        params=params,
        transformer=None,
        additional_data=None,
        config=None,
    )


@pytest.mark.asyncio
async def test_paginate_default_args():
    mock_query = MagicMock()
    expected_result = MagicMock()

    with patch("fastapi_pagination.ext.orm.apaginate", new=AsyncMock(return_value=expected_result)) as mock_apag:
        result = await paginate(mock_query)

    assert result is expected_result
    mock_apag.assert_called_once()
    _, kwargs = mock_apag.call_args
    assert kwargs["params"] is None
