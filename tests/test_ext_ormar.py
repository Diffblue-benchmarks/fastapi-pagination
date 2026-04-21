import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock the ormar module before importing fastapi_pagination.ext.ormar
_ormar_mock = types.ModuleType("ormar")
_QuerySet = type("QuerySet", (), {"__class_getitem__": classmethod(lambda cls, item: cls)})
_Model = type("Model", (), {"__class_getitem__": classmethod(lambda cls, item: cls)})
_ormar_mock.QuerySet = _QuerySet
_ormar_mock.Model = _Model
sys.modules.setdefault("ormar", _ormar_mock)

# Ensure the ext.ormar module is not cached with a broken state
sys.modules.pop("fastapi_pagination.ext.ormar", None)

from fastapi_pagination import Params  # noqa: E402
from fastapi_pagination.ext.ormar import apaginate, paginate  # noqa: E402


@pytest.mark.asyncio
async def test_apaginate_with_queryset_instance():
    mock_qs = _QuerySet()

    with patch("fastapi_pagination.ext.ormar.run_async_flow", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = MagicMock()
        result = await apaginate(mock_qs, Params())

    mock_flow.assert_called_once()
    assert result is mock_flow.return_value


@pytest.mark.asyncio
async def test_apaginate_with_model_class_uses_objects():
    mock_qs = _QuerySet()
    mock_model = MagicMock()
    mock_model.objects = mock_qs

    with patch("fastapi_pagination.ext.ormar.run_async_flow", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = MagicMock()
        result = await apaginate(mock_model, Params())

    mock_flow.assert_called_once()
    assert result is mock_flow.return_value


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate():
    mock_qs = _QuerySet()

    with patch("fastapi_pagination.ext.ormar.apaginate", new_callable=AsyncMock) as mock_apaginate:
        mock_apaginate.return_value = MagicMock()
        result = await paginate(mock_qs, Params())

    mock_apaginate.assert_called_once_with(
        mock_qs,
        params=Params(),
        transformer=None,
        additional_data=None,
        config=None,
    )
    assert result is mock_apaginate.return_value
