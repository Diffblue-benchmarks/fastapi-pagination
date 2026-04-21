from __future__ import annotations

import warnings
from typing import Annotated

import pytest

import fastapi_pagination.utils as utils_module
from fastapi_pagination.default import Params
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


def test_getattr_raises_for_unknown():
    with pytest.raises(AttributeError, match="has no attribute"):
        utils_module.nonexistent_attribute_xyz_123


def test_verify_params_success():
    params = Params(page=1, size=10)
    result_params, raw = verify_params(params, "limit-offset")
    assert result_params is params
    assert raw.type == "limit-offset"


def test_verify_params_wrong_type():
    params = Params(page=1, size=10)
    with pytest.raises(ValueError, match="not supported"):
        verify_params(params, "cursor")


@pytest.mark.asyncio
async def test_await_if_async_with_async_func():
    async def async_func(x):
        return x * 2

    result = await await_if_async(async_func, 5)
    assert result == 10


@pytest.mark.asyncio
async def test_await_if_async_with_sync_func():
    def sync_func(x):
        return x * 3

    result = await await_if_async(sync_func, 4)
    assert result == 12


def test_is_coro_with_coroutine():
    async def coro():
        return 1

    c = coro()
    try:
        assert is_coro(c) is True
    finally:
        c.close()


def test_is_coro_with_non_coroutine():
    assert is_coro(42) is False
    assert is_coro("hello") is False


@pytest.mark.asyncio
async def test_await_if_coro_with_awaitable():
    async def coro():
        return 99

    result = await await_if_coro(coro())
    assert result == 99


@pytest.mark.asyncio
async def test_await_if_coro_with_non_awaitable():
    result = await await_if_coro(42)
    assert result == 42


def test_check_installed_existing_module():
    assert _check_installed("sys") is True


def test_check_installed_nonexistent_module():
    assert _check_installed("nonexistent_module_xyz_abc_999") is False


def test_disable_installed_extensions_check():
    original = utils_module._CHECK_INSTALLED_EXTENSIONS
    try:
        utils_module._CHECK_INSTALLED_EXTENSIONS = True
        disable_installed_extensions_check()
        assert utils_module._CHECK_INSTALLED_EXTENSIONS is False
    finally:
        utils_module._CHECK_INSTALLED_EXTENSIONS = original


def test_check_installed_extensions_disabled():
    original = utils_module._CHECK_INSTALLED_EXTENSIONS
    try:
        utils_module._CHECK_INSTALLED_EXTENSIONS = False
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_installed_extensions()
        assert len(w) == 0
    finally:
        utils_module._CHECK_INSTALLED_EXTENSIONS = original


def test_check_installed_extensions_with_installed(mocker):
    original = utils_module._CHECK_INSTALLED_EXTENSIONS
    try:
        utils_module._CHECK_INSTALLED_EXTENSIONS = True
        mocker.patch("fastapi_pagination.utils._check_installed", return_value=True)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_installed_extensions()
        assert len(w) == 1
        assert issubclass(w[0].category, FastAPIPaginationWarning)
    finally:
        utils_module._CHECK_INSTALLED_EXTENSIONS = original


def test_check_installed_extensions_none_installed(mocker):
    original = utils_module._CHECK_INSTALLED_EXTENSIONS
    try:
        utils_module._CHECK_INSTALLED_EXTENSIONS = True
        mocker.patch("fastapi_pagination.utils._check_installed", return_value=False)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_installed_extensions()
        assert len(w) == 0
    finally:
        utils_module._CHECK_INSTALLED_EXTENSIONS = original


def test_get_caller_returns_string():
    result = get_caller(depth=1)
    assert isinstance(result, str)


def test_get_caller_depth_0():
    result = get_caller(depth=0)
    assert result is not None
    assert "test_utils" in result or result == __name__


def test_get_caller_large_depth_returns_none():
    result = get_caller(depth=10000)
    assert result is None


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
