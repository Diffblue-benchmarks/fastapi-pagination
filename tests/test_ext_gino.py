from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Mock gino modules before importing fastapi_pagination.ext.gino since gino is not installed
_mock_gino = MagicMock()
_mock_gino_crud = MagicMock()


class _MockCRUDModel:
    """Minimal stand-in for gino.crud.CRUDModel."""

    pass


_mock_gino_crud.CRUDModel = _MockCRUDModel
_mock_gino.crud = _mock_gino_crud

sys.modules.setdefault("gino", _mock_gino)
sys.modules.setdefault("gino.crud", _mock_gino_crud)

from fastapi_pagination.ext.gino import apaginate, paginate  # noqa: E402


@pytest.mark.asyncio
async def test_apaginate_with_select_query(mocker):
    mock_result = MagicMock()
    mock_run_async_flow = mocker.patch(
        "fastapi_pagination.ext.gino.run_async_flow",
        new=AsyncMock(return_value=mock_result),
    )
    mocker.patch("fastapi_pagination.ext.gino.generic_flow", return_value=MagicMock())

    mock_query = MagicMock(spec=[])  # plain object, not a type/CRUDModel subclass
    result = await apaginate(mock_query)

    assert result is mock_result
    mock_run_async_flow.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_with_crud_model_class(mocker):
    mock_result = MagicMock()
    mock_run_async_flow = mocker.patch(
        "fastapi_pagination.ext.gino.run_async_flow",
        new=AsyncMock(return_value=mock_result),
    )
    mocker.patch("fastapi_pagination.ext.gino.generic_flow", return_value=MagicMock())

    class MockModel(_MockCRUDModel):
        query = MagicMock()

    # Patch issubclass so it recognises MockModel as a CRUDModel subclass
    original_issubclass = __builtins__["issubclass"] if isinstance(__builtins__, dict) else issubclass

    mocker.patch(
        "fastapi_pagination.ext.gino.CRUDModel",
        _MockCRUDModel,
    )

    result = await apaginate(MockModel)

    assert result is mock_result
    mock_run_async_flow.assert_called_once()


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate(mocker):
    mock_result = MagicMock()
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.gino.apaginate",
        new=AsyncMock(return_value=mock_result),
    )

    mock_query = MagicMock(spec=[])
    result = await paginate(mock_query)

    assert result is mock_result
    mock_apaginate.assert_called_once_with(
        mock_query,
        params=None,
        transformer=None,
        additional_data=None,
        config=None,
    )
