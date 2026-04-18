import pytest
from fastapi_pagination.iterables import paginate, Params


def test_paginate_basic_list():
    items = list(range(10))
    result = paginate(items, Params(page=1, size=5))
    assert result.items == [0, 1, 2, 3, 4]


def test_paginate_second_page():
    items = list(range(10))
    result = paginate(items, Params(page=2, size=5))
    assert result.items == [5, 6, 7, 8, 9]


def test_paginate_with_total():
    items = list(range(5))
    result = paginate(items, Params(page=1, size=5), total=10)
    assert result.items == [0, 1, 2, 3, 4]


def test_paginate_generator():
    def gen():
        yield from range(6)

    result = paginate(gen(), Params(page=1, size=3))
    assert result.items == [0, 1, 2]
