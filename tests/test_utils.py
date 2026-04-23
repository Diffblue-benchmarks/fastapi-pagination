import pytest
from typing import Annotated

import fastapi_pagination.utils as utils_module
from fastapi_pagination.limit_offset import LimitOffsetParams
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


@pytest.fixture
def restore_extensions_check():
    original = utils_module._CHECK_INSTALLED_EXTENSIONS
    yield
    utils_module._CHECK_INSTALLED_EXTENSIONS = original


# Tests for module __getattr__

def test_getattr_unknown_attribute_raises():
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = utils_module.nonexistent_attribute_xyz_abc


# Tests for verify_params

def test_verify_params_valid_type():
    params = LimitOffsetParams()
    result_params, raw_params = verify_params(params, "limit-offset")

    assert result_params is params
    assert raw_params.type == "limit-offset"


def test_verify_params_invalid_type_raises():
    params = LimitOffsetParams()

    with pytest.raises(ValueError, match="not supported"):
        verify_params(params, "cursor")


# Tests for await_if_async

@pytest.mark.asyncio
async def test_await_if_async_with_sync_function():
    def sync_func(x):
        return x * 2

    result = await await_if_async(sync_func, 5)

    assert result == 10


@pytest.mark.asyncio
async def test_await_if_async_with_async_function():
    async def async_func(x):
        return x * 2

    result = await await_if_async(async_func, 5)

    assert result == 10


# Tests for is_coro

def test_is_coro_with_coroutine():
    async def some_coro():
        return 42

    coro = some_coro()
    try:
        assert is_coro(coro) is True
    finally:
        coro.close()


def test_is_coro_with_plain_value():
    assert is_coro(42) is False


def test_is_coro_with_none():
    assert is_coro(None) is False


# Tests for await_if_coro

@pytest.mark.asyncio
async def test_await_if_coro_with_coroutine():
    async def my_coro():
        return 42

    result = await await_if_coro(my_coro())

    assert result == 42


@pytest.mark.asyncio
async def test_await_if_coro_with_plain_value():
    result = await await_if_coro(99)

    assert result == 99


# Tests for _check_installed

def test_check_installed_with_existing_module():
    assert _check_installed("os") is True


def test_check_installed_with_missing_module():
    assert _check_installed("nonexistent_module_xyz_12345") is False


# Tests for disable_installed_extensions_check

def test_disable_installed_extensions_check(restore_extensions_check):
    utils_module._CHECK_INSTALLED_EXTENSIONS = True

    disable_installed_extensions_check()

    assert utils_module._CHECK_INSTALLED_EXTENSIONS is False


# Tests for check_installed_extensions

def test_check_installed_extensions_when_disabled(restore_extensions_check):
    utils_module._CHECK_INSTALLED_EXTENSIONS = False

    check_installed_extensions()


def test_check_installed_extensions_warns_when_extension_found(mocker, restore_extensions_check):
    utils_module._CHECK_INSTALLED_EXTENSIONS = True
    mocker.patch.object(utils_module, "_check_installed", return_value=True)

    with pytest.warns(FastAPIPaginationWarning):
        check_installed_extensions()


def test_check_installed_extensions_no_warn_when_none_found(mocker, restore_extensions_check):
    utils_module._CHECK_INSTALLED_EXTENSIONS = True
    mocker.patch.object(utils_module, "_check_installed", return_value=False)

    check_installed_extensions()


# Tests for get_caller

def test_get_caller_depth_zero_returns_current_module():
    result = get_caller(depth=0)

    assert result == __name__


def test_get_caller_excessive_depth_returns_none():
    result = get_caller(depth=100000)

    assert result is None


# Tests for unwrap_annotated

def test_unwrap_annotated_with_annotated_type():
    ann = Annotated[int, "metadata"]
    result = unwrap_annotated(ann)

    assert result is int


def test_unwrap_annotated_with_plain_type():
    result = unwrap_annotated(str)

    assert result is str


def test_unwrap_annotated_with_none():
    result = unwrap_annotated(None)

    assert result is None
