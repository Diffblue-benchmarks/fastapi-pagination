import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set up gino and sqlalchemy mocks before importing the gino extension module
_CRUDModelBase = type("CRUDModel", (), {})
_gino_crud_mock = MagicMock()
_gino_crud_mock.CRUDModel = _CRUDModelBase
_gino_module_mock = MagicMock()
_gino_module_mock.crud = _gino_crud_mock
sys.modules["gino"] = _gino_module_mock
sys.modules["gino.crud"] = _gino_crud_mock

_sqlalchemy_mock = MagicMock()
_sqlalchemy_sql_mock = MagicMock()
sys.modules.setdefault("sqlalchemy", _sqlalchemy_mock)
sys.modules.setdefault("sqlalchemy.sql", _sqlalchemy_sql_mock)

_create_paginate_query_mock = MagicMock()
_sqlalchemy_ext_mock = MagicMock()
_sqlalchemy_ext_mock.create_paginate_query = _create_paginate_query_mock
sys.modules["fastapi_pagination.ext.sqlalchemy"] = _sqlalchemy_ext_mock

import importlib

if "fastapi_pagination.ext.gino" in sys.modules:
    _gino_ext = importlib.reload(sys.modules["fastapi_pagination.ext.gino"])
else:
    import fastapi_pagination.ext.gino as _gino_ext

apaginate = _gino_ext.apaginate
paginate = _gino_ext.paginate

from fastapi_pagination.api import set_params
from fastapi_pagination.default import Params


@pytest.mark.asyncio
@patch("fastapi_pagination.ext.gino.run_async_flow", new_callable=AsyncMock)
@patch("fastapi_pagination.ext.gino.generic_flow")
async def test_apaginate_with_select_query(mock_generic_flow, mock_run_async_flow):
    mock_page = MagicMock()
    mock_run_async_flow.return_value = mock_page
    mock_flow = MagicMock()
    mock_generic_flow.return_value = mock_flow

    mock_query = MagicMock()
    params = Params(page=1, size=10)

    with set_params(params):
        with pytest.warns(DeprecationWarning):
            result = await apaginate(mock_query)

    assert result == mock_page
    mock_run_async_flow.assert_called_once_with(mock_flow)
    mock_generic_flow.assert_called_once()


@pytest.mark.asyncio
@patch("fastapi_pagination.ext.gino.run_async_flow", new_callable=AsyncMock)
@patch("fastapi_pagination.ext.gino.generic_flow")
async def test_apaginate_with_crud_model_class(mock_generic_flow, mock_run_async_flow):
    mock_page = MagicMock()
    mock_run_async_flow.return_value = mock_page
    mock_flow = MagicMock()
    mock_generic_flow.return_value = mock_flow

    class MyModel(_CRUDModelBase):
        query = MagicMock()

    params = Params(page=1, size=10)

    with set_params(params):
        with pytest.warns(DeprecationWarning):
            result = await apaginate(MyModel)

    assert result == mock_page
    mock_run_async_flow.assert_called_once_with(mock_flow)
    mock_generic_flow.assert_called_once()


@pytest.mark.asyncio
@patch("fastapi_pagination.ext.gino.run_async_flow", new_callable=AsyncMock)
@patch("fastapi_pagination.ext.gino.generic_flow")
async def test_paginate_delegates_to_apaginate(mock_generic_flow, mock_run_async_flow):
    mock_page = MagicMock()
    mock_run_async_flow.return_value = mock_page
    mock_flow = MagicMock()
    mock_generic_flow.return_value = mock_flow

    mock_query = MagicMock()
    params = Params(page=1, size=10)

    with set_params(params):
        with pytest.warns(DeprecationWarning):
            result = await paginate(mock_query)

    assert result == mock_page
    mock_run_async_flow.assert_called_once_with(mock_flow)
