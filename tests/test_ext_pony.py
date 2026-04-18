from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


def _make_pony_mock():
    pony_mock = ModuleType("pony")
    pony_orm_mock = ModuleType("pony.orm")
    pony_orm_core_mock = ModuleType("pony.orm.core")

    pony_orm_core_mock.Query = MagicMock

    pony_mock.orm = pony_orm_mock
    pony_orm_mock.core = pony_orm_core_mock

    return pony_mock, pony_orm_mock, pony_orm_core_mock


@pytest.fixture(autouse=True)
def mock_pony_modules():
    pony_mock, pony_orm_mock, pony_orm_core_mock = _make_pony_mock()
    modules_to_patch = {
        "pony": pony_mock,
        "pony.orm": pony_orm_mock,
        "pony.orm.core": pony_orm_core_mock,
    }
    with patch.dict(sys.modules, modules_to_patch):
        # Remove cached import of ext.pony if any
        sys.modules.pop("fastapi_pagination.ext.pony", None)
        yield
    sys.modules.pop("fastapi_pagination.ext.pony", None)


def _get_paginate():
    from fastapi_pagination.ext.pony import paginate
    return paginate


def test_paginate_calls_run_sync_flow():
    paginate = _get_paginate()

    mock_query = MagicMock()
    mock_query.count.return_value = 3
    mock_query.fetch.return_value.to_list.return_value = [1, 2, 3]

    with patch("fastapi_pagination.ext.pony.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.pony.generic_flow") as mock_generic:
        mock_run.return_value = "page_result"
        mock_generic.return_value = "flow_obj"

        result = paginate(mock_query)

        mock_generic.assert_called_once()
        mock_run.assert_called_once_with("flow_obj")
        assert result == "page_result"


def test_paginate_passes_kwargs_to_generic_flow():
    paginate = _get_paginate()

    mock_query = MagicMock()
    mock_transformer = MagicMock()
    mock_additional_data = {"key": "value"}
    mock_config = MagicMock()
    mock_params = MagicMock()

    with patch("fastapi_pagination.ext.pony.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.pony.generic_flow") as mock_generic:
        mock_run.return_value = "page_result"
        mock_generic.return_value = "flow_obj"

        result = paginate(
            mock_query,
            params=mock_params,
            transformer=mock_transformer,
            additional_data=mock_additional_data,
            config=mock_config,
        )

        call_kwargs = mock_generic.call_args.kwargs
        assert call_kwargs["params"] is mock_params
        assert call_kwargs["transformer"] is mock_transformer
        assert call_kwargs["additional_data"] is mock_additional_data
        assert call_kwargs["config"] is mock_config
        assert result == "page_result"
