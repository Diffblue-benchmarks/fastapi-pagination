import warnings

import pytest

from fastapi_pagination.async_paginator import apaginate
from fastapi_pagination.async_paginator import paginate as deprecated_paginate
from fastapi_pagination.default import Page, Params
from fastapi_pagination.api import set_params


@pytest.fixture
def params():
    return Params(page=1, size=10)


@pytest.mark.asyncio
async def test_apaginate_basic(params):
    items = list(range(20))
    with set_params(params):
        result = await apaginate(items, safe=True)
    assert result.total == 20
    assert result.items == list(range(10))


@pytest.mark.asyncio
async def test_apaginate_with_explicit_params():
    items = list(range(5))
    result = await apaginate(items, params=Params(page=1, size=10), safe=True)
    assert result.total == 5
    assert result.items == list(range(5))


@pytest.mark.asyncio
async def test_apaginate_safe_skips_extension_check(mocker):
    check_mock = mocker.patch("fastapi_pagination.async_paginator.check_installed_extensions")
    items = [1, 2, 3]
    await apaginate(items, params=Params(page=1, size=10), safe=True)
    check_mock.assert_not_called()


@pytest.mark.asyncio
async def test_apaginate_not_safe_calls_extension_check(mocker):
    check_mock = mocker.patch("fastapi_pagination.async_paginator.check_installed_extensions")
    items = [1, 2, 3]
    await apaginate(items, params=Params(page=1, size=10), safe=False)
    check_mock.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_default_length_function():
    items = list(range(7))
    result = await apaginate(items, params=Params(page=1, size=5), safe=True)
    assert result.total == 7
    assert len(result.items) == 5


@pytest.mark.asyncio
async def test_apaginate_custom_length_function():
    items = list(range(10))
    custom_len_called = []

    def custom_len(seq):
        custom_len_called.append(True)
        return len(seq)

    result = await apaginate(items, params=Params(page=1, size=5), length_function=custom_len, safe=True)
    assert result.total == 10
    assert custom_len_called


@pytest.mark.asyncio
async def test_apaginate_async_length_function():
    items = list(range(8))

    async def async_len(seq):
        return len(seq)

    result = await apaginate(items, params=Params(page=1, size=4), length_function=async_len, safe=True)
    assert result.total == 8
    assert len(result.items) == 4


@pytest.mark.asyncio
async def test_apaginate_second_page():
    items = list(range(20))
    result = await apaginate(items, params=Params(page=2, size=5), safe=True)
    assert result.items == list(range(5, 10))


@pytest.mark.asyncio
async def test_deprecated_paginate_calls_apaginate():
    items = list(range(10))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        result = await deprecated_paginate(items, params=Params(page=1, size=5), safe=True)
    assert result.total == 10
    assert result.items == list(range(5))


@pytest.mark.asyncio
async def test_deprecated_paginate_emits_warning():
    items = [1, 2, 3]
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        await deprecated_paginate(items, params=Params(page=1, size=10), safe=True)
    assert any(issubclass(warning.category, DeprecationWarning) for warning in w)


@pytest.mark.asyncio
async def test_apaginate_empty_sequence():
    items = []
    result = await apaginate(items, params=Params(page=1, size=10), safe=True)
    assert result.total == 0
    assert result.items == []
