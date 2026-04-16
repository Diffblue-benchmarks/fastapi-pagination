import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _setup_gino_mock():
    """Inject mock gino modules into sys.modules so the extension can be imported."""
    gino_mod = ModuleType("gino")
    gino_crud_mod = ModuleType("gino.crud")

    class CRUDModel:
        pass

    gino_crud_mod.CRUDModel = CRUDModel
    gino_mod.crud = gino_crud_mod

    sys.modules.setdefault("gino", gino_mod)
    sys.modules.setdefault("gino.crud", gino_crud_mod)
    return CRUDModel


_CRUDModel = _setup_gino_mock()

from fastapi_pagination import Params  # noqa: E402
from fastapi_pagination.ext.gino import apaginate, paginate  # noqa: E402


@pytest.mark.asyncio
async def test_apaginate_with_select_query():
    mock_query = MagicMock()
    mock_page = MagicMock()

    with patch("fastapi_pagination.ext.gino.run_async_flow", new=AsyncMock(return_value=mock_page)):
        result = await apaginate(mock_query, params=Params(page=1, size=10))

    assert result is mock_page


@pytest.mark.asyncio
async def test_apaginate_with_crud_model_class():
    """Tests the isinstance branch (lines 30-31) where query is a CRUDModel subclass."""

    class MyModel(_CRUDModel):
        query = MagicMock()

    mock_page = MagicMock()

    with patch("fastapi_pagination.ext.gino.run_async_flow", new=AsyncMock(return_value=mock_page)):
        result = await apaginate(MyModel, params=Params(page=1, size=10))

    assert result is mock_page


@pytest.mark.asyncio
async def test_apaginate_with_none_params():
    mock_query = MagicMock()
    mock_page = MagicMock()

    with patch("fastapi_pagination.ext.gino.run_async_flow", new=AsyncMock(return_value=mock_page)):
        result = await apaginate(mock_query)

    assert result is mock_page


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate():
    """Tests that paginate (lines 58, 66) delegates to apaginate."""
    mock_query = MagicMock()
    mock_page = MagicMock()
    params = Params(page=1, size=5)

    with patch("fastapi_pagination.ext.gino.apaginate", new=AsyncMock(return_value=mock_page)) as mock_apaginate:
        result = await paginate(mock_query, params=params)

    assert result is mock_page
    mock_apaginate.assert_awaited_once_with(
        mock_query,
        params=params,
        transformer=None,
        additional_data=None,
        config=None,
    )


@pytest.mark.asyncio
async def test_paginate_passes_kwargs():
    mock_query = MagicMock()
    mock_page = MagicMock()
    transformer = MagicMock()
    additional_data = {"extra": "data"}

    with patch("fastapi_pagination.ext.gino.apaginate", new=AsyncMock(return_value=mock_page)) as mock_apaginate:
        result = await paginate(
            mock_query,
            params=Params(page=2, size=20),
            transformer=transformer,
            additional_data=additional_data,
        )

    assert result is mock_page
    mock_apaginate.assert_awaited_once()
    call_kwargs = mock_apaginate.call_args.kwargs
    assert call_kwargs["transformer"] is transformer
    assert call_kwargs["additional_data"] is additional_data
