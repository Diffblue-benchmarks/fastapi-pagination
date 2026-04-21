import pytest

from fastapi_pagination.default import Page, Params
from fastapi_pagination.paginator import paginate
from fastapi_pagination.utils import disable_installed_extensions_check


@pytest.fixture(autouse=True)
def disable_ext_check():
    disable_installed_extensions_check()


def test_paginate_basic_sequence():
    params = Params(page=1, size=10)
    items = list(range(20))
    result = paginate(items, params, safe=True)
    assert isinstance(result, Page)
    assert result.items == list(range(10))
    assert result.total == 20
    assert result.page == 1
    assert result.size == 10


def test_paginate_default_length_function():
    params = Params(page=1, size=5)
    items = [1, 2, 3, 4, 5, 6]
    result = paginate(items, params, safe=True)
    assert result.total == 6
    assert result.items == [1, 2, 3, 4, 5]


def test_paginate_custom_length_function():
    params = Params(page=1, size=3)
    items = [10, 20, 30, 40, 50]
    result = paginate(items, params, length_function=lambda s: 100, safe=True)
    assert result.total == 100
    assert result.items == [10, 20, 30]


def test_paginate_safe_false_calls_check(mocker):
    mock_check = mocker.patch("fastapi_pagination.paginator.check_installed_extensions")
    params = Params(page=1, size=5)
    paginate([1, 2, 3], params, safe=False)
    mock_check.assert_called_once()


def test_paginate_safe_true_skips_check(mocker):
    mock_check = mocker.patch("fastapi_pagination.paginator.check_installed_extensions")
    params = Params(page=1, size=5)
    paginate([1, 2, 3], params, safe=True)
    mock_check.assert_not_called()


def test_paginate_empty_sequence():
    params = Params(page=1, size=10)
    result = paginate([], params, safe=True)
    assert result.items == []
    assert result.total == 0


def test_paginate_second_page():
    params = Params(page=2, size=3)
    items = list(range(10))
    result = paginate(items, params, safe=True)
    assert result.items == [3, 4, 5]
    assert result.page == 2
