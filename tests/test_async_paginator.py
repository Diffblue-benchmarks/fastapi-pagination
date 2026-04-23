import pytest

from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.async_paginator import apaginate
from fastapi_pagination.async_paginator import paginate as deprecated_paginate
from fastapi_pagination.default import Page, Params
from fastapi_pagination.utils import disable_installed_extensions_check


@pytest.fixture(autouse=True)
def _disable_ext_check():
    disable_installed_extensions_check()


@pytest.mark.asyncio
async def test_apaginate_basic_sequence():
    data = list(range(10))
    params = Params(page=1, size=5)
    with set_params(params), set_page(Page):
        result = await apaginate(data, safe=True)

    assert result.total == 10
    assert result.items == list(range(5))


@pytest.mark.asyncio
async def test_apaginate_with_explicit_params():
    data = list(range(20))
    params = Params(page=2, size=5)
    with set_page(Page):
        result = await apaginate(data, params=params, safe=True)

    assert result.total == 20
    assert result.items == list(range(5, 10))


@pytest.mark.asyncio
async def test_apaginate_default_length_function():
    data = list(range(10))
    params = Params(page=1, size=10)
    with set_page(Page):
        result = await apaginate(data, params=params, safe=True)

    assert result.total == 10
    assert len(result.items) == 10


@pytest.mark.asyncio
async def test_apaginate_custom_sync_length_function():
    data = list(range(10))
    params = Params(page=1, size=5)
    with set_page(Page):
        result = await apaginate(data, params=params, length_function=lambda seq: 42, safe=True)

    assert result.total == 42
    assert result.items == list(range(5))


@pytest.mark.asyncio
async def test_apaginate_custom_async_length_function():
    data = list(range(10))
    params = Params(page=1, size=5)

    async def async_len(seq):
        return len(seq)

    with set_page(Page):
        result = await apaginate(data, params=params, length_function=async_len, safe=True)

    assert result.total == 10
    assert result.items == list(range(5))


@pytest.mark.asyncio
async def test_apaginate_safe_false_calls_check():
    data = [1, 2, 3]
    params = Params(page=1, size=10)
    with set_page(Page):
        result = await apaginate(data, params=params, safe=False)

    assert result.items == [1, 2, 3]


@pytest.mark.asyncio
async def test_apaginate_empty_sequence():
    data = []
    params = Params(page=1, size=10)
    with set_page(Page):
        result = await apaginate(data, params=params, safe=True)

    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_deprecated_paginate_calls_apaginate():
    data = list(range(10))
    params = Params(page=1, size=5)
    with set_page(Page):
        result = await deprecated_paginate(data, params=params, safe=True)

    assert result.total == 10
    assert result.items == list(range(5))


@pytest.mark.asyncio
async def test_deprecated_paginate_with_custom_length_function():
    data = list(range(10))
    params = Params(page=1, size=5)
    with set_page(Page):
        result = await deprecated_paginate(data, params=params, length_function=lambda seq: 99, safe=True)

    assert result.total == 99
