import warnings

import pytest

from fastapi_pagination.async_paginator import apaginate, paginate
from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.default import Page, Params


@pytest.fixture
def sample_sequence():
    return list(range(1, 101))


@pytest.mark.asyncio
async def test_apaginate_basic(sample_sequence):
    params = Params(page=1, size=10)
    with set_page(Page):
        with set_params(params):
            result = await apaginate(sample_sequence, params=params, safe=True)

    assert result.total == 100
    assert len(result.items) == 10
    assert result.items == list(range(1, 11))


@pytest.mark.asyncio
async def test_apaginate_second_page(sample_sequence):
    params = Params(page=2, size=10)
    with set_page(Page):
        result = await apaginate(sample_sequence, params=params, safe=True)

    assert result.total == 100
    assert len(result.items) == 10
    assert result.items == list(range(11, 21))


@pytest.mark.asyncio
async def test_apaginate_custom_length_function(sample_sequence):
    params = Params(page=1, size=5)
    custom_len = len

    with set_page(Page):
        result = await apaginate(sample_sequence, params=params, safe=True, length_function=custom_len)

    assert result.total == 100
    assert len(result.items) == 5


@pytest.mark.asyncio
async def test_apaginate_default_length_function(sample_sequence):
    params = Params(page=1, size=20)
    with set_page(Page):
        result = await apaginate(sample_sequence, params=params, safe=True)

    assert result.total == 100
    assert len(result.items) == 20


@pytest.mark.asyncio
async def test_apaginate_safe_false_no_extensions(sample_sequence):
    params = Params(page=1, size=5)
    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = await apaginate(sample_sequence, params=params, safe=False)

    assert result.total == 100
    assert len(result.items) == 5


@pytest.mark.asyncio
async def test_apaginate_with_transformer(sample_sequence):
    params = Params(page=1, size=5)

    def transformer(items):
        return [x * 2 for x in items]

    with set_page(Page):
        result = await apaginate(sample_sequence, params=params, safe=True, transformer=transformer)

    assert len(result.items) == 5
    assert result.items == [2, 4, 6, 8, 10]


@pytest.mark.asyncio
async def test_deprecated_paginate(sample_sequence):
    params = Params(page=1, size=10)
    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(sample_sequence, params=params, safe=True)

    assert result.total == 100
    assert len(result.items) == 10


@pytest.mark.asyncio
async def test_deprecated_paginate_calls_apaginate(sample_sequence):
    params = Params(page=2, size=5)
    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(sample_sequence, params=params, safe=True)

    assert result.items == list(range(6, 11))
    assert result.total == 100
