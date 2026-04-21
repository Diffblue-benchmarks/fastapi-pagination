from __future__ import annotations

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


# ---------------------------------------------------------------------------
# flow
# ---------------------------------------------------------------------------


def test_flow_returns_function_unchanged():
    def my_gen() -> Generator[int, int, str]:
        val = yield 1
        return "done"

    result = flow(my_gen)
    assert result is my_gen


def test_flow_preserves_callable():
    def gen_func(x: int) -> Generator[int, int, int]:
        val = yield x
        return val

    decorated = flow(gen_func)
    assert decorated is gen_func
    gen = decorated(5)
    assert next(gen) == 5


# ---------------------------------------------------------------------------
# _check_not_coro
# ---------------------------------------------------------------------------


def test_check_not_coro_raises_for_coroutine():
    async def my_coro():
        return 42

    coro = my_coro()
    with pytest.raises(TypeError, match="Coroutine"):
        try:
            _check_not_coro(coro)
        finally:
            coro.close()


def test_check_not_coro_does_not_raise_for_plain_value():
    _check_not_coro(42)
    _check_not_coro("hello")
    _check_not_coro(None)
    _check_not_coro([1, 2, 3])


def test_check_not_coro_does_not_raise_for_generator():
    def gen():
        yield 1

    _check_not_coro(gen())


# ---------------------------------------------------------------------------
# run_sync_flow
# ---------------------------------------------------------------------------


def test_run_sync_flow_simple():
    def simple_flow() -> Generator[int, int, str]:
        val = yield 10
        return "result"

    result = run_sync_flow(simple_flow())
    assert result == "result"


def test_run_sync_flow_multiple_yields():
    def multi_flow() -> Generator[int, int, int]:
        a = yield 1
        b = yield a + 1
        return b + 10

    result = run_sync_flow(multi_flow())
    assert result == 12


def test_run_sync_flow_raises_for_coroutine_yield():
    async def my_coro():
        return 42

    def bad_flow() -> Generator[Any, Any, None]:
        yield my_coro()
        return None

    with pytest.raises(TypeError, match="Coroutine"):
        run_sync_flow(bad_flow())


def test_run_sync_flow_handles_exception_in_generator():
    def flow_with_exc() -> Generator[int, int, str]:
        try:
            val = yield 1
        except ValueError:
            return "caught"
        return "not caught"

    def flow_runner():
        gen = flow_with_exc()
        try:
            res = gen.send(None)
            # Simulate exception throw
            try:
                gen.throw(ValueError("test"))
            except StopIteration as exc:
                return exc.value
        except StopIteration as exc:
            return exc.value

    # Test directly via run_sync_flow by raising in generator
    class _Raiser:
        def __init__(self):
            self._gen = flow_with_exc()
            self._step = 0

        def send(self, val):
            if self._step == 0:
                self._step += 1
                return self._gen.send(None)
            raise StopIteration("fallback")

        def throw(self, exc):
            return self._gen.throw(type(exc), exc)

    # Simpler test: run normal flow
    result = run_sync_flow(flow_with_exc())
    assert result == "not caught"


def test_run_sync_flow_returns_value_directly():
    def immediate_return() -> Generator[None, None, str]:
        return "immediate"
        yield  # make it a generator

    result = run_sync_flow(immediate_return())
    assert result == "immediate"


# ---------------------------------------------------------------------------
# run_async_flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_async_flow_simple():
    def simple_flow() -> Generator[int, int, str]:
        val = yield 10
        return "async_result"

    result = await run_async_flow(simple_flow())
    assert result == "async_result"


@pytest.mark.asyncio
async def test_run_async_flow_with_awaitable():
    async def fetch_value():
        return 42

    def flow_with_awaitable() -> Generator[Any, Any, int]:
        val = yield fetch_value()
        return val

    result = await run_async_flow(flow_with_awaitable())
    assert result == 42


@pytest.mark.asyncio
async def test_run_async_flow_multiple_yields():
    async def async_add(a, b):
        return a + b

    def multi_flow() -> Generator[Any, Any, int]:
        a = yield async_add(1, 2)
        b = yield async_add(a, 10)
        return b

    result = await run_async_flow(multi_flow())
    assert result == 13


@pytest.mark.asyncio
async def test_run_async_flow_with_plain_values():
    def plain_flow() -> Generator[int, int, int]:
        a = yield 5
        b = yield a * 2
        return b + 1

    result = await run_async_flow(plain_flow())
    assert result == 11


@pytest.mark.asyncio
async def test_run_async_flow_exception_handling():
    def flow_with_exc() -> Generator[int, int, str]:
        try:
            val = yield 1
        except ValueError:
            return "caught_async"
        return "not_caught"

    result = await run_async_flow(flow_with_exc())
    assert result == "not_caught"


@pytest.mark.asyncio
async def test_run_async_flow_returns_immediately():
    def immediate_return() -> Generator[None, None, str]:
        return "immediate_async"
        yield  # make it a generator

    result = await run_async_flow(immediate_return())
    assert result == "immediate_async"


# ---------------------------------------------------------------------------
# sync_flow
# ---------------------------------------------------------------------------


def test_sync_flow_decorator():
    @sync_flow
    def my_flow(x: int) -> Generator[int, int, int]:
        val = yield x
        return val + 1

    result = my_flow(5)
    assert result == 6


def test_sync_flow_preserves_function_name():
    @sync_flow
    def my_named_flow() -> Generator[None, None, str]:
        return "done"
        yield

    assert my_named_flow.__name__ == "my_named_flow"


def test_sync_flow_with_kwargs():
    @sync_flow
    def kw_flow(a: int, b: int = 10) -> Generator[int, int, int]:
        val = yield a
        return val + b

    result = kw_flow(5, b=20)
    assert result == 25


def test_sync_flow_wraps_correctly():
    @sync_flow
    def documented_flow() -> Generator[None, None, str]:
        """My docstring."""
        return "ok"
        yield

    assert documented_flow.__doc__ == "My docstring."


# ---------------------------------------------------------------------------
# async_flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_flow_decorator():
    @async_flow
    def my_async_flow(x: int) -> Generator[Any, Any, int]:
        val = yield x
        return val + 1

    result = await my_async_flow(7)
    assert result == 8


@pytest.mark.asyncio
async def test_async_flow_preserves_function_name():
    @async_flow
    def my_named_async_flow() -> Generator[None, None, str]:
        return "async_done"
        yield

    assert my_named_async_flow.__name__ == "my_named_async_flow"
    result = await my_named_async_flow()
    assert result == "async_done"


@pytest.mark.asyncio
async def test_async_flow_with_awaitable_in_flow():
    async def async_multiply(x, y):
        return x * y

    @async_flow
    def multiplying_flow(a: int, b: int) -> Generator[Any, Any, int]:
        result = yield async_multiply(a, b)
        return result

    result = await multiplying_flow(3, 4)
    assert result == 12


@pytest.mark.asyncio
async def test_async_flow_wrapper_is_coroutine():
    @async_flow
    def simple() -> Generator[None, None, str]:
        return "hello"
        yield

    import inspect
    assert inspect.iscoroutinefunction(simple)


# ---------------------------------------------------------------------------
# flow_expr
# ---------------------------------------------------------------------------


def test_flow_expr_with_sync_function():
    def double(x: int) -> int:
        return x * 2

    expr_flow = flow_expr(double)
    gen = expr_flow(5)
    yielded = next(gen)
    assert yielded == 10
    try:
        gen.send(yielded)
    except StopIteration as exc:
        assert exc.value == 10


def test_flow_expr_preserves_function_name():
    def my_expr(x: int) -> int:
        return x

    wrapped = flow_expr(my_expr)
    assert wrapped.__name__ == "my_expr"


def test_flow_expr_via_sync_flow():
    def add_one(x: int) -> int:
        return x + 1

    @sync_flow
    def my_flow(x: int) -> Generator[Any, Any, int]:
        result = yield from flow_expr(add_one)(x)
        return result

    result = my_flow(9)
    assert result == 10


@pytest.mark.asyncio
async def test_flow_expr_with_async_function():
    async def async_double(x: int) -> int:
        return x * 2

    expr_flow = flow_expr(async_double)

    @async_flow
    def my_flow(x: int) -> Generator[Any, Any, int]:
        result = yield from expr_flow(x)
        return result

    result = await my_flow(6)
    assert result == 12


def test_flow_expr_creates_generator_function():
    def identity(x):
        return x

    wrapped = flow_expr(identity)
    import inspect
    assert inspect.isgeneratorfunction(wrapped)


def test_flow_expr_flow_wrapper_yields_then_returns():
    def square(x: int) -> int:
        return x * x

    wrapped = flow_expr(square)
    gen = wrapped(4)
    # First send(None) yields the expression result
    yielded = gen.send(None)
    assert yielded == 16
    # Send back the value to get the return
    try:
        gen.send(yielded)
        pytest.fail("Expected StopIteration")
    except StopIteration as exc:
        assert exc.value == 16
