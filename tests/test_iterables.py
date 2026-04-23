import pytest

from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.iterables import Page, Params, paginate
from fastapi_pagination.utils import disable_installed_extensions_check


@pytest.fixture(autouse=True)
def _disable_ext_check():
    disable_installed_extensions_check()


def test_paginate_basic_list():
    data = list(range(10))
    params = Params(page=1, size=5)
    with set_page(Page):
        result = paginate(data, params=params)

    assert result.items == list(range(5))


def test_paginate_second_page():
    data = list(range(20))
    params = Params(page=2, size=5)
    with set_page(Page):
        result = paginate(data, params=params)

    assert result.items == list(range(5, 10))


def test_paginate_with_explicit_total():
    data = list(range(10))
    params = Params(page=1, size=5)
    with set_page(Page):
        result = paginate(data, params=params, total=100)

    assert result.total == 100
    assert result.items == list(range(5))


def test_paginate_empty_iterable():
    data = []
    params = Params(page=1, size=10)
    with set_page(Page):
        result = paginate(data, params=params)

    assert result.items == []


def test_paginate_with_transformer():
    data = list(range(10))
    params = Params(page=1, size=5)
    with set_page(Page):
        result = paginate(data, params=params, transformer=lambda items: [x * 2 for x in items])

    assert result.items == [0, 2, 4, 6, 8]


def test_paginate_uses_set_params_context():
    data = list(range(10))
    params = Params(page=1, size=3)
    with set_params(params), set_page(Page):
        result = paginate(data)

    assert result.items == [0, 1, 2]


def test_paginate_generator():
    data = (x for x in range(10))
    params = Params(page=1, size=4)
    with set_page(Page):
        result = paginate(data, params=params)

    assert result.items == [0, 1, 2, 3]
