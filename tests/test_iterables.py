import pytest

from fastapi_pagination.iterables import paginate, Params


def test_paginate_basic_list():
    items = list(range(10))
    params = Params(page=1, size=5)
    result = paginate(items, params=params)
    assert result is not None
    assert result.items == [0, 1, 2, 3, 4]


def test_paginate_with_total():
    items = list(range(10))
    params = Params(page=1, size=5)
    result = paginate(items, params=params, total=10)
    assert result is not None
    assert result.items == [0, 1, 2, 3, 4]


def test_paginate_second_page():
    items = list(range(10))
    params = Params(page=2, size=5)
    result = paginate(items, params=params)
    assert result is not None
    assert result.items == [5, 6, 7, 8, 9]


def test_paginate_empty_iterable():
    params = Params(page=1, size=10)
    result = paginate([], params=params)
    assert result is not None
    assert result.items == []


def test_paginate_with_generator():
    def gen():
        for i in range(6):
            yield i

    params = Params(page=1, size=3)
    result = paginate(gen(), params=params)
    assert result is not None
    assert result.items == [0, 1, 2]
