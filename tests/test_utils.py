"""Unit tests for fastapi_pagination.utils"""
from __future__ import annotations

import asyncio
from typing import Annotated

import pytest

import fastapi_pagination.utils as utils_module
from fastapi_pagination.utils import (
    FastAPIPaginationWarning,
    _check_installed,
    _CHECK_INSTALLED_EXTENSIONS,
    await_if_async,
    await_if_coro,
    check_installed_extensions,
    disable_installed_extensions_check,
    get_caller,
    is_coro,
    unwrap_annotated,
    verify_params,
)


# ---------------------------------------------------------------------------
# __getattr__
# ---------------------------------------------------------------------------

def test_getattr_unknown_raises():
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = utils_module.nonexistent_attribute_xyz  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# verify_params
# ---------------------------------------------------------------------------

def test_verify_params_limit_offset():
    from fastapi_pagination.default import Params
    from fastapi_pagination.api import set_params

    params = Params(page=1, size=10)
    with set_params(params):
        result_params, raw = verify_params(None, "limit-offset")
        assert raw.type == "limit-offset"
        assert raw.limit == 10


def test_verify_params_wrong_type_raises():
    from fastapi_pagination.default import Params
    from fastapi_pagination.api import set_params

    params = Params(page=1, size=10)
    with set_params(params):
        with pytest.raises(ValueError, match="not supported"):
            verify_params(None, "cursor")


# ---------------------------------------------------------------------------
# await_if_async
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_await_if_async_with_sync_func():
    def sync_func(x: int) -> int:
        return x * 2

    result = await await_if_async(sync_func, 5)
    assert result == 10


@pytest.mark.asyncio
async def test_await_if_async_with_async_func():
    async def async_func(x: int) -> int:
        return x * 3

    result = await await_if_async(async_func, 4)
    assert result == 12


# ---------------------------------------------------------------------------
# is_coro
# ---------------------------------------------------------------------------

def test_is_coro_with_coroutine():
    async def _coro():
        pass

    coro = _coro()
    assert is_coro(coro) is True
    coro.close()


def test_is_coro_with_non_awaitable():
    assert is_coro(42) is False
    assert is_coro("hello") is False


# ---------------------------------------------------------------------------
# await_if_coro
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_await_if_coro_with_coroutine():
    async def _coro():
        return 99

    result = await await_if_coro(_coro())
    assert result == 99


@pytest.mark.asyncio
async def test_await_if_coro_with_plain_value():
    result = await await_if_coro(42)
    assert result == 42


# ---------------------------------------------------------------------------
# _check_installed
# ---------------------------------------------------------------------------

def test_check_installed_existing_module():
    assert _check_installed("os") is True


def test_check_installed_missing_module():
    assert _check_installed("nonexistent_module_xyz_abc_123") is False


# ---------------------------------------------------------------------------
# disable_installed_extensions_check
# ---------------------------------------------------------------------------

def test_disable_installed_extensions_check(monkeypatch):
    monkeypatch.setattr(utils_module, "_CHECK_INSTALLED_EXTENSIONS", True)
    disable_installed_extensions_check()
    assert utils_module._CHECK_INSTALLED_EXTENSIONS is False
    # restore
    monkeypatch.setattr(utils_module, "_CHECK_INSTALLED_EXTENSIONS", True)


# ---------------------------------------------------------------------------
# check_installed_extensions
# ---------------------------------------------------------------------------

def test_check_installed_extensions_no_warning_when_disabled(monkeypatch):
    monkeypatch.setattr(utils_module, "_CHECK_INSTALLED_EXTENSIONS", False)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error", FastAPIPaginationWarning)
        # Should NOT raise/warn when disabled
        check_installed_extensions()


def test_check_installed_extensions_warns_for_installed(monkeypatch):
    monkeypatch.setattr(utils_module, "_CHECK_INSTALLED_EXTENSIONS", True)
    # Make _check_installed always return True for any extension
    monkeypatch.setattr(utils_module, "_check_installed", lambda mod: True)
    with pytest.warns(FastAPIPaginationWarning):
        check_installed_extensions()


def test_check_installed_extensions_no_warn_when_none_installed(monkeypatch):
    monkeypatch.setattr(utils_module, "_CHECK_INSTALLED_EXTENSIONS", True)
    monkeypatch.setattr(utils_module, "_check_installed", lambda mod: False)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error", FastAPIPaginationWarning)
        check_installed_extensions()  # should not raise


# ---------------------------------------------------------------------------
# get_caller
# ---------------------------------------------------------------------------

def test_get_caller_default_depth():
    result = get_caller(depth=1)
    assert result is not None
    assert isinstance(result, str)


def test_get_caller_excessive_depth():
    result = get_caller(depth=9999)
    assert result is None


# ---------------------------------------------------------------------------
# unwrap_annotated
# ---------------------------------------------------------------------------

def test_unwrap_annotated_with_annotated():
    ann = Annotated[int, "some metadata"]
    result = unwrap_annotated(ann)
    assert result is int


def test_unwrap_annotated_with_plain_type():
    result = unwrap_annotated(str)
    assert result is str


def test_unwrap_annotated_with_non_type():
    result = unwrap_annotated(42)
    assert result == 42
