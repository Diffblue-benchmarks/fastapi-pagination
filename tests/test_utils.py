from __future__ import annotations

import warnings
from typing import Annotated, Any

import pytest

import fastapi_pagination.utils as utils_module
from fastapi_pagination.bases import AbstractParams, BaseRawParams, CursorRawParams, RawParams
from fastapi_pagination.utils import (
    FastAPIPaginationWarning,
    await_if_async,
    await_if_coro,
    check_installed_extensions,
    disable_installed_extensions_check,
    get_caller,
    is_coro,
    unwrap_annotated,
    verify_params,
)
from fastapi_pagination.utils import _check_installed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _LimitOffsetParams(AbstractParams):
    __page_type__ = None

    def to_raw_params(self) -> BaseRawParams:
        return RawParams(limit=10, offset=0)


class _CursorParams(AbstractParams):
    __page_type__ = None

    def to_raw_params(self) -> BaseRawParams:
        return CursorRawParams(cursor=None, size=10)


# ---------------------------------------------------------------------------
# __getattr__
# ---------------------------------------------------------------------------


def test_getattr_raises_attribute_error_for_unknown():
    with pytest.raises(AttributeError, match="has no attribute"):
        utils_module.__getattr__("nonexistent_attribute_xyz")


# ---------------------------------------------------------------------------
# verify_params
# ---------------------------------------------------------------------------


def test_verify_params_limit_offset_type():
    params = _LimitOffsetParams()
    result_params, raw = verify_params(params, "limit-offset")
    assert result_params is params
    assert raw.type == "limit-offset"


def test_verify_params_cursor_type():
    params = _CursorParams()
    result_params, raw = verify_params(params, "cursor")
    assert result_params is params
    assert raw.type == "cursor"


def test_verify_params_raises_for_wrong_type():
    params = _LimitOffsetParams()
    with pytest.raises(ValueError, match="not supported"):
        verify_params(params, "cursor")


def test_verify_params_raises_for_cursor_as_limit_offset():
    params = _CursorParams()
    with pytest.raises(ValueError, match="not supported"):
        verify_params(params, "limit-offset")


# ---------------------------------------------------------------------------
# await_if_async
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_await_if_async_with_sync_function():
    def sync_func(x: int) -> int:
        return x * 2

    result = await await_if_async(sync_func, 5)
    assert result == 10


@pytest.mark.asyncio
async def test_await_if_async_with_async_function():
    async def async_func(x: int) -> int:
        return x * 3

    result = await await_if_async(async_func, 4)
    assert result == 12


@pytest.mark.asyncio
async def test_await_if_async_with_no_args():
    def zero_arg() -> str:
        return "hello"

    result = await await_if_async(zero_arg)
    assert result == "hello"


# ---------------------------------------------------------------------------
# is_coro
# ---------------------------------------------------------------------------


def test_is_coro_with_coroutine():
    async def my_coro() -> int:
        return 42

    coro = my_coro()
    try:
        assert is_coro(coro) is True
    finally:
        coro.close()


def test_is_coro_with_plain_int():
    assert is_coro(42) is False


def test_is_coro_with_string():
    assert is_coro("hello") is False


# ---------------------------------------------------------------------------
# await_if_coro
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_await_if_coro_with_coroutine():
    async def my_coro() -> int:
        return 99

    result = await await_if_coro(my_coro())
    assert result == 99


@pytest.mark.asyncio
async def test_await_if_coro_with_plain_value():
    result = await await_if_coro(42)
    assert result == 42


@pytest.mark.asyncio
async def test_await_if_coro_with_string_value():
    result = await await_if_coro("plain")
    assert result == "plain"


# ---------------------------------------------------------------------------
# _check_installed
# ---------------------------------------------------------------------------


def test_check_installed_returns_true_for_existing_module():
    assert _check_installed("os") is True


def test_check_installed_returns_false_for_missing_module():
    assert _check_installed("_nonexistent_module_xyz_abc_12345") is False


def test_check_installed_returns_true_for_sys():
    assert _check_installed("sys") is True


# ---------------------------------------------------------------------------
# disable_installed_extensions_check
# ---------------------------------------------------------------------------


def test_disable_installed_extensions_check():
    original = utils_module._CHECK_INSTALLED_EXTENSIONS
    try:
        disable_installed_extensions_check()
        assert utils_module._CHECK_INSTALLED_EXTENSIONS is False
    finally:
        utils_module._CHECK_INSTALLED_EXTENSIONS = original


# ---------------------------------------------------------------------------
# check_installed_extensions
# ---------------------------------------------------------------------------


def test_check_installed_extensions_skips_when_disabled():
    original = utils_module._CHECK_INSTALLED_EXTENSIONS
    try:
        utils_module._CHECK_INSTALLED_EXTENSIONS = False
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            check_installed_extensions()
        assert not any(issubclass(w.category, FastAPIPaginationWarning) for w in caught)
    finally:
        utils_module._CHECK_INSTALLED_EXTENSIONS = original


def test_check_installed_extensions_warns_when_ext_found(mocker):
    original = utils_module._CHECK_INSTALLED_EXTENSIONS
    try:
        utils_module._CHECK_INSTALLED_EXTENSIONS = True
        mocker.patch.object(utils_module, "_check_installed", return_value=True)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            check_installed_extensions()
        pagination_warns = [w for w in caught if issubclass(w.category, FastAPIPaginationWarning)]
        assert len(pagination_warns) == 1
    finally:
        utils_module._CHECK_INSTALLED_EXTENSIONS = original


def test_check_installed_extensions_no_warning_when_none_found(mocker):
    original = utils_module._CHECK_INSTALLED_EXTENSIONS
    try:
        utils_module._CHECK_INSTALLED_EXTENSIONS = True
        mocker.patch.object(utils_module, "_check_installed", return_value=False)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            check_installed_extensions()
        pagination_warns = [w for w in caught if issubclass(w.category, FastAPIPaginationWarning)]
        assert len(pagination_warns) == 0
    finally:
        utils_module._CHECK_INSTALLED_EXTENSIONS = original


# ---------------------------------------------------------------------------
# get_caller
# ---------------------------------------------------------------------------


def test_get_caller_returns_string():
    result = get_caller()
    assert result is None or isinstance(result, str)


def test_get_caller_depth_zero_returns_module_name():
    result = get_caller(depth=0)
    # depth=0 means 1 frame up from get_caller, which is this test module
    assert result is not None
    assert isinstance(result, str)


def test_get_caller_large_depth_returns_none():
    result = get_caller(depth=100000)
    assert result is None


def test_get_caller_depth_one():
    result = get_caller(depth=1)
    # May be a string or None depending on call stack depth
    assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# unwrap_annotated
# ---------------------------------------------------------------------------


def test_unwrap_annotated_unwraps_annotated_type():
    ann = Annotated[int, "some metadata"]
    result = unwrap_annotated(ann)
    assert result is int


def test_unwrap_annotated_returns_plain_type_unchanged():
    result = unwrap_annotated(str)
    assert result is str


def test_unwrap_annotated_returns_none_unchanged():
    result = unwrap_annotated(None)
    assert result is None


def test_unwrap_annotated_with_multiple_metadata():
    ann = Annotated[str, "first", "second"]
    result = unwrap_annotated(ann)
    assert result is str
