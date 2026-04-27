import pytest

from fastapi_pagination.iterables import paginate, Params, LimitOffsetParams


def test_paginate_returns_first_page():
    items = list(range(20))
    params = Params(page=1, size=5)
    result = paginate(items, params=params)
    assert result.items == [0, 1, 2, 3, 4]


def test_paginate_returns_second_page():
    items = list(range(20))
    params = Params(page=2, size=5)
    result = paginate(items, params=params)
    assert result.items == [5, 6, 7, 8, 9]


def test_paginate_with_total():
    items = list(range(10))
    params = Params(page=1, size=5)
    result = paginate(items, params=params, total=10)
    assert result.items == [0, 1, 2, 3, 4]


def test_paginate_with_limit_offset_params():
    items = list(range(20))
    params = LimitOffsetParams(limit=3, offset=5)
    result = paginate(items, params=params)
    assert result.items == [5, 6, 7]


def test_paginate_with_generator():
    def gen():
        yield from range(10)

    params = Params(page=1, size=4)
    result = paginate(gen(), params=params)
    assert result.items == [0, 1, 2, 3]


def test_paginate_with_transformer():
    items = list(range(10))
    params = Params(page=1, size=5)
    result = paginate(items, params=params, transformer=lambda x: [i * 2 for i in x])
    assert result.items == [0, 2, 4, 6, 8]
