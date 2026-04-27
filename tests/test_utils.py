from __future__ import annotations

import warnings
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
)


# __getattr__

def test_getattr_unknown_raises_attribute_error():
    with pytest.raises(AttributeError, match="has no attribute 'nonexistent_attr'"):
        utils_module.__getattr__("nonexistent_attr")


# verify_params

def test_verify_params_correct_type():
    from fastapi_pagination.default import Params
    from fastapi_pagination.utils import verify_params

    params = Params(page=1, size=10)
    result_params, raw = verify_params(params, "limit-offset")
    assert result_params is params
    assert raw.type == "limit-offset"


def test_verify_params_wrong_type_raises():
    from fastapi_pagination.default import Params
    from fastapi_pagination.utils import verify_params

    params = Params(page=1, size=10)
    with pytest.raises(ValueError, match="not supported"):
        verify_params(params, "cursor")


# is_coro

def test_is_coro_with_coroutine():
    async def coro():
        return 1

    c = coro()
    assert is_coro(c) is True
    c.close()


def test_is_coro_with_plain_value():
    assert is_coro(42) is False
    assert is_coro("hello") is False
    assert is_coro(None) is False


# await_if_async

@pytest.mark.asyncio
async def test_await_if_async_with_sync_func():
    def sync_fn(x):
        return x * 2

    result = await await_if_async(sync_fn, 5)
    assert result == 10


@pytest.mark.asyncio
async def test_await_if_async_with_async_func():
    async def async_fn(x):
        return x + 1

    result = await await_if_async(async_fn, 3)
    assert result == 4


# await_if_coro

@pytest.mark.asyncio
async def test_await_if_coro_with_coroutine():
    async def coro():
        return 99

    result = await await_if_coro(coro())
    assert result == 99


@pytest.mark.asyncio
async def test_await_if_coro_with_plain_value():
    result = await await_if_coro(42)
    assert result == 42


# _check_installed

def test_check_installed_with_known_module():
    assert _check_installed("os") is True


def test_check_installed_with_unknown_module():
    assert _check_installed("nonexistent_module_xyz_abc_123") is False


# disable_installed_extensions_check and check_installed_extensions

def test_disable_installed_extensions_check(monkeypatch):
    monkeypatch.setattr(utils_module, "_CHECK_INSTALLED_EXTENSIONS", True)
    disable_installed_extensions_check()
    assert utils_module._CHECK_INSTALLED_EXTENSIONS is False
    monkeypatch.setattr(utils_module, "_CHECK_INSTALLED_EXTENSIONS", True)


def test_check_installed_extensions_when_disabled(monkeypatch):
    monkeypatch.setattr(utils_module, "_CHECK_INSTALLED_EXTENSIONS", False)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        check_installed_extensions()
    assert not any(issubclass(x.category, FastAPIPaginationWarning) for x in w)


def test_check_installed_extensions_warns_when_ext_installed(monkeypatch):
    monkeypatch.setattr(utils_module, "_CHECK_INSTALLED_EXTENSIONS", True)
    monkeypatch.setattr(utils_module, "_check_installed", lambda module: True)
    with pytest.warns(FastAPIPaginationWarning):
        check_installed_extensions()


def test_check_installed_extensions_no_warn_when_none_installed(monkeypatch):
    monkeypatch.setattr(utils_module, "_CHECK_INSTALLED_EXTENSIONS", True)
    monkeypatch.setattr(utils_module, "_check_installed", lambda module: False)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        check_installed_extensions()
    assert not any(issubclass(x.category, FastAPIPaginationWarning) for x in w)


# get_caller

def test_get_caller_returns_string():
    result = get_caller(depth=1)
    assert isinstance(result, str)


def test_get_caller_depth_exceeds_stack():
    result = get_caller(depth=9999)
    assert result is None


# unwrap_annotated

def test_unwrap_annotated_with_annotated_type():
    ann = Annotated[int, "metadata"]
    result = unwrap_annotated(ann)
    assert result is int


def test_unwrap_annotated_with_plain_type():
    assert unwrap_annotated(int) is int
    assert unwrap_annotated(str) is str


def test_unwrap_annotated_with_non_annotated_value():
    assert unwrap_annotated(42) == 42
