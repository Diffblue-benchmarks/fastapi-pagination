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


# Tests for `flow`
def test_flow_returns_func():
    def my_gen():
        yield 1
        return "done"

    result = flow(my_gen)
    assert result is my_gen


# Tests for `_check_not_coro`
def test_check_not_coro_non_coro_passes():
    _check_not_coro(42)
    _check_not_coro("string")
    _check_not_coro(None)


def test_check_not_coro_raises_on_coroutine():
    async def coro():
        pass

    c = coro()
    with pytest.raises(TypeError, match="Coroutine"):
        _check_not_coro(c)
    c.close()


# Tests for `run_sync_flow`
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


def test_run_sync_flow_raises_on_coroutine_yielded():
    async def coro():
        return 1

    def gen():
        yield coro()
        return "done"

    with pytest.raises(TypeError):
        run_sync_flow(gen())


def test_run_sync_flow_exception_in_gen():
    async def make_coro():
        return 99

    def gen():
        yield 1  # first yield is fine
        try:
            yield make_coro()  # second yield: coroutine causes TypeError via _check_not_coro
        except TypeError:
            return "caught"

    result = run_sync_flow(gen())
    assert result == "caught"


# Tests for `run_async_flow`
@pytest.mark.asyncio
async def test_run_async_flow_simple():
    def gen():
        x = yield 10
        return x * 2

    result = await run_async_flow(gen())
    assert result == 20


@pytest.mark.asyncio
async def test_run_async_flow_with_awaitable():
    async def async_val():
        return 5

    def gen():
        x = yield async_val()
        return x + 1

    result = await run_async_flow(gen())
    assert result == 6


@pytest.mark.asyncio
async def test_run_async_flow_multiple_yields():
    def gen():
        a = yield 3
        b = yield a + 1
        return a + b

    result = await run_async_flow(gen())
    assert result == 3 + 4


@pytest.mark.asyncio
async def test_run_async_flow_exception_in_gen():
    async def failing():
        raise RuntimeError("expected error")

    def gen():
        try:
            yield failing()
        except RuntimeError:
            return "handled"

    result = await run_async_flow(gen())
    assert result == "handled"


# Tests for `sync_flow`
def test_sync_flow_decorator():
    @sync_flow
    def my_flow(x):
        val = yield x + 1
        return val * 3

    result = my_flow(4)
    assert result == 15


def test_sync_flow_preserves_name():
    @sync_flow
    def named_flow():
        yield 1
        return "ok"

    assert named_flow.__name__ == "named_flow"


# Tests for `async_flow`
@pytest.mark.asyncio
async def test_async_flow_decorator():
    @async_flow
    def my_async_gen(x):
        val = yield x + 1
        return val * 2

    result = await my_async_gen(3)
    assert result == 8


@pytest.mark.asyncio
async def test_async_flow_preserves_name():
    @async_flow
    def my_named_gen():
        yield 1
        return "done"

    assert my_named_gen.__name__ == "my_named_gen"


@pytest.mark.asyncio
async def test_async_flow_with_awaitable_yield():
    async def compute(x):
        return x * 10

    @async_flow
    def gen(x):
        val = yield compute(x)
        return val + 1

    result = await gen(2)
    assert result == 21


# Tests for `flow_expr`
def test_flow_expr_sync_callable():
    def add(a, b):
        return a + b

    wrapped = flow_expr(add)
    gen = wrapped(2, 3)
    result = run_sync_flow(gen)
    assert result == 5


def test_flow_expr_preserves_name():
    def my_func(x):
        return x

    wrapped = flow_expr(my_func)
    assert wrapped.__name__ == "my_func"


@pytest.mark.asyncio
async def test_flow_expr_async_callable():
    async def async_add(a, b):
        return a + b

    wrapped = flow_expr(async_add)
    gen = wrapped(4, 5)
    result = await run_async_flow(gen)
    assert result == 9


def test_flow_expr_flow_wrapper_returns_correct_value():
    def mul(a, b):
        return a * b

    wrapped = flow_expr(mul)
    gen = wrapped(3, 4)
    result = run_sync_flow(gen)
    assert result == 12
