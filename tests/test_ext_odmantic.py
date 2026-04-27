"""Tests for fastapi_pagination.ext.odmantic module."""
from __future__ import annotations

import sys
import types
import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Patch unavailable third-party modules before importing the module under test
# ---------------------------------------------------------------------------

def _install_odmantic_mocks() -> None:
    odmantic_mod = types.ModuleType("odmantic")
    odmantic_engine_mod = types.ModuleType("odmantic.engine")
    odmantic_query_mod = types.ModuleType("odmantic.query")

    # Classes used by the extension
    odmantic_mod.AIOEngine = MagicMock()
    odmantic_mod.Model = MagicMock()
    odmantic_mod.SyncEngine = MagicMock()
    odmantic_engine_mod.AIOSessionType = MagicMock()
    odmantic_engine_mod.SyncSessionType = MagicMock()
    odmantic_query_mod.QueryExpression = MagicMock()

    for name, mod in {
        "odmantic": odmantic_mod,
        "odmantic.engine": odmantic_engine_mod,
        "odmantic.query": odmantic_query_mod,
    }.items():
        if name not in sys.modules:
            sys.modules[name] = mod


_install_odmantic_mocks()


# ---------------------------------------------------------------------------
# _limit_offset_flow
# ---------------------------------------------------------------------------

def test_limit_offset_flow_yields_engine_find_and_returns_list():
    """_limit_offset_flow should yield engine.find result and return it as a list."""
    from fastapi_pagination.ext.odmantic import _limit_offset_flow

    model = MagicMock()
    queries = (MagicMock(),)
    sort = None
    session = None
    raw_params = MagicMock()
    raw_params.limit = 10
    raw_params.offset = 0

    expected_items = [MagicMock(), MagicMock()]
    engine = MagicMock()
    engine.find.return_value = expected_items

    gen = _limit_offset_flow(model, queries, sort, engine, session, raw_params)

    # First send(None) yields the engine.find call
    yielded = gen.send(None)

    # The yielded value should be the result of engine.find(...)
    assert yielded is expected_items

    # Send the result back; generator should return a list version
    with pytest.raises(StopIteration) as exc_info:
        gen.send(expected_items)

    assert exc_info.value.value == list(expected_items)


def test_limit_offset_flow_with_offset():
    """_limit_offset_flow should pass offset to engine.find skip parameter."""
    from fastapi_pagination.ext.odmantic import _limit_offset_flow

    model = MagicMock()
    queries = ()
    sort = MagicMock()
    session = MagicMock()
    raw_params = MagicMock()
    raw_params.limit = 5
    raw_params.offset = 20

    items = [MagicMock()]
    engine = MagicMock()
    engine.find.return_value = items

    gen = _limit_offset_flow(model, queries, sort, engine, session, raw_params)
    yielded = gen.send(None)

    assert yielded is items

    engine.find.assert_called_once_with(
        model,
        sort=sort,
        session=session,
        limit=5,
        skip=20,
    )


def test_limit_offset_flow_offset_none_defaults_to_zero():
    """_limit_offset_flow should use 0 when offset is None."""
    from fastapi_pagination.ext.odmantic import _limit_offset_flow

    model = MagicMock()
    queries = ()
    raw_params = MagicMock()
    raw_params.limit = 5
    raw_params.offset = None

    engine = MagicMock()
    engine.find.return_value = []

    gen = _limit_offset_flow(model, queries, None, engine, None, raw_params)
    gen.send(None)

    engine.find.assert_called_once_with(
        model,
        sort=None,
        session=None,
        limit=5,
        skip=0,
    )


# ---------------------------------------------------------------------------
# _paginate_flow
# ---------------------------------------------------------------------------

def test_paginate_flow_calls_generic_flow():
    """_paginate_flow should delegate to generic_flow."""
    mock_page = MagicMock()
    captured = {}

    def fake_generic_flow(**kwargs):
        captured.update(kwargs)
        # Return a simple generator that yields nothing and returns mock_page
        def _gen():
            return mock_page
            yield  # make it a generator
        return _gen()

    with patch("fastapi_pagination.ext.odmantic.generic_flow", side_effect=fake_generic_flow):
        from fastapi_pagination.ext.odmantic import _paginate_flow, run_sync_flow

        engine = MagicMock()
        model = MagicMock()

        result = run_sync_flow(_paginate_flow(False, engine, model))

    assert result is mock_page
    assert "async_" in captured
    assert captured["async_"] is False


def test_paginate_flow_async_true():
    """_paginate_flow with is_async=True should pass async_=True to generic_flow."""
    mock_page = MagicMock()
    captured = {}

    def fake_generic_flow(**kwargs):
        captured.update(kwargs)
        def _gen():
            return mock_page
            yield
        return _gen()

    with patch("fastapi_pagination.ext.odmantic.generic_flow", side_effect=fake_generic_flow):
        from fastapi_pagination.ext.odmantic import _paginate_flow, run_sync_flow

        engine = MagicMock()
        model = MagicMock()

        result = run_sync_flow(_paginate_flow(True, engine, model))

    assert result is mock_page
    assert captured["async_"] is True


# ---------------------------------------------------------------------------
# paginate
# ---------------------------------------------------------------------------

def test_paginate_with_sync_engine_calls_run_sync_flow():
    """paginate with SyncEngine should call run_sync_flow."""
    mock_page = MagicMock()

    class FakeAIOEngine:
        pass

    # sync_engine is NOT an instance of FakeAIOEngine
    sync_engine = MagicMock(spec=[])

    with (
        patch("fastapi_pagination.ext.odmantic.AIOEngine", FakeAIOEngine),
        patch("fastapi_pagination.ext.odmantic.run_sync_flow", return_value=mock_page) as mock_run,
        patch("fastapi_pagination.ext.odmantic._paginate_flow", return_value=MagicMock()),
    ):
        from fastapi_pagination.ext.odmantic import paginate

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = paginate(sync_engine, MagicMock())

    assert result is mock_page
    mock_run.assert_called_once()


def test_paginate_with_aio_engine_warns_and_calls_apaginate():
    """paginate with AIOEngine should warn and delegate to apaginate."""
    mock_coro = MagicMock()

    class FakeAIOEngine:
        pass

    aio_engine = FakeAIOEngine()
    model = MagicMock()

    with (
        patch("fastapi_pagination.ext.odmantic.AIOEngine", FakeAIOEngine),
        patch("fastapi_pagination.ext.odmantic.apaginate", return_value=mock_coro) as mock_ap,
    ):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            from fastapi_pagination.ext.odmantic import paginate
            result = paginate(aio_engine, model)

    mock_ap.assert_called_once()
    call_args = mock_ap.call_args
    assert call_args[0][0] is aio_engine
    assert call_args[0][1] is model


def test_paginate_with_aio_engine_issues_deprecation_warning():
    """paginate with AIOEngine should issue a DeprecationWarning."""
    class FakeAIOEngine:
        pass

    aio_engine = FakeAIOEngine()

    with (
        patch("fastapi_pagination.ext.odmantic.AIOEngine", FakeAIOEngine),
        patch("fastapi_pagination.ext.odmantic.apaginate", return_value=MagicMock()),
    ):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from fastapi_pagination.ext.odmantic import paginate
            paginate(aio_engine, MagicMock())

    deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
    assert len(deprecation_warnings) >= 1


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apaginate_calls_run_async_flow():
    """apaginate should call run_async_flow with _paginate_flow result."""
    mock_page = MagicMock()

    with (
        patch("fastapi_pagination.ext.odmantic.run_async_flow", new_callable=AsyncMock, return_value=mock_page) as mock_run,
        patch("fastapi_pagination.ext.odmantic._paginate_flow", return_value=MagicMock()) as mock_flow,
    ):
        from fastapi_pagination.ext.odmantic import apaginate

        engine = MagicMock()
        model = MagicMock()
        result = await apaginate(engine, model)

    assert result is mock_page
    mock_run.assert_awaited_once()


@pytest.mark.asyncio
async def test_apaginate_passes_kwargs_to_paginate_flow():
    """apaginate should forward sort, session, params, transformer, additional_data, config."""
    mock_page = MagicMock()
    captured_flow_args = {}

    def fake_paginate_flow(is_async, engine, model, *queries, **kwargs):
        captured_flow_args.update(kwargs)
        captured_flow_args["is_async"] = is_async
        return MagicMock()

    async def fake_run_async(gen):
        return mock_page

    with (
        patch("fastapi_pagination.ext.odmantic.run_async_flow", side_effect=fake_run_async),
        patch("fastapi_pagination.ext.odmantic._paginate_flow", side_effect=fake_paginate_flow),
    ):
        from fastapi_pagination.ext.odmantic import apaginate

        sort = MagicMock()
        session = MagicMock()
        params = MagicMock()
        transformer = MagicMock()
        additional_data = MagicMock()
        config = MagicMock()

        engine = MagicMock()
        model = MagicMock()
        result = await apaginate(
            engine,
            model,
            sort=sort,
            session=session,
            params=params,
            transformer=transformer,
            additional_data=additional_data,
            config=config,
        )

    assert result is mock_page
    assert captured_flow_args["is_async"] is True
    assert captured_flow_args["sort"] is sort
    assert captured_flow_args["session"] is session
    assert captured_flow_args["params"] is params
    assert captured_flow_args["transformer"] is transformer
    assert captured_flow_args["additional_data"] is additional_data
    assert captured_flow_args["config"] is config
