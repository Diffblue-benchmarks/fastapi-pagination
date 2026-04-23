"""Tests for fastapi_pagination.flow module."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest

from fastapi_pagination.flow import (
    _check_not_coro,
    async_flow,
    flow,
    flow_expr,
    run_async_flow,
    run_sync_flow,
    sync_flow,
)


def test_flow_returns_func():
    def my_gen() -> Generator[int, int, int]:
        x = yield 1
        return x

    result = flow(my_gen)
    assert result is my_gen


def test_flow_identity_decorator():
    @flow
    def my_flow(x: int) -> Generator[int, int, int]:
        val = yield x
        return val

    gen = my_flow(5)
    res = gen.send(None)
    assert res == 5
    try:
        gen.send(res)
    except StopIteration as exc:
        assert exc.value == 5


def test_check_not_coro_passes_for_int():
    _check_not_coro(42)


def test_check_not_coro_passes_for_string():
    _check_not_coro("hello")


def test_check_not_coro_passes_for_none():
    _check_not_coro(None)


def test_check_not_coro_raises_for_coroutine():
    async def coro() -> None:
        pass

    c = coro()
    with pytest.raises(TypeError, match="is not allowed in sync flow"):
        _check_not_coro(c)
    c.close()


def test_run_sync_flow_simple():
    def gen() -> Generator[int, int, int]:
        x = yield 10
        return x

    result = run_sync_flow(gen())
    assert result == 10


def test_run_sync_flow_multiple_yields():
    def gen() -> Generator[int, int, str]:
        a = yield 1
        b = yield a + 1
        return f"{a},{b}"

    result = run_sync_flow(gen())
    assert result == "1,2"


def test_run_sync_flow_raises_for_coroutine_yield():
    async def coro() -> int:
        return 42

    c = coro()

    def gen_yielding_coro() -> Generator[Any, Any, None]:
        yield c

    with pytest.raises(TypeError, match="is not allowed in sync flow"):
        run_sync_flow(gen_yielding_coro())
    c.close()


def test_run_sync_flow_exception_propagation():
    def gen() -> Generator[int, int, int]:
        try:
            x = yield 10
        except ValueError:
            return -1
        return x

    result = run_sync_flow(gen())
    assert result == 10


@pytest.mark.asyncio
async def test_run_async_flow_simple():
    def gen() -> Generator[int, int, int]:
        x = yield 10
        return x

    result = await run_async_flow(gen())
    assert result == 10


@pytest.mark.asyncio
async def test_run_async_flow_with_awaitable():
    async def fetch(val: int) -> int:
        return val * 2

    def gen() -> Generator[Any, int, int]:
        x = yield fetch(5)
        return x

    result = await run_async_flow(gen())
    assert result == 10


@pytest.mark.asyncio
async def test_run_async_flow_multiple_yields():
    async def double(val: int) -> int:
        return val * 2

    def gen() -> Generator[Any, int, str]:
        a = yield double(3)
        b = yield double(a)
        return f"{a},{b}"

    result = await run_async_flow(gen())
    assert result == "6,12"


@pytest.mark.asyncio
async def test_run_async_flow_with_non_awaitable():
    def gen() -> Generator[int, int, int]:
        x = yield 7
        return x + 1

    result = await run_async_flow(gen())
    assert result == 8


def test_sync_flow_decorator():
    @sync_flow
    def my_flow(x: int) -> Generator[int, int, int]:
        val = yield x
        return val * 2

    result = my_flow(5)
    assert result == 10


def test_sync_flow_preserves_function_name():
    @sync_flow
    def my_named_flow(x: int) -> Generator[int, int, int]:
        val = yield x
        return val

    assert my_named_flow.__name__ == "my_named_flow"


def test_sync_flow_with_kwargs():
    @sync_flow
    def my_flow(a: int, b: int = 1) -> Generator[int, int, int]:
        val = yield a + b
        return val

    result = my_flow(3, b=4)
    assert result == 7


@pytest.mark.asyncio
async def test_async_flow_decorator():
    @async_flow
    def my_flow(x: int) -> Generator[Any, Any, int]:
        val = yield x
        return val * 3

    result = await my_flow(4)
    assert result == 12


@pytest.mark.asyncio
async def test_async_flow_preserves_function_name():
    @async_flow
    def my_named_async_flow(x: int) -> Generator[Any, Any, int]:
        val = yield x
        return val

    assert my_named_async_flow.__name__ == "my_named_async_flow"


@pytest.mark.asyncio
async def test_async_flow_with_awaitable_yield():
    async def fetch(val: int) -> int:
        return val + 1

    @async_flow
    def my_flow(x: int) -> Generator[Any, Any, int]:
        val = yield fetch(x)
        return val

    result = await my_flow(9)
    assert result == 10


def test_flow_expr_with_sync_callable():
    def add(a: int, b: int) -> int:
        return a + b

    wrapped = flow_expr(add)
    result = run_sync_flow(wrapped(3, 4))
    assert result == 7


@pytest.mark.asyncio
async def test_flow_expr_with_async_callable():
    async def fetch(val: int) -> int:
        return val * 2

    expr_flow = flow_expr(fetch)
    result = await run_async_flow(expr_flow(5))
    assert result == 10


def test_flow_expr_preserves_function_name():
    def my_expr(x: int) -> int:
        return x

    wrapped = flow_expr(my_expr)
    assert wrapped.__name__ == "my_expr"


def test_flow_expr_returns_generator_function():
    def my_expr(x: int) -> int:
        return x * 2

    wrapped = flow_expr(my_expr)
    gen = wrapped(5)
    res = gen.send(None)
    assert res == 10
    try:
        gen.send(res)
    except StopIteration as exc:
        assert exc.value == 10
