from __future__ import annotations

import sys
from functools import partial
from unittest.mock import MagicMock

# Mock sqlalchemy and related modules before importing fastapi_pagination.ext.sqlalchemy
for _mod in [
    "sqlalchemy",
    "sqlalchemy.engine",
    "sqlalchemy.exc",
    "sqlalchemy.orm",
    "sqlalchemy.sql",
    "sqlalchemy.sql.elements",
    "sqlalchemy.ext",
    "sqlalchemy.ext.asyncio",
    "sqlalchemy.util",
    "sqlakeyset",
    "sqlakeyset.asyncio",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import pytest

from fastapi_pagination import Page, Params, set_page, set_params
from fastapi_pagination.ext.sqlalchemy import _sqlalchemy_flow
from fastapi_pagination.flow import run_async_flow, run_sync_flow


@pytest.fixture
def pagination_ctx():
    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            yield


def _make_simple_generator(return_value):
    """Returns a generator function that immediately returns return_value without yielding."""

    def gen_func(**kwargs):
        return return_value
        yield  # makes this a generator function

    return gen_func


def test_sqlalchemy_flow_sync_runs_and_returns_page(mocker, pagination_ctx):
    """Test _sqlalchemy_flow with is_async=False covers lines 346, 347, 350, 363"""
    expected_page = MagicMock()

    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.generic_flow",
        side_effect=_make_simple_generator(expected_page),
    )

    conn = MagicMock()
    query = MagicMock()

    gen = _sqlalchemy_flow(is_async=False, conn=conn, query=query)
    result = run_sync_flow(gen)

    assert result is expected_page


def test_sqlalchemy_flow_async_uses_greenlet_spawn(mocker, pagination_ctx):
    """Test _sqlalchemy_flow with is_async=True wraps create_page via greenlet_spawn (line 348)"""
    expected_page = MagicMock()
    captured_kwargs = {}

    def fake_generic_flow(**kwargs):
        captured_kwargs.update(kwargs)
        return expected_page
        yield  # makes this a generator function

    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.generic_flow",
        side_effect=fake_generic_flow,
    )

    conn = MagicMock()
    query = MagicMock()

    gen = _sqlalchemy_flow(is_async=True, conn=conn, query=query)
    result = run_sync_flow(gen)

    assert result is expected_page
    # When is_async=True, create_page_factory must be a partial wrapping greenlet_spawn
    create_page_factory = captured_kwargs.get("create_page_factory")
    assert create_page_factory is not None
    assert isinstance(create_page_factory, partial)


@pytest.mark.asyncio
async def test_sqlalchemy_flow_async_via_run_async_flow(mocker, pagination_ctx):
    """Test _sqlalchemy_flow with is_async=True executed through run_async_flow (lines 347, 348, 350, 363)"""
    expected_page = MagicMock()

    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.generic_flow",
        side_effect=_make_simple_generator(expected_page),
    )

    conn = MagicMock()
    query = MagicMock()

    gen = _sqlalchemy_flow(is_async=True, conn=conn, query=query)
    result = await run_async_flow(gen)

    assert result is expected_page


def test_sqlalchemy_flow_sync_passes_correct_kwargs_to_generic_flow(mocker, pagination_ctx):
    """Test _sqlalchemy_flow passes async_=False and correct params to generic_flow (line 350)"""
    expected_page = MagicMock()
    captured_kwargs = {}

    def fake_generic_flow(**kwargs):
        captured_kwargs.update(kwargs)
        return expected_page
        yield  # makes this a generator function

    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.generic_flow",
        side_effect=fake_generic_flow,
    )

    conn = MagicMock()
    query = MagicMock()
    params = Params(page=1, size=5)

    gen = _sqlalchemy_flow(is_async=False, conn=conn, query=query, params=params)
    result = run_sync_flow(gen)

    assert result is expected_page
    assert captured_kwargs["async_"] is False
    assert captured_kwargs["params"] is params


def test_sqlalchemy_flow_async_passes_async_true_to_generic_flow(mocker, pagination_ctx):
    """Test _sqlalchemy_flow with is_async=True passes async_=True to generic_flow (lines 347, 350)"""
    expected_page = MagicMock()
    captured_kwargs = {}

    def fake_generic_flow(**kwargs):
        captured_kwargs.update(kwargs)
        return expected_page
        yield  # makes this a generator function

    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.generic_flow",
        side_effect=fake_generic_flow,
    )

    conn = MagicMock()
    query = MagicMock()

    gen = _sqlalchemy_flow(is_async=True, conn=conn, query=query)
    run_sync_flow(gen)

    assert captured_kwargs["async_"] is True
