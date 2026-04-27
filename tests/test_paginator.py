import pytest

from fastapi_pagination.paginator import paginate
from fastapi_pagination.default import Params
from fastapi_pagination.limit_offset import LimitOffsetParams


def test_paginate_basic():
    items = list(range(20))
    params = Params(page=1, size=5)
    result = paginate(items, params=params, safe=True)
    assert result.items == [0, 1, 2, 3, 4]


def test_paginate_second_page():
    items = list(range(20))
    params = Params(page=2, size=5)
    result = paginate(items, params=params, safe=True)
    assert result.items == [5, 6, 7, 8, 9]


def test_paginate_uses_len_when_no_length_function():
    items = list(range(10))
    params = Params(page=1, size=5)
    result = paginate(items, params=params, safe=True)
    assert result.total == 10


def test_paginate_with_custom_length_function():
    items = list(range(10))
    params = Params(page=1, size=5)
    result = paginate(items, params=params, length_function=lambda seq: 10, safe=True)
    assert result.total == 10


def test_paginate_with_limit_offset_params():
    items = list(range(20))
    params = LimitOffsetParams(limit=3, offset=6)
    result = paginate(items, params=params, safe=True)
    assert result.items == [6, 7, 8]


def test_paginate_safe_false_calls_check(mocker):
    mock_check = mocker.patch("fastapi_pagination.paginator.check_installed_extensions")
    items = list(range(5))
    params = Params(page=1, size=5)
    paginate(items, params=params, safe=False)
    mock_check.assert_called_once()


def test_paginate_safe_true_skips_check(mocker):
    mock_check = mocker.patch("fastapi_pagination.paginator.check_installed_extensions")
    items = list(range(5))
    params = Params(page=1, size=5)
    paginate(items, params=params, safe=True)
    mock_check.assert_not_called()


def test_paginate_with_transformer():
    items = list(range(10))
    params = Params(page=1, size=5)
    result = paginate(items, params=params, transformer=lambda x: [i * 2 for i in x], safe=True)
    assert result.items == [0, 2, 4, 6, 8]
