import pytest

from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.async_paginator import apaginate, paginate
from fastapi_pagination.default import Page, Params


@pytest.fixture
def sample_sequence():
    return list(range(1, 21))


@pytest.mark.asyncio
async def test_apaginate_basic(sample_sequence):
    params = Params(page=1, size=10)
    with set_page(Page), set_params(params):
        result = await apaginate(sample_sequence, params=params, safe=True)
    assert result.total == 20
    assert result.page == 1
    assert result.size == 10
    assert len(result.items) == 10


@pytest.mark.asyncio
async def test_apaginate_safe_skips_extension_check(sample_sequence):
    params = Params(page=1, size=5)
    with set_page(Page), set_params(params):
        result = await apaginate(sample_sequence, params=params, safe=True)
    assert result.total == 20
    assert len(result.items) == 5


@pytest.mark.asyncio
async def test_apaginate_default_length_function(sample_sequence):
    params = Params(page=2, size=5)
    with set_page(Page), set_params(params):
        result = await apaginate(sample_sequence, params=params, safe=True, length_function=None)
    assert result.total == 20
    assert result.page == 2
    assert len(result.items) == 5


@pytest.mark.asyncio
async def test_apaginate_custom_length_function(sample_sequence):
    params = Params(page=1, size=10)
    with set_page(Page), set_params(params):
        result = await apaginate(sample_sequence, params=params, safe=True, length_function=lambda s: len(s))
    assert result.total == 20


@pytest.mark.asyncio
async def test_apaginate_empty_sequence():
    params = Params(page=1, size=10)
    with set_page(Page), set_params(params):
        result = await apaginate([], params=params, safe=True)
    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_second_page(sample_sequence):
    params = Params(page=2, size=10)
    with set_page(Page), set_params(params):
        result = await apaginate(sample_sequence, params=params, safe=True)
    assert result.page == 2
    assert result.items == list(range(11, 21))


@pytest.mark.asyncio
async def test_paginate_deprecated_wrapper(sample_sequence):
    params = Params(page=1, size=10)
    with set_page(Page), set_params(params):
        result = await paginate(sample_sequence, params=params, safe=True)
    assert result.total == 20
    assert len(result.items) == 10


@pytest.mark.asyncio
async def test_paginate_deprecated_delegates_to_apaginate(sample_sequence):
    params = Params(page=1, size=5)
    with set_page(Page), set_params(params):
        result = await paginate(sample_sequence, params=params, safe=True)
    assert result.page == 1
    assert result.size == 5
    assert result.items == list(range(1, 6))
