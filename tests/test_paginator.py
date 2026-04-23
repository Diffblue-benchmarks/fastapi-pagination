import pytest

from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.default import Page, Params
from fastapi_pagination.paginator import paginate
from fastapi_pagination.utils import disable_installed_extensions_check


@pytest.fixture(autouse=True)
def _disable_ext_check():
    disable_installed_extensions_check()


def test_paginate_basic_sequence():
    data = list(range(10))
    params = Params(page=1, size=5)
    with set_page(Page):
        result = paginate(data, params=params, safe=True)

    assert result.total == 10
    assert result.items == list(range(5))


def test_paginate_second_page():
    data = list(range(20))
    params = Params(page=2, size=5)
    with set_page(Page):
        result = paginate(data, params=params, safe=True)

    assert result.total == 20
    assert result.items == list(range(5, 10))


def test_paginate_default_length_function():
    data = list(range(10))
    params = Params(page=1, size=10)
    with set_page(Page):
        result = paginate(data, params=params, safe=True)

    assert result.total == 10
    assert len(result.items) == 10


def test_paginate_custom_length_function():
    data = list(range(10))
    params = Params(page=1, size=5)
    with set_page(Page):
        result = paginate(data, params=params, length_function=lambda seq: 42, safe=True)

    assert result.total == 42
    assert result.items == list(range(5))


def test_paginate_safe_false_calls_check():
    data = [1, 2, 3]
    params = Params(page=1, size=10)
    with set_page(Page):
        result = paginate(data, params=params, safe=False)

    assert result.items == [1, 2, 3]


def test_paginate_empty_sequence():
    data = []
    params = Params(page=1, size=10)
    with set_page(Page):
        result = paginate(data, params=params, safe=True)

    assert result.total == 0
    assert result.items == []


def test_paginate_uses_set_params_context():
    data = list(range(10))
    params = Params(page=1, size=3)
    with set_params(params), set_page(Page):
        result = paginate(data, safe=True)

    assert result.items == [0, 1, 2]


def test_paginate_with_transformer():
    data = list(range(10))
    params = Params(page=1, size=5)
    with set_page(Page):
        result = paginate(data, params=params, transformer=lambda items: [x * 2 for x in items], safe=True)

    assert result.items == [0, 2, 4, 6, 8]
