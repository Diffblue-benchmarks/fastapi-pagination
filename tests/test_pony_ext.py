from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest


def _install_pony_mock():
    """Install mock pony modules into sys.modules so the ext can be imported."""
    pony_mod = ModuleType("pony")
    pony_orm_mod = ModuleType("pony.orm")
    pony_orm_core_mod = ModuleType("pony.orm.core")

    mock_query_cls = MagicMock()
    pony_orm_core_mod.Query = mock_query_cls

    sys.modules.setdefault("pony", pony_mod)
    sys.modules.setdefault("pony.orm", pony_orm_mod)
    sys.modules.setdefault("pony.orm.core", pony_orm_core_mod)

    pony_mod.orm = pony_orm_mod
    pony_orm_mod.core = pony_orm_core_mod


_install_pony_mock()

from fastapi_pagination.ext.pony import paginate  # noqa: E402


class TestPaginate:
    def test_paginate_returns_result(self, mocker):
        mock_result = MagicMock()
        mocker.patch("fastapi_pagination.ext.pony.run_sync_flow", return_value=mock_result)
        mocker.patch("fastapi_pagination.ext.pony.generic_flow", return_value=MagicMock())

        mock_query = MagicMock()
        result = paginate(mock_query)

        assert result == mock_result

    def test_paginate_calls_run_sync_flow(self, mocker):
        mock_run = mocker.patch("fastapi_pagination.ext.pony.run_sync_flow", return_value=MagicMock())
        mock_flow = MagicMock()
        mocker.patch("fastapi_pagination.ext.pony.generic_flow", return_value=mock_flow)

        mock_query = MagicMock()
        paginate(mock_query)

        mock_run.assert_called_once_with(mock_flow)

    def test_paginate_passes_params_to_generic_flow(self, mocker):
        mocker.patch("fastapi_pagination.ext.pony.run_sync_flow", return_value=MagicMock())
        mock_generic = mocker.patch("fastapi_pagination.ext.pony.generic_flow", return_value=MagicMock())

        mock_query = MagicMock()
        mock_params = MagicMock()
        paginate(mock_query, params=mock_params)

        call_kwargs = mock_generic.call_args.kwargs
        assert call_kwargs["params"] == mock_params

    def test_paginate_passes_transformer_to_generic_flow(self, mocker):
        mocker.patch("fastapi_pagination.ext.pony.run_sync_flow", return_value=MagicMock())
        mock_generic = mocker.patch("fastapi_pagination.ext.pony.generic_flow", return_value=MagicMock())

        mock_query = MagicMock()
        mock_transformer = MagicMock()
        paginate(mock_query, transformer=mock_transformer)

        call_kwargs = mock_generic.call_args.kwargs
        assert call_kwargs["transformer"] == mock_transformer

    def test_paginate_passes_additional_data_to_generic_flow(self, mocker):
        mocker.patch("fastapi_pagination.ext.pony.run_sync_flow", return_value=MagicMock())
        mock_generic = mocker.patch("fastapi_pagination.ext.pony.generic_flow", return_value=MagicMock())

        mock_query = MagicMock()
        additional = {"key": "value"}
        paginate(mock_query, additional_data=additional)

        call_kwargs = mock_generic.call_args.kwargs
        assert call_kwargs["additional_data"] == additional

    def test_paginate_passes_config_to_generic_flow(self, mocker):
        mocker.patch("fastapi_pagination.ext.pony.run_sync_flow", return_value=MagicMock())
        mock_generic = mocker.patch("fastapi_pagination.ext.pony.generic_flow", return_value=MagicMock())

        mock_query = MagicMock()
        mock_config = MagicMock()
        paginate(mock_query, config=mock_config)

        call_kwargs = mock_generic.call_args.kwargs
        assert call_kwargs["config"] == mock_config
