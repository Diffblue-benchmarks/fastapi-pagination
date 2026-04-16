import pytest
import warnings

from fastapi_pagination import Page, Params
from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.async_paginator import apaginate, paginate
from fastapi_pagination.utils import disable_installed_extensions_check


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def disable_ext_check():
    disable_installed_extensions_check()


async def test_apaginate_basic():
    with set_page(Page), set_params(Params(page=1, size=10)):
        result = await apaginate([1, 2, 3], safe=True)

    assert result.total == 3
    assert result.items == [1, 2, 3]


async def test_apaginate_with_pagination():
    data = list(range(20))
    with set_page(Page), set_params(Params(page=2, size=5)):
        result = await apaginate(data, safe=True)

    assert result.total == 20
    assert result.items == [5, 6, 7, 8, 9]
    assert result.page == 2


async def test_apaginate_custom_length_function():
    data = [10, 20, 30]

    def custom_len(seq):
        return 100

    with set_page(Page), set_params(Params(page=1, size=10)):
        result = await apaginate(data, length_function=custom_len, safe=True)

    assert result.total == 100
    assert result.items == [10, 20, 30]


async def test_apaginate_async_length_function():
    data = [1, 2, 3, 4, 5]

    async def async_len(seq):
        return len(seq) * 2

    with set_page(Page), set_params(Params(page=1, size=10)):
        result = await apaginate(data, length_function=async_len, safe=True)

    assert result.total == 10
    assert result.items == [1, 2, 3, 4, 5]


async def test_apaginate_empty_sequence():
    with set_page(Page), set_params(Params(page=1, size=10)):
        result = await apaginate([], safe=True)

    assert result.total == 0
    assert result.items == []


async def test_apaginate_safe_false_no_warning_when_no_extensions():
    with set_page(Page), set_params(Params(page=1, size=5)):
        result = await apaginate([1, 2], safe=False)

    assert result.total == 2


async def test_apaginate_with_params_argument():
    data = list(range(10))
    params = Params(page=1, size=3)
    with set_page(Page):
        result = await apaginate(data, params=params, safe=True)

    assert result.total == 10
    assert result.items == [0, 1, 2]


async def test_paginate_deprecated_calls_apaginate():
    data = [1, 2, 3]
    with set_page(Page), set_params(Params(page=1, size=10)):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(data, safe=True)

    assert result.total == 3
    assert result.items == [1, 2, 3]


async def test_paginate_deprecated_with_params():
    data = list(range(15))
    params = Params(page=2, size=5)
    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(data, params=params, safe=True)

    assert result.total == 15
    assert result.items == [5, 6, 7, 8, 9]
