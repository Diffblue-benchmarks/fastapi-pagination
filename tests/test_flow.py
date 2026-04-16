import asyncio
from collections.abc import Awaitable, Generator
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


def test_flow_returns_function():
    def my_gen() -> Generator[Any, Any, int]:
        yield 1
        return 42

    result = flow(my_gen)
    assert result is my_gen


def test_check_not_coro_raises_for_coroutine():
    async def coro():
        pass

    c = coro()
    try:
        with pytest.raises(TypeError, match="Coroutine"):
            _check_not_coro(c)
    finally:
        c.close()


def test_check_not_coro_passes_for_non_coroutine():
    _check_not_coro(42)
    _check_not_coro("string")
    _check_not_coro(None)
    _check_not_coro([1, 2, 3])


def test_run_sync_flow_simple():
    def simple_gen() -> Generator[Any, Any, int]:
        yield 1
        return 42

    result = run_sync_flow(simple_gen())
    assert result == 42


def test_run_sync_flow_multiple_yields():
    def multi_yield_gen() -> Generator[Any, Any, str]:
        a = yield 1
        b = yield a + 1
        return f"result:{b}"

    result = run_sync_flow(multi_yield_gen())
    assert result == "result:2"


def test_run_sync_flow_raises_for_coroutine_yield():
    async def coro():
        return 1

    def bad_gen() -> Generator[Any, Any, None]:
        yield coro()

    with pytest.raises(TypeError, match="Coroutine"):
        run_sync_flow(bad_gen())


def test_run_sync_flow_propagates_exception():
    def exc_gen() -> Generator[Any, Any, None]:
        yield 1
        raise ValueError("test error")

    with pytest.raises(ValueError, match="test error"):
        run_sync_flow(exc_gen())


@pytest.mark.asyncio
async def test_run_async_flow_simple():
    def simple_gen() -> Generator[Any, Any, int]:
        yield 1
        return 42

    result = await run_async_flow(simple_gen())
    assert result == 42


@pytest.mark.asyncio
async def test_run_async_flow_with_awaitable():
    async def async_val():
        return 10

    def gen_with_awaitable() -> Generator[Any, Any, int]:
        val = yield async_val()
        return val * 2

    result = await run_async_flow(gen_with_awaitable())
    assert result == 20


@pytest.mark.asyncio
async def test_run_async_flow_multiple_yields():
    def multi_yield_gen() -> Generator[Any, Any, str]:
        a = yield 1
        b = yield a + 1
        return f"result:{b}"

    result = await run_async_flow(multi_yield_gen())
    assert result == "result:2"


@pytest.mark.asyncio
async def test_run_async_flow_propagates_exception():
    def exc_gen() -> Generator[Any, Any, None]:
        yield 1
        raise ValueError("async test error")

    with pytest.raises(ValueError, match="async test error"):
        await run_async_flow(exc_gen())


def test_sync_flow_decorator():
    @sync_flow
    def add_one(x: int) -> Generator[Any, Any, int]:
        val = yield x
        return val + 1

    result = add_one(5)
    assert result == 6


def test_sync_flow_preserves_function_name():
    @sync_flow
    def my_named_func() -> Generator[Any, Any, int]:
        yield 1
        return 42

    assert my_named_func.__name__ == "my_named_func"


def test_sync_flow_with_kwargs():
    @sync_flow
    def compute(a: int, b: int = 10) -> Generator[Any, Any, int]:
        x = yield a
        return x + b

    result = compute(5, b=20)
    assert result == 25


@pytest.mark.asyncio
async def test_async_flow_decorator():
    @async_flow
    def add_one(x: int) -> Generator[Any, Any, int]:
        val = yield x
        return val + 1

    result = await add_one(5)
    assert result == 6


@pytest.mark.asyncio
async def test_async_flow_preserves_function_name():
    @async_flow
    def my_async_named_func() -> Generator[Any, Any, int]:
        yield 1
        return 42

    assert my_async_named_func.__name__ == "my_async_named_func"


@pytest.mark.asyncio
async def test_async_flow_with_awaitable_yield():
    async def fetch_value():
        return 99

    @async_flow
    def fetch_gen() -> Generator[Any, Any, int]:
        val = yield fetch_value()
        return val

    result = await fetch_gen()
    assert result == 99


def test_flow_expr_with_sync_function():
    @flow_expr
    def get_value(x: int) -> int:
        return x * 2

    gen = get_value(5)
    result = run_sync_flow(gen)
    assert result == 10


def test_flow_expr_returns_callable():
    def original(x: int) -> int:
        return x

    wrapped = flow_expr(original)
    assert callable(wrapped)


def test_flow_expr_preserves_name():
    def my_expr(x: int) -> int:
        return x

    wrapped = flow_expr(my_expr)
    assert wrapped.__name__ == "my_expr"


@pytest.mark.asyncio
async def test_flow_expr_with_async_function():
    @flow_expr
    async def async_get_value(x: int) -> int:
        return x * 3

    gen = async_get_value(4)
    result = await run_async_flow(gen)
    assert result == 12


def test_flow_expr_flow_wrapper_is_generator():
    @flow_expr
    def expr(x: int) -> int:
        return x

    gen = expr(1)
    assert hasattr(gen, "send")
    assert hasattr(gen, "throw")
