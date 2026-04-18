import pytest
from fastapi_pagination import Params, paginate


def test_paginate_basic():
    items = list(range(10))
    result = paginate(items, Params(page=1, size=5))
    assert result.items == [0, 1, 2, 3, 4]
    assert result.total == 10


def test_paginate_second_page():
    items = list(range(10))
    result = paginate(items, Params(page=2, size=5))
    assert result.items == [5, 6, 7, 8, 9]


def test_paginate_safe_true():
    items = list(range(6))
    result = paginate(items, Params(page=1, size=3), safe=True)
    assert result.items == [0, 1, 2]
    assert result.total == 6


def test_paginate_safe_false():
    items = list(range(6))
    result = paginate(items, Params(page=1, size=3), safe=False)
    assert result.items == [0, 1, 2]


def test_paginate_custom_length_function():
    items = list(range(8))
    custom_len = lambda seq: 100
    result = paginate(items, Params(page=1, size=4), length_function=custom_len)
    assert result.items == [0, 1, 2, 3]
    assert result.total == 100


def test_paginate_default_length_function():
    items = list(range(5))
    result = paginate(items, Params(page=1, size=10))
    assert result.total == 5
    assert result.items == [0, 1, 2, 3, 4]
