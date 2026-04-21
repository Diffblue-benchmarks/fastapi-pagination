from unittest.mock import patch

import pytest

from fastapi_pagination import Page, Params, set_page
from fastapi_pagination.paginator import paginate


@pytest.fixture
def params():
    return Params(page=1, size=10)


def test_paginate_basic_sequence(params):
    items = list(range(5))
    with set_page(Page):
        result = paginate(items, params=params, safe=True)
    assert list(result.items) == items
    assert result.total == 5


def test_paginate_respects_page_and_size():
    items = list(range(20))
    p = Params(page=2, size=5)
    with set_page(Page):
        result = paginate(items, params=p, safe=True)
    assert list(result.items) == list(range(5, 10))
    assert result.total == 20


def test_paginate_empty_sequence(params):
    with set_page(Page):
        result = paginate([], params=params, safe=True)
    assert list(result.items) == []
    assert result.total == 0


def test_paginate_calls_check_installed_extensions_when_not_safe(params):
    items = [1, 2, 3]
    with patch("fastapi_pagination.paginator.check_installed_extensions") as mock_check:
        with set_page(Page):
            paginate(items, params=params, safe=False)
    mock_check.assert_called_once()


def test_paginate_skips_check_installed_extensions_when_safe(params):
    items = [1, 2, 3]
    with patch("fastapi_pagination.paginator.check_installed_extensions") as mock_check:
        with set_page(Page):
            paginate(items, params=params, safe=True)
    mock_check.assert_not_called()


def test_paginate_default_length_function_uses_len(params):
    items = [10, 20, 30]
    with set_page(Page):
        result = paginate(items, params=params, safe=True)
    assert result.total == 3


def test_paginate_custom_length_function(params):
    items = [1, 2, 3, 4, 5]
    custom_len = lambda seq: 100  # noqa: E731
    with set_page(Page):
        result = paginate(items, params=params, safe=True, length_function=custom_len)
    assert result.total == 100


def test_paginate_with_transformer(params):
    items = [1, 2, 3]
    transformer = lambda seq: [x * 2 for x in seq]  # noqa: E731
    with set_page(Page):
        result = paginate(items, params=params, safe=True, transformer=transformer)
    assert list(result.items) == [2, 4, 6]


def test_paginate_last_page():
    items = list(range(10))
    p = Params(page=2, size=7)
    with set_page(Page):
        result = paginate(items, params=p, safe=True)
    assert list(result.items) == [7, 8, 9]
    assert result.total == 10
