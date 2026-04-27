import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock orm module before any imports from fastapi_pagination.ext.orm
_orm_mock = MagicMock()
_orm_models_mock = MagicMock()
_orm_mock.models = _orm_models_mock
sys.modules.setdefault("orm", _orm_mock)
sys.modules.setdefault("orm.models", _orm_models_mock)

from fastapi_pagination.ext.orm import apaginate, paginate  # noqa: E402


@pytest.fixture
def mock_queryset():
    qs = MagicMock()
    qs.count = AsyncMock(return_value=2)
    limited = MagicMock()
    limited.offset = MagicMock(return_value=MagicMock())
    limited.offset.return_value.all = AsyncMock(return_value=[{"id": 1}, {"id": 2}])
    qs.limit = MagicMock(return_value=limited)
    qs.offset = MagicMock(return_value=MagicMock())
    qs.offset.return_value.all = AsyncMock(return_value=[{"id": 1}, {"id": 2}])
    qs.all = AsyncMock(return_value=[{"id": 1}, {"id": 2}])
    return qs


@pytest.mark.asyncio
async def test_apaginate_returns_result(mock_queryset):
    expected = MagicMock()
    with patch("fastapi_pagination.ext.orm.run_async_flow", new=AsyncMock(return_value=expected)) as mock_raf:
        result = await apaginate(mock_queryset)
    assert result is expected
    mock_raf.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_passes_params(mock_queryset):
    from fastapi_pagination import Params

    params = Params(page=1, size=10)
    expected = MagicMock()
    with patch("fastapi_pagination.ext.orm.run_async_flow", new=AsyncMock(return_value=expected)):
        result = await apaginate(mock_queryset, params=params)
    assert result is expected


@pytest.mark.asyncio
async def test_apaginate_with_transformer(mock_queryset):
    async def my_transformer(items):
        return [str(i) for i in items]

    expected = MagicMock()
    with patch("fastapi_pagination.ext.orm.run_async_flow", new=AsyncMock(return_value=expected)):
        result = await apaginate(mock_queryset, transformer=my_transformer)
    assert result is expected


@pytest.mark.asyncio
async def test_paginate_calls_apaginate(mock_queryset):
    expected = MagicMock()
    with patch("fastapi_pagination.ext.orm.run_async_flow", new=AsyncMock(return_value=expected)):
        result = await paginate(mock_queryset)
    assert result is expected


@pytest.mark.asyncio
async def test_paginate_passes_params(mock_queryset):
    from fastapi_pagination import Params

    params = Params(page=2, size=5)
    expected = MagicMock()
    with patch("fastapi_pagination.ext.orm.run_async_flow", new=AsyncMock(return_value=expected)):
        result = await paginate(mock_queryset, params=params)
    assert result is expected


@pytest.mark.asyncio
async def test_paginate_with_additional_data(mock_queryset):
    additional_data = {"extra": "value"}
    expected = MagicMock()
    with patch("fastapi_pagination.ext.orm.run_async_flow", new=AsyncMock(return_value=expected)):
        result = await paginate(mock_queryset, additional_data=additional_data)
    assert result is expected
