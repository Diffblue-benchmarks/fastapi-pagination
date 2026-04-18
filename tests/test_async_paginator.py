import pytest
import warnings

from fastapi_pagination.async_paginator import apaginate, paginate
from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.default import Page, Params


@pytest.mark.asyncio
async def test_apaginate_basic():
    items = list(range(10))
    params = Params(page=1, size=5)

    with set_page(Page):
        result = await apaginate(items, params=params, safe=True)

    assert result.total == 10
    assert result.items == list(range(5))
    assert result.page == 1
    assert result.size == 5


@pytest.mark.asyncio
async def test_apaginate_second_page():
    items = list(range(10))
    params = Params(page=2, size=5)

    with set_page(Page):
        result = await apaginate(items, params=params, safe=True)

    assert result.total == 10
    assert result.items == list(range(5, 10))
    assert result.page == 2


@pytest.mark.asyncio
async def test_apaginate_custom_length_function():
    items = list(range(10))
    params = Params(page=1, size=5)

    with set_page(Page):
        result = await apaginate(items, params=params, safe=True, length_function=lambda s: len(s))

    assert result.total == 10
    assert result.items == list(range(5))


@pytest.mark.asyncio
async def test_apaginate_async_length_function():
    items = list(range(10))
    params = Params(page=1, size=5)

    async def async_len(s):
        return len(s)

    with set_page(Page):
        result = await apaginate(items, params=params, safe=True, length_function=async_len)

    assert result.total == 10
    assert result.items == list(range(5))


@pytest.mark.asyncio
async def test_apaginate_empty_sequence():
    items = []
    params = Params(page=1, size=5)

    with set_page(Page):
        result = await apaginate(items, params=params, safe=True)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_with_transformer():
    items = list(range(5))
    params = Params(page=1, size=5)

    def double(seq):
        return [x * 2 for x in seq]

    with set_page(Page):
        result = await apaginate(items, params=params, safe=True, transformer=double)

    assert result.items == [0, 2, 4, 6, 8]


@pytest.mark.asyncio
async def test_apaginate_unsafe_no_extensions():
    items = list(range(5))
    params = Params(page=1, size=5)

    with set_page(Page):
        result = await apaginate(items, params=params, safe=False)

    assert result.total == 5


@pytest.mark.asyncio
async def test_paginate_deprecated_calls_apaginate():
    items = list(range(6))
    params = Params(page=1, size=3)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(items, params=params, safe=True)

    assert result.total == 6
    assert result.items == [0, 1, 2]
    assert result.page == 1


@pytest.mark.asyncio
async def test_paginate_deprecated_second_page():
    items = list(range(6))
    params = Params(page=2, size=3)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(items, params=params, safe=True)

    assert result.total == 6
    assert result.items == [3, 4, 5]
    assert result.page == 2
