"""Tests for fastapi_pagination/ext/odmantic.py"""
import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from odmantic import AIOEngine, Model, SyncEngine

from fastapi_pagination.ext.odmantic import apaginate, paginate


class SampleModel(Model):
    name: str


@pytest.fixture
def sync_engine():
    engine = MagicMock(spec=SyncEngine)
    engine.find = MagicMock(return_value=[])
    engine.count = MagicMock(return_value=0)
    return engine


@pytest.fixture
def aio_engine():
    engine = MagicMock(spec=AIOEngine)
    engine.find = AsyncMock(return_value=[])
    engine.count = AsyncMock(return_value=0)
    return engine


@pytest.fixture
def pagination_context():
    from fastapi_pagination.api import set_page, set_params
    from fastapi_pagination.default import Page, Params

    params = Params(page=1, size=10)
    with set_page(Page):
        with set_params(params):
            yield params


def test_paginate_sync_engine_calls_run_sync_flow(mocker, sync_engine, pagination_context):
    mock_result = MagicMock()
    mock_run_sync = mocker.patch(
        "fastapi_pagination.ext.odmantic.run_sync_flow",
        return_value=mock_result,
    )
    mocker.patch("fastapi_pagination.ext.odmantic._paginate_flow", return_value=MagicMock())

    result = paginate(sync_engine, SampleModel)

    assert result is mock_result
    mock_run_sync.assert_called_once()


def test_paginate_aio_engine_warns_and_calls_apaginate(mocker, aio_engine, pagination_context):
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.odmantic.apaginate",
        return_value=MagicMock(),
    )

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        paginate(aio_engine, SampleModel)

    mock_apaginate.assert_called_once_with(
        aio_engine,
        SampleModel,
        sort=None,
        session=None,
        params=None,
        transformer=None,
        additional_data=None,
    )


def test_paginate_aio_engine_issues_deprecation_warning(mocker, aio_engine, pagination_context):
    mocker.patch("fastapi_pagination.ext.odmantic.apaginate", return_value=MagicMock())

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        paginate(aio_engine, SampleModel)

    deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
    assert len(deprecation_warnings) >= 1


@pytest.mark.asyncio
async def test_apaginate_calls_run_async_flow(mocker, aio_engine, pagination_context):
    mock_result = MagicMock()
    mock_run_async = mocker.patch(
        "fastapi_pagination.ext.odmantic.run_async_flow",
        new=AsyncMock(return_value=mock_result),
    )
    mocker.patch("fastapi_pagination.ext.odmantic._paginate_flow", return_value=MagicMock())

    result = await apaginate(aio_engine, SampleModel)

    assert result is mock_result
    mock_run_async.assert_called_once()


def test_limit_offset_flow_returns_list(mocker, sync_engine):
    from fastapi_pagination.bases import RawParams
    from fastapi_pagination.ext.odmantic import _limit_offset_flow
    from fastapi_pagination.flow import run_sync_flow

    items = [MagicMock(), MagicMock()]
    sync_engine.find = MagicMock(return_value=items)

    raw_params = RawParams(limit=10, offset=0, include_total=False)

    result = run_sync_flow(
        _limit_offset_flow(SampleModel, (), None, sync_engine, None, raw_params)
    )

    assert result == items


def test_paginate_flow_with_sync_engine(mocker, sync_engine, pagination_context):
    from fastapi_pagination.ext.odmantic import _paginate_flow
    from fastapi_pagination.flow import run_sync_flow

    items = [MagicMock(name="item1")]
    sync_engine.find = MagicMock(return_value=items)
    sync_engine.count = MagicMock(return_value=1)

    result = run_sync_flow(
        _paginate_flow(False, sync_engine, SampleModel)
    )

    assert result is not None


@pytest.mark.asyncio
async def test_paginate_flow_with_async_engine(mocker, aio_engine, pagination_context):
    from fastapi_pagination.ext.odmantic import _paginate_flow
    from fastapi_pagination.flow import run_async_flow

    items = [MagicMock(name="item1")]
    aio_engine.find = AsyncMock(return_value=items)
    aio_engine.count = AsyncMock(return_value=1)

    result = await run_async_flow(
        _paginate_flow(True, aio_engine, SampleModel)
    )

    assert result is not None
