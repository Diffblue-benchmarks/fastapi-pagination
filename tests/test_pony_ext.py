import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


def _make_pony_mock():
    """Create a minimal mock of the pony.orm.core module."""
    pony_mock = ModuleType("pony")
    pony_orm_mock = ModuleType("pony.orm")
    pony_orm_core_mock = ModuleType("pony.orm.core")
    pony_orm_core_mock.Query = MagicMock()
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
        # Reload the ext module so it picks up mocked pony
        if "fastapi_pagination.ext.pony" in sys.modules:
            del sys.modules["fastapi_pagination.ext.pony"]
        yield


def test_paginate_calls_run_sync_flow():
    from fastapi_pagination.ext.pony import paginate

    mock_query = MagicMock()
    mock_result = MagicMock()

    with patch("fastapi_pagination.ext.pony.run_sync_flow", return_value=mock_result) as mock_rsf:
        result = paginate(mock_query)

    assert result is mock_result
    mock_rsf.assert_called_once()


def test_paginate_returns_run_sync_flow_result():
    from fastapi_pagination.ext.pony import paginate

    mock_query = MagicMock()
    expected = {"items": [], "total": 0}

    with patch("fastapi_pagination.ext.pony.run_sync_flow", return_value=expected):
        result = paginate(mock_query)

    assert result == expected
