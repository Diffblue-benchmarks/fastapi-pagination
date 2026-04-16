from __future__ import annotations

import asyncio
from typing import Annotated

import pytest

import fastapi_pagination.utils as utils_module
from fastapi_pagination.utils import (
    FastAPIPaginationWarning,
    _check_installed,
    await_if_async,
    await_if_coro,
    check_installed_extensions,
    disable_installed_extensions_check,
    get_caller,
    is_coro,
    unwrap_annotated,
    verify_params,
)


# ---- __getattr__ ----

def test_getattr_unknown_attribute_raises():
    with pytest.raises(AttributeError, match="has no attribute 'nonexistent_attr'"):
        utils_module.nonexistent_attr  # noqa: B018


# ---- verify_params ----

def test_verify_params_valid_type():
    from fastapi_pagination.limit_offset import LimitOffsetParams

    params = LimitOffsetParams(limit=10, offset=0)
    result_params, raw = verify_params(params, "limit-offset")
    assert result_params is params
    assert raw.type == "limit-offset"


def test_verify_params_invalid_type_raises():
    from fastapi_pagination.limit_offset import LimitOffsetParams

    params = LimitOffsetParams(limit=10, offset=0)
    with pytest.raises(ValueError, match="not supported"):
        verify_params(params, "cursor")


# ---- await_if_async ----

@pytest.mark.asyncio
async def test_await_if_async_with_sync_func():
    def sync_func(x):
        return x * 2

    result = await await_if_async(sync_func, 5)
    assert result == 10


@pytest.mark.asyncio
async def test_await_if_async_with_async_func():
    async def async_func(x):
        return x * 3

    result = await await_if_async(async_func, 4)
    assert result == 12


# ---- is_coro ----

def test_is_coro_with_coroutine():
    async def my_coro():
        return 1

    coro = my_coro()
    try:
        assert is_coro(coro) is True
    finally:
        coro.close()


def test_is_coro_with_non_awaitable():
    assert is_coro(42) is False
    assert is_coro("hello") is False


# ---- await_if_coro ----

@pytest.mark.asyncio
async def test_await_if_coro_with_awaitable():
    async def my_coro():
        return 99

    result = await await_if_coro(my_coro())
    assert result == 99


@pytest.mark.asyncio
async def test_await_if_coro_with_plain_value():
    result = await await_if_coro(42)
    assert result == 42


# ---- _check_installed ----

def test_check_installed_existing_module():
    assert _check_installed("os") is True


def test_check_installed_nonexistent_module():
    assert _check_installed("_nonexistent_module_xyz_abc") is False


# ---- disable_installed_extensions_check ----

def test_disable_installed_extensions_check(mocker):
    mocker.patch.object(utils_module, "_CHECK_INSTALLED_EXTENSIONS", True)
    disable_installed_extensions_check()
    assert utils_module._CHECK_INSTALLED_EXTENSIONS is False
    # restore
    utils_module._CHECK_INSTALLED_EXTENSIONS = True


# ---- check_installed_extensions ----

def test_check_installed_extensions_disabled(mocker):
    mocker.patch.object(utils_module, "_CHECK_INSTALLED_EXTENSIONS", False)
    mock_check = mocker.patch.object(utils_module, "_check_installed")
    check_installed_extensions()
    mock_check.assert_not_called()


def test_check_installed_extensions_warns_when_extension_installed(mocker):
    mocker.patch.object(utils_module, "_CHECK_INSTALLED_EXTENSIONS", True)
    mocker.patch.object(utils_module, "_check_installed", return_value=True)
    with pytest.warns(FastAPIPaginationWarning):
        check_installed_extensions()


def test_check_installed_extensions_no_warning_when_none_installed(mocker):
    mocker.patch.object(utils_module, "_CHECK_INSTALLED_EXTENSIONS", True)
    mocker.patch.object(utils_module, "_check_installed", return_value=False)
    import warnings as _warnings
    with _warnings.catch_warnings(record=True) as record:
        _warnings.simplefilter("always")
        check_installed_extensions()
    pagination_warnings = [w for w in record if issubclass(w.category, FastAPIPaginationWarning)]
    assert len(pagination_warnings) == 0


# ---- get_caller ----

def test_get_caller_returns_string():
    result = get_caller(depth=1)
    assert result is not None
    assert isinstance(result, str)


def test_get_caller_depth_zero():
    result = get_caller(depth=0)
    # depth=0 returns the caller of get_caller, which is this test module
    assert result is not None
    assert isinstance(result, str)


def test_get_caller_large_depth_returns_none():
    result = get_caller(depth=10000)
    assert result is None


# ---- unwrap_annotated ----

def test_unwrap_annotated_with_annotated():
    ann = Annotated[int, "metadata"]
    result = unwrap_annotated(ann)
    assert result is int


def test_unwrap_annotated_with_plain_type():
    result = unwrap_annotated(str)
    assert result is str


def test_unwrap_annotated_with_non_annotated():
    result = unwrap_annotated(42)
    assert result == 42
