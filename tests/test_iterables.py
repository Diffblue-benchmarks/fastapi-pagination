from __future__ import annotations

from fastapi_pagination.iterables import paginate, Params


def test_paginate_basic():
    items = list(range(10))
    result = paginate(items, Params(page=1, size=5))
    assert result.items == [0, 1, 2, 3, 4]


def test_paginate_second_page():
    items = list(range(10))
    result = paginate(items, Params(page=2, size=5))
    assert result.items == [5, 6, 7, 8, 9]


def test_paginate_with_total():
    items = list(range(10))
    result = paginate(items, Params(page=1, size=5), total=10)
    assert result.total == 10


def test_paginate_empty_iterable():
    result = paginate([], Params(page=1, size=10))
    assert result.items == []
