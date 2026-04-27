import asyncio

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


def test_flow_decorator_returns_func():
    def my_gen():
        yield 1
        return "done"

    decorated = flow(my_gen)
    assert decorated is my_gen


def test_check_not_coro_with_non_coro():
    # Should not raise for non-awaitable values
    _check_not_coro(42)
    _check_not_coro("hello")
    _check_not_coro(None)


def test_check_not_coro_raises_for_coro():
    async def my_coro():
        pass

    coro = my_coro()
    with pytest.raises(TypeError, match="Coroutine .* is not allowed in sync flow"):
        _check_not_coro(coro)
    coro.close()


def test_run_sync_flow_simple():
    def gen():
        x = yield 10
        return x * 2

    result = run_sync_flow(gen())
    assert result == 20


def test_run_sync_flow_multiple_yields():
    def gen():
        a = yield 1
        b = yield a + 1
        return a + b

    result = run_sync_flow(gen())
    assert result == 1 + 2


def test_run_sync_flow_raises_on_coro():
    async def my_coro():
        return 1

    def gen():
        yield my_coro()

    with pytest.raises(TypeError, match="Coroutine .* is not allowed in sync flow"):
        run_sync_flow(gen())


def test_run_sync_flow_with_exception_in_yield():
    def gen():
        try:
            yield 1
        except ValueError:
            return "caught"

    def bad_gen():
        g = gen()
        g.send(None)
        g.throw(ValueError("oops"))

    # Test exception propagation through run_sync_flow
    def gen_throwing():
        try:
            val = yield "start"
        except RuntimeError:
            return "handled"

    # We simulate by having the generator handle exceptions
    def raising_gen():
        yield "start"
        raise RuntimeError("oops")

    with pytest.raises(RuntimeError, match="oops"):
        run_sync_flow(raising_gen())


@pytest.mark.asyncio
async def test_run_async_flow_simple():
    def gen():
        x = yield 10
        return x * 2

    result = await run_async_flow(gen())
    assert result == 20


@pytest.mark.asyncio
async def test_run_async_flow_with_awaitable():
    async def compute(x):
        return x + 1

    def gen():
        val = yield compute(5)
        return val

    result = await run_async_flow(gen())
    assert result == 6


@pytest.mark.asyncio
async def test_run_async_flow_multiple_yields():
    async def add_one(x):
        return x + 1

    def gen():
        a = yield add_one(0)
        b = yield add_one(a)
        return a + b

    result = await run_async_flow(gen())
    assert result == 0 + 1 + 1 + 1  # a=1, b=2, returns 3
    assert result == 3


@pytest.mark.asyncio
async def test_run_async_flow_exception_in_generator():
    def gen():
        yield "start"
        raise RuntimeError("async error")

    with pytest.raises(RuntimeError, match="async error"):
        await run_async_flow(gen())


def test_sync_flow_decorator():
    @sync_flow
    def my_flow():
        x = yield 5
        return x + 1

    result = my_flow()
    assert result == 6


def test_sync_flow_preserves_name():
    @sync_flow
    def my_named_flow():
        x = yield 1
        return x

    assert my_named_flow.__name__ == "my_named_flow"


def test_sync_flow_with_args():
    @sync_flow
    def my_flow(a, b):
        x = yield a
        return x + b

    result = my_flow(10, 5)
    assert result == 15


@pytest.mark.asyncio
async def test_async_flow_decorator():
    @async_flow
    def my_flow():
        async def get_val():
            return 42

        x = yield get_val()
        return x

    result = await my_flow()
    assert result == 42


@pytest.mark.asyncio
async def test_async_flow_preserves_name():
    @async_flow
    def my_named_async_flow():
        x = yield 1
        return x

    assert my_named_async_flow.__name__ == "my_named_async_flow"


@pytest.mark.asyncio
async def test_async_flow_with_args():
    @async_flow
    def my_flow(a, b):
        x = yield a
        return x + b

    result = await my_flow(3, 7)
    assert result == 10


def test_flow_expr_sync():
    def add(a, b):
        return a + b

    wrapped = flow_expr(add)
    gen = wrapped(2, 3)
    result = run_sync_flow(gen)
    assert result == 5


@pytest.mark.asyncio
async def test_flow_expr_async():
    async def fetch(x):
        return x * 10

    wrapped = flow_expr(fetch)
    gen = wrapped(4)
    result = await run_async_flow(gen)
    assert result == 40


def test_flow_expr_preserves_name():
    def my_expr(x):
        return x

    wrapped = flow_expr(my_expr)
    assert wrapped.__name__ == "my_expr"


def test_flow_expr_returns_generator():
    def expr(x):
        return x + 1

    wrapped = flow_expr(expr)
    gen = wrapped(5)
    import inspect
    assert inspect.isgenerator(gen)
