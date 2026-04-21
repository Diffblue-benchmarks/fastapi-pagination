import asyncio
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


def simple_sync_flow() -> Generator[Any, Any, int]:
    val = yield 1
    return val


def multi_step_sync_flow() -> Generator[Any, Any, str]:
    a = yield 10
    b = yield 20
    return f"{a}-{b}"


def error_sync_flow() -> Generator[Any, Any, int]:
    try:
        yield 1
    except ValueError as e:
        return -1
    return 0


def test_flow_decorator_returns_func():
    @flow
    def my_flow() -> Generator[Any, Any, int]:
        val = yield 1
        return val

    assert callable(my_flow)
    gen = my_flow()
    result = run_sync_flow(gen)
    assert result == 1


def test_check_not_coro_with_non_coro():
    _check_not_coro(42)
    _check_not_coro("hello")
    _check_not_coro(None)


def test_check_not_coro_raises_for_coro():
    async def some_coro():
        pass

    coro = some_coro()
    with pytest.raises(TypeError, match="Coroutine"):
        _check_not_coro(coro)
    coro.close()


def test_run_sync_flow_simple():
    def gen_func() -> Generator[Any, Any, int]:
        val = yield 42
        return val

    result = run_sync_flow(gen_func())
    assert result == 42


def test_run_sync_flow_multi_step():
    result = run_sync_flow(multi_step_sync_flow())
    assert result == "10-20"


def test_run_sync_flow_raises_on_coro_yield():
    async def some_coro():
        pass

    def bad_flow() -> Generator[Any, Any, None]:
        yield some_coro()

    coro_gen = bad_flow()
    with pytest.raises(TypeError):
        run_sync_flow(coro_gen)


def test_run_sync_flow_exception_in_loop():
    def exc_flow() -> Generator[Any, Any, int]:
        try:
            yield 1
        except ValueError:
            return -1
        return 0

    result = run_sync_flow(exc_flow())
    assert result == 0


@pytest.mark.asyncio
async def test_run_async_flow_simple():
    async def coro_val():
        return 99

    def gen_func() -> Generator[Any, Any, int]:
        val = yield coro_val()
        return val

    result = await run_async_flow(gen_func())
    assert result == 99


@pytest.mark.asyncio
async def test_run_async_flow_plain_value():
    def gen_func() -> Generator[Any, Any, int]:
        val = yield 55
        return val

    result = await run_async_flow(gen_func())
    assert result == 55


@pytest.mark.asyncio
async def test_run_async_flow_multi_step():
    def gen_func() -> Generator[Any, Any, str]:
        a = yield 1
        b = yield 2
        return f"{a}+{b}"

    result = await run_async_flow(gen_func())
    assert result == "1+2"


@pytest.mark.asyncio
async def test_run_async_flow_exception_handling():
    def exc_flow() -> Generator[Any, Any, int]:
        try:
            yield 1
        except ValueError:
            return -99
        return 0

    result = await run_async_flow(exc_flow())
    assert result == 0


def test_sync_flow_decorator():
    @sync_flow
    def my_flow(x: int) -> Generator[Any, Any, int]:
        val = yield x
        return val

    result = my_flow(7)
    assert result == 7


def test_sync_flow_wraps_preserves_name():
    @sync_flow
    def named_flow() -> Generator[Any, Any, int]:
        val = yield 1
        return val

    assert named_flow.__name__ == "named_flow"


def test_sync_flow_with_kwargs():
    @sync_flow
    def kw_flow(*, value: int) -> Generator[Any, Any, int]:
        val = yield value
        return val

    result = kw_flow(value=42)
    assert result == 42


@pytest.mark.asyncio
async def test_async_flow_decorator():
    @async_flow
    def my_flow(x: int) -> Generator[Any, Any, int]:
        val = yield x
        return val

    result = await my_flow(13)
    assert result == 13


@pytest.mark.asyncio
async def test_async_flow_wraps_preserves_name():
    @async_flow
    def named_async_flow() -> Generator[Any, Any, int]:
        val = yield 1
        return val

    assert named_async_flow.__name__ == "named_async_flow"


@pytest.mark.asyncio
async def test_async_flow_with_coro_yield():
    async def fetch(x: int) -> int:
        return x * 2

    @async_flow
    def my_flow(x: int) -> Generator[Any, Any, int]:
        val = yield fetch(x)
        return val

    result = await my_flow(5)
    assert result == 10


def test_flow_expr_sync():
    def add(a: int, b: int) -> int:
        return a + b

    wrapped = flow_expr(add)
    gen = wrapped(3, 4)
    result = run_sync_flow(gen)
    assert result == 7


@pytest.mark.asyncio
async def test_flow_expr_async():
    async def fetch(x: int) -> int:
        return x + 1

    wrapped = flow_expr(fetch)
    gen = wrapped(10)
    result = await run_async_flow(gen)
    assert result == 11


def test_flow_expr_preserves_name():
    def my_func(x: int) -> int:
        return x

    wrapped = flow_expr(my_func)
    assert wrapped.__name__ == "my_func"


def test_flow_wrapper_yields_and_returns():
    def identity(x: int) -> int:
        return x

    wrapped = flow_expr(identity)
    gen = wrapped(42)
    yielded = next(gen)
    assert yielded == 42
    with pytest.raises(StopIteration) as exc_info:
        gen.send(yielded)
    assert exc_info.value.value == 42
